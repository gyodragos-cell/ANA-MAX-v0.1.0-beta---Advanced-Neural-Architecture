#!/usr/bin/env python3
"""ANA MAX OS-16 Emergent Intelligence Engine."""

from __future__ import annotations

import argparse
import time
from typing import Any

from ANA_MAX.self_optimization.anticipation_engine import build_anticipation
from ANA_MAX.self_optimization.emotional_mapping import map_emotional_state
from ANA_MAX.self_optimization.emergent_behavior_engine import build_emergent_behavior
from ANA_MAX.self_optimization.meta_reasoning import build_meta_reasoning
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

ENGINE_NAME = "emergent_intelligence_engine"
LEVEL = 16
LEVEL_SCHEMA = "ana.os16.emergent_intelligence_engine.v1"
REPORT_SCHEMA = "ana.emergent_intelligence.report.v1"
REPORT_PATH = level_report_path(LEVEL).with_name("emergent_intelligence_report.json")


def _report_summary(
    baseline: dict[str, Any],
    meta: dict[str, Any],
    anticipation: dict[str, Any],
    emotion: dict[str, Any],
    emergent: dict[str, Any],
) -> dict[str, Any]:
    risk_count = int(anticipation.get("summary", {}).get("risk_count", 0) or 0)
    opportunity_count = int(anticipation.get("summary", {}).get("opportunity_count", 0) or 0)
    tone = str(emotion.get("tone", "calm"))
    emergence_score = max(0, min(100, 100 - (risk_count * 5) + (opportunity_count * 2)))
    overall_success = (
        baseline.get("health_score", 0) == 100
        and baseline.get("warnings", 0) == 0
        and baseline.get("parse_error_count", 0) == 0
        and bool(emergent.get("patterns"))
    )
    return {
        "emergence_score": emergence_score,
        "risk_count": risk_count,
        "opportunity_count": opportunity_count,
        "tone": tone,
        "health_score": baseline.get("health_score", 0),
        "warnings": baseline.get("warnings", 0),
        "parse_error_count": baseline.get("parse_error_count", 0),
        "overall_success": overall_success,
        "meta_summary": meta.get("summary", {}),
        "anticipation_summary": anticipation.get("summary", {}),
        "emotion_summary": emotion.get("summary", {}),
        "emergent_summary": emergent.get("summary", {}),
    }


def run_cycle(*, dry_run: bool = True) -> dict[str, Any]:
    started = time.perf_counter()
    memory_snapshot = build_memory_snapshot()
    baseline = baseline_metrics()
    reasoning = build_meta_reasoning(memory_snapshot, baseline)
    anticipation = build_anticipation(reasoning, memory_snapshot, baseline)
    emotion = map_emotional_state(memory_snapshot, anticipation, baseline)
    emergent = build_emergent_behavior(reasoning, anticipation, emotion, memory_snapshot)
    consistency = read_json(REPORT_PATH.parent / "self_consistency_report.json", {})
    reasoning_report = read_json(REPORT_PATH.parent / "self_reasoning_report.json", {})
    goals_report = read_json(REPORT_PATH.parent / "self_goals.json", {})
    strategy_report = read_json(REPORT_PATH.parent / "evolution_strategy.json", {})

    summary = _report_summary(baseline, reasoning, anticipation, emotion, emergent)
    report = {
        "schema": REPORT_SCHEMA,
        "generated_at": utc_now(),
        "engine": ENGINE_NAME,
        "workspace_root": str(WORKSPACE_ROOT),
        "dry_run": dry_run,
        "memory_snapshot": memory_snapshot,
        "consistency_report": consistency,
        "reasoning_report": reasoning_report,
        "goals_report": goals_report,
        "strategy_report": strategy_report,
        "meta_reasoning": reasoning,
        "anticipation": anticipation,
        "emotional_mapping": emotion,
        "emergent_behavior": emergent,
        "emergent_signals": {
            "tone": emotion.get("tone"),
            "risk_count": summary["risk_count"],
            "opportunity_count": summary["opportunity_count"],
            "patterns": emergent.get("patterns", []),
            "feedback_loops": emergent.get("feedback_loops", []),
        },
        "summary": summary,
        "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
        "report_path": str(REPORT_PATH),
    }
    write_json(REPORT_PATH, report)
    level_report = build_level_report(
        os_level=LEVEL,
        engine=ENGINE_NAME,
        status="PASS" if summary["overall_success"] else "WARN",
        next_level="OS-17",
        summary=summary,
        payload=report,
        dry_run=dry_run,
        memory_snapshot=memory_snapshot,
    )
    write_level_report(LEVEL, level_report)
    return report


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ANA MAX OS-16 Emergent Intelligence Engine")
    parser.add_argument("--cycle", action="store_true", help="Run the emergent intelligence cycle.")
    parser.add_argument("--dry-run", action="store_true", help="Keep the engine read-only.")
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
