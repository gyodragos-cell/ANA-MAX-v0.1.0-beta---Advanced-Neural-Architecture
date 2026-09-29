#!/usr/bin/env python3
"""
ANA MAX bridge performance + behavior benchmark v3.
Safe, localhost-only, with latency + basic behavior checks.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any, Dict, List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from test_all_tools import (  # noqa: E402
    DEFAULT_BRIDGE_URL,
    SKIP_REASONS,
    call_tool,
    fetch_tools,
    params_for,
)

REPORT_ROOT = Path(os.environ.get("TEMP", ".")) / "ana-max-test-suite"


def percentile(values: List[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * pct)))
    return round(ordered[index], 3)


def output_dir() -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = REPORT_ROOT / stamp / "benchmarks_v3"
    path.mkdir(parents=True, exist_ok=True)
    return path


def classify_tool(
    name: str,
    durations: List[float],
    failures: List[str],
    slow_threshold: float,
) -> Tuple[str, bool]:
    p95 = percentile(durations, 0.95)
    if failures:
        return "FAIL", False
    if p95 >= slow_threshold:
        return "WARN", True
    return "PASS", False


def behavior_hint(name: str, result: Dict[str, Any]) -> str:
    """
    Very lightweight behavior checks.
    You can extend this per-tool later.
    """
    cls = result.get("classification", "")
    detail = result.get("detail", "")
    extra = []

    # Generic checks
    if cls == "FAIL":
        extra.append("tool reported FAIL")
    if "timeout" in detail.lower():
        extra.append("possible timeout / slow backend")

    # Simple per-tool hints
    if name == "terminal":
        if "created" in detail.lower() or "folder" in detail.lower():
            extra.append("terminal side-effect seems OK")
    if name == "file_operations":
        if "write" in detail.lower() or "read" in detail.lower():
            extra.append("file_operations basic IO seems OK")

    return "; ".join(extra) if extra else "ok"


def run_single_tool(
    bridge_url: str,
    tool: Dict[str, Any],
    runs: int,
    timeout: int,
    slow_threshold: float,
    include_risky: bool,
) -> Dict[str, Any]:
    name = str(tool.get("name", ""))
    if name in SKIP_REASONS and not include_risky:
        return {
            "tool": name,
            "classification": "WARN",
            "detail": SKIP_REASONS[name],
            "runs": 0,
            "avg": 0.0,
            "p50": 0.0,
            "p95": 0.0,
            "p99": 0.0,
            "slow": False,
            "behavior": "skipped (risky)",
        }

    durations: List[float] = []
    failures: List[str] = []
    params = params_for(tool)

    for _ in range(runs):
        result = call_tool(bridge_url, name, params, timeout)
        durations.append(float(result.get("elapsed_seconds", 0.0)))
        if result.get("classification") == "FAIL":
            failures.append(result.get("detail", "unknown failure"))

    p50 = percentile(durations, 0.50)
    p95 = percentile(durations, 0.95)
    p99 = percentile(durations, 0.99)
    cls, slow_flag = classify_tool(name, durations, failures, slow_threshold)
    behavior = behavior_hint(name, {"classification": cls, "detail": "; ".join(failures)})

    print(f"{cls} {name}: p95={p95}s (runs={len(durations)})")

    return {
        "tool": name,
        "classification": cls,
        "detail": "; ".join(failures[:3]) if failures else "ok",
        "runs": len(durations),
        "avg": round(mean(durations), 3) if durations else 0.0,
        "p50": p50,
        "p95": p95,
        "p99": p99,
        "slow": slow_flag,
        "behavior": behavior,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="ANA MAX safe performance + behavior benchmark v3.")
    parser.add_argument("--bridge-url", default=DEFAULT_BRIDGE_URL)
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--slow-threshold", type=float, default=2.0)
    parser.add_argument("--include-risky", action="store_true")
    parser.add_argument("--workers", type=int, default=8, help="max parallel workers")
    args = parser.parse_args()

    bridge_url = args.bridge_url.rstrip("/")
    if not bridge_url.startswith("http://127.0.0.1:"):
        raise SystemExit("Refusing non-localhost bridge URL.")

    tools = sorted(fetch_tools(bridge_url, args.timeout), key=lambda item: item["name"])
    if args.limit:
        tools = tools[: args.limit]

    rows: List[Dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = {
            pool.submit(
                run_single_tool,
                bridge_url,
                tool,
                args.runs,
                args.timeout,
                args.slow_threshold,
                args.include_risky,
            ): tool
            for tool in tools
        }
        for fut in as_completed(futures):
            rows.append(fut.result())

    counts = {key: sum(1 for row in rows if row["classification"] == key) for key in ("PASS", "WARN", "FAIL")}
    out = output_dir()

    # JSON report
    (out / "perf_benchmark_v3.json").write_text(
        json.dumps(
            {
                "suite": "benchmarks_v3",
                "counts": counts,
                "results": rows,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    # Markdown report
    lines = [
        "# ANA MAX Performance + Behavior Benchmark v3",
        "",
        f"PASS: {counts['PASS']}",
        f"WARN: {counts['WARN']}",
        f"FAIL: {counts['FAIL']}",
        "",
        "| Tool | Class | Avg | P50 | P95 | P99 | Slow | Behavior |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['tool']} | {row['classification']} | {row['avg']} | "
            f"{row['p50']} | {row['p95']} | {row['p99']} | "
            f"{'yes' if row['slow'] else 'no'} | {row['behavior']} |"
        )
    (out / "perf_benchmark_v3.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Report folder: {out}")
    return 1 if counts["FAIL"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
