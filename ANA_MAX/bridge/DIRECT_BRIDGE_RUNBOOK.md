#!/usr/bin/env python3
"""
ANA MAX Direct Bridge Plus
Extended CLI for diagnostics, smoke-test, benchmark, security, and tool execution.
Compatible with ANA MAX OS v2 (2026).
"""

from __future__ import annotations
import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = ROOT.parents[0]
BRIDGE_URL = "http://127.0.0.1:8766"

REPORT_ROOT = Path(os.environ.get("TEMP", ".")) / "ana-max-direct-bridge-plus"


def out_dir() -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = REPORT_ROOT / stamp
    path.mkdir(parents=True, exist_ok=True)
    return path


def get(path: str, timeout: int = 10) -> Dict[str, Any]:
    r = requests.get(f"{BRIDGE_URL}{path}", timeout=timeout)
    return r.json()


def post(path: str, payload: Dict[str, Any], timeout: int = 20) -> Dict[str, Any]:
    r = requests.post(f"{BRIDGE_URL}{path}", json=payload, timeout=timeout)
    return r.json()


def color(text: str, cls: str) -> str:
    if cls == "PASS":
        return f"\033[92m{text}\033[0m"
    if cls == "WARN":
        return f"\033[93m{text}\033[0m"
    if cls == "FAIL":
        return f"\033[91m{text}\033[0m"
    return text


# ------------------------------------------------------------
# HEALTH CHECK
# ------------------------------------------------------------
def health_check() -> None:
    print("\n=== HEALTH CHECK ===")
    try:
        h = get("/health")
        print(color("PASS", "PASS"), "MCP server online")
        print("tools:", h.get("tools_count"))
        print("version:", h.get("version"))
    except Exception as e:
        print(color("FAIL", "FAIL"), "health check failed:", e)


# ------------------------------------------------------------
# SMOKE TEST
# ------------------------------------------------------------
def smoke_test() -> None:
    print("\n=== SMOKE TEST ===")
    tools = ["agent_coach", "tool_router", "file_operations", "system_control"]
    for t in tools:
        try:
            r = post("/execute", {"tool": t, "payload": {}}, timeout=10)
            cls = r.get("classification", "FAIL")
            print(color(cls, cls), t, "-", r.get("detail", ""))
        except Exception as e:
            print(color("FAIL", "FAIL"), t, "error:", e)


# ------------------------------------------------------------
# LIST TOOLS
# ------------------------------------------------------------
def list_tools() -> None:
    print("\n=== TOOL LIST ===")
    try:
        tools = get("/tools")
        for t in tools.get("tools", []):
            print("-", t.get("name"))
    except Exception as e:
        print(color("FAIL", "FAIL"), "cannot list tools:", e)


# ------------------------------------------------------------
# EXECUTE TOOL
# ------------------------------------------------------------
def execute_tool(name: str, payload: str, dry_run: bool) -> None:
    print("\n=== EXECUTE TOOL ===")
    try:
        data = json.loads(payload) if payload else {}
        if dry_run:
            print("DRY-RUN:", name, data)
            return
        r = post("/execute", {"tool": name, "payload": data}, timeout=30)
        cls = r.get("classification", "FAIL")
        print(color(cls, cls), name)
        print(json.dumps(r, indent=2))
    except Exception as e:
        print(color("FAIL", "FAIL"), "execution error:", e)


# ------------------------------------------------------------
# SECURITY DIAGNOSTICS
# ------------------------------------------------------------
def security_diag() -> None:
    print("\n=== SECURITY DIAGNOSTICS ===")
    tools = ["network_diag", "security_audit", "privacy_shield"]
    for t in tools:
        try:
            r = post("/execute", {"tool": t, "payload": {}}, timeout=20)
            cls = r.get("classification", "FAIL")
            print(color(cls, cls), t, "-", r.get("detail", ""))
        except Exception as e:
            print(color("FAIL", "FAIL"), t, "error:", e)


# ------------------------------------------------------------
# BENCHMARK
# ------------------------------------------------------------
def run_single(name: str, iterations: int, timeout: int) -> Dict[str, Any]:
    durations = []
    failures = []
    for _ in range(iterations):
        start = time.time()
        try:
            r = post("/execute", {"tool": name, "payload": {}}, timeout=timeout)
            if r.get("classification") == "FAIL":
                failures.append(r.get("detail", "unknown"))
        except Exception as e:
            failures.append(str(e))
        durations.append(time.time() - start)

    p95 = sorted(durations)[int(len(durations) * 0.95)]
    cls = "FAIL" if failures else ("WARN" if p95 >= 2.0 else "PASS")
    return {
        "tool": name,
        "classification": cls,
        "avg": round(sum(durations) / len(durations), 3),
        "p95": round(p95, 3),
        "failures": failures[:3],
    }


def benchmark(iterations: int, timeout: int, include_mcp: bool) -> None:
    print("\n=== BENCHMARK ===")
    tools = get("/tools").get("tools", [])
    names = [t.get("name") for t in tools]

    if not include_mcp:
        names = [n for n in names if not n.startswith("mcp.")]

    results = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(run_single, n, iterations, timeout): n for n in names}
        for fut in as_completed(futures):
            results.append(fut.result())

    out = out_dir()
    (out / "direct_bridge_plus.json").write_text(json.dumps(results, indent=2))
    print("Report:", out)

    for r in results:
        print(color(r["classification"], r["classification"]), r["tool"], "p95=", r["p95"])


# ------------------------------------------------------------
# MAIN
# ------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(description="ANA MAX Direct Bridge Plus")
    parser.add_argument("--health-check", action="store_true")
    parser.add_argument("--smoke-test", action="store_true")
    parser.add_argument("--list-tools", action="store_true")
    parser.add_argument("--execute", type=str, default="")
    parser.add_argument("--payload", type=str, default="")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--security-diagnostics", action="store_true")
    parser.add_argument("--benchmark", action="store_true")
    parser.add_argument("--iterations", type=int, default=5)
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--include-mcp", action="store_true")
    args = parser.parse_args()

    if args.health_check:
        health_check()
    if args.smoke_test:
        smoke_test()
    if args.list_tools:
        list_tools()
    if args.execute:
        execute_tool(args.execute, args.payload, args.dry_run)
    if args.security_diagnostics:
        security_diag()
    if args.benchmark:
        benchmark(args.iterations, args.timeout, args.include_mcp)


if __name__ == "__main__":
    main()
