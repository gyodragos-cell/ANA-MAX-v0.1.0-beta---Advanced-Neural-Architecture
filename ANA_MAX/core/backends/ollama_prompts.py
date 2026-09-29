import json
import logging
from typing import Any
from core.backends.ollama_parser import _normalize_text

logger = logging.getLogger(__name__)

_TOOL_DESCRIPTIONS = {
    "terminal": (
        'terminal: executa comenzi PowerShell/CMD pe Windows.\n'
        '  ARGS: {"operation": "run", "command": "<powershell command>", "timeout": 30}'
    ),
    "file_operations": (
        'file_operations: operatii COMPLETE cu fisiere si directoare (PREFER PESTE TERMINAL).\n'
        '  Operatii: read, write, write_lines, write_base64, append, head, tail, grep, \n'
        '           delete, move, copy, rename, mkdir, exists, tree, stats, hash, \n'
        '           list, search, edit, find, info, diff_preview, surgical_edit, analyze, patch\n'
        '  GOLDEN RULE: Pentru orice operatie cu fisiere (sterge, muta, copiaza, creaza director)\n'
        '               foloseste file_operations, NU terminal. Zero quoting bugs.\n'
        '  ARGS: {"operation": "delete"|"move"|"copy"|"rename"|"mkdir"|"exists"|"tree"|\n'
        '                      "append"|"head"|"tail"|"grep"|"stats"|"hash"|\n'
        '                      "read"|"write"|"edit"|"find"|"info"|"list",\n'
        '         "path": "<cale absoluta>",\n'
        '         "destination": "<pentru move/copy/rename>",\n'
        '         "content": "<text pentru write/append>",\n'
        '         "pattern": "<regex pentru grep/search>",\n'
        '         "n_lines": 50,\n'
        '         "recursive": true}'
    ),
    "code_tools": (
        'code_tools: analizeaza sau ruleaza cod Python, creaza proiect.\n'
        '  ARGS: {"operation": "run_python"|"analyze_ast"|"create_project", "path": "<optional>"}'
    ),
    "web_search": (
        'web_search: cauta informatii sau documentatie pe internet (DuckDuckGo).\n'
        '  ARGS: {"query": "<termen cautare>", "max_results": 5}'
    ),
    "smart_search": (
        'smart_search: cauta pe internet si extrage textul complet din primul URL (mai lent dar exact).\n'
        '  ARGS: {"query": "<termen cautare>"}'
    ),
    "system_control": (
        'system_control: operatii speciale (goleste recycle bin, shut down, restart).\n'
        '  ARGS: {"action": "empty_recycle_bin"}'
    ),
    "ana_memory": (
        'ana_memory: scrie sau citeste memoria persistenta.\n'
        '  ARGS: {"action": "read"|"write"|"search", "key": "<cheie>", "value": "<valoare>"}'
    ),
    "browser_control": (
        'browser_control: deschide URL-uri sau interactioneaza cu browserul.\n'
        '  ARGS: {"operation": "open"|"screenshot", "url": "<url>"}'
    ),
    "uia_type": (
        'uia_type: scrie text intr-o aplicatie/fereastra Windows prin UI Automation.\n'
        '  ARGS: {"window_title": "<titlu partial, ex: Notepad>", "control_type": "Edit", "text": "<text de scris>"}'
    ),
    "window_manager": (
        'window_manager: listeaza sau focalizeaza ferestre Windows.\n'
        '  ARGS: {"action": "list"|"focus", "title": "<titlu partial>"}'
    ),
    "desktop_capture": (
        'desktop_capture: captura ecran sau ferestre.\n'
        '  ARGS: {"operation": "capture"|"capture_region"|"capture_window"|"get_windows"|"monitor", "window_title": "<optional>", "region": "<x,y,w,h optional>"}'
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
        '  ARGS: {"action": "list_windows"|"inspect_window"|"type_text", "window_title": "<titlu>", "control_type": "Edit", "text": "<text>"}'
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
    "windows_frida_telemetry": (
        'windows_frida_telemetry: Frida hooking pe procese Windows (CreateFile, CreateProcess, WriteProcessMemory, SendMessage etc.).\n'
        '  ARGS: {"action": "start"|"stop"|"get_events", "target": "<process name or PID>"}'
    ),
    "uia_click": (
        'uia_click: click pe elemente UI prin UI Automation (fara coordonate vizuale).\n'
        '  ARGS: {"window_title": "<titlu fereastra>", "element_title": "<nume element>", "control_type": "Button|MenuItem"}'
    ),
    "vision_region_capture": (
        'vision_region_capture: captureaza o regiune specifica a ecranului.\n'
        '  ARGS: {"action": "capture", "region": "<x,y,w,h>"}'
    ),
    "vision_find_element": (
        'vision_find_element: gaseste elemente vizuale pe ecran (buton, text, icon).\n'
        '  ARGS: {"query": "<descriere element>", "region": "<x,y,w,h optional>"}'
    ),
    "watchdog_bus": (
        'watchdog_bus: porneste/opreste magistrala centrala de evenimente (Event Bus).\n'
        '  ARGS: {"action": "start"|"stop"|"status"}'
    ),
    "ollama_live_logger": (
        'ollama_live_logger: tail live pe logurile serverului Ollama.\n'
        '  ARGS: {"action": "start"|"stop"}'
    ),
    "large_file_reader": (
        'large_file_reader: citeste fisiere MARI (cod, loguri, JSON) de pana la 10k+ linii fara sa consumi tot RAM-ul.\n'
        '  Foloseste INTOTDEAUNA large_file_reader in loc de file_operations read cand fisierul e > 200 linii.\n'
        '  ARGS: {"file_path": "<cale absoluta la fisier>",\n'
        '         "start_line": 1,\n'
        '         "chunk_size": 200,\n'
        '         "max_chunks": 5}\n'
        '  Exemplu: {"file_path": "C:\\\\Users\\\\billy\\\\Desktop\\\\ana-manus\\\\large_file_reader.py", "start_line": 1, "chunk_size": 300, "max_chunks": 3}'
    ),
}

_KEYWORD_TO_TOOLS: list[tuple[set[str], list[str]]] = [
    (
        {"fisier", "folder", "director", "directory", "script", "py", "python",
         "cod", "code", "creeaza", "creaza", "fa", "mkdir", "scrie",
         "salveaza", "save", "write", "read", "create", "file", "busola",
         "compass", "program", "aplicatie"},
        ["terminal", "file_operations", "code_tools"],
    ),
    (
        {"citeste", "citeste fisier", "deschide fisier", "open file", "read file",
         "large file", "fisier mare", "linii", "lines", "chunk", "log", "loguri",
         "vizualizeaza", "arata codul", "arata fisierul", "show file", "view file",
         "continut", "content", "pana la linia", "de la linia"},
        ["large_file_reader", "file_operations"],
    ),
    (
        {"terminal", "comanda", "command", "run", "ruleaza", "executa",
         "powershell", "cmd", "bash", "shell", "sistem", "process",
         "notepad", "note pad", "calculator", "calc"},
        ["terminal", "system_control"],
    ),
    (
        {"cos", "gunoi", "recycle", "bin", "goleste", "golire", "trash"},
        ["system_control"],
    ),
    (
        {"sterge", "delete", "sterg", "rm", "del", "erase",
         "muta", "move", "muta", "copiaza", "copy", "redenumeste", "rename",
         "mkdir", "creeaza director", "folder nou", "nou director"},
        ["file_operations", "terminal"],
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
         "citeste", "scrie", "scri", "tasteaza", "type", "notepad", "note pad",
         "posa", "descktop", "decktop", "fotografie", "imagine", "captureaza"},
        ["desktop_capture", "ocr_tool", "window_manager", "uia_type", "uia_click"],
    ),
    (
        {"click", "apas", "apasa", "buton", "button", "element", "ui", "control"},
        ["uia_click", "windows_uia_bridge"],
    ),
    (
        {"vision", "vizual", "gaseste", "find", "element", " regiune", "region"},
        ["vision_find_element", "vision_region_capture", "foreground_ui_snapshot"],
    ),
    (
        {"observa", "inspect", "snapshot", "situational", "workspace", "context"},
        ["workspace_situational_awareness", "foreground_ui_snapshot"],
    ),
    (
        {"voce", "vocal", "tts", "audio", "auzi", "aud", "spune", "vorbeste", "speak"},
        ["edge_tts_voice"],
    ),
]

_ALWAYS_TOOLS = ["terminal", "file_operations", "large_file_reader"]

def _select_tool_names(message: str) -> list[str]:
    lowered = message.lower()
    words = set(lowered.split())
    selected: list[str] = list(_ALWAYS_TOOLS)
    for keywords, tool_names in _KEYWORD_TO_TOOLS:
        matched = bool(keywords & words)
        if not matched:
            matched = any(kw in lowered and len(kw) >= 4 for kw in keywords)
        if matched:
            for t in tool_names:
                if t not in selected:
                    selected.append(t)
    return selected[:8]

def _router_mode_hint(message: str) -> str:
    text = _normalize_text(message)
    if any(ext in text for ext in (".log", ".txt", ".py", ".json", ".csv", ".xml", ".md", ".cfg", ".ini", ".bat")):
        return "file_analysis"
    if any(token in text for token in ("analizeaza", "rezumat", "citeste fisier", "continut fisier", "read file")):
        return "file_analysis"
    if any(token in text for token in ("notepad", "note pad", "fereastra", "ecran", "click", "tasteaza", "ocr", "screenshot", "porneste", "lanseaza", "iconita", "shortcut", "lnk", "xbox", "game", "poza", "posa", "desktop", "descktop")):
        return "ui_desktop"
    if any(token in text for token in ("proces", "procese", "frida", "watchdog", "runtime", "sub capota")):
        return "runtime_deep"
    if any(token in text for token in ("fisier", "file", "cod", "code", "patch", "test")):
        return "code_change"
    return "auto"

def _route_tool_names(message: str) -> list[str]:
    try:
        from core.backends.ollama_backend import _get_tool_registry
        reg = _get_tool_registry()
        if reg is None:
            return []
        mode = _router_mode_hint(message)
        result = reg.execute("tool_router", task=message, mode=mode, max_tools=12)
        if not result.is_success or not isinstance(result.data, dict):
            logger.warning("tool_router unavailable or failed: %s", result.error or result.message)
            return []
        recommended = [str(name).strip() for name in result.data.get("recommended_tools", []) if str(name).strip()]
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
        logger.info("tool_router recommendation: mode=%s recommended=%s selected=%s", result.data.get("mode", mode), recommended, compact[:12])
        return compact[:12]
    except Exception as exc:
        logger.warning("tool_router preflight failed: %s", exc)
        return []

def _build_tools_text(tool_names: list[str]) -> str:
    lines = ["UNELTE DISPONIBILE (foloseste ACTION+ARGS pentru a le apela):"]
    try:
        from core.backends.ollama_backend import _get_tool_registry
        reg = _get_tool_registry()
        tools = getattr(reg, "_tools", {}) if reg is not None else {}
    except Exception:
        tools = {}
    for name in tool_names:
        desc = _TOOL_DESCRIPTIONS.get(name)
        if desc:
            lines.append(f"\n- {desc}")
            continue
        tool = tools.get(name)
        if not tool:
            lines.append(f"\n- {name}: tool disponibil in ANA")
            continue
        try:
            definition = tool.get_definition()
            description = getattr(definition, "description", "").replace("\n", " ")
            params = getattr(definition, "parameters", []) or []
            args_example = {}
            for param in params:
                p_name = getattr(param, "name", "")
                p_desc = getattr(param, "description", "")
                p_type = getattr(param, "type", "string")
                choices = getattr(param, "choices", None)
                if choices:
                    args_example[p_name] = "|".join(str(c) for c in choices)
                else:
                    args_example[p_name] = f"<{p_desc or p_type}>"
            args_str = json.dumps(args_example, ensure_ascii=False)
            lines.append(f"\n- {name}: {description}\n  ARGS: {args_str}")
        except Exception:
            lines.append(f"\n- {name}: tool disponibil in ANA")
    return "\n".join(lines)

def _decorate_user_message(content: str, tool_names: list[str], is_result: bool = False) -> str:
    if not tool_names:
        return content
    tool_list_str = ", ".join(tool_names)
    PLAN_FIRST_RULES = """
=== REGULI OBLIGATORII (CITESTE INAINTE DE ORICE ACTIUNE) ===
1. PLAN FIRST: Inainte de prima actiune, scrie un <plan> scurt (max 3 pasi).
   Ex: <plan>1. Verific existenta. 2. Sterg cu file_operations. 3. Confirm.</plan>
2. NO REPEAT: Daca un tool a esuat, NU il apela din nou cu ACELEASI argumente.
   Incearca un alt tool sau alta abordare. Acelasi tool + aceleasi args = loop interzis.
3. ERROR RECOVERY: La eroare, citeste stderr/message si corecteaza argumentele.
4. PREFER file_operations: Pentru orice operatie cu fisiere (sterge, muta, copiaza,
   creeaza dir, citeste, scrie, append), foloseste INTOTDEAUNA file_operations, NU terminal.
   Terminal = doar pentru comenzi sistem (pornit procese, net, registry etc.)
5. VERIFY: Dupa write/delete/move, verifica cu file_operations exists sau stats.
6. MAX LOOPS: Nu executa mai mult de 6 actiuni pentru un task simplu.
   Daca nu ai reusit in 6 pasi, raporteaza blocajul utilizatorului in romana.
=== SFARSIT REGULI ===
"""
    if is_result:
        return (
            f"Rezultatele actiunilor tale anterioare:\n\n{content}\n\n"
            f"UNELTE PERMISE in continuare: [{tool_list_str}].\n"
            "Daca ai nevoie de o alta unealta, raspunde strict in formatul:\n"
            "ACTION: <nume_tool>\n"
            "ARGS: { ... }\n"
            "Altfel, daca task-ul este complet, raspunde direct cu un rezumat in romana.\n"
            "REMINDER: NU repeta acelasi tool cu aceleasi argumente daca a esuat deja."
        )
    else:
        return (
            f"{PLAN_FIRST_RULES}\n"
            f"Task utilizator: {content}\n\n"
            f"UNELTE DISPONIBILE pentru acest task: [{tool_list_str}].\n"
            "Raspunde strict in formatul:\n"
            "<plan>pasii tai</plan>\n"
            "ACTION: <nume_tool>\n"
            "ARGS: { ... }\n"
            "Sau, daca task-ul e simplu si nu necesita tool, raspunde direct in romana."
        )

def _is_read_only_request(message: str) -> bool:
    text = _normalize_text(message)
    read_only_verbs = ["citeste", "read", "arata", "show", "listeaza", "list", "vizualizeaza", "view", "cauta", "search", "find", "gaseste"]
    return any(text.startswith(verb) for verb in read_only_verbs)
