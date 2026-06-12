"""Dynamic ToolBridge prompt policy for ANA_MAX chat mode."""

from __future__ import annotations

import unicodedata
from typing import Iterable

from ANA_MAX.tools.tool_manifest_loader import get_tool_contracts


SCHEMA = "ana.os22.tool_prompt_policy.v1"


def _ascii_lower(value: object) -> str:
    return unicodedata.normalize("NFKD", str(value or "")).encode("ascii", errors="ignore").decode("ascii").lower()


def _has_any(text: str, words: Iterable[str]) -> bool:
    return any(word in text for word in words)


def select_tools_for_prompt(prompt: str) -> list[str]:
    """Return a deterministic, minimal tool set for the current prompt."""

    text = _ascii_lower(prompt)
    selected: set[str] = set()

    if _has_any(text, ("ce ora", "cat este ora", "ce zi", "ce data", "azi", "today", "current time")):
        selected.add("current_time")

    if _has_any(text, ("system info", "status sistem", "info sistem", "diagnostic local")):
        selected.add("system_info")

    if _has_any(text, ("sub capota", "overview sistem", "system overview", "hardware local", "full spec", "specificatii", "sistem de operare", "ce sistem", "hardware")):
        selected.add("system_overview")

    if _has_any(text, ("procese", "processes", "tasklist", "ce ruleaza", "ruleaza acum", "task manager")):
        selected.add("process_list")

    if _has_any(text, ("aplicatii instalate", "programe instalate", "ce am instalat", "installed apps")):
        selected.add("installed_apps")

    if _has_any(text, ("unde este", "gaseste aplicatia", "find app", "find_app")):
        selected.add("find_app")

    if "frida" in text:
        selected.add("frida_status")

    if _has_any(text, ("cat fac", "calculeaza", "calculate", "=", " x ", "*")) and any(ch.isdigit() for ch in text):
        selected.add("calculate_expression")

    if _has_any(text, ("calculator", "calc", "notepad", "paint", "brave", "chrome", "edge", "explorer")) and _has_any(text, ("deschide", "open", "porneste", "start")):
        selected.add("open_windows_app")

    if _has_any(text, ("http://", "https://")) and _has_any(text, ("brave", "chrome", "edge", "browser")) and _has_any(text, ("deschide", "open", "intra", "start")):
        selected.add("open_url_in_windows_app")

    if _has_any(text, ("screenshot", "poza la desktop", "poza desktop", "fa poza", "captureaza desktop")):
        selected.add("desktop_screenshot")

    if "desktop" in text and _has_any(
        text,
        (
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
        ),
    ):
        selected.add("desktop_list_items")

    if "desktop" in text and "folder" in text and _has_any(
        text,
        ("intra", "inspecteaza", "verifica", "continut", "inauntru", "acolo"),
    ):
        selected.add("desktop_inspect_folder")

    if "desktop" in text and _has_any(text, ("citeste", "read", "arata continut", "vezi continut")) and _has_any(text, ("fisier", "file", ".py", ".txt", ".md", ".json")):
        selected.add("desktop_read_text_file")

    if "desktop" in text and _has_any(text, ("salveaza", "save", "scrie", "write")) and _has_any(text, ("fisier", "file", "notite", "notes")):
        selected.add("desktop_write_text_file")

    if _has_any(text, ("open browser", "browser", "pagina web", "url", "http://", "https://")):
        selected.add("open_browser")

    if _has_any(text, ("cauta", "search")) and _has_any(text, ("browser", "brave", "chrome", "edge", "web", "internet", "google")):
        selected.add("browser_search_read")

    if _has_any(text, ("fetch", "web_fetch", "scrape", "web_scrape", "site", "pagina web", "http://", "https://")):
        selected.update({"web_fetch", "web_scrape"})

    if _has_any(text, ("http://", "https://")) and _has_any(
        text,
        (
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
        ),
    ):
        selected.add("web_learn_course")

    if _has_any(text, ("http://", "https://")) and _has_any(text, ("webscrape", "scrape", "extrage", "invata", "learn")) and _has_any(text, ("tot", "desktop", "salveaza")):
        selected.add("web_learn_course")

    if _has_any(text, ("http://", "https://")) and _has_any(text, ("invata", "learn", "citeste", "studiaza", "memoreaza", "retine", "important", "course", "curs")):
        selected.add("web_learn_url")

    if _has_any(text, ("citeste", "read file", "read_file", "fisier", "file")):
        selected.add("read_file")

    if _has_any(text, ("scrie", "write file", "write_file", "creeaza fisier", "editeaza fisier")):
        selected.add("write_file")

    if _has_any(text, ("desktop", "folder", "script python", "python script")) and _has_any(text, ("script", "py", "python", "creeaza", "fa un")):
        selected.add("desktop_create_python_script")

    if _has_any(text, ("cauta in memorie", "search memory", "vector_search", "rag search", "cauta rag")):
        selected.add("vector_search")

    if _has_any(text, ("salveaza in memorie", "tine minte", "memoreaza", "vector_store", "rag_store")):
        selected.update({"vector_store", "rag_store_text"})

    return sorted(selected)


def render_tool_specs(tool_names: Iterable[str]) -> str:
    names = {str(name).strip() for name in tool_names if str(name).strip()}
    if not names:
        return ""

    contracts = [
        tool for tool in get_tool_contracts()
        if str(tool.get("name", "")).strip() in names
    ]
    if not contracts:
        return ""

    lines = ["Available tools for this turn (emit TOOL_CALL only if needed):"]
    for tool in sorted(contracts, key=lambda item: str(item.get("name", ""))):
        args_schema = tool.get("args_schema", {})
        if isinstance(args_schema, dict) and args_schema:
            args_text = ", ".join(f"{key}: {value}" for key, value in args_schema.items())
        else:
            args_text = "no arguments"
        description = str(tool.get("description", "")).strip()
        category = str(tool.get("category", "")).strip()
        category_text = f" [{category}]" if category else ""
        lines.append(f"- {tool.get('name')}({args_text}){category_text} - {description}")
    return "\n".join(lines)


def get_tool_specs_for_prompt(prompt: str) -> str:
    return render_tool_specs(select_tools_for_prompt(prompt))


def summarize_tool_prompt_policy(prompt: str) -> dict[str, object]:
    tool_names = select_tools_for_prompt(prompt)
    return {
        "schema": SCHEMA,
        "prompt": str(prompt or ""),
        "tool_count": len(tool_names),
        "tools": tool_names,
        "tool_specs": render_tool_specs(tool_names),
    }
