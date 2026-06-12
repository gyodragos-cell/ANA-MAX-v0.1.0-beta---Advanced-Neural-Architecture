#!/usr/bin/env python3
"""ANA MAX OS-19 Creative Synthesis Engine."""

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

ENGINE_NAME = "creative_synthesis_engine"
LEVEL = 19
LEVEL_SCHEMA = "ana.os19.creative_synthesis_engine.v1"
REPORT_PATH = level_report_path(LEVEL).with_name("creative_synthesis_report.json")


def _proposals(memory_snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    preferences = memory_snapshot.get("preferences", {}) if isinstance(memory_snapshot, dict) else {}
    conservative = str(preferences.get("evolution_aggressiveness", "low")) in {"low", "medium"}
    return [
        {
            "id": "memory_dashboard_snapshot",
            "kind": "module",
            "title": "Create a compact memory dashboard snapshot",
            "risk": "low",
            "benefit": "Surface memory health without exposing raw archives.",
            "validation": "dashboard output remains bounded and local-only.",
        },
        {
            "id": "graph_diff_review",
            "kind": "refactor",
            "title": "Add a graph diff review pass for hot/cold nodes",
            "risk": "low",
            "benefit": "Make repeated graph evolution easier to inspect.",
            "validation": "graph delta stays additive and deterministic.",
        },
        {
            "id": "phase_order_guard",
            "kind": "experiment",
            "title": "Add a phase-order regression guard",
            "risk": "low",
            "benefit": "Prevent accidental phase drift as new levels accumulate.",
            "validation": "OS-11+ wrappers continue to pass smoke tests.",
        },
        {
            "id": "one_command_studio_snapshot",
            "kind": "module",
            "title": "Create a one-command studio snapshot command",
            "risk": "low",
            "benefit": "Make OS-20 views easier to inspect and share locally.",
            "validation": "final summary remains RAW-tagged and bounded.",
        },
    ] if conservative else [
        {
            "id": "creative_experiment_lane",
            "kind": "experiment",
            "title": "Add a sandboxed experiment lane",
            "risk": "medium",
            "benefit": "Allow future experimentation without touching baseline reports.",
            "validation": "sandbox remains local-only and non-destructive.",
        }
    ]


def run_cycle(*, dry_run: bool = True) -> dict[str, Any]:
    started = time.perf_counter()
    memory_snapshot = build_memory_snapshot()
    baseline = baseline_metrics()
    knowledge_graph = read_json(REPORT_PATH.parent / "knowledge_graph.json", {})
    habit_routines = read_json(REPORT_PATH.parent / "habit_routine_report.json", {})
    knowledge_consolidation = read_json(REPORT_PATH.parent / "knowledge_consolidation_v2_report.json", {})
    emergent = read_json(REPORT_PATH.parent / "emergent_intelligence_report.json", {})
    proposals = _proposals(memory_snapshot)
    overall_success = baseline.get("health_score", 0) == 100 and baseline.get("warnings", 0) == 0 and baseline.get("parse_error_count", 0) == 0 and len(proposals) > 0

    report = {
        "schema": LEVEL_SCHEMA,
        "generated_at": utc_now(),
        "engine": ENGINE_NAME,
        "workspace_root": str(WORKSPACE_ROOT),
        "dry_run": dry_run,
        "memory_snapshot": memory_snapshot,
        "knowledge_graph": knowledge_graph.get("metadata", {}) if isinstance(knowledge_graph, dict) else {},
        "habit_routines": habit_routines,
        "knowledge_consolidation": knowledge_consolidation,
        "emergent_intelligence": emergent,
        "proposals": proposals,
        "summary": {
            "proposal_count": len(proposals),
            "module_count": sum(1 for proposal in proposals if proposal["kind"] == "module"),
            "refactor_count": sum(1 for proposal in proposals if proposal["kind"] == "refactor"),
            "experiment_count": sum(1 for proposal in proposals if proposal["kind"] == "experiment"),
            "health_score": baseline.get("health_score", 0),
            "warnings": baseline.get("warnings", 0),
            "parse_error_count": baseline.get("parse_error_count", 0),
            "overall_success": overall_success,
        },
        "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
        "report_path": str(REPORT_PATH),
    }
    write_json(REPORT_PATH, report)
    level_report = build_level_report(
        os_level=LEVEL,
        engine=ENGINE_NAME,
        status="PASS" if overall_success else "WARN",
        next_level="OS-20",
        summary=report["summary"],
        payload=report,
        dry_run=dry_run,
        memory_snapshot=memory_snapshot,
    )
    write_level_report(LEVEL, level_report)
    return report


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ANA MAX OS-19 Creative Synthesis Engine")
    parser.add_argument("--cycle", action="store_true", help="Run the synthesis cycle.")
    parser.add_argument("--dry-run", action="store_true", help="Keep the synthesis read-only.")
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
