#!/usr/bin/env python3
"""ANA MAX OS-20 Personal AI Studio."""

from __future__ import annotations

import argparse
import time
from typing import Any

try:
    from ANA_MAX.context import context_injector
except Exception:
    context_injector = None

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

ENGINE_NAME = "personal_ai_studio"
LEVEL = 20
LEVEL_SCHEMA = "ana.os20.personal_ai_studio.v1"
REPORT_PATH = level_report_path(LEVEL).with_name("personal_ai_studio_report.json")


def _context_bundle() -> dict[str, Any]:
    if context_injector is None:
        return {"schema": "ana.context.bundle.v1", "error": "module_missing"}
    try:
        return context_injector.build_context_bundle()
    except Exception as exc:
        return {"schema": "ana.context.bundle.v1", "error": str(exc)}


def _agent_bootstrap_prompt() -> str:
    if context_injector is None:
        return ""
    try:
        return context_injector.export_agent_bootstrap_prompt()
    except Exception:
        return ""


def _load_level_reports() -> dict[str, Any]:
    levels: dict[str, Any] = {}
    for level in range(11, 21):
        path = level_report_path(level)
        levels[f"OS-{level}"] = {
            "exists": path.exists(),
            "path": str(path),
            "report": read_json(path, {}),
        }
    return levels


def _final_summary(
    baseline: dict[str, Any],
    memory_snapshot: dict[str, Any],
    agent_registry: dict[str, Any],
    distributed_topology: dict[str, Any],
    levels: dict[str, Any],
) -> dict[str, Any]:
    registry_agents = agent_registry.get("agents", {}) if isinstance(agent_registry, dict) else {}
    distributed_summary = distributed_topology.get("summary", {}) if isinstance(distributed_topology, dict) else {}
    multi_agent_status = "OK" if agent_registry.get("summary", {}).get("failure_count_total", 1) == 0 else "DEGRADED"
    distributed_status = "OK" if distributed_summary.get("agent_failure_count", 1) == 0 and distributed_summary.get("node_count", 0) >= 3 else "DEGRADED"
    memory_system = memory_snapshot.get("memory_system", {}) if isinstance(memory_snapshot, dict) else {}
    return {
        "health_score": baseline.get("health_score", 0),
        "warnings": baseline.get("warnings", 0),
        "parse_error_count": baseline.get("parse_error_count", 0),
        "memory_system_status": memory_system.get("status", "UNKNOWN"),
        "multi_agent_status": multi_agent_status,
        "distributed_status": distributed_status,
        "agent_count": len(registry_agents) if isinstance(registry_agents, dict) else 0,
        "level_count": len(levels),
    }


def run_cycle(*, dry_run: bool = True) -> dict[str, Any]:
    started = time.perf_counter()
    memory_snapshot = build_memory_snapshot()
    baseline = baseline_metrics()
    agent_registry = agent_registry_snapshot()
    distributed_topology = read_json(REPORT_PATH.parent / "distributed_topology.json", {})
    levels = _load_level_reports()
    context_bundle = _context_bundle()
    agent_bootstrap_prompt = _agent_bootstrap_prompt()
    final_summary = _final_summary(baseline, memory_snapshot, agent_registry, distributed_topology, levels)
    report_count = sum(1 for level in levels.values() if level.get("exists"))
    missing_levels = [name for name, data in levels.items() if not data.get("exists")]
    overall_success = (
        baseline.get("health_score", 0) == 100
        and baseline.get("warnings", 0) == 0
        and baseline.get("parse_error_count", 0) == 0
        and final_summary["memory_system_status"] == "OK"
        and final_summary["multi_agent_status"] == "OK"
        and final_summary["distributed_status"] == "OK"
    )

    report = {
        "schema": LEVEL_SCHEMA,
        "generated_at": utc_now(),
        "engine": ENGINE_NAME,
        "workspace_root": str(WORKSPACE_ROOT),
        "dry_run": dry_run,
        "memory_snapshot": memory_snapshot,
        "agent_registry": agent_registry,
        "distributed_topology": distributed_topology,
        "levels": levels,
        "context_bundle": context_bundle,
        "agent_bootstrap_prompt": agent_bootstrap_prompt,
        "final_summary": final_summary,
        "summary": {
            "report_count": report_count,
            "missing_level_count": len(missing_levels),
            "health_score": baseline.get("health_score", 0),
            "warnings": baseline.get("warnings", 0),
            "parse_error_count": baseline.get("parse_error_count", 0),
            "memory_system_status": final_summary["memory_system_status"],
            "multi_agent_status": final_summary["multi_agent_status"],
            "distributed_status": final_summary["distributed_status"],
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
        next_level=None,
        summary=report["summary"],
        payload=report,
        dry_run=dry_run,
        memory_snapshot=memory_snapshot,
    )
    write_level_report(LEVEL, level_report)
    return report


def _stdout_view(report: dict[str, Any]) -> dict[str, Any]:
    context_bundle = report.get("context_bundle", {})
    context_summary = context_bundle.get("summary", {}) if isinstance(context_bundle, dict) else {}
    return {
        "schema": report.get("schema"),
        "generated_at": report.get("generated_at"),
        "engine": report.get("engine"),
        "workspace_root": report.get("workspace_root"),
        "dry_run": report.get("dry_run"),
        "summary": report.get("summary", {}),
        "final_summary": report.get("final_summary", {}),
        "context_bundle": {
            "schema": context_bundle.get("schema") if isinstance(context_bundle, dict) else None,
            "summary": context_summary,
        },
        "agent_bootstrap_prompt": report.get("agent_bootstrap_prompt", ""),
        "report_path": report.get("report_path"),
    }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ANA MAX OS-20 Personal AI Studio")
    parser.add_argument("--cycle", action="store_true", help="Run the studio cycle.")
    parser.add_argument("--dry-run", action="store_true", help="Keep the studio read-only.")
    return parser


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()
    dry_run = args.dry_run or not args.cycle
    result = run_cycle(dry_run=dry_run)
    emit_raw_json(_stdout_view(result))
    return 0 if result.get("summary", {}).get("overall_success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
