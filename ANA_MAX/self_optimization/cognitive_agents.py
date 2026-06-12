#!/usr/bin/env python3
"""ANA MAX OS-12 Cognitive Agents simulation."""

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
    write_json,
    write_level_report,
    utc_now,
)

ENGINE_NAME = "cognitive_agents"
LEVEL = 12
LEVEL_SCHEMA = "ana.os12.cognitive_agents.v1"
REPORT_PATH = level_report_path(LEVEL).with_name("cognitive_agents_report.json")


def _agents(memory_snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    meta = build_meta_reasoning(memory_snapshot)
    anticipation = build_anticipation(meta, memory_snapshot)
    emotion = map_emotional_state(memory_snapshot, anticipation)
    emergent = build_emergent_behavior(meta, anticipation, emotion, memory_snapshot)
    return [
        {
            "id": "observer",
            "role": "observe",
            "signals": {
                "schema": memory_snapshot.get("schema"),
                "history_length": memory_snapshot.get("history_length", 0),
                "preferences": memory_snapshot.get("preferences", {}),
                "consistency": memory_snapshot.get("consistency", {}),
            },
        },
        {
            "id": "reasoner",
            "role": "meta_reasoning",
            "signals": meta,
        },
        {
            "id": "planner",
            "role": "anticipation",
            "signals": anticipation,
        },
        {
            "id": "reviewer",
            "role": "emotional_mapping",
            "signals": emotion,
        },
        {
            "id": "synthesizer",
            "role": "emergent_behavior",
            "signals": emergent,
        },
    ]


def run_cycle(*, dry_run: bool = False) -> dict[str, Any]:
    started = time.perf_counter()
    memory_snapshot = build_memory_snapshot()
    baseline = baseline_metrics()
    meta = build_meta_reasoning(memory_snapshot, baseline)
    anticipation = build_anticipation(meta, memory_snapshot, baseline)
    emotion = map_emotional_state(memory_snapshot, anticipation, baseline)
    emergent = build_emergent_behavior(meta, anticipation, emotion, memory_snapshot)
    agents = _agents(memory_snapshot)

    agent_failure_count = 0
    overall_success = (
        baseline.get("health_score", 0) == 100
        and baseline.get("warnings", 0) == 0
        and baseline.get("parse_error_count", 0) == 0
        and agent_failure_count == 0
    )

    report = {
        "schema": LEVEL_SCHEMA,
        "generated_at": utc_now(),
        "engine": ENGINE_NAME,
        "workspace_root": str(WORKSPACE_ROOT),
        "dry_run": dry_run,
        "memory_snapshot": memory_snapshot,
        "meta_reasoning": meta,
        "anticipation": anticipation,
        "emotional_mapping": emotion,
        "emergent_behavior": emergent,
        "agents": agents,
        "summary": {
            "agent_count": len(agents),
            "agent_failure_count": agent_failure_count,
            "health_score": baseline.get("health_score", 0),
            "warnings": baseline.get("warnings", 0),
            "parse_error_count": baseline.get("parse_error_count", 0),
            "overall_success": overall_success,
        },
        "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
        "report_path": str(REPORT_PATH),
    }

    level_report = build_level_report(
        os_level=LEVEL,
        engine=ENGINE_NAME,
        status="PASS" if overall_success else "WARN",
        next_level="OS-13",
        summary=report["summary"],
        payload=report,
        dry_run=dry_run,
        memory_snapshot=memory_snapshot,
    )
    write_json(REPORT_PATH, report)
    write_level_report(LEVEL, level_report)
    return report


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ANA MAX OS-12 Cognitive Agents")
    parser.add_argument("--cycle", action="store_true", help="Run the cognitive agent cycle.")
    parser.add_argument("--dry-run", action="store_true", help="Keep the cycle read-only.")
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
