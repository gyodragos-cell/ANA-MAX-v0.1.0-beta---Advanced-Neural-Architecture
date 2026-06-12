from __future__ import annotations

import json
import logging
import os
import re
import time
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from core.config import config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constante
# ---------------------------------------------------------------------------

_EXCLUDED_FROM_AI = {
    "live_desktop_viewer",
    "desktop_control",
    "desktop_control_tool",
    "windows_insight",
    "windows_insight_tool",
    "windows_deep_sight",
}

_MAX_TOOL_LOOPS = 8
_WARM = False
_TIMEOUT_COLD = 200
_OLLAMA_NUM_CTX = 2048
_OLLAMA_CHAT_TOKENS = 160
_OLLAMA_TOOL_TOKENS = 384
_ROMANIA_PRESIDENT = "Nicusor Dan"
_ROMANIA_PRESIDENT_VERIFIED = "2026-06-06"
_RO_WEEKDAYS = {
    0: "luni",
    1: "marti",
    2: "miercuri",
    3: "joi",
    4: "vineri",
    5: "sambata",
    6: "duminica",
}
_TIMEOUT_WARM = 90   # redus - cu text injection e mult mai rapid

_ANA_ROOT = Path(__file__).resolve().parents[2]
_LAST_CREATIVE_PATH = _ANA_ROOT / "memory" / "last_creative_response.json"


def _get_ollama_host(agent: Any) -> str:
    url = getattr(agent, "_ollama_url", "http://localhost:11434/api/generate")
    if "/api/" in url:
        return url.split("/api/", 1)[0]
    return url


def _get_ollama_model(agent: Any) -> str:
    return getattr(agent, "_ollama_model", config.get("ai.ollama.model", "qwen2.5:7b"))


def init(agent: Any) -> None:
    logger.info("ollama_backend.init() called (no-op)")


# ---------------------------------------------------------------------------
# Tool registry access
# ---------------------------------------------------------------------------

def _get_tool_registry():
    """Returneaza registrul de tools ANA (singleton lazy)."""
    try:
        from tools.base import ToolRegistry
        return ToolRegistry()
    except Exception as exc:
        logger.warning("Nu am putut incarca ToolRegistry: %s", exc)
        return None


def _clean_args(arguments: dict) -> dict:
    """
    Mistral trimite uneori valori cu ghilimele suplimentare: "'run'" in loc de "run".
    Stripuim ghilimelele simple/duble de la inceputul si sfarsitul valorilor string.
    Ex: "'run'" -> "run", '"terminal"' -> "terminal"
    """
    cleaned = {}
    for k, v in arguments.items():
        if isinstance(v, str):
            s = v.strip()
            # Strip perechi de ghilimele: 'val' sau "val"
            if (s.startswith("'") and s.endswith("'")) or \
               (s.startswith('"') and s.endswith('"')):
                s = s[1:-1].strip()
            cleaned[k] = s
        else:
            cleaned[k] = v
    return cleaned


def _is_read_only_request(message: str) -> bool:
    text = message.lower()
    read_only_markers = (
        "read-only",
        "read only",
        "doar citire",
        "nu modifica",
        "nu scrie",
        "nu sterge",
        "nu rula comenzi mutante",
        "analizeaza",
        "inspecteaza",
        "fara sa faca nimic",
        "fara modificari",
    )
    return any(marker in text for marker in read_only_markers)


def _is_single_action_request(message: str) -> bool:
    text = message.lower()
    single_action_markers = (
        "deschide",
        "porneste",
        "porneste",
        "open ",
        "start ",
        "lanseaza",
        "lanseaza",
    )
    analysis_markers = (
        "analizeaza",
        "inspecteaza",
        "testeaza",
        "si apoi",
        "si sa",
        "scrie",
        "scri",
        "tasteaza",
        "type",
        "dupa aceea",
        "apoi",
    )
    return any(marker in text for marker in single_action_markers) and not any(
        marker in text for marker in analysis_markers
    )


def _is_mutating_action(name: str, arguments: dict) -> bool:
    tool_name = name.strip().lower()
    args = _clean_args(arguments)
    operation = str(args.get("operation") or args.get("action") or "").strip().lower()
    command = str(args.get("command") or "").strip().lower()

    mutating_tools = {
        "edit",
        "file_patch",
        "uia_click",
        "uia_type",
        "desktop_control",
        "remote_control",
        "terminal",
        "bash_exec",
    }
    mutating_file_ops = {
        "write",
        "delete",
        "remove",
        "edit",
        "surgical_edit",
        "move",
        "copy",
        "mkdir",
        "create",
    }
    mutating_commands = (
        "remove-item",
        "del ",
        "erase ",
        "rd ",
        "rmdir ",
        "new-item",
        "set-content",
        "add-content",
        "out-file",
        "move-item",
        "copy-item",
        "rename-item",
        "start-process",
    )

    if tool_name == "file_operations":
        return operation in mutating_file_ops
    if tool_name in mutating_tools:
        if tool_name in {"terminal", "bash_exec"}:
            return any(command.startswith(cmd) or cmd in command for cmd in mutating_commands)
        return True
    return False


def _remap_local_app_open(name: str, arguments: dict) -> tuple[str, dict]:
    tool_name = name.strip().lower()
    args = _clean_args(arguments)
    operation = str(args.get("operation") or args.get("action") or "").strip().lower()
    target = str(args.get("url") or args.get("target") or args.get("path") or "").strip().lower()

    if tool_name != "browser_control" or operation != "open":
        return name, arguments

    app_commands = {
        "calc": "calc",
        "calculator": "calc",
        "notepad": "notepad",
        "note pad": "notepad",
        "cmd": "cmd",
        "powershell": "Start-Process powershell",
        "power shell": "Start-Process powershell",
        "power shel": "Start-Process powershell",
        "brave": "Start-Process 'C:\\Program Files\\BraveSoftware\\Brave-Browser\\Application\\brave.exe'",
        "brave browser": "Start-Process 'C:\\Program Files\\BraveSoftware\\Brave-Browser\\Application\\brave.exe'",
    }
    command = app_commands.get(target)
    if not command:
        return name, arguments

    logger.info("Remap browser_control open %s -> terminal run %s", target, command)
    return "terminal", {"operation": "run", "command": command}


def _normalize_terminal_gui_command(name: str, arguments: dict) -> dict:
    if name.strip().lower() not in {"terminal", "bash_exec"}:
        return arguments

    command = str(arguments.get("command") or "").strip().strip("'\"")
    gui_commands = {
        "notepad": "Start-Process notepad",
        "note pad": "Start-Process notepad",
        "calc": "Start-Process calc",
        "calculator": "Start-Process calc",
        "brave": "Start-Process 'C:\\Program Files\\BraveSoftware\\Brave-Browser\\Application\\brave.exe'",
        "brave browser": "Start-Process 'C:\\Program Files\\BraveSoftware\\Brave-Browser\\Application\\brave.exe'",
    }
    normalized = gui_commands.get(command.lower())
    if not normalized:
        return arguments

    updated = dict(arguments)
    updated["command"] = normalized
    updated.setdefault("timeout", 10)
    logger.info("Normalize GUI terminal command %s -> %s", command, normalized)
    return updated


def _execute_tool(name: str, arguments: dict, read_only: bool = False, task_message: str = "") -> str:
    """Executa un tool ANA si returneaza rezultatul ca string."""
    try:
        reg = _get_tool_registry()
        if reg is None:
            return "EROARE: ToolRegistry indisponibil"
        arguments = _clean_args(arguments)
        name, arguments = _remap_local_app_open(name, arguments)
        arguments = _normalize_terminal_gui_command(name, arguments)
        task_text = _normalize_text(task_message)
        command_text = str(arguments.get("command") or "").strip().lower()
        operation = str(arguments.get("operation") or arguments.get("action") or "").strip().lower()
        notepad_task = "notepad" in task_text or "note pad" in task_text
        calc_task = "calc" in task_text or "calculator" in task_text
        close_requested = any(word in task_text for word in ("inchide", "inchide", "opreste", "opreste", "kill", "termina"))
        file_requested = any(word in task_text for word in ("fisier", "fisier", "file", ".txt", "salveaza", "salveaza"))
        if name.strip().lower() == "terminal" and "start-process notepad" in command_text and not notepad_task:
            return "BLOCAT: taskul nu cere deschiderea Notepad."
        if name.strip().lower() == "terminal" and "start-process calc" in command_text and not calc_task:
            return "BLOCAT: taskul nu cere deschiderea Calculator."
        if name.strip().lower() == "terminal" and "taskkill" in command_text and not close_requested:
            return "BLOCAT: taskul nu cere inchiderea/omorarea proceselor."
        if notepad_task and not file_requested:
            if name.strip().lower() == "file_operations" and operation in {"write", "create"}:
                return "BLOCAT: taskul cere scriere in Notepad, nu creare de fisier alternativ."
            if name.strip().lower() == "terminal" and any(token in command_text for token in (">", "out-file", "set-content")):
                return "BLOCAT: taskul cere scriere in Notepad, nu creare de fisier alternativ."
        if read_only and _is_mutating_action(name, arguments):
            logger.warning("READ_ONLY BLOCK tool=%s args=%s", name, arguments)
            return f"BLOCAT read-only: toolul {name} ar modifica sistemul."
        # Eliminam cheia 'name' din args daca exista - ToolRegistry.execute(name, **kwargs)
        # are 'name' ca prim argument pozitional si ar primi valori duble.
        if name.strip().lower() in {"uia_type", "uia_click"} and os.environ.get("ANA_AUTO_CONFIRM") == "1":
            arguments.setdefault("confirm", True)
        safe_args = {k: v for k, v in arguments.items() if k != "name"}
        logger.debug("_execute_tool %s args_clean=%s", name, safe_args)
        result = reg.execute(name, **safe_args)
        if result.is_success:
            if name.strip().lower() == "terminal" and "start-process" in str(safe_args.get("command", "")).lower():
                time.sleep(1.0)
            data = result.data
            if isinstance(data, dict):
                return json.dumps(data, ensure_ascii=False, default=str)[:3000]
            return str(data)[:3000] if data else result.message or "OK"
        return f"EROARE tool {name}: {result.error or result.message}"
    except Exception as exc:
        return f"EXCEPTIE tool {name}: {exc}"


# ---------------------------------------------------------------------------
# Text Injection Mode
# ---------------------------------------------------------------------------
#
# In loc sa trimitem 86 JSON schemas la Mistral (care se ineaca),
# descriem tools ca text simplu in system prompt si ii spunem lui Mistral
# sa raspunda cu blocuri ACTION: pe care ANA le parseaza si executa.
#
# Format raspuns Mistral:
#   ACTION: terminal
#   ARGS: {"operation": "run", "command": "mkdir C:\\Users\\billy\\Desktop\\busola"}
#
# ANA parseaza ACTION+ARGS, executa tool-ul, injecteaza rezultatul si continua.
# ---------------------------------------------------------------------------

# Descriere compacta a tools disponibile - injected as text in system prompt
_TOOL_DESCRIPTIONS = {
    "terminal": (
        'terminal: executa comenzi PowerShell/CMD pe Windows.\n'
        '  ARGS: {"operation": "run", "command": "<powershell command>", "timeout": 30}'
    ),
    "file_operations": (
        'file_operations: citeste, scrie, listeaza fisiere si directoare.\n'
        '  ARGS: {"operation": "write"|"read"|"list"|"search"|"edit"|"find", '
        '"path": "<cale absoluta>", "content": "<text, doar pentru write>"}'
    ),
    "code_tools": (
        'code_tools: analizeaza sau ruleaza cod Python, creaza proiect.\n'
        '  ARGS: {"operation": "analyze"|"run"|"create_project", '
        '"target": "<cale fisier sau descriere proiect>", "name": "<nume proiect, doar pentru create_project>"}'
    ),
    "web_search": (
        'web_search: cauta pe internet.\n'
        '  ARGS: {"operation": "search", "query": "<termeni cautare>"}'
    ),
    "smart_search": (
        'smart_search: cauta in codebase sau fisiere locale.\n'
        '  ARGS: {"action": "search", "query": "<ce cauti>", "path": "<optional>"}'
    ),
    "system_control": (
        'system_control: informatii sistem, procese, resurse.\n'
        '  ARGS: {"operation": "vitals"|"processes"|"kill_process", "target": "<optional>"}'
    ),
    "ana_memory": (
        'ana_memory: salveaza sau recupereaza informatii din memoria ANA.\n'
        '  ARGS: {"operation": "save"|"get"|"list", "key": "<topic>", "value": "<continut>"}'
    ),
    "browser_control": (
        'browser_control: deschide URL-uri sau interactioneaza cu browserul.\n'
        '  ARGS: {"operation": "open"|"screenshot", "url": "<url>"}'
    ),
    "uia_type": (
        'uia_type: scrie text intr-o aplicatie/fereastra Windows prin UI Automation.\n'
        '  ARGS: {"window_title": "<titlu partial, ex: Notepad>", "control_type": "Edit", '
        '"text": "<text de scris>"}'
    ),
    "window_manager": (
        'window_manager: listeaza sau focalizeaza ferestre Windows.\n'
        '  ARGS: {"action": "list"|"focus", "title": "<titlu partial>"}'
    ),
    "desktop_capture": (
        'desktop_capture: captura ecran sau ferestre.\n'
        '  ARGS: {"operation": "capture"|"capture_region"|"capture_window"|"get_windows"|"monitor", '
        '"window_title": "<optional>", "region": "<x,y,w,h optional>"}'
    ),
    "error_radar": (
        'error_radar: detecteaza si explica erori din logs sau cod.\n'
        '  ARGS: {"operation": "scan"|"explain", "text": "<error text>"}'
    ),
    "agent_coach": (
        'agent_coach: recomanda actiuni sau tools pentru un task.\n'
        '  ARGS: {"action": "recommend", "task": "<descriere task>"}'
    ),
    "tool_router": (
        'tool_router: recomanda un stack mic de tooluri pentru task.\n'
        '  ARGS: {"task": "<descriere task>", "mode": "auto", "max_tools": 8}'
    ),
    "foreground_ui_snapshot": (
        'foreground_ui_snapshot: observa fereastra activa si controalele vizibile inainte de actiuni UI.\n'
        '  ARGS: {"action": "snapshot"}'
    ),
    "windows_uia_bridge": (
        'windows_uia_bridge: inspecteaza ferestre UIA, listeaza controale, click si type prin UI Automation.\n'
        '  ARGS: {"action": "list_windows"|"inspect_window"|"type_text", "window_title": "<titlu>", '
        '"control_type": "Edit", "text": "<text>"}'
    ),
    "workspace_situational_awareness": (
        'workspace_situational_awareness: observa aplicatia activa, fereastra, UIA, log errors si fisiere deschise.\n'
        '  ARGS: {"include_uia": true, "include_errors": true}'
    ),
    "ocr_tool": (
        'ocr_tool: citeste textul/cuvintele de pe ecran sau dintr-un fisier (OCR).\n'
        '  ARGS: {"action": "screen"|"check"|"file"|"clipboard"|"region", "image_path": "<optional for file>"}'
    ),
    "edge_tts_voice": (
        'edge_tts_voice: voce/TTS pentru ANA, poate activa/dezactiva si rosti text local.\n'
        '  ARGS: {"operation": "enable"|"disable"|"speak"|"list_voices", "text": "<text pentru speak>"}'
    ),
}

# Mapeaza keywords din mesaj -> tool names relevante
_KEYWORD_TO_TOOLS: list[tuple[set[str], list[str]]] = [
    (
        {"fisier", "folder", "director", "directory", "script", "py", "python",
         "cod", "code", "creeaza", "creaza", "fa", "mkdir", "scrie",
         "salveaza", "save", "write", "read", "create", "file", "busola",
         "compass", "program", "aplicatie"},
        ["terminal", "file_operations", "code_tools"],
    ),
    (
        {"terminal", "comanda", "command", "run", "ruleaza", "executa",
         "powershell", "cmd", "bash", "shell", "sistem", "process",
         "notepad", "note pad", "calculator", "calc"},
        ["terminal", "system_control"],
    ),
    (
        {"cauta", "search", "google", "web", "internet", "site", "url"},
        ["web_search", "smart_search"],
    ),
    (
        {"memorie", "memory", "remember", "aminteste", "invata", "retine"},
        ["ana_memory"],
    ),
    (
        {"eroare", "error", "bug", "fix", "diagnoza", "healthcheck", "problema"},
        ["error_radar", "agent_coach"],
    ),
    (
        {"browser", "site", "url", "deschide", "open"},
        ["browser_control"],
    ),
    (
        {"desktop", "ecran", "screen", "screenshot", "fereastra", "window", "poza", "ocr",
         "citeste", "scrie", "scri", "tasteaza", "type", "notepad", "note pad"},
        ["desktop_capture", "ocr_tool", "window_manager", "uia_type"],
    ),
    (
        {"voce", "vocal", "tts", "audio", "auzi", "aud", "spune", "vorbeste", "speak"},
        ["edge_tts_voice"],
    ),
]

_ALWAYS_TOOLS = ["terminal", "file_operations"]  # mereu disponibile


def _select_tool_names(message: str) -> list[str]:
    """Selecteaza tool names relevante pe baza keywords din mesaj."""
    lowered = message.lower()
    words = set(lowered.split())

    selected: list[str] = list(_ALWAYS_TOOLS)
    for keywords, tool_names in _KEYWORD_TO_TOOLS:
        # Word match: keyword exista ca cuvant separat in mesaj
        # Substr match: doar pentru keywords >= 4 chars (evita 'fa' in 'faci')
        matched = bool(keywords & words)
        if not matched:
            matched = any(
                kw in lowered and len(kw) >= 4
                for kw in keywords
            )
        if matched:
            for t in tool_names:
                if t not in selected:
                    selected.append(t)

    # Cap la 8 tools max
    return selected[:8]


def _router_mode_hint(message: str) -> str:
    text = _normalize_text(message)
    if any(token in text for token in (
        "notepad", "note pad", "fereastra", "ecran", "desktop", "click",
        "scrie", "scri", "tasteaza", "type", "ocr", "screenshot",
    )):
        return "ui_desktop"
    if any(token in text for token in ("proces", "procese", "frida", "watchdog", "runtime", "sub capota")):
        return "runtime_deep"
    if any(token in text for token in ("fisier", "file", "cod", "code", "patch", "test")):
        return "code_change"
    return "auto"


def _route_tool_names(message: str) -> list[str]:
    """Cere tool_router stack-ul compact; fallback-ul ramane _select_tool_names."""
    try:
        reg = _get_tool_registry()
        if reg is None:
            return []
        mode = _router_mode_hint(message)
        result = reg.execute("tool_router", task=message, mode=mode, max_tools=8)
        if not result.is_success or not isinstance(result.data, dict):
            logger.warning("tool_router unavailable or failed: %s", result.error or result.message)
            return []
        recommended = [
            str(name).strip()
            for name in result.data.get("recommended_tools", [])
            if str(name).strip()
        ]
        available = set(getattr(reg, "_tools", {}).keys())
        filtered = [name for name in recommended if name in available]
        if any(token in _normalize_text(message) for token in ("notepad", "note pad", "calc", "calculator")):
            filtered.insert(0, "terminal")
        if "workspace_situational_awareness" in available and "workspace_situational_awareness" not in filtered:
            filtered.insert(0, "workspace_situational_awareness")
        if _router_mode_hint(message) == "ui_desktop" and "foreground_ui_snapshot" in available:
            filtered.insert(1, "foreground_ui_snapshot")
        if "file_operations" not in filtered:
            filtered.append("file_operations")
        if "terminal" not in filtered and not _is_read_only_request(message):
            filtered.insert(0, "terminal")
        compact = []
        for name in filtered:
            if name not in compact:
                compact.append(name)
        logger.info(
            "tool_router recommendation: mode=%s recommended=%s selected=%s",
            result.data.get("mode", mode),
            recommended,
            compact[:8],
        )
        return compact[:8]
    except Exception as exc:
        logger.warning("tool_router preflight failed: %s", exc)
        return []


def _safe_compact_json(value: Any, limit: int = 1600) -> str:
    text = json.dumps(value, ensure_ascii=False, default=str)
    return text[:limit] + ("..." if len(text) > limit else "")


def _desktop_listing(limit: int = 80) -> dict:
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    try:
        entries = []
        for name in sorted(os.listdir(desktop), key=str.lower)[:limit]:
            path = os.path.join(desktop, name)
            entries.append({
                "name": name,
                "type": "dir" if os.path.isdir(path) else "file",
            })
        return {"path": desktop, "count_shown": len(entries), "entries": entries}
    except Exception as exc:
        return {"path": desktop, "error": str(exc)}


def _drive_listing(limit_per_drive: int = 40) -> dict:
    drives: dict[str, Any] = {}
    if os.name == "nt":
        candidates = [f"{letter}:\\" for letter in "CDEFGHIJKLMNOPQRSTUVWXYZ"]
    else:
        candidates = ["/"]
    for drive in candidates:
        if not os.path.exists(drive):
            continue
        try:
            entries = []
            for name in sorted(os.listdir(drive), key=str.lower)[:limit_per_drive]:
                path = os.path.join(drive, name)
                entries.append({
                    "name": name,
                    "type": "dir" if os.path.isdir(path) else "file",
                })
            drives[drive] = {"count_shown": len(entries), "entries": entries}
        except Exception as exc:
            drives[drive] = {"error": str(exc)}
    return drives


def _build_preflight_context(message: str, tool_names: list[str]) -> str:
    """Observatie read-only inainte de Qwen, ca agentul local sa nu lucreze orbeste."""
    if _looks_like_simple_chat(message):
        return ""
    context: dict[str, Any] = {
        "desktop": _desktop_listing(),
        "drives": _drive_listing(),
    }
    try:
        reg = _get_tool_registry()
        available = set(getattr(reg, "_tools", {}).keys()) if reg is not None else set()
        if reg is not None and "workspace_situational_awareness" in available:
            result = reg.execute(
                "workspace_situational_awareness",
                include_uia=True,
                include_errors=True,
            )
            if result.is_success:
                context["workspace_situational_awareness"] = result.data
            else:
                context["workspace_situational_awareness_error"] = result.error or result.message
        if reg is not None and "system_control" in available:
            result = reg.execute("system_control", operation="processes")
            if result.is_success:
                context["processes_under_hood"] = str(result.data)[:1200]
            else:
                context["processes_under_hood_error"] = result.error or result.message
            vitals = reg.execute("system_control", operation="vitals")
            if vitals.is_success:
                context["system_vitals"] = str(vitals.data)[:600]
        if reg is not None and "foreground_ui_snapshot" in available and (
            "foreground_ui_snapshot" in tool_names and any(
                token in _normalize_text(message)
                for token in ("click", "scrie", "scri", "tasteaza", "type", "fereastra", "notepad", "note pad")
            )
        ):
            result = reg.execute("foreground_ui_snapshot", include_text=True, max_elements="15")
            if result.is_success:
                context["foreground_ui_snapshot"] = result.data
            else:
                context["foreground_ui_snapshot_error"] = result.error or result.message
    except Exception as exc:
        context["preflight_error"] = str(exc)
    return _safe_compact_json(context, limit=2600)


def _maybe_answer_observation_query(message: str) -> str | None:
    text = _normalize_text(message)
    asks_processes = any(token in text for token in ("proces", "procese", "pid", "task manager", "taskmanager"))
    asks_drives = any(token in text for token in ("partitie", "partitii", "drive", "c:", "d:"))
    if not asks_processes and not asks_drives:
        return None

    parts: list[str] = []
    if asks_processes:
        try:
            reg = _get_tool_registry()
            if reg is not None:
                result = reg.execute("system_control", operation="processes")
                if result.is_success:
                    lines = str(result.data).splitlines()[:8]
                    parts.append("Procese/PID sub capota (top):\n" + "\n".join(lines))
                else:
                    parts.append(f"Procese/PID: eroare {result.error or result.message}")
        except Exception as exc:
            parts.append(f"Procese/PID: eroare {exc}")

    if asks_drives:
        drives = _drive_listing(limit_per_drive=12)
        drive_lines = []
        for drive, info in drives.items():
            if "entries" in info:
                names = ", ".join(entry["name"] for entry in info["entries"][:8])
                drive_lines.append(f"{drive} {names}")
            else:
                drive_lines.append(f"{drive} eroare: {info.get('error')}")
        parts.append("Partitii/drives vazute read-only:\n" + "\n".join(drive_lines))

    return "\n\n".join(parts) if parts else None


def _looks_like_creative_text_request(message: str) -> bool:
    text = _normalize_text(message)
    return any(token in text for token in ("poezie", "poem", "poveste", "cantec", "text creativ", "recita"))


def _save_last_creative_response(message: str, content: str) -> None:
    if not content or not _looks_like_creative_text_request(message):
        return
    if "recita" in _normalize_text(message) or "reciteste" in _normalize_text(message) or "reciti" in _normalize_text(message):
        return
    try:
        _LAST_CREATIVE_PATH.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "saved_at": datetime.now().isoformat(timespec="seconds"),
            "prompt": message,
            "content": content.strip(),
        }
        _LAST_CREATIVE_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info("Saved last creative response for later recitation.")
    except Exception as exc:
        logger.debug("Could not save last creative response: %s", exc)


def _load_last_creative_response() -> str | None:
    try:
        if not _LAST_CREATIVE_PATH.exists():
            return None
        payload = json.loads(_LAST_CREATIVE_PATH.read_text(encoding="utf-8-sig"))
        content = str(payload.get("content") or "").strip()
        return content or None
    except Exception as exc:
        logger.debug("Could not load last creative response: %s", exc)
        return None


def _maybe_handle_voice_request(message: str) -> str | None:
    """Ruteaza determinist cererile despre voce, inainte de raspunsul generic despre tooluri."""
    text = _normalize_text(message)
    voice_intent = any(token in text for token in ("voce", "vocal", "tts", "audio", "auzi", "aud", "vorbeste", "speak", "recita", "reciti", "reciteste"))
    if not voice_intent:
        return None

    wants_disable = any(token in text for token in ("dezactiveaza", "opreste", "disable", "mute"))
    wants_enable = any(token in text for token in ("activeaza", "porneste", "enable", "vreau sa aud"))
    wants_speak = any(token in text for token in ("spune", "vorbeste", "citeste cu voce", "speak", "recita", "reciti", "reciteste"))
    asks_capability = "tool" in text or "ai " in text or "poti" in text

    try:
        reg = _get_tool_registry()
        available = set(getattr(reg, "_tools", {}).keys()) if reg is not None else set()
        if reg is None or "edge_tts_voice" not in available:
            return "Toolul de voce nu este incarcat in runtime."

        if wants_disable:
            result = reg.execute("edge_tts_voice", operation="disable")
            if result.is_success:
                return "Vocea ANA a fost dezactivata."
            return f"Nu am putut dezactiva vocea: {result.error or result.message}"

        if wants_enable:
            result = reg.execute("edge_tts_voice", operation="enable")
            if not result.is_success:
                return f"Nu am putut activa vocea: {result.error or result.message}"
            speak = reg.execute(
                "edge_tts_voice",
                operation="speak",
                text="Vocea ANA este activata. Ma auzi?",
                **{"async": True},
            )
            if speak.is_success:
                return "Vocea ANA este activata. Am trimis si un test audio: Ma auzi?"
            return f"Vocea ANA este activata, dar testul audio a esuat: {speak.error or speak.message}"

        if wants_speak:
            spoken_text = None
            if any(token in text for token in ("poezie", "poezia", "poem", "ultima", "o reciti", "reciteste", "recita")):
                spoken_text = _load_last_creative_response()
            loaded_creative = bool(spoken_text)
            if not spoken_text:
                spoken_text = message
            if not loaded_creative:
                for marker in ("spune", "vorbeste", "speak"):
                    if marker in text:
                        spoken_text = message.lower().split(marker, 1)[-1].strip(" :,-") or "Salut, sunt ANA MAX."
                        break
            result = reg.execute("edge_tts_voice", operation="speak", text=spoken_text, **{"async": True})
            if result.is_success:
                return f"Am trimis la voce: {spoken_text}"
            return f"Nu am putut vorbi: {result.error or result.message}"

        if asks_capability:
            return "Da, am tool de voce: `edge_tts_voice` cu operatii `enable`, `disable`, `speak` si `list_voices`."

        return None
    except Exception as exc:
        return f"Eroare la toolul de voce: {exc}"


def _maybe_handle_local_app_open_request(message: str) -> str | None:
    text = _normalize_text(message)
    wants_open = any(token in text for token in ("deschide", "porneste", "porneste", "open", "start"))
    if not wants_open:
        return None
    app_commands = {
        "brave": "Start-Process 'C:\\Program Files\\BraveSoftware\\Brave-Browser\\Application\\brave.exe'",
        "brave browser": "Start-Process 'C:\\Program Files\\BraveSoftware\\Brave-Browser\\Application\\brave.exe'",
        "notepad": "Start-Process notepad",
        "note pad": "Start-Process notepad",
        "calc": "Start-Process calc",
        "calculator": "Start-Process calc",
        "cmd": "Start-Process cmd",
        "powershell": "Start-Process powershell",
    }
    selected = None
    for app_name, command in app_commands.items():
        if app_name in text:
            selected = (app_name, command)
            break
    if not selected:
        return None

    try:
        reg = _get_tool_registry()
        available = set(getattr(reg, "_tools", {}).keys()) if reg is not None else set()
        if reg is None or "terminal" not in available:
            return f"As deschide {selected[0]}, dar toolul `terminal` nu este incarcat."
        result = reg.execute("terminal", operation="run", command=selected[1], timeout=10, confirm=True)
        if result.is_success:
            return f"Am deschis {selected[0]} din terminal/cmd."
        return f"Nu am putut deschide {selected[0]}: {result.error or result.message}"
    except Exception as exc:
        return f"Eroare la deschiderea aplicatiei locale: {exc}"


def _extract_search_query(message: str) -> str:
    text = _normalize_text(message)
    text = re.sub(r"\bppe\s+google\b", "pe google", text)
    text = re.sub(r"\bpe\s+gogle\b", "pe google", text)
    text = re.sub(r"\bgoogle\s+search\b", "google", text)
    text = re.sub(r"\b(ana|te rog|deschide|browserul|browser|si|cauta|cauta|search|pe|google|web|internet)\b", " ", text)
    text = re.sub(r"\s+", " ", text).strip(" :-,.;")
    return text


def _maybe_handle_search_request(message: str) -> str | None:
    """Normalizeaza cererile romanesti de cautare inainte ca modelul sa includa zgomot in query."""
    text = _normalize_text(message)
    wants_search = any(token in text for token in ("cauta", "cauta", "search", "google", "web", "internet"))
    if not wants_search:
        return None
    if any(token in text for token in ("fisier", "folder", "cod", "code", "in proiect", "ana_dev")):
        return None

    query = _extract_search_query(message)
    if not query:
        return None

    try:
        reg = _get_tool_registry()
        available = set(getattr(reg, "_tools", {}).keys()) if reg is not None else set()
        if reg is None or "web_search" not in available:
            return f"As cauta pe web dupa `{query}`, dar `web_search` nu este incarcat."
        result = reg.execute("web_search", operation="search", query=query, max_results=5)
        if not result.is_success:
            return f"Nu am putut cauta `{query}`: {result.error or result.message}"
        data = result.data
        if isinstance(data, list):
            lines = [f"Am cautat pe web dupa: `{query}`"]
            for index, item in enumerate(data[:5], start=1):
                if isinstance(item, dict):
                    title = item.get("title") or item.get("name") or "rezultat"
                    url = item.get("url") or item.get("href") or ""
                    snippet = item.get("snippet") or item.get("description") or ""
                    lines.append(f"[{index}] {title}\n{snippet}\nURL: {url}".strip())
                else:
                    lines.append(f"[{index}] {item}")
            return "\n\n".join(lines)
        return f"Am cautat pe web dupa `{query}`:\n{data}"
    except Exception as exc:
        return f"Eroare la cautarea web pentru `{query}`: {exc}"


def _build_tools_text(tool_names: list[str]) -> str:
    """Construieste descrierea text a tools selectate pentru system prompt."""
    lines = ["UNELTE DISPONIBILE (foloseste ACTION+ARGS pentru a le apela):"]
    for name in tool_names:
        desc = _TOOL_DESCRIPTIONS.get(name)
        if desc:
            lines.append(f"\n- {desc}")
        else:
            lines.append(f"\n- {name}: tool disponibil in ANA")
    return "\n".join(lines)


def _get_active_tool_count() -> int:
    """Returneaza numarul de tooluri incarcate in registry, daca este disponibil."""
    try:
        reg = _get_tool_registry()
        tools = getattr(reg, "_tools", {}) if reg is not None else {}
        return len(tools)
    except Exception:
        return 0


def _tool_catalog() -> list[dict[str, Any]]:
    """Citeste catalogul real de tools din registry, nu din memoria modelului."""
    try:
        reg = _get_tool_registry()
        tools = getattr(reg, "_tools", {}) if reg is not None else {}
        catalog: list[dict[str, Any]] = []
        for name, tool in sorted(tools.items()):
            try:
                definition = tool.get_definition()
                params = getattr(definition, "parameters", []) or []
                operations: list[str] = []
                for param in params:
                    param_name = getattr(param, "name", "")
                    choices = getattr(param, "choices", None)
                    if param_name in ("operation", "action", "mode") and choices:
                        operations.extend(str(choice) for choice in choices)
                catalog.append(
                    {
                        "name": str(getattr(definition, "name", name)),
                        "category": str(getattr(definition, "category", "")),
                        "description": str(getattr(definition, "description", "")),
                        "operations": operations[:12],
                    }
                )
            except Exception:
                catalog.append({"name": str(name), "category": "", "description": "", "operations": []})
        return catalog
    except Exception:
        return []


def _maybe_answer_tool_catalog_query(message: str, active_tool_count: int) -> str | None:
    """Raspunde inteligent la 'ai tool pentru X?' cautand in catalogul real ANA."""
    text = _normalize_text(message)
    asks_tool = "tool" in text or "unealta" in text or "unelte" in text
    if not asks_tool:
        return None
    if any(token in text for token in ("ce zi", "data", "azi", "astazi", "ora", "presedinte", "cine esti")):
        return None

    catalog = _tool_catalog()
    if not catalog:
        return f"Am {active_tool_count} tooluri active, dar catalogul runtime nu a putut fi citit acum."

    stopwords = {
        "ai", "are", "am", "tool", "tooluri", "ptr", "pt", "pentru", "de", "la", "cu", "si", "sau",
        "ce", "care", "imi", "poti", "poate", "activeaza", "vreau", "sa", "aud", "scrii", "folosesc",
        "folosi", "un", "o", "in", "pe", "te", "rog",
        "cate", "cat", "cati",
    }
    query_terms = [
        token for token in re.findall(r"[a-z0-9_]+", text)
        if len(token) >= 3 and token not in stopwords
    ]

    if not query_terms:
        categories: dict[str, int] = {}
        for item in catalog:
            category = item["category"] or "uncategorized"
            categories[category] = categories.get(category, 0) + 1
        top_categories = ", ".join(f"{name}={count}" for name, count in sorted(categories.items())[:12])
        return (
            f"Am {active_tool_count} tooluri active. Categorii principale: {top_categories}. "
            "Intreaba natural, de exemplu: `ai tool pentru voce?`, `ai tool pentru procese?`, `ai tool pentru fisiere?`."
        )

    scored: list[tuple[int, dict[str, Any]]] = []
    for item in catalog:
        haystack = _normalize_text(
            " ".join(
                [
                    item["name"],
                    item["category"],
                    item["description"],
                    " ".join(item.get("operations", [])),
                ]
            )
        )
        score = sum(3 if term in item["name"] else 1 for term in query_terms if term in haystack)
        if any(term in ("proces", "procese", "pid") for term in query_terms):
            if item["name"] in ("system_control", "windows_deep_sight", "windows_insight"):
                score += 5
        if any(term in ("fisier", "fisiere", "file", "folder") for term in query_terms):
            if item["name"] in ("file_operations", "glob_search", "grep_content", "grep_file"):
                score += 5
        if any(term in ("browser", "url", "site") for term in query_terms):
            if item["name"] == "browser_control":
                score += 5
        if score:
            scored.append((score, item))
    scored.sort(key=lambda pair: (-pair[0], pair[1]["name"]))

    if not scored:
        return (
            f"Am {active_tool_count} tooluri active, dar nu gasesc un match clar pentru: "
            f"{', '.join(query_terms)}. Pot lista catalogul pe categorii."
        )

    lines = [f"Da. Am gasit tooluri relevante pentru `{', '.join(query_terms)}`:"]
    for _, item in scored[:6]:
        ops = ", ".join(item.get("operations", [])[:6])
        suffix = f" Operatii: {ops}." if ops else ""
        lines.append(f"- `{item['name']}` ({item['category']}): {item['description'][:140]}{suffix}")
    return "\n".join(lines)


def _normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text.lower())
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def _romania_now() -> datetime:
    return datetime.now(ZoneInfo("Europe/Bucharest"))


def _maybe_answer_current_facts(message: str, active_tool_count: int) -> str | None:
    """Raspuns determinist pentru intrebari curente unde modelul local tinde sa halucineze."""
    text = _normalize_text(message)
    asks_identity = "cine esti" in text
    asks_tools = "tool" in text or "unelte" in text
    asks_date = any(token in text for token in ("ce zi", "data", "azi", "astazi"))
    asks_time = any(token in text for token in ("ora", "cat este ceasul", "cat e ceasul"))
    asks_president = "presedinte" in text or "presedintele" in text

    if not any((asks_identity, asks_tools, asks_date, asks_time, asks_president)):
        return None

    now = _romania_now()
    parts: list[str] = []
    if asks_identity:
        parts.append("Sunt ANA MAX, agentul tau local privat.")
    if asks_tools:
        parts.append(f"Am {active_tool_count} tooluri active in runtime.")
    if asks_date:
        day_name = _RO_WEEKDAYS.get(now.weekday(), now.strftime("%A"))
        parts.append(f"Astazi in Romania este {day_name}, {now.strftime('%d.%m.%Y')}.")
    if asks_time:
        parts.append(f"Ora in Romania este {now.strftime('%H:%M')}.")
    if asks_president:
        parts.append(
            f"Presedintele Romaniei este {_ROMANIA_PRESIDENT} "
            f"(verificat in lab la {_ROMANIA_PRESIDENT_VERIFIED})."
        )

    return " ".join(parts)


def _looks_like_simple_chat(message: str) -> bool:
    text = message.strip().lower()
    if not text:
        return True

    action_words = (
        "creeaza",
        "creaza",
        "scrie",
        "scri",
        "tasteaza",
        "type",
        "sterge",
        "muta",
        "copiaza",
        "ruleaza",
        "deschide",
        "notepad",
        "note pad",
        "cauta",
        "citeste fisier",
        "fa folder",
        "fa un folder",
        "executa",
        "testeaza",
        "repara",
        "modifica",
        "proces",
        "procese",
        "pid",
        "task manager",
        "taskmanager",
        "partitie",
        "partitii",
        "drive",
        "c:",
        "d:",
    )
    if any(word in text for word in action_words):
        return False

    return len(text) < 180


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

    # Format multi-linie
    pattern = re.compile(
        r"ACTION\s*:\s*(\w+)\s*\n\s*ARGS\s*:\s*(\{.*?\})",
        re.IGNORECASE | re.DOTALL,
    )
    for m in pattern.finditer(text):
        tool_name = m.group(1).strip()
        args_raw = m.group(2).strip()
        parse_error = None
        try:
            args = json.loads(args_raw)
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
        for m in pattern2.finditer(text):
            tool_name = m.group(1).strip()
            args_raw = m.group(2).strip()
            parse_error = None
            try:
                args = json.loads(args_raw)
            except Exception as exc:
                args = {}
                parse_error = str(exc)
            actions.append({"tool": tool_name, "args": args, "parse_error": parse_error, "args_raw": args_raw})

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
                msg["content"] = content[:500] + "\n... [trunchiat assistant message] ...\n"
                logger.info("Compressed old assistant message at index %d", i)
    return copied


def _detect_and_inject_skill(message: str) -> str:
    """Detecteaza daca mesajul se potriveste cu un skill din ana/skills/skills/ si returneaza instructiunile din SKILL.md."""
    text = _normalize_text(message)
    skill_name = None

    if any(token in text for token in ("repara", "repair", "cooperation", "self-repair", "self.repair")):
        skill_name = "self-repair"
    elif any(token in text for token in ("health", "check", "stare", "diagnostic", "healthcheck", "health-check", "health.check")):
        skill_name = "health-check"
    elif any(token in text for token in ("fs", "inspect", "inspecteaza", "filesystem", "path", "fs-inspect", "fs.inspect")):
        skill_name = "fs-inspect"

    if not skill_name:
        return ""

    try:
        skills_dir = _ANA_ROOT / "ana" / "skills" / "skills"
        skill_md_path = skills_dir / skill_name / "SKILL.md"
        if skill_md_path.exists():
            content = skill_md_path.read_text(encoding="utf-8")
            logger.info("Dynamically injected skill: %s", skill_name)
            return (
                f"\n\nGHID DE EXECUTIE DECLARATIV (Urmeaza pasii din acest SKILL pentru realizarea task-ului):\n"
                f"```markdown\n{content}\n```\n"
            )
    except Exception as exc:
        logger.warning("Failed to load skill %s: %s", skill_name, exc)
    return ""


_CACHE_PATH = _ANA_ROOT / "memory" / "response_cache.json"
_RESPONSE_CACHE = None


def _load_response_cache() -> dict[str, str]:
    try:
        if _CACHE_PATH.exists():
            return json.loads(_CACHE_PATH.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        logger.debug("Failed to load response cache: %s", exc)
    return {}


def _save_response_cache(cache: dict[str, str]) -> None:
    try:
        _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as exc:
        logger.debug("Failed to save response cache: %s", exc)


def _get_cached_response(message: str) -> str | None:
    global _RESPONSE_CACHE
    if _RESPONSE_CACHE is None:
        _RESPONSE_CACHE = _load_response_cache()

    normalized = _normalize_text(message)
    return _RESPONSE_CACHE.get(normalized)


def _cache_response(message: str, response: str) -> None:
    global _RESPONSE_CACHE
    if _RESPONSE_CACHE is None:
        _RESPONSE_CACHE = _load_response_cache()

    normalized = _normalize_text(message)
    # Nu cache-uim erori
    if response and not response.startswith(("Eroare", "EROARE", "EXCEPTIE", "BLOCAT")):
        if len(_RESPONSE_CACHE) >= 100:
            oldest = next(iter(_RESPONSE_CACHE))
            _RESPONSE_CACHE.pop(oldest, None)

        _RESPONSE_CACHE[normalized] = response
        _save_response_cache(_RESPONSE_CACHE)


def _decorate_user_message(content: str, tool_names: list[str], is_result: bool = False) -> str:
    """Injeteaza lista de tool-uri active si regulile de format direct in mesajul utilizatorului (Codex pattern)."""
    if not tool_names:
        return content

    tool_list_str = ", ".join(tool_names)

    if is_result:
        return (
            f"Rezultatele actiunilor tale anterioare:\n\n{content}\n\n"
            f"UNELTE PERMISE in continuare: [{tool_list_str}].\n"
            "Daca ai nevoie de o alta unealta, raspunde strict in formatul:\n"
            "ACTION: <nume_tool>\n"
            "ARGS: { ... }\n"
            "Altfel, daca task-ul este complet, raspunde direct cu un rezumat in romana."
        )
    else:
        return (
            f"Task utilizator: {content}\n\n"
            f"UNELTE DISPONIBILE pentru acest task: [{tool_list_str}].\n"
            "Daca ai nevoie de o unealta, raspunde strict in formatul:\n"
            "ACTION: <nume_tool>\n"
            "ARGS: { ... }\n"
            "Altfel, raspunde direct in romana."
        )


# ---------------------------------------------------------------------------
# Send - Text Injection Loop
# ---------------------------------------------------------------------------

def send(agent: Any, message: str) -> str:
    """
    Trimite mesajul la Mistral folosind TEXT INJECTION MODE.

    In loc de JSON tool schemas (care sufoca Mistral 7B cu 86 definitii),
    injectam tools ca text simplu in system prompt si parsam raspunsul
    pentru blocuri ACTION:/ARGS: pe care ANA le executa direct.

    Flow:
      1. Selectam 4-8 tools relevante pentru mesaj
      2. Le descriem ca text in system prompt
      3. Mistral raspunde cu ACTION:tool ARGS:{...}
      4. ANA executa tool-ul, injecteaza rezultatul
      5. Mistral continua pana termina task-ul
    """
    global _WARM
    import requests

    host = _get_ollama_host(agent)
    model = _get_ollama_model(agent)
    chat_url = f"{host}/api/chat"
    timeout = _TIMEOUT_WARM if _WARM else _TIMEOUT_COLD

    simple_chat = _looks_like_simple_chat(message)
    read_only = _is_read_only_request(message)
    single_action = _is_single_action_request(message)
    active_tool_count = _get_active_tool_count()
    voice_answer = _maybe_handle_voice_request(message)
    if voice_answer:
        logger.info("Voice request handled deterministically.")
        return voice_answer
    local_app_answer = _maybe_handle_local_app_open_request(message)
    if local_app_answer:
        logger.info("Local app open request handled deterministically.")
        return local_app_answer
    tool_catalog_answer = _maybe_answer_tool_catalog_query(message, active_tool_count)
    if tool_catalog_answer:
        logger.info("Tool catalog query answered deterministically.")
        return tool_catalog_answer
    current_facts_answer = _maybe_answer_current_facts(message, active_tool_count)
    if current_facts_answer:
        logger.info("Current facts answered deterministically.")
        return current_facts_answer
    observation_answer = _maybe_answer_observation_query(message)
    if observation_answer:
        logger.info("Observation query answered deterministically.")
        return observation_answer
    search_answer = _maybe_handle_search_request(message)
    if search_answer:
        logger.info("Search request handled deterministically.")
        return search_answer

    cached_response = _get_cached_response(message)
    if cached_response:
        logger.info("Response cache HIT for: %s", message)
        return cached_response

    # Selectam tools relevante: intai router/coach ANA, apoi fallback keyword local.
    tool_names = [] if simple_chat else (_route_tool_names(message) or _select_tool_names(message))
    tools_text = _build_tools_text(tool_names)
    preflight_context = _build_preflight_context(message, tool_names)
    num_predict = _OLLAMA_CHAT_TOKENS if simple_chat else _OLLAMA_TOOL_TOKENS

    logger.info(
        "Ollama TEXT-INJECTION: model=%s tools=%s timeout=%ds warm=%s num_predict=%d",
        model, tool_names, timeout, _WARM, num_predict,
    )

    system_prompt = (
        "Esti ANA MAX, un agent AI local care executa task-uri reale pe sistemul Windows.\n\n"
        f"Ai {active_tool_count} tooluri active incarcate in runtime-ul ANA.\n\n"
        + tools_text + "\n\n"
        "REGULI STRICTE:\n"
        "1. Daca mesajul este conversatie simpla (salut, multumesc, cum esti, ce mai faci etc.) "
        "raspunde DOAR cu text scurt in romana, FARA blocuri ACTION+ARGS.\n"
        "2. Pentru orice actiune concreta (creaza fisier/folder, cauta, ruleaza comanda etc.) "
        "raspunde EXCLUSIV cu blocuri ACTION+ARGS. NU da explicatii, NU simula, EXECUTA.\n"
        "3. Format obligatoriu pentru tool call:\n"
        "   ACTION: <nume_tool>\n"
        "   ARGS: {\"param\": \"valoare\"}\n"
        "4. Poti face mai multe ACTION-uri in acelasi raspuns.\n"
        "5. Dupa ce primesti rezultatul unui tool, continua cu urmatorul ACTION daca e nevoie.\n"
        "6. Cand task-ul e complet, scrie un scurt rezumat in romana.\n"
        "7. Caile Windows folosesc backslash: C:\\Users\\billy\\Desktop\\\n"
        "8. Pentru comenzi PowerShell native (Get-Process, New-Item etc.) foloseste "
        "terminal cu operation=run si command=<cmdlet PS direct, FARA prefix powershell>.\n"
        "9. NU folosi code_tools pentru task-uri simple de fisiere/foldere - foloseste terminal sau file_operations."
    )

    system_prompt += (
        "\n10. Pentru 'deschide Notepad si scrie text': prima actiune este terminal command=notepad, "
        "apoi uia_type cu window_title=Notepad, control_type=Edit, text=<textul cerut>.\n"
        "11. Aplicatii locale precum calc, notepad, cmd sau powershell NU sunt URL-uri; foloseste terminal.\n"
        "12. Daca task-ul cere scriere in Notepad si uia_type esueaza, NU crea fisier alternativ; raporteaza eroarea."
    )
    if preflight_context:
        system_prompt += (
            "\n\nCONTEXT REAL OBSERVAT READ-ONLY (desktop/procese/workspace, nu presupune):\n"
            f"{preflight_context}\n"
            "Foloseste acest context ca sa nu lucrezi orbeste. Nu deschide ferestre doar pentru observatie.\n"
        )

    # Inseram dynamic skills injection
    skill_injection = _detect_and_inject_skill(message)
    if skill_injection:
        system_prompt += skill_injection

    if simple_chat:
        system_prompt = (
            "Esti ANA MAX, asistent local in romana. "
            f"Ai {active_tool_count} tooluri active incarcate in runtime-ul ANA. "
            "Daca esti intrebat cine esti, spune ca esti ANA MAX, agent local privat. "
            "Raspunde scurt si natural. Nu folosi ACTION sau ARGS."
        )
    elif single_action:
        system_prompt += (
            "\n\nMOD SINGLE-ACTION ACTIV:\n"
            "- Task-ul cere o singura actiune de deschidere/pornire.\n"
            "- Executa doar actiunea ceruta si opreste-te.\n"
            "- Nu crea fisiere de test, nu scrie pe disk si nu inventa verificari.\n"
            "- Pentru aplicatii locale precum calc, notepad, cmd sau powershell foloseste terminal, nu browser_control.\n"
        )
    elif read_only:
        system_prompt += (
            "\n\nMOD READ-ONLY ACTIV:\n"
            "- Ai voie doar sa inspectezi, listezi, citesti si cauti.\n"
            "- Nu folosi delete/write/edit/patch/click/type/remove/move/copy.\n"
            "- Nu folosi terminal pentru comenzi mutante.\n"
            "- Daca nu poti analiza fara mutatie, spune clar ce lipseste.\n"
        )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": message},
    ]

    failed_actions = []
    empty_retries = 0
    for loop_i in range(_MAX_TOOL_LOOPS):
        # Actualizam system prompt in messages cu eventualele esecuri din aceasta bucla
        current_system_prompt = system_prompt
        if failed_actions:
            failures_text = "\n\nAVERTISMENT: Următoarele acțiuni din această sesiune au eșuat deja:\n"
            for f_name, f_args, f_err in failed_actions:
                failures_text += f"- Tool '{f_name}' cu argumente '{f_args}' a eșuat: {f_err}\n"
            failures_text += "NU repeta aceleași acțiuni sau aceiași parametri. Adaptează-ți strategia sau folosește altă uneltă.\n"
            current_system_prompt += failures_text
        messages[0]["content"] = current_system_prompt

        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {
                "num_ctx": _OLLAMA_NUM_CTX,
                "num_predict": num_predict,
                "temperature": 0.2,
            },
            # NU trimitem 'tools' - folosim text injection
        }

        try:
            resp = requests.post(chat_url, json=payload, timeout=timeout)
            resp.raise_for_status()
        except requests.exceptions.Timeout:
            if not _WARM:
                logger.warning("Timeout cold start, retry cu %ds...", _TIMEOUT_COLD + 60)
                try:
                    resp = requests.post(chat_url, json=payload, timeout=_TIMEOUT_COLD + 60)
                    resp.raise_for_status()
                except Exception as exc:
                    logger.error("Cold start retry esuat: %s", exc)
                    return "Eroare: Ollama nu raspunde (cold start timeout)."
            else:
                logger.error("Ollama timeout (warm): loop %d", loop_i + 1)
                return "Eroare: Ollama timeout. Reincearca."
        except requests.exceptions.HTTPError as exc:
            status_code = getattr(exc.response, "status_code", None)
            response_text = (getattr(exc.response, "text", "") or "")[:500]
            logger.error("Eroare HTTP Ollama status=%s body=%s", status_code, response_text)
            if status_code == 500 and loop_i == 0:
                logger.warning("Ollama 500: retry cu context mai mic si raspuns scurt.")
                retry_payload = dict(payload)
                retry_payload["options"] = dict(payload["options"])
                retry_payload["options"]["num_ctx"] = 1024
                retry_payload["options"]["num_predict"] = min(num_predict, 96)
                try:
                    resp = requests.post(chat_url, json=retry_payload, timeout=timeout)
                    resp.raise_for_status()
                except Exception as retry_exc:
                    logger.error("Ollama 500 retry esuat: %s", retry_exc)
                    return "Eroare: Ollama a returnat 500 si retry-ul scurt a esuat. Reincearca dupa cateva secunde."
            else:
                return f"Eroare conexiune Ollama: {exc}"
        except Exception as exc:
            logger.error("Eroare HTTP Ollama: %s", exc)
            return f"Eroare conexiune Ollama: {exc}"

        _WARM = True
        data = resp.json()
        msg = data.get("message", {})
        content = (msg.get("content") or "").strip()

        if not content:
            empty_retries += 1
            logger.warning("Ollama loop %d: raspuns gol (retry %d/2)", loop_i + 1, empty_retries)
            if empty_retries >= 2:
                logger.error("Doua raspunsuri goale consecutive - returnez fallback.")
                return "Modelul nu a generat un raspuns. Reincearca sau reformuleaza cererea."
            # Simplificam mesajele si reincercam cu un prompt mai scurt
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message + "\n\nRaspunde scurt in romana."},
            ]
            continue

        logger.info(
            "Ollama loop %d: raspuns %d chars",
            loop_i + 1, len(content),
        )

        # Parsam ACTION blocks din raspuns
        actions = _parse_action_blocks(content)

        if not actions:
            # Raspuns text final
            logger.info("Ollama loop %d: raspuns text final (no actions)", loop_i + 1)
            _save_last_creative_response(message, content)
            _cache_response(message, content)
            return content

        # Executam toate action-urile gasite
        logger.info(
            "Ollama loop %d: %d actiuni gasite: %s",
            loop_i + 1,
            len(actions),
            [a["tool"] for a in actions],
        )

        # Adaugam raspunsul in istoric
        messages.append({"role": "assistant", "content": content})

        # Executam tools si colectam rezultatele
        results_text_parts = []
        successful_results = []
        for action in actions:
            tool_name = action["tool"]
            tool_args = action["args"]
            parse_error = action.get("parse_error")

            if parse_error:
                result = f"EROARE: Formatul argumentelor pentru '{tool_name}' este invalid JSON. Detalii: {parse_error}. Te rog trimite JSON valid dupa 'ARGS:'."
                failed_actions.append((tool_name, action.get("args_raw") or str(tool_args), result))
            else:
                # Preflight validation of tool availability
                reg = _get_tool_registry()
                available = set(getattr(reg, "_tools", {}).keys()) if reg is not None else set()
                # allow special helper tools
                available.add("tool_router")
                available.add("agent_coach")

                if tool_name not in available:
                    result = f"EROARE: Tool-ul '{tool_name}' nu este disponibil in acest runtime local. Uneltele permise sunt: {list(available)}. Alege alta abordare sau unealta."
                    failed_actions.append((tool_name, str(tool_args), result))
                else:
                    logger.info("Executie tool (text-inject): %s args=%s", tool_name, list(tool_args.keys()))
                    result = _execute_tool(tool_name, tool_args, read_only=read_only, task_message=message)
                    logger.info("Rezultat %s: %s", tool_name, result[:150])

                    if result.startswith(("EROARE", "EXCEPTIE", "BLOCAT")):
                        failed_actions.append((tool_name, str(tool_args), result))
                    else:
                        successful_results.append((tool_name, result))

            results_text_parts.append(f"REZULTAT {tool_name}:\n{result}")

        if single_action and successful_results:
            tool_name, result = successful_results[-1]
            logger.info("Single-action request completed after %s; stopping loop.", tool_name)
            return f"Actiune executata cu {tool_name}: {result[:500]}"

        task_text = _normalize_text(message)
        if any(tool_name == "uia_type" for tool_name, _ in successful_results) and (
            "notepad" in task_text or "note pad" in task_text or "scrie" in task_text or "scri" in task_text
        ):
            logger.info("Typing task completed after uia_type; stopping loop.")
            return "Textul a fost scris in aplicatia ceruta."

        # Injectam rezultatele inapoi ca mesaj user (standard pentru text mode)
        tool_results_msg = "\n\n".join(results_text_parts)
        messages.append({
            "role": "user",
            "content": (
                f"Rezultatele actiunilor tale:\n\n{tool_results_msg}\n\n"
                "Continua cu urmatorul pas sau, daca task-ul e gata, "
                "scrie un scurt rezumat in romana."
            ),
        })

        # Dynamic Context Budget: comprimam istoricul daca este prea lung
        messages = _compress_history(messages, max_chars=5000)

    # Loop epuizat
    logger.warning("Agentic loop epuizat dupa %d iteratii.", _MAX_TOOL_LOOPS)
    return "Task executat (loop maxim atins)."
