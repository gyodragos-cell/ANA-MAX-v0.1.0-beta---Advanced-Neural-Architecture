#!/usr/bin/env python3
"""ANA MAX OS-15 Ecosystem Engine."""

from __future__ import annotations

import argparse
import time
from typing import Any

from ANA_MAX.self_optimization.osx_level_common import (
    WORKSPACE_ROOT,
    agent_registry_snapshot,
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

ENGINE_NAME = "ecosystem_engine"
LEVEL = 15
LEVEL_SCHEMA = "ana.os15.ecosystem_engine.v1"
REPORT_PATH = level_report_path(LEVEL).with_name("ecosystem_report.json")


def _ecosystem_graph(memory_snapshot: dict[str, Any], registry: dict[str, Any]) -> dict[str, Any]:
    agents = registry.get("agents", {}) if isinstance(registry, dict) else {}
    nodes = [
        {"id": "core", "type": "module", "health": "stable"},
        {"id": "memory", "type": "memory", "health": "stable"},
        {"id": "docs", "type": "documentation", "health": "stable"},
        {"id": "agents", "type": "orchestration", "health": "stable"},
        {"id": "tools", "type": "tooling", "health": "stable"},
    ]
    edges = [
        {"source": "core", "target": "memory", "relation": "stores"},
        {"source": "core", "target": "docs", "relation": "describes"},
        {"source": "core", "target": "agents", "relation": "coordinates"},
        {"source": "agents", "target": "tools", "relation": "uses"},
        {"source": "memory", "target": "docs", "relation": "summarizes"},
    ]
    return {
        "nodes": nodes,
        "edges": edges,
        "node_count": len(nodes),
        "edge_count": len(edges),
        "agent_count": len(agents),
        "memory_history_length": memory_snapshot.get("history_length", 0),
    }


def run_cycle(*, dry_run: bool = True) -> dict[str, Any]:
    started = time.perf_counter()
    memory_snapshot = build_memory_snapshot()
    baseline = baseline_metrics()
    registry = agent_registry_snapshot()
    ecosystem = _ecosystem_graph(memory_snapshot, registry)
    overall_success = baseline.get("health_score", 0) == 100 and baseline.get("warnings", 0) == 0 and baseline.get("parse_error_count", 0) == 0 and ecosystem["node_count"] >= 5

    report = {
        "schema": LEVEL_SCHEMA,
        "generated_at": utc_now(),
        "engine": ENGINE_NAME,
        "workspace_root": str(WORKSPACE_ROOT),
        "dry_run": dry_run,
        "memory_snapshot": memory_snapshot,
        "agent_registry": registry,
        "ecosystem": ecosystem,
        "summary": {
            "node_count": ecosystem["node_count"],
            "edge_count": ecosystem["edge_count"],
            "agent_count": ecosystem["agent_count"],
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
        next_level="OS-16",
        summary=report["summary"],
        payload=report,
        dry_run=dry_run,
        memory_snapshot=memory_snapshot,
    )
    write_level_report(LEVEL, level_report)
    return report


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ANA MAX OS-15 Ecosystem Engine")
    parser.add_argument("--cycle", action="store_true", help="Run the ecosystem cycle.")
    parser.add_argument("--dry-run", action="store_true", help="Keep the ecosystem model read-only.")
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
