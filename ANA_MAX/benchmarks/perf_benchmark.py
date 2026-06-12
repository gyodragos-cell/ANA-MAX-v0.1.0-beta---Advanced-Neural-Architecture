"""ANA MAX bridge performance benchmark."""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from test_all_tools import DEFAULT_BRIDGE_URL, SKIP_REASONS, call_tool, fetch_tools, params_for  # noqa: E402

REPORT_ROOT = Path(os.environ.get("TEMP", ".")) / "ana-max-test-suite"


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * pct)))
    return round(ordered[index], 3)


def output_dir() -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = REPORT_ROOT / stamp / "benchmarks"
    path.mkdir(parents=True, exist_ok=True)
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="ANA MAX safe performance benchmark.")
    parser.add_argument("--bridge-url", default=DEFAULT_BRIDGE_URL)
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--slow-threshold", type=float, default=2.0)
    parser.add_argument("--include-risky", action="store_true")
    args = parser.parse_args()
    bridge_url = args.bridge_url.rstrip("/")
    if not bridge_url.startswith("http://127.0.0.1:"):
        raise SystemExit("Refusing non-localhost bridge URL.")
    tools = sorted(fetch_tools(bridge_url, args.timeout), key=lambda item: item["name"])
    if args.limit:
        tools = tools[: args.limit]
    rows: list[dict[str, Any]] = []
    for tool in tools:
        name = str(tool.get("name", ""))
        if name in SKIP_REASONS and not args.include_risky:
            rows.append({"tool": name, "classification": "WARN", "detail": SKIP_REASONS[name], "runs": 0, "avg": 0, "p50": 0, "p95": 0, "p99": 0, "slow": False})
            print(f"WARN {name}: skipped")
            continue
        durations = []
        failures = []
        params = params_for(tool)
        for _ in range(args.runs):
            result = call_tool(bridge_url, name, params, args.timeout)
            durations.append(float(result["elapsed_seconds"]))
            if result["classification"] == "FAIL":
                failures.append(result["detail"])
        p95 = percentile(durations, 0.95)
        cls = "FAIL" if failures else ("WARN" if p95 >= args.slow_threshold else "PASS")
        rows.append({"tool": name, "classification": cls, "detail": "; ".join(failures[:3]) if failures else "ok", "runs": len(durations), "avg": round(mean(durations), 3), "p50": percentile(durations, 0.50), "p95": p95, "p99": percentile(durations, 0.99), "slow": p95 >= args.slow_threshold})
        print(f"{cls} {name}: p95={p95}s")
    counts = {key: sum(1 for row in rows if row["classification"] == key) for key in ("PASS", "WARN", "FAIL")}
    out = output_dir()
    (out / "perf_benchmark.json").write_text(json.dumps({"suite": "benchmarks", "counts": counts, "results": rows}, indent=2), encoding="utf-8")
    lines = ["# ANA MAX Performance Benchmark", "", f"PASS: {counts['PASS']}", f"WARN: {counts['WARN']}", f"FAIL: {counts['FAIL']}", "", "| Tool | Class | Avg | P50 | P95 | P99 |", "| --- | --- | ---: | ---: | ---: | ---: |"]
    for row in rows:
        lines.append(f"| {row['tool']} | {row['classification']} | {row['avg']} | {row['p50']} | {row['p95']} | {row['p99']} |")
    (out / "perf_benchmark.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Report folder: {out}")
    return 1 if counts["FAIL"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
