#!/usr/bin/env python3
"""ANA MAX OS-17 Knowledge Consolidation v2."""

from __future__ import annotations

import argparse
import time
from collections import Counter
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

ENGINE_NAME = "knowledge_consolidation_v2"
LEVEL = 17
LEVEL_SCHEMA = "ana.os17.knowledge_consolidation_v2.v1"
REPORT_PATH = level_report_path(LEVEL).with_name("knowledge_consolidation_v2_report.json")


def _topic_clusters() -> list[dict[str, Any]]:
    clusters = [
        {
            "topic": "stability",
            "sources": ["self_evaluation", "self_consistency", "memory_system"],
            "priority": "high",
        },
        {
            "topic": "automation",
            "sources": ["os4_daemon", "self_evolution", "distributed_orchestrator"],
            "priority": "medium",
        },
        {
            "topic": "memory",
            "sources": ["core_memory", "memory_context", "memory_consolidation"],
            "priority": "high",
        },
        {
            "topic": "coordination",
            "sources": ["agent_registry", "multi_agent_orchestrator", "distributed_topology"],
            "priority": "medium",
        },
    ]
    return clusters


def _trend_summary() -> dict[str, Any]:
    evolution_history = len(list((REPORT_PATH.parent / "evolution_strategy_history").glob("*.json")))
    graph_history = len(list((REPORT_PATH.parent / "knowledge_graph_history").glob("*.json")))
    return {
        "evolution_strategy_history_count": evolution_history,
        "knowledge_graph_history_count": graph_history,
        "trend_count": sum(1 for count in [evolution_history, graph_history] if count > 0),
    }


def run_cycle(*, dry_run: bool = False) -> dict[str, Any]:
    started = time.perf_counter()
    memory_snapshot = build_memory_snapshot()
    baseline = baseline_metrics()
    knowledge_graph = read_json(REPORT_PATH.parent / "knowledge_graph.json", {})
    reasoning = read_json(REPORT_PATH.parent / "self_reasoning_report.json", {})
    consistency = read_json(REPORT_PATH.parent / "self_consistency_report.json", {})
    clusters = _topic_clusters()
    trends = _trend_summary()
    topic_counter = Counter(cluster["topic"] for cluster in clusters)
    overall_success = (
        baseline.get("health_score", 0) == 100
        and baseline.get("warnings", 0) == 0
        and baseline.get("parse_error_count", 0) == 0
        and len(clusters) >= 4
    )

    report = {
        "schema": LEVEL_SCHEMA,
        "generated_at": utc_now(),
        "engine": ENGINE_NAME,
        "workspace_root": str(WORKSPACE_ROOT),
        "dry_run": dry_run,
        "memory_snapshot": memory_snapshot,
        "knowledge_graph": {
            "metadata": knowledge_graph.get("metadata", {}) if isinstance(knowledge_graph, dict) else {},
            "hot_node_count": len((knowledge_graph.get("metadata", {}).get("evolution", {}).get("hot_nodes", [])) if isinstance(knowledge_graph, dict) else []),
            "cold_node_count": len((knowledge_graph.get("metadata", {}).get("evolution", {}).get("cold_nodes", [])) if isinstance(knowledge_graph, dict) else []),
        },
        "reasoning_report": reasoning,
        "consistency_report": consistency,
        "topic_clusters": clusters,
        "topic_counter": dict(topic_counter),
        "trend_summary": trends,
        "summary": {
            "topic_count": len(clusters),
            "trend_count": trends["trend_count"],
            "history_count": trends["evolution_strategy_history_count"] + trends["knowledge_graph_history_count"],
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
        next_level="OS-18",
        summary=report["summary"],
        payload=report,
        dry_run=dry_run,
        memory_snapshot=memory_snapshot,
    )
    write_level_report(LEVEL, level_report)
    return report


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ANA MAX OS-17 Knowledge Consolidation v2")
    parser.add_argument("--cycle", action="store_true", help="Run the knowledge consolidation cycle.")
    parser.add_argument("--dry-run", action="store_true", help="Keep the consolidation read-only.")
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
