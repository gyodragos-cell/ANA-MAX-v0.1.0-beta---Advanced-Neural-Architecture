from __future__ import annotations

import json
import re
import unicodedata
from typing import Any

from ANA_MAX.local.tool_dispatcher import execute_tool


SCHEMA = "ana.os22.operator_intent_router.v1"


def _ascii_text(value: Any) -> str:
    return unicodedata.normalize("NFKD", str(value or "")).encode("ascii", errors="ignore").decode("ascii")


def _contains_all(text: str, tokens: tuple[str, ...]) -> bool:
    return all(token in text for token in tokens)


def _extract_script_name(text: str) -> str:
    patterns = (
        r"script\s+(?:numit|numele|cu\s+numele)\s+([A-Za-z0-9_.-]+)",
        r"script(?:\s+in)?\s+python\s+([A-Za-z0-9_.-]+)",
        r"script(?:\s+in)?\s+py\s+([A-Za-z0-9_.-]+)",
        r"python\s+([A-Za-z0-9_.-]+)",
        r"\bpy\s+([A-Za-z0-9_.-]+)",
        r"script\s+([A-Za-z0-9_.-]+)",
    )
    stop_words = {"mic", "simplu", "small", "simple", "py", "python", "in"}
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            candidate = match.group(1).strip(". ")
            if candidate and candidate not in stop_words:
                return candidate
    return "script"


def _extract_folder_name(text: str) -> str:
    if "numele tau" in text or "numele vostru" in text:
        return "ANA_MAX"
    patterns = (
        r"folder(?:ul)?(?:\s+pe\s+desktop)?\s+(?:cu\s+)?(?:numele|numit)\s+([A-Za-z0-9_. -]+?)(?:\s+si\b|,|\.|$)",
        r"folder(?:ul)?\s+([A-Za-z0-9_.-]+)(?:\s+pe\s+desktop)?(?:\s+si\b|,|\.|$)",
    )
    stop_words = {"pe", "desktop", "cu", "numele", "numit", "si", "un", "o", "mic", "script"}
    for pattern in patterns:
        match = re.search(pattern, text)
        if not match:
            continue
        candidate = " ".join(match.group(1).strip(" .").split())
        if candidate and candidate not in stop_words:
            return candidate
    return "ANA_MAX"


def _desktop_python_script_intent(prompt: str) -> dict[str, Any] | None:
    text = _ascii_text(prompt).lower()
    if not _contains_all(text, ("desktop", "folder", "script")):
        return None
    if not any(marker in text for marker in ("fa", "creeaza", "creaza", "adauga", "pune", "scrie", "make", "create")):
        return None
    if "python" not in text and ".py" not in text and not re.search(r"\bpy\b", text):
        return None
    folder_name = _extract_folder_name(text)
    script_name = _extract_script_name(text)
    tool_args = {"folder_name": folder_name, "script_name": script_name}
    raw_result = execute_tool("desktop_create_python_script", tool_args)
    try:
        payload = json.loads(raw_result)
    except json.JSONDecodeError:
        payload = {"success": False, "error": raw_result}
    if payload.get("success"):
        text_result = (
            "Am creat pe Desktop folderul si scriptul Python cerut: "
            f"{payload.get('script_path', '')}"
        )
    else:
        text_result = f"Nu am putut crea scriptul: {payload.get('error', raw_result)}"
    return {
        "schema": SCHEMA,
        "handled": True,
        "kind": "desktop_python_script",
        "tool_name": "desktop_create_python_script",
        "tool_args": tool_args,
        "tool_result": payload,
        "text": text_result,
    }


def _extract_desktop_file_name(text: str) -> str:
    patterns = (
        r"fisier(?:ul)?\s+([A-Za-z0-9_. -]+\.[A-Za-z0-9]+)",
        r"file\s+([A-Za-z0-9_. -]+\.[A-Za-z0-9]+)",
        r"citeste\s+([A-Za-z0-9_. -]+\.[A-Za-z0-9]+)",
        r"read\s+([A-Za-z0-9_. -]+\.[A-Za-z0-9]+)",
    )
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return " ".join(match.group(1).strip(" .").split())
    return ""


def _extract_desktop_file_folder(text: str) -> str:
    patterns = (
        r"folder(?:ul)?\s+([A-Za-z0-9_. -]+?)\s+(?:de\s+)?pe\s+desktop",
        r"din\s+([A-Za-z0-9_. -]+?)\s+(?:de\s+)?pe\s+desktop",
    )
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return " ".join(match.group(1).strip(" .").split())
    return ""


def _desktop_read_text_file_intent(prompt: str) -> dict[str, Any] | None:
    text = _ascii_text(prompt).lower()
    if "desktop" not in text:
        return None
    if not any(marker in text for marker in ("citeste", "read", "arata continut", "vezi continut")):
        return None
    file_name = _extract_desktop_file_name(text)
    if not file_name:
        return None
    folder_name = _extract_desktop_file_folder(text)
    tool_args = {"folder_name": folder_name, "file_name": file_name, "max_chars": 6000}
    raw_result = execute_tool("desktop_read_text_file", tool_args)
    try:
        payload = json.loads(raw_result)
    except json.JSONDecodeError:
        payload = {"success": False, "error": raw_result, "text": "", "file_name": file_name}
    if payload.get("success"):
        text_preview = _ascii_text(payload.get("text", "")).strip()
        if len(text_preview) > 1600:
            text_preview = text_preview[:1600].rsplit(" ", 1)[0].strip() + "..."
        suffix = " Continutul a fost scurtat." if payload.get("truncated") else ""
        text_result = f"Am citit `{payload.get('file_name', file_name)}` de pe Desktop.{suffix}\n{text_preview}"
    else:
        text_result = f"Nu am putut citi fisierul Desktop `{file_name}`: {payload.get('error', raw_result)}"
    return {
        "schema": SCHEMA,
        "handled": True,
        "kind": "desktop_read_text_file",
        "tool_name": "desktop_read_text_file",
        "tool_args": tool_args,
        "tool_result": payload,
        "text": text_result,
    }


def _format_desktop_items(payload: dict[str, Any]) -> str:
    items = payload.get("items") if isinstance(payload.get("items"), list) else []
    preview = []
    for item in items[:20]:
        if not isinstance(item, dict):
            continue
        marker = "[D]" if item.get("type") == "directory" else "[F]" if item.get("type") == "file" else "[?]"
        name = _ascii_text(item.get("name", "")).strip()
        if name:
            preview.append(f"{marker} {name}")
    if not preview:
        return "Nu am gasit elemente vizibile pe Desktop."
    suffix = " Lista a fost scurtata." if payload.get("truncated") else ""
    return (
        f"Pe Desktop am gasit {payload.get('count', len(items))} elemente vizibile. "
        f"Primele: {', '.join(preview)}.{suffix} "
        "Detaliile complete sunt in tool_result: desktop_list_items."
    )


def _extract_desktop_folder_inspection_name(text: str) -> str:
    patterns = (
        r"folder(?:ul)?\s+([A-Za-z0-9_. -]+?)\s+(?:de\s+)?pe\s+desktop",
        r"(?:din|in|inspecteaza|verifica|listeaza)\s+folder(?:ul)?\s+([A-Za-z0-9_. -]+?)(?:\s+si\b|\s+de\b|,|\.|$)",
        r"desktop\s+folder(?:ul)?\s+([A-Za-z0-9_. -]+?)(?:\s+si\b|,|\.|$)",
    )
    stop_words = {"pe", "desktop", "folder", "folderul", "si", "ce", "este", "e", "acolo"}
    for pattern in patterns:
        match = re.search(pattern, text)
        if not match:
            continue
        candidate = " ".join(match.group(1).strip(" .").split())
        if candidate and candidate not in stop_words:
            return candidate
    return _extract_folder_name(text)


def _format_desktop_folder_items(payload: dict[str, Any]) -> str:
    items = payload.get("items") if isinstance(payload.get("items"), list) else []
    preview = []
    for item in items[:20]:
        if not isinstance(item, dict):
            continue
        marker = "[D]" if item.get("type") == "directory" else "[F]" if item.get("type") == "file" else "[?]"
        name = _ascii_text(item.get("name", "")).strip()
        if name:
            preview.append(f"{marker} {name}")
    folder_name = _ascii_text(payload.get("folder_name", "")).strip()
    if not preview:
        return f"Folderul Desktop `{folder_name}` exista, dar nu am gasit elemente vizibile in el."
    suffix = " Lista a fost scurtata." if payload.get("truncated") else ""
    return (
        f"Am inspectat folderul Desktop `{folder_name}` si am gasit {payload.get('count', len(items))} elemente vizibile. "
        f"Primele: {', '.join(preview)}.{suffix} "
        "Detaliile complete sunt in tool_result: desktop_inspect_folder."
    )


def _desktop_folder_inspection_intent(prompt: str) -> dict[str, Any] | None:
    text = _ascii_text(prompt).lower()
    if "desktop" not in text or "folder" not in text:
        return None
    wants_inspection = any(
        marker in text
        for marker in (
            "intra",
            "inspecteaza",
            "verifica",
            "listeaza",
            "ce e",
            "ce este",
            "arata",
            "vezi",
            "continut",
            "inauntru",
            "acolo",
        )
    )
    if not wants_inspection:
        return None
    if "script" in text and any(marker in text for marker in ("fa", "creeaza", "scrie")):
        return None
    folder_name = _extract_desktop_folder_inspection_name(text)
    tool_args = {"folder_name": folder_name, "max_items": 80, "include_hidden": False}
    raw_result = execute_tool("desktop_inspect_folder", tool_args)
    try:
        payload = json.loads(raw_result)
    except json.JSONDecodeError:
        payload = {"success": False, "error": raw_result, "items": [], "folder_name": folder_name}
    if payload.get("success"):
        text_result = _format_desktop_folder_items(payload)
    else:
        text_result = f"Nu am putut inspecta folderul Desktop `{folder_name}`: {payload.get('error', raw_result)}"
    return {
        "schema": SCHEMA,
        "handled": True,
        "kind": "desktop_inspect_folder",
        "tool_name": "desktop_inspect_folder",
        "tool_args": tool_args,
        "tool_result": payload,
        "text": text_result,
    }


def _desktop_inventory_intent(prompt: str) -> dict[str, Any] | None:
    text = _ascii_text(prompt).lower()
    if "desktop" not in text:
        return None
    wants_inventory = any(
        marker in text
        for marker in (
            "listeaza",
            "lista",
            "ce am",
            "ce este",
            "ce e",
            "arata",
            "vezi",
            "fisiere",
            "foldere",
            "items",
            "files",
        )
    )
    if not wants_inventory:
        return None
    tool_args = {"max_items": 80, "include_hidden": False}
    raw_result = execute_tool("desktop_list_items", tool_args)
    try:
        payload = json.loads(raw_result)
    except json.JSONDecodeError:
        payload = {"success": False, "error": raw_result, "items": []}
    if payload.get("success"):
        text_result = _format_desktop_items(payload)
    else:
        text_result = f"Nu am putut lista Desktop-ul: {payload.get('error', raw_result)}"
    return {
        "schema": SCHEMA,
        "handled": True,
        "kind": "desktop_list_items",
        "tool_name": "desktop_list_items",
        "tool_args": tool_args,
        "tool_result": payload,
        "text": text_result,
    }


def _open_calculator_intent(prompt: str) -> dict[str, Any] | None:
    text = _ascii_text(prompt).lower()
    if not ("calculator" in text or "calc" in text):
        return None
    if not any(marker in text for marker in ("deschide", "porneste", "open", "start")):
        return None
    raw_result = execute_tool("open_windows_app", {"app_name": "calculator"})
    try:
        payload = json.loads(raw_result)
    except json.JSONDecodeError:
        payload = {"success": False, "error": raw_result}
    if payload.get("success"):
        text_result = "Am deschis Calculatorul din Windows."
    else:
        text_result = f"Nu am putut deschide Calculatorul: {payload.get('error', raw_result)}"
    return {
        "schema": SCHEMA,
        "handled": True,
        "kind": "open_calculator",
        "tool_name": "open_windows_app",
        "tool_args": {"app_name": "calculator"},
        "tool_result": payload,
        "text": text_result,
    }


def _open_named_app_intent(prompt: str) -> dict[str, Any] | None:
    text = _ascii_text(prompt).lower()
    if not any(marker in text for marker in ("deschide", "porneste", "open", "start")):
        return None
    app_markers = (
        ("brave", ("brave",)),
        ("chrome", ("chrome", "google chrome")),
        ("edge", ("edge", "microsoft edge")),
        ("notepad", ("notepad", "notes")),
        ("paint", ("paint", "mspaint")),
        ("explorer", ("explorer", "file explorer")),
    )
    app_name = ""
    for candidate, markers in app_markers:
        if any(marker in text for marker in markers):
            app_name = candidate
            break
    if not app_name:
        return None
    raw_result = execute_tool("open_windows_app", {"app_name": app_name})
    try:
        payload = json.loads(raw_result)
    except json.JSONDecodeError:
        payload = {"success": False, "error": raw_result}
    display_name = {
        "brave": "Brave",
        "chrome": "Google Chrome",
        "edge": "Microsoft Edge",
        "notepad": "Notepad",
        "paint": "Paint",
        "explorer": "File Explorer",
    }.get(app_name, app_name)
    if payload.get("success"):
        text_result = f"Am deschis {display_name}."
    else:
        text_result = f"Nu am putut deschide {display_name}: {payload.get('error', raw_result)}"
    return {
        "schema": SCHEMA,
        "handled": True,
        "kind": f"open_{app_name}",
        "tool_name": "open_windows_app",
        "tool_args": {"app_name": app_name},
        "tool_result": payload,
        "text": text_result,
    }


def _extract_web_search_query(text: str) -> str:
    patterns = (
        r"\bcauta(?:\s+pe\s+(?:web|internet|google|browser|brave|chrome|edge))?\s+(.+)$",
        r"\bsearch(?:\s+for)?\s+(.+)$",
    )
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            query = match.group(1).strip(" .?!")
            query = re.sub(r"\b(si\s+)?(?:citeste|spune-mi|arata-mi|read)\b.*$", "", query).strip(" .?!")
            return query
    return ""


def _browser_from_prompt(text: str) -> str:
    if "chrome" in text:
        return "chrome"
    if "edge" in text:
        return "edge"
    return "brave"


def _search_engine_from_prompt(text: str) -> str:
    if "google" in text:
        return "google"
    if "duckduckgo" in text or "duck duck go" in text:
        return "duckduckgo"
    return "bing"


def _browser_search_read_intent(prompt: str) -> dict[str, Any] | None:
    text = _ascii_text(prompt).lower()
    if not any(marker in text for marker in ("cauta", "search")):
        return None
    if not any(marker in text for marker in ("browser", "brave", "chrome", "edge", "web", "internet", "google")):
        return None
    query = _extract_web_search_query(text)
    if not query:
        return None
    browser = _browser_from_prompt(text)
    tool_args = {
        "query": query,
        "browser": browser,
        "engine": _search_engine_from_prompt(text),
        "max_chars": 3500,
    }
    raw_result = execute_tool("browser_search_read", tool_args)
    try:
        payload = json.loads(raw_result)
    except json.JSONDecodeError:
        payload = {"success": False, "error": raw_result, "summary": ""}
    browser_name = {"brave": "Brave", "chrome": "Google Chrome", "edge": "Microsoft Edge"}.get(browser, browser)
    if payload.get("success"):
        summary = str(payload.get("summary", "")).strip()
        if summary:
            text_result = f"Am deschis {browser_name}, am cautat `{query}` si am citit pagina. Pe scurt: {summary}"
        else:
            text_result = f"Am deschis {browser_name} si am cautat `{query}`, dar scraperul nu a extras text util din pagina."
    else:
        text_result = f"Nu am putut cauta si citi `{query}`: {payload.get('error', raw_result)}"
    return {
        "schema": SCHEMA,
        "handled": True,
        "kind": "browser_search_read",
        "tool_name": "browser_search_read",
        "tool_args": tool_args,
        "tool_result": payload,
        "text": text_result,
    }


def _extract_first_url(text: str) -> str:
    match = re.search(r"https?://[^\s`\"']+", text)
    if not match:
        return ""
    return match.group(0).rstrip(".,);]")


def _web_learn_url_intent(prompt: str) -> dict[str, Any] | None:
    text = _ascii_text(prompt).lower()
    url = _extract_first_url(text)
    if not url:
        return None
    wants_learning = any(
        marker in text
        for marker in (
            "invata",
            "learn",
            "citeste",
            "studiaza",
            "memoreaza",
            "retine",
            "important",
            "course",
            "curs",
        )
    )
    if not wants_learning:
        return None
    tool_args = {
        "url": url,
        "source_label": f"web_learning:{url}",
        "max_chars": 12000,
        "chunk_size": 1200,
        "chunk_overlap": 100,
    }
    raw_result = execute_tool("web_learn_url", tool_args)
    try:
        payload = json.loads(raw_result)
    except json.JSONDecodeError:
        payload = {"success": False, "error": raw_result, "summary": "", "stored_count": 0}
    if payload.get("success"):
        summary = _ascii_text(payload.get("summary", "")).strip()
        text_result = (
            f"Am citit linkul si am invatat continutul in RAG: {payload.get('stored_count', 0)} chunkuri salvate. "
            f"Pe scurt: {summary}"
        )
    else:
        text_result = f"Nu am putut invata linkul `{url}`: {payload.get('error', raw_result)}"
    return {
        "schema": SCHEMA,
        "handled": True,
        "kind": "web_learn_url",
        "tool_name": "web_learn_url",
        "tool_args": tool_args,
        "tool_result": payload,
        "text": text_result,
    }


def _web_learn_course_intent(prompt: str) -> dict[str, Any] | None:
    text = _ascii_text(prompt).lower()
    url = _extract_first_url(text)
    if not url:
        return None
    wants_learning = any(
        marker in text
        for marker in (
            "invata",
            "learn",
            "studiaza",
            "memoreaza",
            "retine",
            "important",
        )
    )
    wants_course = any(
        marker in text
        for marker in (
            "tot cursul",
            "cursul",
            "the course",
            "all course",
            "entire course",
            "whole course",
            "paginile interne",
            "toate paginile",
            "site-ul",
            "siteul",
            "multi-page",
        )
    )
    if not (wants_learning and wants_course):
        return None
    tool_args = {
        "start_url": url,
        "source_label": f"course_learning:{url}",
        "max_pages": 8,
        "max_depth": 2,
        "same_domain": True,
        "max_chars_per_page": 10000,
        "chunk_size": 1200,
        "chunk_overlap": 100,
    }
    raw_result = execute_tool("web_learn_course", tool_args)
    try:
        payload = json.loads(raw_result)
    except json.JSONDecodeError:
        payload = {"success": False, "error": raw_result, "summary": "", "stored_count": 0, "page_count": 0}
    if payload.get("success"):
        summary = _ascii_text(payload.get("summary", "")).strip()
        page_count = int(payload.get("page_count", 0) or 0)
        page_label = "pagina" if page_count == 1 else "pagini"
        text_result = (
            f"Am invatat cursul din {page_count} {page_label} si am salvat "
            f"{payload.get('stored_count', 0)} chunkuri in RAG."
        )
        if summary:
            text_result += f" Pe scurt: {summary}"
    else:
        text_result = f"Nu am putut invata cursul `{url}`: {payload.get('error', raw_result)}"
    return {
        "schema": SCHEMA,
        "handled": True,
        "kind": "web_learn_course",
        "tool_name": "web_learn_course",
        "tool_args": tool_args,
        "tool_result": payload,
        "text": text_result,
    }


def _extract_desktop_report_name(text: str, url: str) -> str:
    match = re.search(r"(?:numele|numit|fisier(?:ul)?(?: cu numele)?)\s+([a-zA-Z0-9_.-]+)", text)
    if match:
        return match.group(1).strip(" .")
    parsed = re.sub(r"[^a-zA-Z0-9]+", "_", url.strip("/").split("/")[-1] or "web_course")
    return parsed.strip("_") or "web_course"


def _course_report_text(url: str, payload: dict[str, Any]) -> str:
    learned_urls = payload.get("learned_urls") if isinstance(payload.get("learned_urls"), list) else []
    pages = payload.get("pages") if isinstance(payload.get("pages"), list) else []
    lines = [
        "# ANA_MAX Web Course Notes",
        "",
        f"Source: {url}",
        f"Pages learned: {payload.get('page_count', 0)}",
        f"RAG chunks stored: {payload.get('stored_count', 0)}",
        "",
        "## Summary",
        _ascii_text(payload.get("summary", "")).strip() or "No summary extracted.",
        "",
        "## Page notes",
    ]
    if pages:
        for page in pages[:50]:
            if not isinstance(page, dict):
                continue
            lines.append(f"- {_ascii_text(page.get('url', ''))}: {_ascii_text(page.get('summary', '')).strip()}")
    else:
        lines.append("- No per-page summaries available.")
    lines.extend(
        [
            "",
            "## Learned URLs",
        ]
    )
    for item in learned_urls[:50]:
        lines.append(f"- {_ascii_text(item)}")
    return "\n".join(lines).strip() + "\n"


def _browser_from_prompt_for_open(text: str) -> str:
    if "brave" in text:
        return "brave"
    if "chrome" in text or "google" in text:
        return "chrome"
    if "edge" in text:
        return "edge"
    return "brave"


def _web_course_extract_save_learn_intent(prompt: str) -> dict[str, Any] | None:
    text = _ascii_text(prompt).lower()
    url = _extract_first_url(text)
    if not url:
        return None
    wants_course = any(marker in text for marker in ("tot", "curs", "course", "paginile interne", "site-ul", "siteul"))
    wants_save = "desktop" in text and any(marker in text for marker in ("salveaza", "save", "fisier", "file"))
    wants_extract = any(marker in text for marker in ("webscrape", "scrape", "extrage", "citeste", "invata", "learn"))
    if not (wants_course and wants_save and wants_extract):
        return None

    browser_args = {"app_name": _browser_from_prompt_for_open(text), "url": url}
    browser_raw = execute_tool("open_url_in_windows_app", browser_args)
    try:
        browser_payload = json.loads(browser_raw)
    except json.JSONDecodeError:
        browser_payload = {"success": False, "error": browser_raw}

    course_args = {
        "start_url": url,
        "source_label": f"course_learning:{url}",
        "max_pages": 12,
        "max_depth": 2,
        "same_domain": True,
        "max_chars_per_page": 10000,
        "chunk_size": 1200,
        "chunk_overlap": 100,
    }
    course_raw = execute_tool("web_learn_course", course_args)
    try:
        course_payload = json.loads(course_raw)
    except json.JSONDecodeError:
        course_payload = {"success": False, "error": course_raw, "summary": "", "page_count": 0, "stored_count": 0}

    report_name = _extract_desktop_report_name(text, url)
    report_content = _course_report_text(url, course_payload)
    save_args = {"file_name": report_name, "content": report_content}
    save_raw = execute_tool("desktop_write_text_file", save_args)
    try:
        save_payload = json.loads(save_raw)
    except json.JSONDecodeError:
        save_payload = {"success": False, "error": save_raw, "file_path": ""}

    if course_payload.get("success") and save_payload.get("success"):
        text_result = (
            f"Am deschis {browser_args['app_name']}, am extras cursul din "
            f"{course_payload.get('page_count', 0)} pagini, am salvat notitele in "
            f"{save_payload.get('file_path', '')} si am memorat "
            f"{course_payload.get('stored_count', 0)} chunkuri in RAG."
        )
    else:
        text_result = (
            "Pipeline-ul web course nu a fost complet: "
            f"course_error={course_payload.get('error', '')}; save_error={save_payload.get('error', '')}."
        )

    return {
        "schema": SCHEMA,
        "handled": True,
        "kind": "web_course_extract_save_learn",
        "tool_name": "open_url_in_windows_app+web_learn_course+desktop_write_text_file",
        "tool_args": {
            "browser": browser_args,
            "course": course_args,
            "save": save_args,
        },
        "tool_result": {
            "browser": browser_payload,
            "course": course_payload,
            "save": save_payload,
        },
        "text": text_result,
    }


def _desktop_screenshot_and_calculator_intent(prompt: str) -> dict[str, Any] | None:
    text = _ascii_text(prompt).lower()
    wants_screenshot = any(marker in text for marker in ("poza", "screenshot", "captureaza"))
    wants_calculator = "calculator" in text or "calc" in text
    if not (wants_screenshot and wants_calculator):
        return None
    screenshot_raw = execute_tool("desktop_screenshot", {})
    app_raw = execute_tool("open_windows_app", {"app_name": "calculator"})
    try:
        screenshot = json.loads(screenshot_raw)
    except json.JSONDecodeError:
        screenshot = {"success": False, "error": screenshot_raw}
    try:
        app = json.loads(app_raw)
    except json.JSONDecodeError:
        app = {"success": False, "error": app_raw}
    parts = []
    if screenshot.get("success"):
        parts.append(f"am facut screenshot: {screenshot.get('path', '')}")
    else:
        parts.append(f"screenshot nereusit: {screenshot.get('error', screenshot_raw)}")
    if app.get("success"):
        parts.append("am deschis Calculatorul")
    else:
        parts.append(f"Calculator nedeschis: {app.get('error', app_raw)}")
    return {
        "schema": SCHEMA,
        "handled": True,
        "kind": "desktop_screenshot_and_calculator",
        "tool_name": "desktop_screenshot+open_windows_app",
        "tool_args": {},
        "tool_result": {"screenshot": screenshot, "app": app},
        "text": "Gata: " + "; ".join(parts) + ".",
    }


def _gb(value: Any) -> str:
    try:
        number = float(value or 0)
    except (TypeError, ValueError):
        number = 0
    if number <= 0:
        return "n/a"
    return f"{number / (1024 ** 3):.1f} GB"


def _format_full_system_report(overview: dict[str, Any], process_payload: dict[str, Any]) -> str:
    os_info = overview.get("os") if isinstance(overview.get("os"), dict) else {}
    computer = overview.get("computer") if isinstance(overview.get("computer"), dict) else {}
    cpu = overview.get("cpu") if isinstance(overview.get("cpu"), dict) else {}
    memory = overview.get("memory") if isinstance(overview.get("memory"), dict) else {}
    disks = overview.get("disks") if isinstance(overview.get("disks"), list) else []
    gpus = overview.get("gpus") if isinstance(overview.get("gpus"), list) else []
    processes = process_payload.get("processes") if isinstance(process_payload.get("processes"), list) else []

    disk_text = "n/a"
    if disks and isinstance(disks[0], dict):
        first_disk = disks[0]
        disk_text = (
            f"{first_disk.get('drive', '')} "
            f"{_gb(first_disk.get('free_bytes'))} liber / {_gb(first_disk.get('total_bytes'))} total"
        )
    gpu_names = [str(gpu.get("Name", "")).strip() for gpu in gpus if isinstance(gpu, dict) and str(gpu.get("Name", "")).strip()]
    process_names = [
        f"{item.get('image_name')}({item.get('pid')})"
        for item in processes[:12]
        if isinstance(item, dict) and item.get("image_name")
    ]

    return "\n".join(
        [
            "Raport local sub capota:",
            f"- OS: {os_info.get('name', overview.get('platform', ''))} {os_info.get('version', '')} build {os_info.get('build', '')} {os_info.get('architecture', '')}".strip(),
            f"- PC: {computer.get('manufacturer', '')} {computer.get('model', '')} ({computer.get('name', '')})".strip(),
            f"- CPU: {cpu.get('name', overview.get('processor', ''))} | cores={cpu.get('cores', 0)} | logical={cpu.get('logical_processors', overview.get('cpu_count', 0))}",
            f"- RAM: {_gb(memory.get('available_physical_bytes'))} liber / {_gb(memory.get('total_physical_bytes'))} total | load={memory.get('memory_load_percent', 'n/a')}%",
            f"- Disk: {disk_text}",
            f"- GPU: {', '.join(gpu_names[:3]) if gpu_names else 'n/a'}",
            f"- Procese Task Manager: {process_payload.get('count', len(processes))} afisate. Primele: {', '.join(process_names) if process_names else 'n/a'}",
            "Detaliile complete sunt in tool_result: system_overview + process_list.",
        ]
    )


def _full_system_report_intent(prompt: str) -> dict[str, Any] | None:
    text = _ascii_text(prompt).lower()
    wants_specs = any(
        marker in text
        for marker in (
            "full spec",
            "specificatii",
            "specificatii pc",
            "spec pc",
            "sistem de operare",
            "ce sistem",
            "sub capota",
            "task manager",
            "hardware",
        )
    )
    if not wants_specs:
        return None
    overview_raw = execute_tool("system_overview", {})
    processes_raw = execute_tool("process_list", {"max_items": 30})
    try:
        overview = json.loads(overview_raw)
    except json.JSONDecodeError:
        overview = {"success": False, "error": overview_raw}
    try:
        processes = json.loads(processes_raw)
    except json.JSONDecodeError:
        processes = {"success": False, "error": processes_raw, "processes": []}
    return {
        "schema": SCHEMA,
        "handled": True,
        "kind": "full_system_report",
        "tool_name": "system_overview+process_list",
        "tool_args": {"process_max_items": 30},
        "tool_result": {"system_overview": overview, "process_list": processes},
        "text": _format_full_system_report(overview, processes),
    }


def _process_inventory_intent(prompt: str) -> dict[str, Any] | None:
    text = _ascii_text(prompt).lower()
    if not any(marker in text for marker in ("procese", "processes", "tasklist", "ce ruleaza", "ruleaza acum")):
        return None
    raw_result = execute_tool("process_list", {"max_items": 20})
    try:
        payload = json.loads(raw_result)
    except json.JSONDecodeError:
        payload = {"success": False, "error": raw_result, "processes": []}
    processes = payload.get("processes") if isinstance(payload.get("processes"), list) else []
    names = [str(item.get("image_name", "")) for item in processes if isinstance(item, dict)]
    preview = ", ".join(name for name in names[:10] if name)
    text_result = (
        f"Am gasit {payload.get('count', len(processes))} procese locale."
        + (f" Primele: {preview}." if preview else "")
    )
    return {
        "schema": SCHEMA,
        "handled": True,
        "kind": "process_list",
        "tool_name": "process_list",
        "tool_args": {"max_items": 20},
        "tool_result": payload,
        "text": text_result,
    }


def _installed_apps_intent(prompt: str) -> dict[str, Any] | None:
    text = _ascii_text(prompt).lower()
    if not any(marker in text for marker in ("aplicatii instalate", "programe instalate", "ce am instalat", "installed apps")):
        return None
    raw_result = execute_tool("installed_apps", {"max_items": 20})
    try:
        payload = json.loads(raw_result)
    except json.JSONDecodeError:
        payload = {"success": False, "error": raw_result, "apps": []}
    apps = payload.get("apps") if isinstance(payload.get("apps"), list) else []
    names = [str(item.get("name", "")) for item in apps if isinstance(item, dict)]
    preview = ", ".join(name for name in names[:10] if name)
    text_result = (
        f"Am gasit {payload.get('count', len(apps))} aplicatii instalate in inventarul local."
        + (f" Primele: {preview}." if preview else "")
    )
    return {
        "schema": SCHEMA,
        "handled": True,
        "kind": "installed_apps",
        "tool_name": "installed_apps",
        "tool_args": {"max_items": 20},
        "tool_result": payload,
        "text": text_result,
    }


def _frida_status_intent(prompt: str) -> dict[str, Any] | None:
    text = _ascii_text(prompt).lower()
    if "frida" not in text:
        return None
    raw_result = execute_tool("frida_status", {})
    try:
        payload = json.loads(raw_result)
    except json.JSONDecodeError:
        payload = {"success": False, "error": raw_result}
    if payload.get("available"):
        text_result = f"Frida este disponibil local. Versiune: {payload.get('version', '')}. Modul curent este status-only."
    else:
        text_result = "Frida nu este disponibil ca modul Python local sau nu este incarcat in acest env."
    return {
        "schema": SCHEMA,
        "handled": True,
        "kind": "frida_status",
        "tool_name": "frida_status",
        "tool_args": {},
        "tool_result": payload,
        "text": text_result,
    }


def _simple_math_intent(prompt: str) -> dict[str, Any] | None:
    text = _ascii_text(prompt).lower()
    if not any(marker in text for marker in ("cat fac", "calculeaza", "calculate", "=")):
        return None
    if not any(char.isdigit() for char in text):
        return None
    raw_result = execute_tool("calculate_expression", {"expression": text})
    try:
        payload = json.loads(raw_result)
    except json.JSONDecodeError:
        payload = {"success": False, "error": raw_result}
    if not payload.get("success"):
        return None
    return {
        "schema": SCHEMA,
        "handled": True,
        "kind": "simple_math",
        "tool_name": "calculate_expression",
        "tool_args": {"expression": text},
        "tool_result": payload,
        "text": f"Rezultatul este {payload.get('result')}.",
    }


def route_operator_intent(prompt: str) -> dict[str, Any]:
    for detector in (
        _web_course_extract_save_learn_intent,
        _desktop_read_text_file_intent,
        _desktop_python_script_intent,
        _desktop_folder_inspection_intent,
        _desktop_inventory_intent,
        _desktop_screenshot_and_calculator_intent,
        _web_learn_course_intent,
        _web_learn_url_intent,
        _browser_search_read_intent,
        _full_system_report_intent,
        _open_named_app_intent,
        _open_calculator_intent,
        _process_inventory_intent,
        _installed_apps_intent,
        _frida_status_intent,
        _simple_math_intent,
    ):
        result = detector(prompt)
        if result is not None:
            return result
    return {
        "schema": SCHEMA,
        "handled": False,
        "kind": "unhandled",
        "text": "",
    }
