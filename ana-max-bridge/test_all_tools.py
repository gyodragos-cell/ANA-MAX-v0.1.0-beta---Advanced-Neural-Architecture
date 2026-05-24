"""Safe ANA MAX bridge tool tester.

Runs a non-destructive smoke test of tools exposed by ana-max-bridge.
Runtime reports are written outside the repo by default.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Tuple

import requests


DEFAULT_BRIDGE_URL = "http://127.0.0.1:8790"
DEFAULT_OUTPUT_DIR = Path(os.environ.get("TEMP", ".")) / "ana-max-tool-test"

SKIP_REASONS: Dict[str, str] = {
    "advanced_scanner": "security scanner; skipped in safe mode",
    "apk_analyzer": "requires an APK path; skipped in safe mode",
    "autonomous_engine": "autonomous execution; skipped in safe mode",
    "desktop_capture": "may capture private screen content; skipped in safe mode",
    "desktop_control": "premium/destructive desktop control; skipped in safe mode",
    "edit": "can modify files; skipped in safe mode",
    "file_patch": "can modify files; skipped in safe mode",
    "foreground_ui_snapshot": "may expose private foreground UI content; skipped in safe mode",
    "frida_instrument": "dynamic instrumentation; requires explicit target authorization",
    "hardware_scanner": "hardware/network scanner; skipped in safe mode",
    "live_desktop_viewer": "premium live desktop stream; skipped in safe mode",
    "mitm_analyzer": "traffic inspection workflow; skipped in safe mode",
    "network_pentest": "pentest workflow; skipped in safe mode",
    "ocr_tool": "may read private screen or image content; skipped in safe mode",
    "security_audit": "may scan secrets; skipped in safe mode",
    "science_research": "requires dataset/model inputs; skipped in safe mode",
    "swarm_orchestrator": "multi-agent execution; skipped in safe mode",
    "system_optimization": "can change system state; skipped in safe mode",
    "uia_click": "desktop click action; skipped in safe mode",
    "uia_type": "desktop typing action; skipped in safe mode",
    "vision_fallback": "vision GUI control; skipped in safe mode",
    "vision_find_element": "requires template image and may inspect screen; skipped in safe mode",
    "vision_region_capture": "captures screen region; skipped in safe mode",
    "web_ai_bridge": "external AI provider request; skipped in safe mode",
    "web_search": "external web request; skipped in safe mode",
    "windows_deep_sight": "premium/deep Windows monitoring; skipped in safe mode",
    "windows_insight": "premium Windows monitoring; skipped in safe mode",
    "windows_uia_bridge": "may expose private window structure; skipped in safe mode",
}

SAFE_PARAMS: Dict[str, Dict[str, Any]] = {
    "adal_integration": {"operation": "version"},
    "adb_operations": {"operation": "devices", "timeout": 5},
    "ana_identity": {},
    "ana_memory": {"action": "stats"},
    "ana_orchestrator": {"action": "status"},
    "bash_exec": {"command": "echo ana-max-test", "timeout": 10},
    "browser_control": {"operation": "open_external", "url": "http://127.0.0.1:8790/health"},
    "clipboard_manager": {"action": "get"},
    "code_search": {"operation": "grep", "pattern": "ANA MAX", "path": ".", "max_results": 5},
    "code_tools": {"operation": "analyze", "target": "main.py"},
    "codebase_understanding": {"action": "analyze", "project_path": "."},
    "context_bridge": {"action": "status"},
    "context_engine": {"action": "get_context"},
    "conversation_learning": {"action": "recent", "limit": 5},
    "debugger": {"action": "analyze", "traceback_text": "ValueError: test"},
    "edge_tts_voice": {"action": "status"},
    "error_radar": {"scope": "quick"},
    "event_stream": {"action": "stats"},
    "file_operations": {"operation": "list", "path": "."},
    "git_operations": {"operation": "status"},
    "glob_search": {"pattern": "*.md", "dir_path": ".", "limit": 10},
    "grep_content": {"regex": "ANA MAX", "search_path": ".", "glob": "*.md", "limit": 5},
    "grep_file": {"regex": "ANA MAX", "search_path": ".", "glob": "*.md", "limit": 5},
    "memory_cortex": {"action": "status"},
    "network_diag": {"operation": "ping", "target": "127.0.0.1"},
    "privacy_shield": {"operation": "scan", "text": "Contact test@example.com"},
    "proactive_interrupt": {"action": "status"},
    "project_navigator": {"operation": "list", "path": ".", "limit": 10},
    "qa_testing": {"operation": "edge_case_analysis", "target": "def add(a, b): return a + b"},
    "remote_control": {"action": "list"},
    "self_evolving_tool": {"action": "status"},
    "session_log_miner": {"action": "analyze", "path": "README.md", "limit": 5},
    "smart_search": {"action": "search", "query": "ANA MAX", "project_path": "."},
    "system_control": {"operation": "vitals"},
    "task": {"task": "Return a one step status plan", "plan_only": True, "max_steps": 1},
    "terminal": {"operation": "session_info"},
    "todowrite": {"operation": "list", "session_id": "bridge-test"},
    "tool_healthcheck": {"scope": "safe"},
    "vector_memory": {"action": "stats"},
    "web_fetch": {"url": "http://127.0.0.1:8790/health", "timeout": 10, "max_chars": 1000},
    "web_scraper": {"operation": "parse", "html": "<html><title>ana-max-test</title></html>"},
    "window_manager": {"action": "list"},
    "workspace_situational_awareness": {"path": ".", "max_files": 10},
}


def fetch_tools(bridge_url: str, timeout: int) -> list[dict[str, Any]]:
    response = requests.get(f"{bridge_url}/tools/list", timeout=timeout)
    response.raise_for_status()
    payload = response.json()
    return list(payload.get("tools", []))


def fallback_params(schema: dict[str, Any]) -> dict[str, Any]:
    params: dict[str, Any] = {}
    properties = schema.get("properties", {}) if isinstance(schema, dict) else {}
    for key, spec in properties.items():
        if not isinstance(spec, dict) or not spec.get("required", False):
            continue
        choices = spec.get("choices")
        default = spec.get("default")
        value_type = spec.get("type")
        if choices:
            params[key] = choices[0]
        elif default is not None:
            params[key] = default
        elif value_type == "integer":
            params[key] = 0
        elif value_type == "boolean":
            params[key] = False
        elif value_type == "number":
            params[key] = 0
        elif value_type in {"object", "dict"}:
            params[key] = {}
        elif value_type == "array":
            params[key] = []
        else:
            params[key] = ""
    return params


def params_for(tool: dict[str, Any]) -> dict[str, Any]:
    name = str(tool.get("name", ""))
    if name in SAFE_PARAMS:
        return dict(SAFE_PARAMS[name])
    return fallback_params(tool.get("input_schema", {}))


def classify_response(http_status: int, payload: Any, skipped: bool = False) -> Tuple[str, str]:
    if skipped:
        return "WARN", "skipped by safe-mode policy"
    if http_status != 200:
        return "FAIL", f"HTTP {http_status}"
    if not isinstance(payload, dict):
        return "FAIL", "response is not a JSON object"
    if payload.get("success") is False:
        error = payload.get("error") or payload.get("message") or "tool returned success=false"
        lowered = str(error).lower()
        warn_markers = (
            "requires confirmation",
            "necesita confirm",
            "cannot find the file specified",
            "no such file",
            "not installed",
            "missing dependency",
            "premium",
        )
        if any(marker in lowered for marker in warn_markers):
            return "WARN", str(error)
        return "FAIL", str(error)
    if "success" not in payload:
        return "WARN", "response has no success field"
    return "PASS", str(payload.get("message") or "ok")


def call_tool(bridge_url: str, tool_name: str, params: dict[str, Any], timeout: int) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        response = requests.post(
            f"{bridge_url}/tools/call",
            json={"tool": tool_name, "params": params},
            timeout=timeout,
        )
        elapsed = round(time.perf_counter() - started, 3)
        try:
            payload: Any = response.json()
        except ValueError:
            payload = {"raw": response.text[:2000]}
        status, detail = classify_response(response.status_code, payload)
        return {
            "tool": tool_name,
            "classification": status,
            "http_status": response.status_code,
            "elapsed_seconds": elapsed,
            "params": params,
            "detail": detail,
            "response_preview": json.dumps(payload, default=str)[:2000],
        }
    except requests.RequestException as exc:
        elapsed = round(time.perf_counter() - started, 3)
        return {
            "tool": tool_name,
            "classification": "FAIL",
            "http_status": "EXCEPTION",
            "elapsed_seconds": elapsed,
            "params": params,
            "detail": str(exc),
            "response_preview": "",
        }


def write_reports(results: list[dict[str, Any]], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    json_path = output_dir / f"ana_max_tool_report_{stamp}.json"
    md_path = output_dir / f"ana_max_tool_report_{stamp}.md"

    counts = {key: sum(1 for row in results if row["classification"] == key) for key in ("PASS", "WARN", "FAIL")}
    report = {
        "generated_at": stamp,
        "counts": counts,
        "results": results,
    }
    json_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

    lines = [
        "# ANA MAX Tool Test Report",
        "",
        f"Generated: {stamp}",
        "",
        f"PASS: {counts['PASS']}",
        f"WARN: {counts['WARN']}",
        f"FAIL: {counts['FAIL']}",
        "",
        "| Tool | Class | HTTP | Seconds | Detail |",
        "| --- | --- | --- | ---: | --- |",
    ]
    for row in results:
        detail = str(row["detail"]).replace("|", "/").replace("\n", " ")[:180]
        lines.append(
            f"| {row['tool']} | {row['classification']} | {row['http_status']} | "
            f"{row['elapsed_seconds']} | {detail} |"
        )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"JSON report: {json_path}")
    print(f"Markdown report: {md_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Safe end-to-end ANA MAX bridge tool tester.")
    parser.add_argument("--bridge-url", default=DEFAULT_BRIDGE_URL)
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--include-risky", action="store_true", help="Run tools normally skipped by safe mode.")
    args = parser.parse_args()

    if not args.bridge_url.startswith("http://127.0.0.1:"):
        raise SystemExit("Refusing to test non-localhost bridge URL.")

    tools = sorted(fetch_tools(args.bridge_url.rstrip("/"), args.timeout), key=lambda item: item["name"])
    print(f"Found {len(tools)} tools at {args.bridge_url}")

    results: list[dict[str, Any]] = []
    for tool in tools:
        name = str(tool.get("name", ""))
        if name in SKIP_REASONS and not args.include_risky:
            row = {
                "tool": name,
                "classification": "WARN",
                "http_status": "SKIP",
                "elapsed_seconds": 0,
                "params": {},
                "detail": SKIP_REASONS[name],
                "response_preview": "",
            }
            print(f"WARN {name}: {row['detail']}")
            results.append(row)
            continue

        params = params_for(tool)
        row = call_tool(args.bridge_url.rstrip("/"), name, params, args.timeout)
        print(f"{row['classification']} {name}: HTTP {row['http_status']} in {row['elapsed_seconds']}s")
        results.append(row)

    write_reports(results, args.output_dir)
    failed = sum(1 for row in results if row["classification"] == "FAIL")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
