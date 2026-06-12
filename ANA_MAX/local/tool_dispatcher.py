from __future__ import annotations

import json
import os
import platform
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from ANA_MAX.core.vector_memory import get_vector_memory
from ANA_MAX.local.tool_telemetry import log_tool_event
from ANA_MAX.tools.browser_search_tools import browser_search_read
from ANA_MAX.tools.desktop_workspace import (
    create_desktop_python_script,
    inspect_desktop_folder,
    list_desktop_items,
    read_desktop_text_file,
    write_desktop_text_file,
)
from ANA_MAX.tools.rag_store_text import rag_store_text
from ANA_MAX.tools.web_learning import web_learn_course, web_learn_url
from ANA_MAX.tools.web_scraper import web_scrape
from ANA_MAX.tools.windows_local_tools import (
    calculate_expression,
    capture_desktop_screenshot,
    dumps_result,
    find_app,
    frida_status,
    list_installed_apps,
    list_processes,
    open_url_in_windows_app,
    open_windows_app,
    system_overview,
)


ROOT = Path(__file__).resolve().parents[2]


def _ascii_text(value: Any) -> str:
    return str(value or "").encode("ascii", errors="replace").decode("ascii")


def _resolve_workspace_path(value: str | Path) -> Path:
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = ROOT / candidate
    resolved = candidate.resolve()
    workspace = ROOT.resolve()
    if resolved != workspace and workspace not in resolved.parents:
        raise ValueError(f"path_outside_workspace:{resolved}")
    return resolved


def parse_tool_call(text: str) -> tuple[str, dict[str, Any]]:
    normalized = str(text or "").strip()
    if not normalized.startswith("TOOL_CALL:"):
        raise ValueError(f"Invalid TOOL_CALL format: {text!r}")
    try:
        payload = normalized[len("TOOL_CALL:") :].strip()
    except ValueError as exc:
        raise ValueError(f"Invalid TOOL_CALL format: {text!r}") from exc

    if payload.startswith("{"):
        try:
            parsed_payload = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid TOOL_CALL JSON payload: {exc}") from exc
        if not isinstance(parsed_payload, dict):
            raise ValueError(f"TOOL_CALL payload must be an object: {text!r}")
        tool_name = str(
            parsed_payload.get("tool_name")
            or parsed_payload.get("name")
            or parsed_payload.get("tool")
            or ""
        ).strip()
        args = parsed_payload.get("args")
        if args is None:
            args = parsed_payload.get("arguments")
        if args is None:
            args = parsed_payload.get("params")
        if not tool_name:
            raise ValueError(f"Missing tool name in TOOL_CALL: {text!r}")
        if args is None:
            args = {}
        if not isinstance(args, dict):
            raise ValueError(f"TOOL_CALL args must be an object: {text!r}")
        return tool_name, args

    function_match = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_]*)\((.*)\)", payload)
    if function_match:
        tool_name = function_match.group(1).strip()
        raw_args = function_match.group(2).strip()
        if not raw_args:
            return tool_name, {}
        if raw_args.startswith("{") and raw_args.endswith("}"):
            try:
                parsed_args = json.loads(raw_args)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid TOOL_CALL JSON payload: {exc}") from exc
            if not isinstance(parsed_args, dict):
                raise ValueError(f"TOOL_CALL args must be an object: {text!r}")
            return tool_name, parsed_args
        try:
            parsed_value = json.loads(raw_args)
        except json.JSONDecodeError:
            parsed_value = raw_args.strip("\"'")
        first_arg_names = {
            "open_browser": "url",
            "browser_search_read": "query",
            "open_windows_app": "app_name",
            "find_app": "app_name",
            "installed_apps": "query",
            "process_list": "name_filter",
            "desktop_list_items": "max_items",
            "desktop_inspect_folder": "folder_name",
            "desktop_read_text_file": "file_name",
            "desktop_write_text_file": "file_name",
            "calculate_expression": "expression",
            "read_file": "path",
            "open_url_in_windows_app": "url",
            "web_fetch": "url",
            "web_learn_course": "start_url",
            "web_learn_url": "url",
            "web_scrape": "url",
            "vector_search": "query",
            "vector_store": "text",
        }
        arg_name = first_arg_names.get(tool_name, "value")
        return tool_name, {arg_name: parsed_value}

    try:
        header, json_payload = payload.split(" ", 1)
    except ValueError:
        if "{" in payload and payload.endswith("}"):
            header, json_payload = payload.split("{", 1)
            tool_name = header.strip()
            if not tool_name:
                raise ValueError(f"Missing tool name in TOOL_CALL: {text!r}")
            try:
                args = json.loads("{" + json_payload)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid TOOL_CALL JSON payload: {exc}") from exc
            if not isinstance(args, dict):
                raise ValueError(f"TOOL_CALL args must be an object: {text!r}")
            return tool_name, args
        tool_name = payload.strip()
        if not tool_name:
            raise ValueError(f"Missing tool name in TOOL_CALL: {text!r}")
        return tool_name, {}

    tool_name = header.strip()
    if not tool_name:
        raise ValueError(f"Missing tool name in TOOL_CALL: {text!r}")

    try:
        args = json.loads(json_payload)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid TOOL_CALL JSON payload: {exc}") from exc
    if not isinstance(args, dict):
        raise ValueError(f"TOOL_CALL args must be an object: {text!r}")
    return tool_name, args


def _result_text(result: Any) -> str:
    if result is None:
        return ""
    if isinstance(result, str):
        return result
    if isinstance(result, Mapping):
        for key in ("message", "error", "text", "data"):
            value = result.get(key)
            if isinstance(value, str):
                return value
            if isinstance(value, (dict, list)):
                try:
                    return json.dumps(value, ensure_ascii=True, sort_keys=True)
                except Exception:
                    return _ascii_text(value)
        try:
            return json.dumps(dict(result), ensure_ascii=True, sort_keys=True)
        except Exception:
            return _ascii_text(result)
    return _ascii_text(result)


def execute_tool(tool_name: str, args: dict[str, Any]) -> str:
    tool = str(tool_name or "").strip()
    normalized_args = dict(args or {})
    start = time.perf_counter()
    status = "success"
    result_text = ""

    try:
        if tool == "read_file":
            path = _resolve_workspace_path(normalized_args["path"])
            result_text = path.read_text(encoding="utf-8", errors="ignore")

        elif tool == "write_file":
            path = _resolve_workspace_path(normalized_args["path"])
            content = str(normalized_args.get("content", ""))
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            result_text = f"[write_file] wrote {len(content)} bytes to {path}"

        elif tool == "open_browser":
            from ANA_MAX.tools import BrowserControlTool

            url = str(normalized_args["url"]).strip()
            visible = bool(normalized_args.get("visible", True))
            new_session = bool(normalized_args.get("new_session", False))
            wait_seconds = int(normalized_args.get("wait_seconds", 3) or 3)
            result = BrowserControlTool().execute(
                operation="open",
                url=url,
                visible=visible,
                new_session=new_session,
                wait_seconds=wait_seconds,
            )
            result_text = _result_text(getattr(result, "data", None) or getattr(result, "message", None) or result)

        elif tool == "web_fetch":
            from ANA_MAX.tools import WebFetchTool

            url = str(normalized_args["url"]).strip()
            timeout = int(normalized_args.get("timeout", 30) or 30)
            max_chars = int(normalized_args.get("max_chars", 8000) or 8000)
            result = WebFetchTool().execute(url=url, timeout=timeout, max_chars=max_chars)
            result_text = _result_text(getattr(result, "data", None) or getattr(result, "message", None) or result)

        elif tool == "web_scrape":
            result = web_scrape(
                url=str(normalized_args["url"]).strip(),
                max_chars=int(normalized_args.get("max_chars", 8000) or 8000),
                timeout=int(normalized_args.get("timeout", 30) or 30),
            )
            result_text = json.dumps(result, ensure_ascii=True, sort_keys=True)

        elif tool == "web_learn_url":
            result = web_learn_url(
                url=str(normalized_args.get("url", "")).strip(),
                source_label=str(normalized_args.get("source_label", "")).strip(),
                max_chars=int(normalized_args.get("max_chars", 12000) or 12000),
                chunk_size=int(normalized_args.get("chunk_size", 1200) or 1200),
                chunk_overlap=int(normalized_args.get("chunk_overlap", 100) or 100),
                timeout=int(normalized_args.get("timeout", 30) or 30),
            )
            result_text = json.dumps(result, ensure_ascii=True, sort_keys=True)

        elif tool == "web_learn_course":
            result = web_learn_course(
                start_url=str(normalized_args.get("start_url", "")).strip(),
                source_label=str(normalized_args.get("source_label", "")).strip(),
                max_pages=int(normalized_args.get("max_pages", 8) or 8),
                max_depth=int(normalized_args.get("max_depth", 2) or 2),
                same_domain=bool(normalized_args.get("same_domain", True)),
                max_chars_per_page=int(normalized_args.get("max_chars_per_page", 10000) or 10000),
                chunk_size=int(normalized_args.get("chunk_size", 1200) or 1200),
                chunk_overlap=int(normalized_args.get("chunk_overlap", 100) or 100),
                timeout=int(normalized_args.get("timeout", 30) or 30),
            )
            result_text = json.dumps(result, ensure_ascii=True, sort_keys=True)

        elif tool == "browser_search_read":
            result = browser_search_read(
                query=str(normalized_args.get("query", "")).strip(),
                browser=str(normalized_args.get("browser", "brave")).strip() or "brave",
                engine=str(normalized_args.get("engine", "bing")).strip() or "bing",
                max_chars=int(normalized_args.get("max_chars", 4000) or 4000),
                timeout=int(normalized_args.get("timeout", 20) or 20),
            )
            result_text = json.dumps(result, ensure_ascii=True, sort_keys=True)

        elif tool == "vector_search":
            query = str(normalized_args["query"]).strip()
            top_k = int(normalized_args.get("top_k", 5) or 5)
            memory_type = normalized_args.get("memory_type")
            tags = normalized_args.get("tags")
            min_importance = float(normalized_args.get("min_importance", 0.0) or 0.0)
            results = get_vector_memory().search(
                query,
                top_k=top_k,
                memory_type=memory_type if isinstance(memory_type, str) and memory_type else None,
                tags=tags,
                min_importance=min_importance,
            )
            result_text = json.dumps(results, ensure_ascii=True, sort_keys=True)

        elif tool == "vector_store":
            text = str(normalized_args["text"]).strip()
            memory_type = str(normalized_args.get("memory_type", "semantic")).strip() or "semantic"
            tags = normalized_args.get("tags")
            importance = float(normalized_args.get("importance", 0.5) or 0.5)
            memory_id = get_vector_memory().store(
                text,
                memory_type=memory_type,
                tags=tags,
                importance=importance,
            )
            result_text = f"[vector_store] stored {memory_id}"

        elif tool == "rag_store_text":
            result = rag_store_text(
                text=str(normalized_args["text"]),
                source=str(normalized_args["source"]),
                chunk_size=int(normalized_args.get("chunk_size", 1200) or 1200),
                chunk_overlap=int(normalized_args.get("chunk_overlap", 100) or 100),
            )
            result_text = json.dumps(result, ensure_ascii=True, sort_keys=True)

        elif tool == "desktop_create_python_script":
            result = create_desktop_python_script(
                folder_name=str(normalized_args.get("folder_name", "ANA_MAX")),
                script_name=str(normalized_args.get("script_name", "binoclu")),
                content=normalized_args.get("content") if "content" in normalized_args else None,
            )
            result_text = json.dumps(result, ensure_ascii=True, sort_keys=True)

        elif tool == "desktop_list_items":
            result = list_desktop_items(
                max_items=int(normalized_args.get("max_items", 200) or 200),
                include_hidden=bool(normalized_args.get("include_hidden", False)),
            )
            result_text = json.dumps(result, ensure_ascii=True, sort_keys=True)

        elif tool == "desktop_inspect_folder":
            result = inspect_desktop_folder(
                folder_name=str(normalized_args.get("folder_name", "")),
                max_items=int(normalized_args.get("max_items", 200) or 200),
                include_hidden=bool(normalized_args.get("include_hidden", False)),
            )
            result_text = json.dumps(result, ensure_ascii=True, sort_keys=True)

        elif tool == "desktop_read_text_file":
            result = read_desktop_text_file(
                file_name=str(normalized_args.get("file_name", "")),
                folder_name=str(normalized_args.get("folder_name", "")),
                max_chars=int(normalized_args.get("max_chars", 6000) or 6000),
            )
            result_text = json.dumps(result, ensure_ascii=True, sort_keys=True)

        elif tool == "desktop_write_text_file":
            result = write_desktop_text_file(
                file_name=str(normalized_args.get("file_name", "")),
                folder_name=str(normalized_args.get("folder_name", "")),
                content=str(normalized_args.get("content", "")),
            )
            result_text = json.dumps(result, ensure_ascii=True, sort_keys=True)

        elif tool == "open_windows_app":
            result_text = dumps_result(open_windows_app(str(normalized_args.get("app_name", "calculator"))))

        elif tool == "open_url_in_windows_app":
            result_text = dumps_result(
                open_url_in_windows_app(
                    str(normalized_args.get("app_name", "brave") or "brave"),
                    str(normalized_args.get("url", "")).strip(),
                )
            )

        elif tool == "find_app":
            result_text = dumps_result(find_app(str(normalized_args.get("app_name", ""))))

        elif tool == "process_list":
            result_text = dumps_result(
                list_processes(
                    name_filter=normalized_args.get("name_filter"),
                    max_items=int(normalized_args.get("max_items", 50) or 50),
                )
            )

        elif tool == "installed_apps":
            result_text = dumps_result(
                list_installed_apps(
                    query=normalized_args.get("query"),
                    max_items=int(normalized_args.get("max_items", 50) or 50),
                )
            )

        elif tool == "system_overview":
            result_text = dumps_result(system_overview())

        elif tool == "frida_status":
            result_text = dumps_result(frida_status())

        elif tool == "desktop_screenshot":
            result_text = dumps_result(capture_desktop_screenshot())

        elif tool == "calculate_expression":
            result_text = dumps_result(calculate_expression(str(normalized_args.get("expression", ""))))

        elif tool == "system_info":
            result_text = json.dumps(
                {
                    "schema": "ana.local.tool_bridge.system_info.v1",
                    "metadata_only": True,
                    "local_only": True,
                    "platform": platform.platform(),
                    "python": platform.python_version(),
                    "cwd": str(Path.cwd()),
                    "workspace_root": str(ROOT),
                    "os": os.name,
                },
                ensure_ascii=True,
                sort_keys=True,
            )

        elif tool == "current_time":
            now = datetime.now().astimezone()
            result_text = json.dumps(
                {
                    "schema": "ana.local.tool_bridge.current_time.v1",
                    "metadata_only": True,
                    "local_only": True,
                    "iso": now.isoformat(timespec="seconds"),
                    "date": now.date().isoformat(),
                    "time": now.time().isoformat(timespec="seconds"),
                    "weekday": now.strftime("%A"),
                    "timezone": now.tzname() or "",
                    "utc_offset_seconds": int(now.utcoffset().total_seconds()) if now.utcoffset() else 0,
                },
                ensure_ascii=True,
                sort_keys=True,
            )

        else:
            status = "error"
            result_text = f"[tool_dispatcher] unknown tool: {tool}"

    except Exception as exc:
        status = "error"
        result_text = f"[tool_dispatcher] error: {_ascii_text(exc)}"

    duration_ms = (time.perf_counter() - start) * 1000.0
    log_tool_event(tool, normalized_args, result_text, duration_ms, status=status)
    return result_text
