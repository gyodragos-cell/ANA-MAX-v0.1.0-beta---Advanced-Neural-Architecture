#!/usr/bin/env python3
"""ANA MAX OS-14 Self Design Engine."""

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

ENGINE_NAME = "self_design_engine"
LEVEL = 14
LEVEL_SCHEMA = "ana.os14.self_design_engine.v1"
REPORT_PATH = level_report_path(LEVEL).with_name("self_design_report.json")


def _design_proposals(memory_snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    patterns = memory_snapshot.get("patterns", {}) if isinstance(memory_snapshot, dict) else {}
    preference = memory_snapshot.get("preferences", {}) if isinstance(memory_snapshot, dict) else {}
    conservative = str(preference.get("evolution_aggressiveness", "low")) in {"low", "medium"}
    proposals = [
        {
            "id": "shared_level_helpers",
            "title": "Consolidate repetitive OS-11+ helpers",
            "risk": "low",
            "benefit": "Reduce duplication across additive level engines.",
            "validation": "compileall and smoke tests remain green.",
        },
        {
            "id": "memory_dashboard_snapshot",
            "title": "Add a compact memory dashboard snapshot",
            "risk": "low",
            "benefit": "Make reasoning, planning, and synthesis easier to review.",
            "validation": "report summaries remain bounded and RAW-tagged.",
        },
    ]
    if conservative or int(patterns.get("stable_cycles", 0) or 0) > 0:
        proposals.append(
            {
                "id": "safe_phase_order_tuning",
                "title": "Tune additive phase ordering conservatively",
                "risk": "low",
                "benefit": "Keep the ladder stable while new layers accumulate history.",
                "validation": "no schema drift and no baseline regression.",
            }
        )
    return proposals


def run_cycle(*, dry_run: bool = True) -> dict[str, Any]:
    started = time.perf_counter()
    memory_snapshot = build_memory_snapshot()
    baseline = baseline_metrics()
    proposals = _design_proposals(memory_snapshot)
    graph_report = read_json(REPORT_PATH.parent / "knowledge_graph.json", {})
    graph_metadata = graph_report.get("metadata", {}) if isinstance(graph_report, dict) else {}
    knowledge_graph = {
        "metadata": {
            "total_nodes": graph_metadata.get("total_nodes", 0),
            "total_edges": graph_metadata.get("total_edges", 0),
            "node_types": graph_metadata.get("node_types", {}),
        },
        "evolution": graph_metadata.get("evolution", {}),
        "hot_node_count": len(graph_metadata.get("evolution", {}).get("hot_nodes", [])) if isinstance(graph_metadata.get("evolution", {}), dict) else 0,
        "cold_node_count": len(graph_metadata.get("evolution", {}).get("cold_nodes", [])) if isinstance(graph_metadata.get("evolution", {}), dict) else 0,
    }
    overall_success = baseline.get("health_score", 0) == 100 and baseline.get("warnings", 0) == 0 and baseline.get("parse_error_count", 0) == 0 and len(proposals) > 0

    report = {
        "schema": LEVEL_SCHEMA,
        "generated_at": utc_now(),
        "engine": ENGINE_NAME,
        "workspace_root": str(WORKSPACE_ROOT),
        "dry_run": dry_run,
        "memory_snapshot": memory_snapshot,
        "knowledge_graph": knowledge_graph,
        "design_proposals": proposals,
        "summary": {
            "proposal_count": len(proposals),
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
        next_level="OS-15",
        summary=report["summary"],
        payload=report,
        dry_run=dry_run,
        memory_snapshot=memory_snapshot,
    )
    write_level_report(LEVEL, level_report)
    return report


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ANA MAX OS-14 Self Design Engine")
    parser.add_argument("--cycle", action="store_true", help="Run the design cycle.")
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
