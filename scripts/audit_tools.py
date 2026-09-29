"""
OS-27 Full Bridge Tool Audit — v2
Testeaza fiecare tool cu parametrii corecti.
"""
import sys, os, time, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "ANA_MAX"))

from bridge.direct_bridge import DirectBridge

b = DirectBridge()

print("=" * 60)
print(" OS-27 Full Bridge Tool Audit v2")
print("=" * 60)
print()

results = {"pass": [], "fail": [], "warn": []}

# Parametrii corecti descoperiti prin testare directa
# Toate toolurile care cer "operation" in loc de "action"
TOOL_TESTS = {
    "agent_coach":                   {"action": "recommend", "context": "audit"},
    "tool_router":                   {"action": "recommend", "context": "audit"},
    "file_operations":               {"action": "list", "path": "."},
    "system_control":                {"operation": "vitals"},
    "smart_search":                  {"action": "search", "query": "test"},
    "code_search":                   {"operation": "grep", "pattern": "def safe_execute", "path": "ANA_MAX/tools"},
    "large_file_reader":             {"operation": "read", "file_path": "ANA_MAX/tools/base.py", "start_line": 1, "end_line": 5},
    "error_radar":                   {"action": "scan"},
    "workspace_situational_awareness": {"action": "snapshot"},
    "tool_healthcheck":              {"action": "run_all"},
    "project_navigator":             {"operation": "find", "query": "ANAMemoryCortex"},
    "ocr_tool":                      {"action": "check"},
    "clipboard_manager":             {"action": "get", "target": "clipboard"},
    "window_manager":                {"action": "list"},
    "desktop_control":               {"operation": "view"},
    "swarm_orchestrator":            {"action": "status"},
    "git_operations":                {"operation": "status", "path": "."},
    "network_diag":                  {"operation": "ping", "target": "127.0.0.1"},
    "terminal":                      {"action": "run", "command": "echo OS27_OK"},
    "privacy_shield":                {"operation": "scan", "text": "test data no PII"},
    "security_audit":                {"operation": "scan_secrets", "target": "."},
}

for tool_name, payload in TOOL_TESTS.items():
    start = time.time()
    try:
        result = b.execute_tool(tool_name, payload)
        elapsed = round((time.time() - start) * 1000, 1)

        if isinstance(result, dict):
            ok = result.get("success", False) or result.get("status") == "success"
        else:
            ok = bool(result)

        if ok:
            results["pass"].append(tool_name)
            print(f"  [OK]   {tool_name:<40} {elapsed}ms")
        else:
            err = ""
            if isinstance(result, dict):
                err = str(result.get("error", result.get("message", "")))[:60]
            results["warn"].append(tool_name)
            print(f"  [WARN] {tool_name:<40} {elapsed}ms | {err}")
    except Exception as ex:
        elapsed = round((time.time() - start) * 1000, 1)
        results["fail"].append(tool_name)
        print(f"  [FAIL] {tool_name:<40} {elapsed}ms | {str(ex)[:60]}")

print()
print("=" * 60)
total = len(results["pass"]) + len(results["warn"]) + len(results["fail"])
print(f"  {len(results['pass'])}/{total} PASS | {len(results['warn'])} WARN | {len(results['fail'])} FAIL")
print("=" * 60)

if results["fail"]:
    print("\nFAILED (exception thrown):")
    for t in results["fail"]:
        print(f"  - {t}")
if results["warn"]:
    print("\nWARN (wrong params or missing dep):")
    for t in results["warn"]:
        print(f"  - {t}")
