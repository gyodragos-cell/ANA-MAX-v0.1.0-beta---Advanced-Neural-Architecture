import json
import re
import unicodedata
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

def _normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text.lower())
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


# Romanian diacritics -> plain ASCII (both comma-below and legacy cedilla forms).

_DIACRITIC_MAP = {
    "\u0103": "a", "\u00e2": "a", "\u00ee": "i", "\u0219": "s", "\u021b": "t",
    "\u015f": "s", "\u0163": "t",
    "\u0102": "A", "\u00c2": "A", "\u00ce": "I", "\u0218": "S", "\u021a": "T",
    "\u015e": "S", "\u0162": "T",
}



def _ascii_fold(text: str) -> str:
    """Fold diacritics to plain ASCII (case-preserving) and drop any remaining
    non-ASCII (e.g. emoji). Applied only to the final user-facing answer so ANA
    output never crashes the Windows console or the dashboard SSE stream."""
    if not text:
        return text
    for src, dst in _DIACRITIC_MAP.items():
        text = text.replace(src, dst)
    decomposed = unicodedata.normalize("NFKD", text)
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return stripped.encode("ascii", "ignore").decode("ascii")



def _clean_json_args(args_raw: str) -> dict:
    """Cleans markdown blocks, trailing commas, comments, and unclosed blocks from JSON string."""
    clean_args = args_raw.strip()
    
    # 1. Extrage doar blocul dintre { si } daca exista text inainte sau dupa
    start_idx = clean_args.find("{")
    end_idx = clean_args.rfind("}")
    if start_idx != -1 and end_idx != -1 and end_idx >= start_idx:
        clean_args = clean_args[start_idx:end_idx+1]
    
    # 2. Sterge comentariile JS-style // comentariu adaugate uneori de modele
    clean_args = re.sub(r'//.*', '', clean_args)
    
    # 3. Fix trailing commas
    clean_args = re.sub(r',\s*\}', '}', clean_args)
    clean_args = re.sub(r',\s*\]', ']', clean_args)
    
    # 4. [ANA OS AUTO-CORRECTOR]: Fix missing closing braces and brackets
    open_braces = clean_args.count('{')
    close_braces = clean_args.count('}')
    if open_braces > close_braces:
        clean_args += '}' * (open_braces - close_braces)
        
    open_brackets = clean_args.count('[')
    close_brackets = clean_args.count(']')
    if open_brackets > close_brackets:
        clean_args += ']' * (open_brackets - close_brackets)
        
    # 5. Fix common unescaped newlines inside strings (dar pastram newlines structurale goale pentru regex)
    # E periculos sa facem replace global pe \n pentru ca stricam spatiile daca e pprint.
    # O facem doar daca crapa.
    
    try:
        return json.loads(clean_args)
    except json.JSONDecodeError:
        # Daca a picat, incercam unescapping agresiv
        clean_args_aggressive = clean_args.replace('\n', '\\n').replace('\r', '')
        try:
            return json.loads(clean_args_aggressive)
        except json.JSONDecodeError:
            # One last brute-force attempt for raw strings that LLM forgot to wrap in {"command": "..."}
            if " " in clean_args and not clean_args.startswith("{"):
                return {"command": clean_args}
            raise


def _parse_action_blocks(text: str) -> list[dict]:
    """
    Parseaza blocuri ACTION:/ARGS: din raspunsul text al lui Mistral.

    Formate acceptate:
      ACTION: tool_name
      ARGS: {"key": "value"}

      sau pe o singura linie:
      ACTION: tool_name | ARGS: {"key": "value"}
    """
    actions = []

    # Strip outer codeblocks if Qwen wraps everything in ```plaintext ... ```
    clean_text = text
    codeblock_match = re.search(r"^```(?:plaintext|json|yaml)?\s*\n(.*?)\n```$", text, re.IGNORECASE | re.DOTALL | re.MULTILINE)
    if codeblock_match:
        clean_text = codeblock_match.group(1)

    # Auto-Heal: Daca LLM raspunde cu un JSON structurat direct {"action": "...", "args": {...}}
    try:
        candidate = clean_text.strip()
        start_idx = candidate.find("{")
        end_idx = candidate.rfind("}")
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            json_candidate = candidate[start_idx:end_idx+1]
            parsed = json.loads(json_candidate)
            if isinstance(parsed, dict) and ("action" in parsed or "ACTION" in parsed) and ("args" in parsed or "ARGS" in parsed):
                tool_name = parsed.get("action") or parsed.get("ACTION")
                tool_args = parsed.get("args") or parsed.get("ARGS")
                actions.append({
                    "tool": str(tool_name).strip(),
                    "args": tool_args if isinstance(tool_args, dict) else {},
                    "parse_error": None,
                    "args_raw": json.dumps(tool_args)
                })
                return actions
    except Exception:
        pass

    # Format multi-linie
    pattern = re.compile(
        r"ACTION\s*:\s*(\w+)\s*\n\s*ARGS\s*:\s*(.*?)(?=\n\s*ACTION:|\Z)",
        re.IGNORECASE | re.DOTALL,
    )
    for m in pattern.finditer(clean_text):
        tool_name = m.group(1).strip()
        args_raw = m.group(2).strip()
        parse_error = None
        try:
            args = _clean_json_args(args_raw)
        except Exception as exc:
            args = {}
            parse_error = str(exc)
        actions.append({"tool": tool_name, "args": args, "parse_error": parse_error, "args_raw": args_raw})

    # Format single-line fallback
    if not actions:
        pattern2 = re.compile(
            r"ACTION\s*:\s*(\w+)\s*\|?\s*ARGS\s*:\s*(\{[^\n]*\})",
            re.IGNORECASE,
        )
        for m in pattern2.finditer(clean_text):
            tool_name = m.group(1).strip()
            args_raw = m.group(2).strip()
            parse_error = None
            try:
                args = _clean_json_args(args_raw)
            except Exception as exc:
                args = {}
                parse_error = str(exc)
            actions.append({"tool": tool_name, "args": args, "parse_error": parse_error, "args_raw": args_raw})

    # Auto-Heal RAG: Daca LLM-ul halucineaza un bloc de cod simplu in loc de actiune formala
    # IMPORTANT: ignoram blocuri care sunt OUTPUT text (ex: tabele PowerShell, [ERROR] logs, mesaje)
    # si executam doar comenzi reale PS/CMD/bash
    _OUTPUT_INDICATORS = (
        "Directory:", "Mode ", "LastWriteTime", "[ERROR]", "[INFO]", "[WARN]",
        "Name", "----", "d----", "d-r--", "------",  # PS table headers/rows
        "Traceback", "Exception", "Error at line",
    )
    if not actions:
        code_pattern = re.compile(r"```(?:cmd|bash|powershell|ps1)?\n(.*?)\n```", re.IGNORECASE | re.DOTALL)
        for m in code_pattern.finditer(text):
            cmd = m.group(1).strip()
            if not cmd or cmd.startswith("{") or "RAW_CONTENT_START" in cmd:
                continue
            if cmd.startswith("ACTION:"):
                continue  # Handled by the earlier regexes
            # Exclude output text blocks (not executable commands)
            first_line = cmd.split("\n")[0].strip()
            if any(first_line.startswith(ind) or first_line == ind.strip() for ind in _OUTPUT_INDICATORS):
                continue
            if any(ind in cmd[:200] for ind in _OUTPUT_INDICATORS):
                continue
            escaped_cmd = cmd.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
            actions.append({
                "tool": "terminal",
                "args": {"operation": "run", "command": cmd},
                "parse_error": None,
                "args_raw": '{"operation": "run", "command": "' + escaped_cmd + '"}'
            })

    # -------------------------------------------------------------------------
    # Auto-Heal: Qwen halucineaza cmdlet-uri PowerShell ca ACTION (ex: Remove-Item, Copy-Item)
    # Le redirectam automat la tool-ul 'terminal' cu ARGS corecti.
    # -------------------------------------------------------------------------
    _PS_CMDLETS = {
        "Remove-Item", "Remove-ItemForce", "del", "erase", "rm",
        "Copy-Item", "Move-Item", "Rename-Item", "New-Item",
        "Get-Content", "Set-Content", "Out-File", "Add-Content",
        "Start-Process", "Stop-Process", "Get-Process",
        "Invoke-WebRequest", "Invoke-RestMethod",
        "Get-ChildItem", "dir", "ls", "mkdir", "rmdir",
        "Set-Location", "Get-Location", "Write-Output", "Write-Host",
        "Clear-Host", "cls",
    }
    healed = []
    for action in actions:
        tname = action["tool"]
        # Detectam PS cmdlets: in lista hardcodata SAU match CamelCase cu cratima (ex: Remove-Item)
        is_ps_cmdlet = tname in _PS_CMDLETS or bool(re.match(r"^[A-Z][a-zA-Z]+-[A-Z][a-zA-Z]+$", tname))
        if is_ps_cmdlet:
            args_raw = action.get("args_raw", "").strip()
            # ARGS in format PS-style (nu JSON): ex: -Path "..." -Force
            if not args_raw.startswith("{"):
                ps_cmd = f"{tname} {args_raw}"
            else:
                try:
                    parsed = json.loads(args_raw)
                    path_val = parsed.get("Path") or parsed.get("path") or parsed.get("LiteralPath") or ""
                    force_flag = "-Force" if parsed.get("Force") or parsed.get("force") else ""
                    ps_cmd = f'{tname} -Path "{path_val}" {force_flag}'.strip()
                except Exception:
                    ps_cmd = f"{tname} {args_raw}"
            logger.info("[AUTO-HEAL] Converted PS cmdlet '%s' to terminal: %s", tname, ps_cmd)
            healed.append({
                "tool": "terminal",
                "args": {"operation": "run", "command": ps_cmd},
                "parse_error": None,
                "args_raw": json.dumps({"operation": "run", "command": ps_cmd}),
            })
        else:
            healed.append(action)
    actions = healed

    # Cauta bloc RAW_CONTENT_START ... RAW_CONTENT_END
    raw_pattern = re.compile(r"RAW_CONTENT_START\s*\n(.*?)\nRAW_CONTENT_END", re.IGNORECASE | re.DOTALL)
    raw_match = raw_pattern.search(text)

    if actions and raw_match:
        raw_content = raw_match.group(1)
        last_action = actions[-1]
        if last_action.get("parse_error"):
            path_match = re.search(r'"path"\s*:\s*"([^"]+)"', last_action["args_raw"])
            if path_match:
                last_action["args"]["path"] = path_match.group(1)
                last_action["parse_error"] = None
        last_action["args"]["content"] = raw_content

    return actions



def _compress_history(messages: list[dict], max_chars: int = 5000) -> list[dict]:
    """Comprima rezultatele vechi din istoric daca lungimea totala depaseste max_chars."""
    total_len = sum(len(m.get("content", "")) for m in messages)
    if total_len <= max_chars:
        return messages

    copied = [dict(m) for m in messages]
    # Comprimam doar mesajele mai vechi, lasand ultimele 3 mesaje neatinse (pentru a pastra contextul imediat)
    for i in range(2, len(copied) - 3):
        msg = copied[i]
        content = msg.get("content", "")
        if msg.get("role") == "user" and "Rezultatele actiunilor tale:" in content:
            if "[trunchiat pentru economisirea contextului]" in content:
                continue
            if len(content) > 600:
                # Trunchiem rezultatele lungi, pastrand inceputul si sfarsitul
                msg["content"] = content[:400] + "\n... [trunchiat pentru economisirea contextului] ...\n" + content[-200:]
                logger.info("Compressed old tool results message at index %d", i)
        elif msg.get("role") == "assistant" and len(content) > 1000:
            if "ACTION:" in content:
                action_idx = content.find("ACTION:")
                if action_idx != -1:
                    thought_part = content[:action_idx]
                    action_part = content[action_idx:]
                    if len(thought_part) > 300:
                        thought_part = thought_part[:150] + "\n... [gandire trunchiata] ...\n" + thought_part[-100:]
                    msg["content"] = thought_part + action_part
                    logger.info("Compressed old thought block at index %d", i)
            else:
                msg["content"] = content[:500] + "\n... [trunchiat assistant message] ...\n"
                logger.info("Compressed old assistant message at index %d", i)
    return copied


def extract_plan_or_thought(text: str) -> Optional[str]:
    """
    Extrage blocul de deliberare (Hermes Scratchpad / DeepSeek CoT) din raspunsul LLM.
    Recunoaste tag-uri <thought>, <plan> sau prefixe PLAN: / THOUGHT:.
    """
    if not text:
        return None

    # 1. Tag-uri <thought>...</thought> sau <plan>...</plan>
    tag_match = re.search(r"<(?:thought|plan)>(.*?)</(?:thought|plan)>", text, re.IGNORECASE | re.DOTALL)
    if tag_match:
        return tag_match.group(1).strip()

    # 2. Format marcat PLAN: ... sau THOUGHT: ... pana la primul ACTION: sau final
    plan_match = re.search(r"(?:PLAN|THOUGHT|RATIONAMENT)\s*:\s*(.*?)(?=\n\s*ACTION:|\Z)", text, re.IGNORECASE | re.DOTALL)
    if plan_match:
        return plan_match.group(1).strip()

    return None
