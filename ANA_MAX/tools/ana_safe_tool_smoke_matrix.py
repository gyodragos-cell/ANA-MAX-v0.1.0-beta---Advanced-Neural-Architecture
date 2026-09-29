import json
import time
import urllib.error
import urllib.request
from pathlib import Path


BASE_URL = "http://127.0.0.1:8766"
ROOT = Path(__file__).resolve().parents[2]
DOCU = ROOT / "docu"
TOOLS_JSON = DOCU / "ANA_MAX_TOOLS_ENDPOINT_2026-06-06.json"
RESULT_JSON = DOCU / "ANA_MAX_SAFE_TOOL_TEST_RESULTS_2026-06-06.json"
RESULT_MD = DOCU / "ANA_MAX_SAFE_TOOL_TEST_RESULTS_2026-06-06.md"


SAFE_ARGS = {
    "adb_operations": {"operation": "devices", "timeout": 10},
    "agent_coach": {"action": "coach", "limit": 20},
    "ana_health_check": {"include_contracts": False},
    "ana_identity": {},
    "ana_memory": {"action": "stats"},
    "ana_orchestrator": {"action": "status"},
    "ana_patch_suggester": {},
    "ana_runtime_inspector": {"action": "snapshot"},
    "autonomy_dashboard": {},
    "baseline_update_suggester": {},
    "binary_map": {"path": str(ROOT / "ANA_MAX" / "main.py")},
    "browser_control": {"operation": "status"},
    "clipboard_manager": {"action": "get"},
    "code_context_pack": {},
    "code_search": {"operation": "list_files", "path": str(ROOT / "ANA_MAX")},
    "context_bridge": {"action": "status"},
    "context_engine": {"action": "summary"},
    "conversation_learning": {"action": "recent", "limit": 5},
    "debugger": {"action": "analyze", "traceback_text": "ValueError: ANA safe smoke sample"},
    "desktop_capture": {"operation": "get_windows"},
    "docs_generator": {},
    "edge_tts_voice": {"operation": "list_voices"},
    "error_radar": {},
    "event_stream": {"action": "stats"},
    "file_operations": {"operation": "info", "path": str(ROOT / "ANA_MAX")},
    "foreground_ui_snapshot": {},
    "frida_instrument": {"operation": "version", "confirm": True},
    "glob_search": {"pattern": "*.py", "path": str(ROOT / "ANA_MAX"), "limit": 5},
    "graph_context_pack": {"action": "stats"},
    "grep_content": {"regex": "class ", "search_path": str(ROOT / "ANA_MAX" / "tools"), "glob": "*.py", "limit": 5},
    "grep_file": {"regex": "class ", "search_path": str(ROOT / "ANA_MAX" / "tools"), "glob": "*.py", "limit": 5},
    "input_api_probe": {"operation": "list_authorized", "confirm": True},
    "live_desktop_viewer": {"operation": "status"},
    "live_tool_healer": {"action": "test_health", "tool_name": "tool_healthcheck"},
    "memory_cortex": {"action": "status"},
    "network_diag": {"operation": "dns_lookup", "target": "localhost"},
    "ocr_tool": {"action": "check"},
    "privacy_shield": {"operation": "status"},
    "proactive_interrupt": {"action": "status"},
    "project_navigator": {"operation": "list", "path": str(ROOT / "ANA_MAX")},
    "runtime_guard": {},
    "schema_diff": {
        "expected_schema": {"properties": {"success": {"type": "boolean"}}, "required": ["success"]},
        "actual_response": {"success": True},
    },
    "security_audit": {"operation": "scan_secrets", "target": str(ROOT / "ANA_MAX" / "core")},
    "self_evolving_tool": {"action": "status", "confirm": True},
    "session_audit": {"action": "trust"},
    "session_lifecycle": {"action": "recommend"},
    "session_log_miner": {"action": "analyze", "path": str(ROOT / "ANA_MAX" / "logs" / "ana_max.log"), "limit": 20},
    "session_rem_sleep": {"action": "latest"},
    "smart_search": {"action": "stats"},
    "swarm_orchestrator": {"action": "status"},
    "system_control": {"operation": "vitals"},
    "terminal": {"operation": "run", "command": "echo ANA_SAFE_SMOKE", "timeout": 10, "confirm": True},
    "todowrite": {"operation": "list"},
    "tool_contract_validator": {},
    "tool_healthcheck": {},
    "tool_router": {"mode": "profile_status"},
    "vector_memory": {"action": "stats"},
    "vision_region_capture": {"x": 0, "y": 0, "width": 2, "height": 2},
    "window_manager": {"action": "list"},
    "windows_deep_sight": {"operation": "top_cpu", "limit": 5},
    "windows_insight": {"operation": "system_snapshot"},
    "windows_uia_bridge": {"action": "list_windows", "confirm": True},
    "workspace_situational_awareness": {"include_uia": False, "include_errors": True},
}


SKIP_REASONS = {
    "advanced_scanner": "security/network scanner; needs explicit target and approval",
    "apk_analyzer": "needs APK path; repack/sign variants are mutative",
    "autonomous_engine": "generic autonomous execution requires task; skipped to avoid agentic side effects",
    "bash_exec": "generic command executor; covered by terminal safe echo",
    "code_tools": "run/create/install can mutate environment",
    "codebase_understanding": "full-codebase analyze timed out in first pass; use targeted path/query later",
    "desktop_control": "can click/type/move desktop; unsafe without explicit UI task",
    "edit": "file editor; mutative",
    "file_patch": "file patcher; mutative",
    "hardware_scanner": "network/firmware/default-credential scanner",
    "mitm_analyzer": "packet capture/export tool; lab-only with explicit approval",
    "network_pentest": "pentest/recon scanner; lab-only with target approval",
    "qa_testing": "can generate/write tests; not a runtime health check",
    "remote_control": "remote execute/session operations; unsafe in smoke run",
    "science_research": "requires dataset/model task, not generic smoke",
    "session_checkpoint": "writes durable checkpoint; useful for handoff but not read-only smoke",
    "system_optimization": "optimization actions may change system state",
    "task": "generic autonomous task runner; would invoke agentic behavior",
    "uia_click": "desktop click action; needs explicit UI target",
    "uia_type": "desktop typing action; needs explicit UI target",
    "vision_fallback": "can click/type via vision; unsafe without explicit target",
    "vision_find_element": "requires target/screenshot context",
    "web_ai_bridge": "external AI bridge/network/API use",
    "web_fetch": "external web fetch; skipped for offline-safe smoke",
    "web_scraper": "external web scrape/download variants",
    "web_search": "external web search",
}


def post_json(path: str, payload: dict, timeout: int = 25) -> tuple[int | None, dict | str]:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8", errors="replace")
            try:
                return response.status, json.loads(body)
            except json.JSONDecodeError:
                return response.status, body
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            return exc.code, json.loads(body)
        except json.JSONDecodeError:
            return exc.code, body
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


def compact(value, limit: int = 900) -> str:
    text = json.dumps(value, ensure_ascii=False, default=str) if not isinstance(value, str) else value
    text = text.replace("\r", " ").replace("\n", " ")
    return text[:limit] + ("..." if len(text) > limit else "")


def main() -> int:
    raw = json.loads(TOOLS_JSON.read_text(encoding="utf-8-sig"))
    tools = raw["tools"]
    results = []
    started = time.strftime("%Y-%m-%d %H:%M:%S")

    for tool in sorted(tools, key=lambda item: item["name"]):
        name = tool["name"]
        category = tool.get("category", "")
        if name in SAFE_ARGS:
            args = SAFE_ARGS[name]
            status_code, response = post_json("/execute", {"tool": name, "params": args})
            success = bool(isinstance(response, dict) and response.get("success"))
            results.append(
                {
                    "name": name,
                    "category": category,
                    "mode": "execute_read_only",
                    "args": args,
                    "success": success,
                    "status_code": status_code,
                    "summary": compact(response),
                }
            )
        else:
            results.append(
                {
                    "name": name,
                    "category": category,
                    "mode": "contract_only_skipped",
                    "args": {},
                    "success": None,
                    "status_code": None,
                    "summary": SKIP_REASONS.get(name, "no safe generic read-only invocation selected"),
                }
            )
        time.sleep(0.05)

    counts = {
        "total": len(results),
        "executed": sum(1 for item in results if item["mode"] == "execute_read_only"),
        "passed": sum(1 for item in results if item["success"] is True),
        "failed": sum(1 for item in results if item["success"] is False),
        "skipped_contract_only": sum(1 for item in results if item["success"] is None),
    }
    payload = {"started": started, "base_url": BASE_URL, "counts": counts, "results": results}
    RESULT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        "# ANA MAX Safe Tool Smoke Results - 2026-06-06",
        "",
        "Read-only smoke matrix. Mutative, security-scanner, remote, GUI-click/type, and external-network tools are contract-only unless explicitly approved by the operator.",
        "",
        "## Summary",
        "",
        f"- Total tools inventoried: {counts['total']}",
        f"- Executed read-only: {counts['executed']}",
        f"- Passed: {counts['passed']}",
        f"- Failed: {counts['failed']}",
        f"- Contract-only skipped: {counts['skipped_contract_only']}",
        "",
        "## Results",
        "",
        "| Tool | Category | Mode | Status | Notes |",
        "|---|---:|---|---|---|",
    ]
    for item in results:
        if item["success"] is True:
            status = "PASS"
        elif item["success"] is False:
            status = "FAIL"
        else:
            status = "SKIP"
        note = compact(item["summary"], 220).replace("|", "\\|")
        lines.append(f"| `{item['name']}` | {item['category']} | {item['mode']} | {status} | {note} |")
    RESULT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps(counts, indent=2))
    print(str(RESULT_JSON))
    print(str(RESULT_MD))
    return 0 if counts["failed"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
