import json
import os
import re
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Any
from pathlib import Path
from core.backends.ollama_parser import _normalize_text
from core.backends.ollama_context import _drive_listing

logger = logging.getLogger(__name__)

# ===========================================================================
# BLOC HANDLERE DETERMINISTE OS27
# Toate operatiile de sistem de baza sunt executate DIRECT in Python,
# fara sa mai trecem prin LLM. Zero latenta, zero refuzuri Safety Alignment.
# ===========================================================================

def _extract_quoted_paths(message: str) -> list[str]:
    """Extrage caile din ghilimele duble sau simple din mesaj."""
    paths = re.findall(r'"([^"]+)"', message)
    paths += re.findall(r"'([^']+)'", message)
    return [p for p in paths if len(p) > 2 and ('\\' in p or '/' in p)]


# ---------------------------------------------------------------------------
# 1. STERGE fisier/folder
# ---------------------------------------------------------------------------
def _maybe_handle_file_delete_request(message: str) -> str | None:
    text_low = message.lower()
    if not any(kw in text_low for kw in ("sterge", "delete", "remove", "sterg", "elimina", "scapa", "da afara", "scoate")):
        return None
    target_paths = _extract_quoted_paths(message)
    if not target_paths:
        return None
    results = []
    for path_str in target_paths:
        target = Path(path_str)
        if not target.exists():
            results.append(f"'{path_str}' nu exista sau a fost deja sters.")
            continue
        try:
            if target.is_dir():
                import shutil; shutil.rmtree(target)
                results.append(f"Folder sters: {path_str}")
            else:
                target.unlink()
                results.append(f"Fisier sters: {path_str}")
            logger.info("[DET-DELETE] %s", path_str)
        except Exception as exc:
            results.append(f"Eroare stergere '{path_str}': {exc}")
    return "\n".join(results) if results else None


# ---------------------------------------------------------------------------
# 2. CREAZA fisier sau folder
# ---------------------------------------------------------------------------
def _maybe_handle_create_request(message: str) -> str | None:
    text_low = message.lower()
    wants_create = any(kw in text_low for kw in ("creeaza", "creaza", "mkdir", "new folder", "folder nou", "fisier nou", "new file", "fa un folder", "fa un fisier"))
    if not wants_create:
        return None
    target_paths = _extract_quoted_paths(message)
    if not target_paths:
        return None
    results = []
    for path_str in target_paths:
        target = Path(path_str)
        try:
            # Daca are extensie → fisier, altfel → folder
            if target.suffix:
                target.parent.mkdir(parents=True, exist_ok=True)
                if not target.exists():
                    target.touch()
                results.append(f"Fisier creat: {path_str}")
            else:
                target.mkdir(parents=True, exist_ok=True)
                results.append(f"Folder creat: {path_str}")
            logger.info("[DET-CREATE] %s", path_str)
        except Exception as exc:
            results.append(f"Eroare creare '{path_str}': {exc}")
    return "\n".join(results) if results else None


# ---------------------------------------------------------------------------
# 3. RENAME fisier/folder
# ---------------------------------------------------------------------------
def _maybe_handle_rename_request(message: str) -> str | None:
    text_low = message.lower()
    if not any(kw in text_low for kw in ("redenumeste", "rename", "schimba numele")):
        return None
    paths = _extract_quoted_paths(message)
    if len(paths) < 2:
        return None
    src, dst = Path(paths[0]), Path(paths[1])
    if not src.exists():
        return f"'{paths[0]}' nu exista."
    try:
        # Daca dst e doar un nume (fara separator), il punem in acelasi folder
        if '\\' not in paths[1] and '/' not in paths[1]:
            dst = src.parent / paths[1]
        src.rename(dst)
        logger.info("[DET-RENAME] %s -> %s", src, dst)
        return f"Redenumit: '{src.name}' → '{dst.name}'"
    except Exception as exc:
        return f"Eroare redenumire: {exc}"


# ---------------------------------------------------------------------------
# 4. KILL proces dupa nume
# ---------------------------------------------------------------------------
def _maybe_handle_kill_process_request(message: str) -> str | None:
    text_low = message.lower()
    kill_kws = ("opreste procesul", "kill", "termina procesul", "inchide procesul", "opreste aplicatia", "forteaza inchiderea")
    if not any(kw in text_low for kw in kill_kws):
        return None
    # Extrage numele procesului: fie din ghilimele, fie ultimul cuvant dupa keyword
    names_in_quotes = re.findall(r'"([^"]+)"', message)
    proc_names = [n for n in names_in_quotes if '.' in n or len(n) < 30]
    if not proc_names:
        # Fallback: extrage ultimul cuvant care arata a process name
        m = re.search(r'(?:kill|opreste procesul|termina procesul)\s+([a-zA-Z0-9_\-\.]+)', text_low)
        if m:
            proc_names = [m.group(1)]
    if not proc_names:
        return None
    import subprocess
    results = []
    for name in proc_names:
        name_clean = name.lower().replace(".exe", "")
        try:
            import psutil
            killed = []
            for proc in psutil.process_iter(['pid', 'name']):
                if name_clean in proc.info['name'].lower():
                    proc.kill()
                    killed.append(str(proc.info['pid']))
            if killed:
                results.append(f"Proces '{name}' oprit (PID: {', '.join(killed)})")
                logger.info("[DET-KILL] %s PIDs=%s", name, killed)
            else:
                results.append(f"Niciun proces '{name}' gasit.")
        except ImportError:
            # Fallback fara psutil
            r = subprocess.run(["taskkill", "/F", "/IM", f"{name_clean}.exe"], capture_output=True, text=True)
            results.append(r.stdout.strip() or r.stderr.strip() or f"taskkill rulat pentru {name}")
        except Exception as exc:
            results.append(f"Eroare kill '{name}': {exc}")
    return "\n".join(results) if results else None


# ---------------------------------------------------------------------------
# 5. DESCHIDE terminal (cmd/powershell)
# ---------------------------------------------------------------------------
def _maybe_handle_open_terminal_request(message: str) -> str | None:
    text_low = message.lower()
    if not any(kw in text_low for kw in ("deschide terminal", "deschide cmd", "deschide powershell", "open terminal", "open cmd", "porneste terminal", "terminal nou")):
        return None
    import subprocess
    try:
        if "cmd" in text_low:
            subprocess.Popen(["cmd.exe"], creationflags=subprocess.CREATE_NEW_CONSOLE)
            return "Terminal CMD deschis."
        else:
            subprocess.Popen(["powershell.exe", "-NoExit"], creationflags=subprocess.CREATE_NEW_CONSOLE)
            return "Terminal PowerShell deschis."
    except Exception as exc:
        return f"Eroare deschidere terminal: {exc}"


# ---------------------------------------------------------------------------
# 6. SCAN porturi deschise
# ---------------------------------------------------------------------------
def _maybe_handle_port_scan_request(message: str) -> str | None:
    text_low = message.lower()
    if not any(kw in text_low for kw in ("porturi deschise", "scan port", "ce porturi", "netstat", "porturi active", "open ports")):
        return None
    import subprocess
    try:
        result = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True, text=True, timeout=10
        )
        lines = [l for l in result.stdout.splitlines() if "LISTENING" in l or "ESTABLISHED" in l]
        # Extrage port + PID, dedup
        ports_seen = {}
        for line in lines:
            parts = line.split()
            if len(parts) >= 5:
                local = parts[1]
                state = parts[3]
                pid = parts[4]
                port = local.rsplit(":", 1)[-1]
                if port not in ports_seen:
                    ports_seen[port] = f":{port} [{state}] PID={pid}"
        top = list(ports_seen.values())[:25]
        logger.info("[DET-PORTSCAN] found %d listening ports", len(top))
        return f"Porturi active ({len(ports_seen)} total, top 25):\n" + "\n".join(top)
    except Exception as exc:
        return f"Eroare port scan: {exc}"


# ---------------------------------------------------------------------------
# MASTER DISPATCHER — apelat o singura data inainte de LLM
# ---------------------------------------------------------------------------
def _maybe_handle_os_request(message: str) -> str | None:
    """Incearca toti handlerii deterministi in ordine. Primul care returneaza non-None castiga."""
    for handler in (
        _maybe_handle_file_delete_request,
        _maybe_handle_create_request,
        _maybe_handle_rename_request,
        _maybe_handle_kill_process_request,
        _maybe_handle_open_terminal_request,
        _maybe_handle_port_scan_request,
    ):
        result = handler(message)
        if result is not None:
            return result
    return None

def _maybe_answer_observation_query(message: str) -> str | None:
    from core.backends.ollama_backend import _get_tool_registry
    text = _normalize_text(message)
    asks_processes = any(re.search(r'\b' + kw + r'\b', text) for kw in ("proces", "procese", "pid", "task manager", "taskmanager"))
    asks_drives = any(re.search(r'\b' + kw + r'\b', text) for kw in ("partitie", "partitii", "lista drive", "spatiu disc"))
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
    return any(re.search(r"\b" + token + r"\b", text) for token in ("poezie", "poem", "poveste", "cantec", "text creativ", "recita"))



def _save_last_creative_response(message: str, content: str) -> None:
    from core.backends.ollama_backend import _LAST_CREATIVE_PATH
    if not content or not _looks_like_creative_text_request(message):
        return
    text = _normalize_text(message)
    if any(re.search(r"\b" + kw + r"\b", text) for kw in ("recita", "reciteste", "reciti")):
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
    from core.backends.ollama_backend import _LAST_CREATIVE_PATH
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
    from core.backends.ollama_backend import _get_tool_registry
    text = _normalize_text(message)
    voice_intent = any(re.search(r"\b" + kw + r"\b", text) for kw in ("voce", "vocal", "tts", "audio", "auzi", "aud", "vorbeste", "speak", "recita", "reciti", "reciteste"))
    if not voice_intent:
        return None

    wants_disable = any(re.search(r"\b" + kw + r"\b", text) for kw in ("dezactiveaza", "opreste", "disable", "mute"))
    wants_enable = any(re.search(r"\b" + kw + r"\b", text) for kw in ("activeaza", "porneste", "enable", "vreau sa aud"))
    wants_speak = any(re.search(r"\b" + kw + r"\b", text) for kw in ("spune", "vorbeste", "citeste cu voce", "speak", "recita", "reciti", "reciteste"))
    asks_capability = bool(re.search(r"\b(tool|ai |poti)\b", text))

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
            if any(re.search(r"\b" + re.escape(token) + r"\b", text) for token in ("poezie", "poezia", "poem", "ultima", "o reciti", "reciteste", "recita")):
                spoken_text = _load_last_creative_response()
            loaded_creative = bool(spoken_text)
            if not spoken_text:
                spoken_text = message
            if not loaded_creative:
                for marker in ("spune", "vorbeste", "speak"):
                    if re.search(r"\b" + re.escape(marker) + r"\b", text):
                        # Extract what comes after the marker
                        match = re.search(r"\b" + re.escape(marker) + r"\b(.*)", text, re.IGNORECASE)
                        spoken_text = (match.group(1).strip(" :,-") if match else "") or "Salut, sunt ANA MAX."
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



def _maybe_handle_notepad_write_request(message: str) -> str | None:
    """Handler determinist pentru cereri compuse: 'deschide aplicatie si scrie cod/text'
       sau 'creaza script si deschide in aplicatie'.

    In loc sa lasam Qwen sa faca multi-step agentic (care esueaza cu token budget mic),
    facem totul programatic:
    1. Detectam pattern-ul (deschide notepad + scrie cod/text)
    2. Generam codul prin Ollama cu un prompt focusat (fara tools overhead)
    3. Scriem fisierul pe Desktop
    4. Deschidem fisierul cu notepad
    """
    from core.backends.ollama_backend import _get_tool_registry
    text = _normalize_text(message)

    # Detectam: cere deschidere aplicatie + scriere/creare de cod/text
    wants_open = any(re.search(r"\b" + kw + r"\b", text) for kw in ("deschide", "open", "porneste", "lanseaza"))
    # Extindem wants_write cu toti verbii de creare/salvare
    wants_write = any(re.search(r"\b" + kw + r"\b", text) for kw in (
        "scrie", "scri", "write", "creeaza", "create", "fa un", "fa o", "fa",
        "salveaza", "save", "genereaza", "generaza", "genereaz", "faci", "creaza",
        "construieste", "build", "make", "produce",
    ))
    wants_code = any(re.search(r"\b" + kw + r"\b", text) for kw in (
        "cod", "code", "script", "python", "linii", "lini", "program",
        "react", "html", "js", "javascript", "site", "pagina", "web",
    ))
    wants_browser = any(re.search(r"\b" + kw + r"\b", text) for kw in ("browser", "brave", "chrome", "edge"))
    wants_notepad = any(re.search(r"\b" + kw + r"\b", text) for kw in ("notepad", "note pad"))

    # Detectie directa: cerere de creare site/html deschis in browser
    is_html_browser_task = wants_code and wants_browser

    if not ((wants_open and wants_write) or (wants_write and wants_browser) or
            (wants_write and wants_notepad) or is_html_browser_task):
        return None

    is_code_request = wants_code
    
    # Determinam target app
    target_app = "notepad"
    if wants_browser:
        target_app = "browser"

    # Extragem subiectul din mesaj
    # Eliminam verbe si cuvinte comune, ramanem cu subiectul
    subject = text
    for noise in ("deschide", "notepad", "note pad", "browser", "in", "si", "scrie", "scri",
                   "linii", "lini", "de", "cod", "code", "python", "react", "html",
                   "despre", "write", "create", "creeaza", "program", "script",
                   "un", "o", "niste", "cateva", "10", "20", "5", "15", "fa"):
        subject = re.sub(r"\b" + re.escape(noise) + r"\b", "", subject)
    subject = re.sub(r"\s+", " ", subject).strip(" ,-.:;")
    if not subject:
        subject = "exemplu general"

    # Extragem numarul de linii cerut
    line_count_match = re.search(r"(\d+)\s*(?:linii|lini|lines|randuri)", text)
    num_lines = int(line_count_match.group(1)) if line_count_match else 10

    # Generam codul prin Ollama (prompt simplu, fara tools overhead)
    import requests
    try:
        from core.backends.ollama_backend import _get_ollama_host, _get_ollama_model
        from core.config import config
        host = "http://localhost:11434"
        model = config.get("ai.ollama.model", "qwen2.5-coder:7b")

        if is_code_request:
            if "react" in text.lower():
                gen_prompt = (
                    f"Scrie un script functional de React.js (sau HTML/JS cu React CDN) despre {subject}. "
                    f"Raspunde DOAR cu codul complet. FARA explicatii. FARA markdown. FARA backticks. FARA ``` sau ```html. "
                    f"Prima linie trebuie sa fie <!DOCTYPE html> sau <html. Gata de rulat in browser."
                )
            elif "html" in text.lower() or target_app == "browser":
                gen_prompt = (
                    f"Scrie un fisier HTML complet si profesional despre/pentru: {subject}. "
                    f"REGULI STRICTE:\n"
                    f"1. Raspunde DOAR cu codul HTML. Zero text in afara codului.\n"
                    f"2. FARA markdown. FARA backticks. FARA ``` sau ```html la inceput sau sfarsit.\n"
                    f"3. Prima linie trebuie sa fie exact: <!DOCTYPE html>\n"
                    f"4. Include CSS si JS inline. Design modern si profesional.\n"
                    f"5. Nu scrie nicio explicatie, niciun comentariu in afara codului."
                )
            else:
                gen_prompt = (
                    f"Scrie aproximativ {num_lines} linii de cod Python (sau ce limbaj ai fost rugat) despre {subject}. "
                    f"Doar codul, fara explicatii, fara markdown, fara backticks, fara ``` blocuri. "
                    f"Codul trebuie sa fie functional."
                )
        else:
            gen_prompt = (
                f"Scrie un text scurt (circa {num_lines} linii) despre {subject}. "
                f"Doar textul, fara formatare markdown."
            )

        # HTML/React au nevoie de mult mai multi tokeni decat Python
        is_html = "html" in text.lower() or target_app == "browser" or "react" in text.lower()
        gen_payload = {
            "model": model,
            "prompt": gen_prompt,
            "stream": False,
            "options": {
                "num_ctx": 4096 if is_html else 2048,
                "num_predict": 4096 if is_html else 1024,
                "temperature": 0.2,
            },
        }
        resp = requests.post(f"{host}/api/generate", json=gen_payload, timeout=300)
        resp.raise_for_status()
        generated_content = resp.json().get("response", "").strip()

        # Curatam agresiv orice markdown fencing pe care Qwen il adauga
        # Prinde: ```html, ```python, ```js, ``` fara lang, etc.
        generated_content = re.sub(r"^```[a-zA-Z]*\s*\n?", "", generated_content, flags=re.MULTILINE)
        generated_content = re.sub(r"\n?```\s*$", "", generated_content)
        # Daca modelul a adaugat text intro inainte de <!DOCTYPE
        if is_html:
            doctype_idx = generated_content.lower().find("<!doctype")
            if doctype_idx == -1:
                doctype_idx = generated_content.lower().find("<html")
            if doctype_idx > 0:
                # Taiem textul introductiv
                generated_content = generated_content[doctype_idx:]
        generated_content = generated_content.strip()

        if not generated_content:
            return None  # fallback la agentic loop

    except Exception as exc:
        logger.warning("Notepad write code generation failed: %s", exc)
        return None  # fallback la agentic loop

    # Scriem fisierul pe Desktop
    ext = ".txt"
    if is_code_request:
        if "react" in text.lower() or "html" in text.lower() or target_app == "browser":
            ext = ".html"
        else:
            ext = ".py"
            
    safe_subject = re.sub(r"[^a-zA-Z0-9_]", "_", subject)[:30].strip("_") or "script"
    filename = f"{safe_subject}{ext}"
    desktop_path = Path(os.path.expanduser("~")) / "Desktop" / filename

    try:
        desktop_path.write_text(generated_content, encoding="utf-8")
        logger.info("Wrote generated content to %s", desktop_path)
    except Exception as exc:
        logger.error("Failed to write file %s: %s", desktop_path, exc)
        return f"Am generat codul dar nu am putut salva fisierul: {exc}"

    # Deschidem cu aplicatia target
    try:
        reg = _get_tool_registry()
        available = set(getattr(reg, "_tools", {}).keys()) if reg is not None else set()
        
        if target_app == "browser":
            cmd = f'Start-Process "{desktop_path}"'
            app_display = "Browser"
        else:
            cmd = f'Start-Process notepad "{desktop_path}"'
            app_display = "Notepad"

        if reg is not None and "terminal" in available:
            result = reg.execute("terminal", operation="run", command=cmd, timeout=10)  # OS27 UNCENSORED MODE - No confirm
            if not result.is_success:
                logger.warning("Terminal open app failed: %s", result.error)
        else:
            import subprocess
            subprocess.Popen(["powershell", "-Command", cmd])
    except Exception as exc:
        logger.warning("Could not open %s: %s", target_app, exc)

    # Formatam raspunsul
    preview_lines = generated_content.split("\n")[:5]
    preview = "\n".join(preview_lines)
    total_lines = len(generated_content.split("\n"))

    return (
        f"Am scris scriptul / textul cerut despre '{subject}' in fisierul:\n"
        f"  {desktop_path}\n\n"
        f"{app_display} a fost deschis automat cu fisierul.\n\n"
        f"Preview (primele 5 linii):\n{preview}"
    )


def _maybe_handle_local_app_open_request(message: str) -> str | None:
    from core.backends.ollama_backend import _get_tool_registry, _resolve_desktop_lnk
    text = _normalize_text(message)
    wants_open = any(re.search(r"\b" + kw + r"\b", text) for kw in ("deschide", "porneste", "open", "start", "lanseaza"))
    if not wants_open:
        return None

    # [FIX OS-27] Prevent intercepting compound requests (like "deschide notepad si scrie cod").
    # If the user wants to write or save, we should let the LLM handle it
    # so it can use file_operations instead of just blindly opening the UI.
    if any(re.search(r"\b" + kw + r"\b", text) for kw in ("scrie", "scri", "write", "creeaza", "create", "salveaza", "save", "cod", "code", "script", "python", "lini", "linii", "fisier", "file")):
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
        "file explorer": "Start-Process explorer",
        "explorer": "Start-Process explorer",
        "folder": "Start-Process explorer",
    }
    selected = None
    for app_name, command in app_commands.items():
        if re.search(r"\b" + re.escape(app_name) + r"\b", text):
            selected = (app_name, command)
            break

    if not selected:
        # --- Cauta fuzzy un shortcut .lnk pe Desktop dupa cuvintele din mesaj ---
        # Extragem "substantivul" aplicatiei: cuvintele dupa verbul de deschidere
        open_verbs = ("deschide", "porneste", "porneste", "open", "start", "lanseaza", "lanseaza")
        remainder = text
        for verb in open_verbs:
            if re.search(r"\b" + re.escape(verb) + r"\b", remainder):
                remainder = re.split(r"\b" + re.escape(verb) + r"\b", remainder, 1)[-1].strip()
                break
        # Curata cuvinte comune: 'pe', 'de pe', 'desktop', 'iconita', 'icona', 'shortcut'
        stop_words = {"pe", "de", "pe desktop", "desktop", "iconita", "icona", "shortcut", "aplicatia", "aplicatia"}
        search_hint = remainder
        for sw in stop_words:
            search_hint = search_hint.replace(sw, " ")
        search_hint = re.sub(r"\s+", "", search_hint).strip()
        if len(search_hint) >= 2:
            resolved_path = _resolve_desktop_lnk(search_hint)
            if resolved_path:
                app_display = Path(resolved_path).stem
                selected = (app_display, f'Start-Process "{resolved_path}"')
                logger.info("Desktop LNK fuzzy match: hint=%s -> %s", search_hint, resolved_path)

    if not selected:
        return None

    try:
        reg = _get_tool_registry()
        available = set(getattr(reg, "_tools", {}).keys()) if reg is not None else set()
        if reg is None or "terminal" not in available:
            return f"As deschide {selected[0]}, dar toolul `terminal` nu este incarcat."
        logger.info("Local app open request handled deterministically.")
        result = reg.execute("terminal", operation="run", command=selected[1], timeout=15)  # OS27 UNCENSORED MODE - No confirm
        if result.is_success:
            return f"Am deschis {selected[0]} din terminal/cmd."
        return f"Nu am putut deschide {selected[0]}: {result.error or result.message}"
    except Exception as exc:
        return f"Eroare la deschiderea aplicatiei locale: {exc}"


# ---------------------------------------------------------------------------
# Weather handler — apel direct Python la open-meteo.com (fara curl, fara jq)
# ---------------------------------------------------------------------------

_WEATHER_CITIES: dict[str, tuple[float, float]] = {
    "bucuresti": (44.4268, 26.0963),
    "bucharest": (44.4268, 26.0963),
    "cluj": (46.7712, 23.6236),
    "timisoara": (45.7489, 21.2087),
    "iasi": (47.1585, 27.6014),
    "constanta": (44.1598, 28.6348),
    "brasov": (45.6427, 25.5887),
    "galati": (45.4353, 28.0080),
    "craiova": (44.3302, 23.7949),
    "ploiesti": (44.9369, 26.0226),
    "oradea": (47.0722, 21.9214),
    "sibiu": (45.7983, 24.1256),
    "pitesti": (44.8565, 24.8692),
    "arad": (46.1866, 21.3122),
    "bacau": (46.5670, 26.9146),
}

_WMO_CODES: dict[int, str] = {
    0: "cer senin", 1: "predominant senin", 2: "partial innnorat", 3: "acoperit",
    45: "ceata", 48: "ceata cu bruma", 51: "burna usoara", 53: "burna moderata",
    55: "burna intensa", 61: "ploaie slaba", 63: "ploaie moderata", 65: "ploaie abundenta",
    71: "ninsoare slaba", 73: "ninsoare moderata", 75: "ninsoare abundenta",
    77: "gresie", 80: "averse slabe", 81: "averse moderate", 82: "averse puternice",
    85: "ninsoare cu vant", 86: "viscol", 95: "furtuna", 96: "furtuna cu grindina",
    99: "furtuna intensa cu grindina",
}


def _maybe_handle_weather_request(message: str) -> str | None:
    """Handler deterministic: returneaza vremea curenta sau prognoza fara LLM.
    Apeleaza direct api.open-meteo.com via requests Python - fara curl, fara jq.
    """
    text = _normalize_text(message)

    # Detectare intent vreme
    weather_keywords = ("vreme", "vremea", "temperatura", "grad", "grade",
                        "ploua", "soare", "ninge", "frig", "cald", "forecast",
                        "meteo", "weather", "prognoza")
    if not any(kw in text for kw in weather_keywords):
        return None

    # Detectare oras
    city_key = None
    city_display = None
    for city, coords in _WEATHER_CITIES.items():
        if city in text:
            city_key = city
            city_display = city.title()
            lat, lon = coords
            break

    if city_key is None:
        # Fallback: Bucuresti daca nu e specificat
        city_key = "bucuresti"
        city_display = "Bucuresti"
        lat, lon = _WEATHER_CITIES["bucuresti"]

    # Detectare tip interogare: curenta vs prognoza maine/saptamana
    wants_tomorrow = any(kw in text for kw in ("maine", "tomorrow", "urmatoarea", "urmatoarele"))
    wants_week = any(kw in text for kw in ("saptamana", "week", "7 zile", "saptamanii"))

    try:
        import requests as _req
        if wants_tomorrow or wants_week:
            days = 7 if wants_week else 2
            url = (
                f"https://api.open-meteo.com/v1/forecast"
                f"?latitude={lat}&longitude={lon}"
                f"&daily=temperature_2m_max,temperature_2m_min,weathercode,precipitation_sum"
                f"&timezone=Europe/Bucharest&forecast_days={days}"
            )
            resp = _req.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            daily = data.get("daily", {})
            dates = daily.get("time", [])
            tmax = daily.get("temperature_2m_max", [])
            tmin = daily.get("temperature_2m_min", [])
            codes = daily.get("weathercode", [])
            precip = daily.get("precipitation_sum", [])

            lines = [f"Prognoza meteo {city_display}:"]
            start = 1 if wants_tomorrow and not wants_week else 0
            end = min(len(dates), days)
            for i in range(start, end):
                cond = _WMO_CODES.get(int(codes[i]) if codes[i] is not None else 0, "necunoscut")
                prec = f", precipitatii: {precip[i]:.1f}mm" if precip[i] else ""
                lines.append(
                    f"  {dates[i]}: {cond}, max {tmax[i]:.0f}°C / min {tmin[i]:.0f}°C{prec}"
                )
            return "\n".join(lines)
        else:
            # Vreme curenta
            url = (
                f"https://api.open-meteo.com/v1/forecast"
                f"?latitude={lat}&longitude={lon}"
                f"&current_weather=true&hourly=relativehumidity_2m,apparent_temperature"
                f"&timezone=Europe/Bucharest&forecast_days=1"
            )
            resp = _req.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            cw = data.get("current_weather", {})
            temp = cw.get("temperature", "N/A")
            wind = cw.get("windspeed", "N/A")
            wmo = int(cw.get("weathercode", 0))
            cond = _WMO_CODES.get(wmo, "necunoscut")
            # Umiditate la prima ora
            hourly = data.get("hourly", {})
            humidity_list = hourly.get("relativehumidity_2m", [])
            apparent_list = hourly.get("apparent_temperature", [])
            humidity = humidity_list[0] if humidity_list else "N/A"
            apparent = apparent_list[0] if apparent_list else "N/A"
            return (
                f"Vremea curenta in {city_display}:\n"
                f"  Temperatura: {temp} grade C (simtita: {apparent} grade C)\n"
                f"  Conditii: {cond}\n"
                f"  Vant: {wind} km/h\n"
                f"  Umiditate: {humidity}%\n"
                f"  (sursa: open-meteo.com)"
            )
    except Exception as exc:
        logger.warning("Weather API failed for %s: %s", city_display, exc)
        return f"Nu am putut obtine vremea pentru {city_display}: {exc}"


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
    from core.backends.ollama_backend import _get_tool_registry
    text = _normalize_text(message)
    wants_search = any(re.search(r"\b" + kw + r"\b", text) for kw in ("cauta", "search", "google", "web", "internet"))
    if not wants_search:
        return None
    if any(re.search(r"\b" + kw + r"\b", text) for kw in ("fisier", "folder", "cod", "code", "in proiect", "ana_dev")):
        return None

    query = _extract_search_query(message)
    if not query:
        return None

    # [FIX OS-27] Daca interogarea este foarte complexa (> 8 cuvinte) sau contine
    # instructiuni aditionale, o lasam pentru LLM pentru a o rula secvential.
    if len(query.split()) > 8:
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



def _maybe_handle_url_read(message: str) -> str | None:
    """Handler deterministic: citeste continut de la un URL si returneaza text scurt."""
    text = _normalize_text(message)

    url_triggers = ("citeste", "citeste site", "citeste url", "citeste pagina",
                    "deschide url", "read url", "fetch", "scrape")
    if not any(kw in text for kw in url_triggers):
        return None

    # Extrage URL din mesaj
    url_match = re.search(r"https?://[^\s\"']+", message)
    if not url_match:
        return None
    url = url_match.group(0).rstrip(".,;)")

    try:
        import requests as _req
        from html.parser import HTMLParser

        class _TextExtractor(HTMLParser):
            def __init__(self):
                super().__init__()
                self._text = []
                self._skip = False
            def handle_starttag(self, tag, attrs):
                if tag in ("script", "style", "nav", "header", "footer"):
                    self._skip = True
            def handle_endtag(self, tag):
                if tag in ("script", "style", "nav", "header", "footer"):
                    self._skip = False
            def handle_data(self, data):
                if not self._skip:
                    stripped = data.strip()
                    if stripped:
                        self._text.append(stripped)
            def get_text(self):
                return " ".join(self._text)

        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        resp = _req.get(url, timeout=15, headers=headers)
        resp.raise_for_status()
        parser = _TextExtractor()
        parser.feed(resp.text)
        raw_text = parser.get_text()
        # Comprima spatii si taie la 2000 chars
        compressed = re.sub(r"\s+", " ", raw_text).strip()[:2000]
        # Strip diacritice pentru compatibilitate ASCII (consola Windows)
        import unicodedata
        safe = unicodedata.normalize("NFKD", compressed).encode("ascii", errors="replace").decode("ascii")
        return f"Continut de la {url}:\n\n{safe}\n\n[extras primele 2000 caractere]"
    except Exception as exc:
        logger.warning("URL read failed for %s: %s", url, exc)
        return f"Nu am putut citi {url}: {exc}"


def _get_active_tool_count() -> int:
    """Returneaza numarul de tooluri incarcate in registry, daca este disponibil."""
    from core.backends.ollama_backend import _get_tool_registry
    try:
        reg = _get_tool_registry()
        tools = getattr(reg, "_tools", {}) if reg is not None else {}
        return len(tools)
    except Exception:
        return 0



def _tool_catalog() -> list[dict[str, Any]]:
    from core.backends.ollama_backend import _get_tool_registry
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
    asks_tool = any(re.search(r"\b" + kw + r"\b", text) for kw in ("tool", "tooluri", "unealta", "unelte", "instrumente", "instrument"))
    if not asks_tool:
        return None
    if any(re.search(r"\b" + kw + r"\b", text) for kw in ("ce zi", "data", "azi", "astazi", "ora", "presedinte", "cine esti")):
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



def _romania_now() -> datetime:
    """Return current timestamp in Romanian timezone (no globals loaded here)."""
    try:
        return datetime.now(ZoneInfo("Europe/Bucharest"))
    except Exception:
        # Fallback: UTC+2 (Romania standard) / UTC+3 (Romania summer DST)
        import time as _time
        _is_dst = bool(_time.localtime().tm_isdst)
        _offset = 3 if _is_dst else 2
        from datetime import timezone, timedelta
        return datetime.now(timezone(timedelta(hours=_offset)))



def _maybe_answer_current_facts(message: str, active_tool_count: int) -> str | None:
    """Raspuns determinist pentru intrebari curente unde modelul local tinde sa halucineze.

    Importuri LOCALE de constante (pentru a evita circular import intre
    ``ollama_backend`` si ``ollama_deterministic``).
    """
    from core.backends.ollama_backend import (
        _RO_WEEKDAYS,
        _ROMANIA_PRESIDENT,
        _ROMANIA_PRESIDENT_VERIFIED,
    )

    text = _normalize_text(message)
    asks_identity = bool(re.search(r'\bcine esti\b', text))
    asks_tools = bool(re.search(r'\b(tool|unelte)\b', text))
    asks_date = any(re.search(r'\b' + kw + r'\b', text) for kw in ("ce zi", "data", "azi", "astazi"))
    asks_time = any(re.search(r'\b' + kw + r'\b', text) for kw in ("ora", "cat este ceasul", "cat e ceasul"))
    asks_president = bool(re.search(r'\b(presedinte|presedintele)\b', text))

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
    """Determina daca un mesaj este conversatie simpla (fara nevoia de tools).

    REGULI (in ordinea prioritatii):
      1. Mesaj gol → chat simplu.
      2. Strip sufixe romanesti (-ul/-ului/-urile/-ele/-elor/-uri) pentru matching corect.
      3. Orice keyword tehnic/actiune gasit → NU e chat simplu (da-i tools).
      4. Orice intrebare tehnica (cum/de ce/cate + context) → NU e chat simplu.
      5. Fallback: daca textul e sub 80 caractere SI nu a fost prins → chat simplu.

    Pragul de lungime a fost redus de la 180 la 80 pentru a nu mai taia cereri
    tehnice scurte ca 'Afla cate fisiere am pe Desktop' (care are ~40 chars).
    """
    text = _normalize_text(message)
    if not text:
        return True

    # --- Helper: strip common Romanian noun suffixes for better keyword matching ---
    # "serverul" → "server", "ecranul" → "ecran", "fisierele" → "fisier"
    _RO_SUFFIXES = re.compile(
        r"\b(\w{3,?}?)(urilor|urile|ului|elor|ele|uri|ului|ilor|ul|ii|ei|ul)\b"
    )
    text_stemmed = _RO_SUFFIXES.sub(r"\1", text)

    # --- 1. Desktop automation keywords (check both original and stemmed) ---
    desktop_keywords = (
        "screenshot", "ocr", "ecran", "desktop", "capture", "captura",
        "click", "ui", "window", "fereastra", "pixel", "coordonate", "mouse",
    )
    for kw in desktop_keywords:
        if re.search(r"\b" + re.escape(kw), text) or re.search(r"\b" + re.escape(kw), text_stemmed):
            return False

    # --- 2. Action verbs & technical nouns (RO + EN) ---
    action_words = (
        # Verbe imperative RO
        "creeaza", "creaza", "scrie", "scri", "tasteaza", "sterge", "muta",
        "copiaza", "ruleaza", "deschide", "cauta", "executa", "testeaza",
        "repara", "modifica", "instaleaza", "dezinstaleaza", "descarca",
        "incarca", "porneste", "opreste", "lanseaza", "analizeaza",
        "scaneaza", "verifica", "arata", "afiseaza", "listeaza",
        "numara", "calculeaza", "compara", "converteste", "extrage",
        "comprima", "decomprima", "arhiveaza", "trimite", "salveaza",
        "redenumeste", "gaseste", "afla", "spune", "explica",
        "configureaza", "seteaza", "reseteaza", "activeaza", "dezactiveaza",
        "monitorizeaza", "inspecteza", "inspecteaza", "diagnosticheaza",
        "optimizeaza", "curata", "fa", "captura", "captureaza",
        # Verbe imperative RO — add-on (fix simple_chat false-positives)
        "goleste", "golire", "goliti", "goleasca",
        "inchide", "reporneste", "reboot", "restarteaza",
        "importa", "exporta",
        "conecteaza", "deconecteaza", "conecta", "deconecta",
        "blocheaza", "debloqueaza", "permite", "interzice",
        "ascunde", "elimina", "inlocuieste", "inlocuieste",
        "actualizeaza", "upgrade", "suspenda", "relua",
        "cripteaza", "decripteaza", "protejeaza",
        "monteaza", "demonteaza", "parcheaza", "compila",
        "restore", "partajeaza", "distribuie",
        # Verbe cu forme conjugate frecvente (compilez, compilare, merge etc.)
        "compilez", "compilare", "compileaza", "merge", "functioneaza",
        "pornesc", "rulez", "instalez", "downloadez",
        # Verbe imperative EN
        "create", "write", "delete", "move", "copy", "run", "open", "close",
        "search", "find", "execute", "test", "fix", "modify", "install",
        "download", "upload", "start", "stop", "launch", "analyze",
        "scan", "check", "show", "display", "list", "count", "compare",
        "convert", "extract", "compress", "send", "save", "rename",
        "build", "compile", "deploy", "debug", "profile", "benchmark",
        "grep", "awk", "sed", "curl", "wget", "ping", "nmap", "tracert",
        # Substantive tehnice RO
        "fisier", "fisiere", "folder", "director", "directoare",
        "proces", "procese", "pid", "task manager", "taskmanager",
        "partitie", "partitii", "drive", "disc",
        "retea", "ip", "port", "server", "client", "dns", "http", "https",
        "baza de date", "database", "sql", "tabel", "tabela",
        "script", "cod", "code", "program", "functie", "clasa", "modul",
        "eroare", "error", "bug", "crash", "log", "loguri",
        "registry", "serviciu", "service", "daemon",
        "memorie", "ram", "cpu", "gpu", "vram", "temperatura",
        "firewall", "antivirus", "permisiuni", "permission",
        # App-uri / tool-uri specifice
        "notepad", "note pad", "cmd", "powershell", "terminal",
        "browser", "brave", "chrome", "edge", "firefox",
        "python", "node", "npm", "pip", "git", "docker",
        "ollama", "qwen", "ana",
        # Aplicatii / stare sistem — FIX false-positive simple_chat
        "applicatii", "aplicatii", "aplicatie", "application", "applications",
        "merg", "running", "active", "activ", "activat",
        "capota", "background",
        "interfata", "interface", "dashboard", "api",
        # Tools / unelte — FIX: "cate tooluri ai active?" trebuie sa primeasca tools
        "tooluri", "tool", "tools", "unelte", "unealta",
        # Path patterns
        "c:", "d:", "e:",
    )
    # Check both original text and stemmed text for each keyword
    for kw in action_words:
        pattern = r"\b" + re.escape(kw) + r"\b"
        if re.search(pattern, text) or re.search(pattern, text_stemmed):
            return False

    # --- 3. Technical question patterns (RO) ---
    # "cate fisiere", "care procese", "unde este serverul", "cum fac sa compilez"
    tech_question_re = re.compile(
        r"\b(cate|cati|cat|care|unde|cum|de ce|ce fel|ce tip|ce versiune)"
        r"\s+"
        r"(fisier|folder|proces|serviciu|port|eroare|tool|script|program|"
        r"fisiere|foldere|procese|servicii|porturi|erori|tooluri|scripturi|programe|"
        r"linii|bytes|mb|gb|ram|cpu|gpu|spatiu|memorie|partiti|drive|disc|retea)",
        re.IGNORECASE,
    )
    if tech_question_re.search(text) or tech_question_re.search(text_stemmed):
        return False

    # --- 4. Broad RO question patterns (catch "cum fac sa X", "de ce nu merge") ---
    # These are almost always technical intent even without a tech noun following.
    broad_ro_question_re = re.compile(
        r"\b(cum\s+fac|cum\s+sa|cum\s+pot|cum\s+se|de\s+ce\s+nu|nu\s+mai\s+merge"
        r"|nu\s+functioneaza|nu\s+porneste|nu\s+ruleaza|nu\s+se\s+deschide)\b",
        re.IGNORECASE,
    )
    if broad_ro_question_re.search(text):
        return False

    # --- 5. English technical question patterns ---
    en_question_re = re.compile(
        r"\b(how many|how much|which|where|what|how to|how do i|why)"
        r"\s+"
        r"(file|folder|process|service|port|error|tool|script|program|"
        r"files|folders|processes|services|ports|errors|tools|scripts|programs|"
        r"lines|bytes|mb|gb|ram|cpu|gpu|space|memory|partition|drive|disk|network)",
        re.IGNORECASE,
    )
    if en_question_re.search(text):
        return False

    # --- 6. Fallback: very short messages with no technical signal → simple chat ---
    # Reduced from 180 to 80 to avoid cutting legitimate short technical requests.
    return len(text) < 80


def _detect_and_inject_skill(message: str) -> str:
    from core.backends.ollama_backend import _ANA_ROOT
    """Detecteaza daca mesajul se potriveste cu un skill din ana/skills/skills/ si returneaza instructiunile din SKILL.md."""
    text = _normalize_text(message)
    skill_name = None

    if any(re.search(r"\b" + re.escape(token) + r"\b", text) for token in ("repara", "repair", "cooperation", "self-repair", "self.repair")):
        skill_name = "self-repair"
    elif any(re.search(r"\b" + re.escape(token) + r"\b", text) for token in ("health", "check", "stare", "diagnostic", "healthcheck", "health-check", "health.check")):
        skill_name = "health-check"
    elif any(re.search(r"\b" + re.escape(token) + r"\b", text) for token in ("fs", "inspect", "inspecteaza", "filesystem", "path", "fs-inspect", "fs.inspect")):
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


def _condense_tool_result(res: str, max_len: int = 6000) -> str:
    """Condenseaza output-ul mare (ex: terminal, logs) la elementele critice.
    Daca rezultatul depaseste max_len, in loc de trunchere oarba, se pastreaza:
    - Primele 20 linii (context)
    - Orice linie care contine 'error', 'exception', 'traceback', 'fail', 'fatal'
    - Ultimele 20 linii (rezultat final/exit status)
    """
    if len(res) <= max_len:
        return res
        
    try:
        import json
        # Daca e un array JSON lung (ex: file_operations list_dir)
        data = json.loads(res)
        if isinstance(data, list) and len(data) > 30:
            condensed = data[:15] + [{"INFO": f"... alte {len(data)-30} elemente omise de OS pentru viteza LLM ...", "hint": "Foloseste utilitare mai specifice daca ai nevoie de lista completa"}] + data[-15:]
            return json.dumps(condensed, indent=2)
    except Exception:
        pass
        
    lines = res.splitlines()
    if len(lines) < 60:
        return res[:max_len//2] + "\n... [TRUNCHIAT DE OS] ...\n" + res[-max_len//2:]
        
    head = lines[:20]
    tail = lines[-20:]
    middle = lines[20:-20]
    
    crit_lines = []
    error_kws = ("error", "exception", "traceback", "fail", "fatal", "warn", "denied")
    for l in middle:
        if any(kw in l.lower() for kw in error_kws):
            crit_lines.append(l)
            
    # Daca am strans prea multe linii critice, si ele pot umple buffer-ul
    if len(crit_lines) > 50:
        crit_lines = crit_lines[:25] + ["... [multe erori similare omise] ..."] + crit_lines[-25:]
        
    condensed_lines = head + ["\n... [ANA OS CONDENSER: Linii de log normale omise, extrag doar contextul de eroare] ...\n"] + crit_lines + ["\n... [ANA OS CONDENSER: Sari la finalul executiei] ...\n"] + tail
    condensed = "\n".join(condensed_lines)
    
    if len(condensed) > max_len:
        # Fallback de siguranta extrema
        return condensed[:max_len//2] + "\n... [HARD-TRUNCATED] ...\n" + condensed[-max_len//2:]
    return condensed
