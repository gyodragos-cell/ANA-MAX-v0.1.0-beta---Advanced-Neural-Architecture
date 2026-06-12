#!/usr/bin/env python3
"""ANA MAX OS-13 Long Horizon Planner."""

from __future__ import annotations

import argparse
import time
from typing import Any

from ANA_MAX.self_optimization.osx_level_common import (
    WORKSPACE_ROOT,
    baseline_metrics,
    build_level_report,
    build_memory_snapshot,
    emit_raw_json,
    level_report_path,
    read_json,
    write_json,
    write_level_report,
    utc_now,
)

ENGINE_NAME = "long_horizon_planner"
LEVEL = 13
LEVEL_SCHEMA = "ana.os13.long_horizon_planner.v1"
PLAN_PATH = level_report_path(LEVEL).with_name("long_horizon_plan.json")


def _planned_steps(memory_snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    preferences = memory_snapshot.get("preferences", {}) if isinstance(memory_snapshot, dict) else {}
    stability_priority = str(preferences.get("stability_priority", "high"))
    return [
        {
            "timeframe": "24h",
            "priority": "high",
            "action": "Keep OS-3/OS-4 baseline health at 100/0 and preserve RAW-tagged output.",
        },
        {
            "timeframe": "7d",
            "priority": "medium",
            "action": "Consolidate memory history and confirm evolution phases remain bounded.",
        },
        {
            "timeframe": "30d",
            "priority": "medium" if stability_priority == "high" else "low",
            "action": "Expand additive higher-level planning only after consistency remains stable.",
        },
    ]


def run_cycle(*, dry_run: bool = True) -> dict[str, Any]:
    started = time.perf_counter()
    memory_snapshot = build_memory_snapshot()
    baseline = baseline_metrics()
    steps = _planned_steps(memory_snapshot)
    goals = read_json(PLAN_PATH.parent / "self_goals.json", {})
    strategy = read_json(PLAN_PATH.parent / "evolution_strategy.json", {})
    horizon_count = 3
    overall_success = baseline.get("health_score", 0) == 100 and baseline.get("warnings", 0) == 0 and baseline.get("parse_error_count", 0) == 0 and len(steps) >= 3

    report = {
        "schema": LEVEL_SCHEMA,
        "generated_at": utc_now(),
        "engine": ENGINE_NAME,
        "workspace_root": str(WORKSPACE_ROOT),
        "dry_run": dry_run,
        "memory_snapshot": memory_snapshot,
        "goals": goals,
        "strategy": strategy,
        "plan": {
            "horizons": steps,
            "horizon_count": horizon_count,
        },
        "summary": {
            "horizon_count": horizon_count,
            "step_count": len(steps),
            "health_score": baseline.get("health_score", 0),
            "warnings": baseline.get("warnings", 0),
            "parse_error_count": baseline.get("parse_error_count", 0),
            "overall_success": overall_success,
        },
        "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
        "report_path": str(PLAN_PATH),
    }
    write_json(PLAN_PATH, report)
    level_report = build_level_report(
        os_level=LEVEL,
        engine=ENGINE_NAME,
        status="PASS" if overall_success else "WARN",
        next_level="OS-14",
        summary=report["summary"],
        payload=report,
        dry_run=dry_run,
        memory_snapshot=memory_snapshot,
    )
    write_level_report(LEVEL, level_report)
    return report


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ANA MAX OS-13 Long Horizon Planner")
    parser.add_argument("--cycle", action="store_true", help="Run the planner cycle.")
    parser.add_argument("--dry-run", action="store_true", help="Keep the planner read-only.")
    return parser


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()
    dry_run = args.dry_run or not args.cycle
    result = run_cycle(dry_run=dry_run)
    emit_raw_json(result)
    return 0 if result.get("summary", {}).get("overall_success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
