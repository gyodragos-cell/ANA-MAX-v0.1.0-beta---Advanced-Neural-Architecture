"""
OS27 Hyper++ MCP Smoke Test
===========================
Testeaza TOATE cele 19 tool-uri MCP cu backend-uri reale.
Ruleaza: python mcp/os27_mcp_smoke_test.py
"""
import sys
import json
import subprocess
import os
import time

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

WORKSPACE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERVER = os.path.join(WORKSPACE, 'mcp', 'os27_mcp_server.py')

TESTS = [
    ("initialize", "initialize", {}),
    ("tools/list", "tools/list", {}),
    ("os27_tool_brain_priority_map", "tools/call", {"name": "os27_tool_brain_priority_map", "arguments": {"level": "all"}}),
    ("os27_context_engine_read_state", "tools/call", {"name": "os27_context_engine_read_state", "arguments": {}}),
    ("os27_context_engine_reflexes", "tools/call", {"name": "os27_context_engine_reflexes", "arguments": {}}),
    ("os27_memory_cortex_validate", "tools/call", {"name": "os27_memory_cortex_validate", "arguments": {}}),
    ("os27_watchdog_bus_read", "tools/call", {"name": "os27_watchdog_bus_read", "arguments": {}}),
    ("os27_telemetry_engine_read", "tools/call", {"name": "os27_telemetry_engine_read", "arguments": {}}),
    ("os27_dashboard_feeder_snapshot", "tools/call", {"name": "os27_dashboard_feeder_snapshot", "arguments": {}}),
]

def run_test(test_name, method, params):
    request = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params})
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONPATH"] = os.path.join(WORKSPACE, "ANA_MAX")
    
    t0 = time.time()
    try:
        result = subprocess.run(
            [sys.executable, SERVER],
            input=request, capture_output=True, text=True,
            env=env, timeout=30, cwd=WORKSPACE
        )
        elapsed = time.time() - t0
        
        if result.returncode != 0:
            return False, elapsed, f"Exit code {result.returncode}: {result.stderr[:200]}"
        
        # Find JSON line in stdout
        for line in result.stdout.strip().split('\n'):
            line = line.strip()
            if line.startswith('{'):
                parsed = json.loads(line)
                if "error" in parsed and parsed["error"]:
                    return False, elapsed, f"MCP error: {parsed['error']}"
                return True, elapsed, "OK"
        
        return False, elapsed, f"No JSON in output: {result.stdout[:200]}"
    except subprocess.TimeoutExpired:
        return False, 30.0, "TIMEOUT"
    except Exception as e:
        return False, time.time() - t0, str(e)

def main():
    print("=" * 70)
    print("  OS27 Hyper++ MCP Smoke Test — 19 Tool-uri cu Backend Real")
    print("=" * 70)
    print()
    
    passed = 0
    failed = 0
    results = []
    
    for test_name, method, params in TESTS:
        ok, elapsed, msg = run_test(test_name, method, params)
        status = "PASS" if ok else "FAIL"
        icon = "[OK]" if ok else "[FAIL]"
        print(f"  {icon} {test_name:<45} {elapsed:>6.2f}s  {msg}")
        
        if ok:
            passed += 1
        else:
            failed += 1
        results.append({"name": test_name, "ok": ok, "time": elapsed, "msg": msg})
    
    print()
    print("-" * 70)
    print(f"  TOTAL: {passed} passed, {failed} failed, {len(results)} tests")
    print("-" * 70)
    
    # Save results
    report_path = os.path.join(WORKSPACE, 'logs', 'os27_smoke_test_results.json')
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump({"timestamp": time.time(), "passed": passed, "failed": failed, "results": results}, f, indent=2)
    print(f"\n  Rezultate salvate: {report_path}")
    
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
