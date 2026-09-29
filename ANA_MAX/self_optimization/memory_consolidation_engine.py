#!/usr/bin/env python3
"""ANA MAX memory consolidation engine."""

from __future__ import annotations

import argparse
import sys
import time
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ANA_MAX.self_optimization.memory_context import (
    CORE_MEMORY_PATH,
    CORE_MEMORY_SCHEMA,
    SYSTEM_REPORT_PATH,
    build_memory_context,
    load_core_memory,
    memory_context_summary,
    save_core_memory,
    update_memory_system_report,
)
from ANA_MAX.self_optimization.os3_common import print_raw_json
from ANA_MAX.self_optimization.osx_common import MEMORY_DIR, WORKSPACE_ROOT, read_json, utc_now

ENGINE_NAME = "memory_consolidation_engine"
REPORT_SCHEMA = "ana.memory.consolidation.report.v1"

INPUTS = {
    "evaluation": MEMORY_DIR / "self_evaluation_report.json",
    "reasoning": MEMORY_DIR / "self_reasoning_report.json",
    "evolution": MEMORY_DIR / "evolution_report.json",
    "skills": MEMORY_DIR / "self_skills_report.json",
    "graph": MEMORY_DIR / "knowledge_graph.json",
    "daemon": MEMORY_DIR / "os4_daemon_report.json",
    "goals": MEMORY_DIR / "self_goals.json",
    "strategy": MEMORY_DIR / "evolution_strategy.json",
    "consistency": MEMORY_DIR / "self_consistency_report.json",
}


def _load_inputs() -> dict[str, dict[str, Any]]:
    return {name: read_json(path, {}) for name, path in INPUTS.items()}


def _summary(report: Any) -> dict[str, Any]:
    summary = report.get("summary", {}) if isinstance(report, dict) else {}
    return summary if isinstance(summary, dict) else {}


def _goal_ids(goals_report: dict[str, Any]) -> list[str]:
    goals = goals_report.get("goals", []) if isinstance(goals_report, dict) else []
    goal_ids = [goal.get("id") for goal in goals if isinstance(goal, dict) and goal.get("id")]
    return [str(goal_id) for goal_id in goal_ids]


def _strategy_phase_order(strategy_report: dict[str, Any]) -> list[str]:
    phase_order = strategy_report.get("phase_order", []) if isinstance(strategy_report, dict) else []
    return [str(item) for item in phase_order if item is not None] if isinstance(phase_order, list) else []


def _extract_signals(inputs: dict[str, dict[str, Any]], core_memory: dict[str, Any]) -> dict[str, Any]:
    evaluation = _summary(inputs["evaluation"])
    reasoning = inputs["reasoning"] if isinstance(inputs["reasoning"], dict) else {}
    evolution = inputs["evolution"] if isinstance(inputs["evolution"], dict) else {}
    skills = _summary(inputs["skills"])
    graph = inputs["graph"].get("metadata", {}) if isinstance(inputs["graph"], dict) else {}
    daemon = inputs["daemon"] if isinstance(inputs["daemon"], dict) else {}
    daemon_summary = daemon.get("summary", {}) if isinstance(daemon.get("summary", {}), dict) else {}
    if not daemon_summary and isinstance(daemon.get("cycles", []), list):
        last_cycle = daemon["cycles"][-1] if daemon["cycles"] else {}
        daemon_summary = last_cycle.get("summary", {}) if isinstance(last_cycle, dict) else {}
    goals = inputs["goals"] if isinstance(inputs["goals"], dict) else {}
    strategy = inputs["strategy"] if isinstance(inputs["strategy"], dict) else {}
    consistency = inputs["consistency"] if isinstance(inputs["consistency"], dict) else {}

    goal_ids = _goal_ids(goals)
    goal_count = len(goal_ids)
    stable_goal_count = sum(
        1
        for goal in goals.get("goals", [])
        if isinstance(goal, dict) and goal.get("status") in {"stable", "monitoring"}
    )
    active_goal_count = max(goal_count - stable_goal_count, 0)

    graph_nodes = int(graph.get("total_nodes", 0) or 0)
    graph_edges = int(graph.get("total_edges", 0) or 0)
    graph_density = round(graph_edges / max(graph_nodes, 1), 3)
    health_score = int(evaluation.get("health_score", 0) or 0)
    warning_count = int(evaluation.get("warning_count", 0) or 0)
    parse_error_count = int(skills.get("parse_error_count", 0) or 0)
    evolution_success = bool(evolution.get("overall_success", True))
    daemon_success = bool(daemon.get("overall_success", True))
    daemon_failed_cycles = int(daemon_summary.get("failed_cycles", 0) or 0)
    daemon_failed_phases = int(daemon_summary.get("failed_phases", 0) or 0)
    strategy_phase_order = _strategy_phase_order(strategy)
    reasoning_strategy_count = len(reasoning.get("strategies", [])) if isinstance(reasoning.get("strategies", []), list) else 0
    reasoning_hypotheses = len(reasoning.get("hypotheses", [])) if isinstance(reasoning.get("hypotheses", []), list) else 0

    patterns = deepcopy(core_memory.get("patterns", {})) if isinstance(core_memory.get("patterns", {}), dict) else {}
    goal_frequency = Counter(patterns.get("goal_frequency", {})) if isinstance(patterns.get("goal_frequency", {}), dict) else Counter()
    for goal_id in goal_ids:
        goal_frequency[goal_id] += 1

    issue_frequency = Counter(patterns.get("issue_frequency", {})) if isinstance(patterns.get("issue_frequency", {}), dict) else Counter()
    stable_cycle = health_score >= 100 and warning_count == 0 and parse_error_count == 0 and evolution_success and daemon_success
    if stable_cycle:
        issue_frequency["stable_cycles"] += 1
    if warning_count > 0:
        issue_frequency["warning_cycles"] += 1
    if parse_error_count > 0:
        issue_frequency["parse_error_cycles"] += 1
    if not evolution_success:
        issue_frequency["evolution_failure_cycles"] += 1
    if not daemon_success:
        issue_frequency["daemon_failure_cycles"] += 1

    return {
        "health_score": health_score,
        "warning_count": warning_count,
        "parse_error_count": parse_error_count,
        "evolution_overall_success": evolution_success,
        "daemon_overall_success": daemon_success,
        "graph_nodes": graph_nodes,
        "graph_edges": graph_edges,
        "graph_density": graph_density,
        "goal_count": goal_count,
        "goal_ids": goal_ids,
        "stable_goal_count": stable_goal_count,
        "active_goal_count": active_goal_count,
        "strategy_phase_count": len(strategy_phase_order),
        "strategy_phase_order": strategy_phase_order,
        "reasoning_strategy_count": reasoning_strategy_count,
        "reasoning_hypothesis_count": reasoning_hypotheses,
        "daemon_failed_cycles": daemon_failed_cycles,
        "daemon_failed_phases": daemon_failed_phases,
        "goal_frequency": dict(goal_frequency),
        "issue_frequency": dict(issue_frequency),
        "consistency_present": bool(consistency),
        "consistency_overall_consistent": bool(consistency.get("overall_consistent", True)) if isinstance(consistency, dict) else True,
        "consistency_contradiction_count": len(consistency.get("contradictions", [])) if isinstance(consistency.get("contradictions", []), list) else 0,
        "consistency_regression_count": len(consistency.get("regressions", [])) if isinstance(consistency.get("regressions", []), list) else 0,
    }


def _apply_preferences(core_memory: dict[str, Any], signals: dict[str, Any]) -> dict[str, Any]:
    patterns = core_memory.setdefault("patterns", {})
    if not isinstance(patterns, dict):
        patterns = {}
        core_memory["patterns"] = patterns

    stable_cycles = int(signals.get("issue_frequency", {}).get("stable_cycles", 0) or 0)
    warning_cycles = int(signals.get("issue_frequency", {}).get("warning_cycles", 0) or 0)
    parse_error_cycles = int(signals.get("issue_frequency", {}).get("parse_error_cycles", 0) or 0)
    evolution_failure_cycles = int(signals.get("issue_frequency", {}).get("evolution_failure_cycles", 0) or 0)
    daemon_failure_cycles = int(signals.get("issue_frequency", {}).get("daemon_failure_cycles", 0) or 0)

    patterns["stable_cycles"] = stable_cycles
    patterns["warning_cycles"] = warning_cycles
    patterns["parse_error_cycles"] = parse_error_cycles
    patterns["evolution_failure_cycles"] = evolution_failure_cycles
    patterns["daemon_failure_cycles"] = daemon_failure_cycles
    patterns["goal_frequency"] = signals.get("goal_frequency", {})
    patterns["issue_frequency"] = signals.get("issue_frequency", {})

    preferences = core_memory.setdefault("preferences", {})
    if not isinstance(preferences, dict):
        preferences = {}
        core_memory["preferences"] = preferences

    if signals["warning_count"] > 0 or signals["parse_error_count"] > 0 or not signals["evolution_overall_success"]:
        preferences["stability_priority"] = "high"
        preferences["warnings_tolerance"] = "zero"
        preferences["evolution_aggressiveness"] = "low"
    elif stable_cycles >= 3:
        preferences["stability_priority"] = "high"
        preferences["warnings_tolerance"] = "zero"
        preferences["evolution_aggressiveness"] = "medium"
    else:
        preferences["stability_priority"] = "high"
        preferences["warnings_tolerance"] = "zero"
        preferences["evolution_aggressiveness"] = "low"

    preferences["goal_persistence"] = "high"
    preferences["memory_consolidation"] = "bounded"
    return core_memory


def _apply_long_term(core_memory: dict[str, Any], signals: dict[str, Any], inputs: dict[str, dict[str, Any]], generated_at: str) -> dict[str, Any]:
    long_term = core_memory.setdefault("long_term", {})
    if not isinstance(long_term, dict):
        long_term = {}
        core_memory["long_term"] = long_term

    long_term.update(
        {
            "last_consolidation": generated_at,
            "last_health_score": signals["health_score"],
            "last_warning_count": signals["warning_count"],
            "last_parse_error_count": signals["parse_error_count"],
            "last_overall_success": signals["evolution_overall_success"],
            "last_daemon_success": signals["daemon_overall_success"],
            "last_graph_nodes": signals["graph_nodes"],
            "last_graph_edges": signals["graph_edges"],
            "last_graph_density": signals["graph_density"],
            "last_goal_count": signals["goal_count"],
            "last_strategy_phase_count": signals["strategy_phase_count"],
            "last_strategy_phase_order": signals["strategy_phase_order"],
            "last_reasoning_strategy_count": signals["reasoning_strategy_count"],
            "last_reasoning_hypothesis_count": signals["reasoning_hypothesis_count"],
            "last_consistency_overall_consistent": signals["consistency_overall_consistent"],
            "last_consistency_contradiction_count": signals["consistency_contradiction_count"],
            "last_consistency_regression_count": signals["consistency_regression_count"],
            "goal_frequency": signals["goal_frequency"],
            "current_goal_ids": signals["goal_ids"],
            "strategy_phase_order": signals["strategy_phase_order"],
        }
    )

    short_term = core_memory.setdefault("short_term", {})
    if not isinstance(short_term, dict):
        short_term = {}
        core_memory["short_term"] = short_term
    short_term["last_cycle"] = {
        "timestamp": generated_at,
        "health_score": signals["health_score"],
        "warning_count": signals["warning_count"],
        "parse_error_count": signals["parse_error_count"],
        "overall_success": signals["evolution_overall_success"],
        "daemon_success": signals["daemon_overall_success"],
        "goal_count": signals["goal_count"],
        "strategy_phase_count": signals["strategy_phase_count"],
        "consistency_present": signals["consistency_present"],
        "consistency_overall_consistent": signals["consistency_overall_consistent"],
    }

    history = core_memory.setdefault("history", [])
    if not isinstance(history, list):
        history = []
        core_memory["history"] = history
    history.append(
        {
            "timestamp": generated_at,
            "signals": {
                "health_score": signals["health_score"],
                "warning_count": signals["warning_count"],
                "parse_error_count": signals["parse_error_count"],
                "overall_success": signals["evolution_overall_success"],
                "daemon_success": signals["daemon_overall_success"],
                "goal_count": signals["goal_count"],
                "strategy_phase_count": signals["strategy_phase_count"],
                "graph_density": signals["graph_density"],
                "consistency_overall_consistent": signals["consistency_overall_consistent"],
            },
            "preferences": {
                "stability_priority": core_memory.get("preferences", {}).get("stability_priority"),
                "warnings_tolerance": core_memory.get("preferences", {}).get("warnings_tolerance"),
                "evolution_aggressiveness": core_memory.get("preferences", {}).get("evolution_aggressiveness"),
            },
            "goal_ids": signals.get("goal_ids", [])[:10],
            "current_goal_ids": signals.get("goal_ids", [])[:10],
        }
    )
    core_memory["history"] = history[-200:]
    core_memory["schema"] = CORE_MEMORY_SCHEMA
    return core_memory


def consolidate(*, dry_run: bool = False) -> dict[str, Any]:
    started = time.perf_counter()
    generated_at = utc_now()
    inputs = _load_inputs()
    core_memory = load_core_memory()
    context = build_memory_context(core_memory)
    signals = _extract_signals(inputs, core_memory)
    core_memory = _apply_preferences(core_memory, signals)
    core_memory = _apply_long_term(core_memory, signals, inputs, generated_at)

    notes = [
        f"stable_cycles={signals['issue_frequency'].get('stable_cycles', 0)}",
        f"warning_cycles={signals['issue_frequency'].get('warning_cycles', 0)}",
        f"parse_error_cycles={signals['issue_frequency'].get('parse_error_cycles', 0)}",
        f"goal_count={signals['goal_count']}",
        f"strategy_phase_count={signals['strategy_phase_count']}",
    ]
    status = "OK" if signals["health_score"] >= 100 and signals["warning_count"] == 0 and signals["parse_error_count"] == 0 and signals["evolution_overall_success"] else "DEGRADED"
    system_report = update_memory_system_report(
        status=status,
        notes=notes,
        last_consolidation=generated_at,
        dry_run=dry_run,
    )

    if not dry_run:
        save_core_memory(core_memory, dry_run=False)

    report = {
        "schema": REPORT_SCHEMA,
        "engine": ENGINE_NAME,
        "generated_at": generated_at,
        "dry_run": dry_run,
        "workspace_root": str(WORKSPACE_ROOT),
        "inputs": {name: str(path) for name, path in INPUTS.items()},
        "core_memory_path": str(CORE_MEMORY_PATH),
        "system_report_path": str(SYSTEM_REPORT_PATH),
        "core_memory_schema_ok": core_memory.get("schema") == CORE_MEMORY_SCHEMA,
        "memory_context": memory_context_summary(context),
        "signals": signals,
        "long_term": deepcopy(core_memory.get("long_term", {})),
        "short_term": deepcopy(core_memory.get("short_term", {})),
        "preferences": deepcopy(core_memory.get("preferences", {})),
        "patterns": deepcopy(core_memory.get("patterns", {})),
        "history_length": len(core_memory.get("history", [])) if isinstance(core_memory.get("history", []), list) else 0,
        "system_report": system_report,
        "summary": {
            "health_score": signals["health_score"],
            "warning_count": signals["warning_count"],
            "parse_error_count": signals["parse_error_count"],
            "goal_count": signals["goal_count"],
            "strategy_phase_count": signals["strategy_phase_count"],
            "stable_cycles": signals["issue_frequency"].get("stable_cycles", 0),
            "warning_cycles": signals["issue_frequency"].get("warning_cycles", 0),
            "overall_status": status,
        },
        "written": not dry_run,
    }
    report["verification"] = {
        "passed": all(
            [
                report["schema"] == REPORT_SCHEMA,
                report["core_memory_schema_ok"],
                isinstance(report.get("memory_context"), dict),
                isinstance(report.get("signals"), dict),
                isinstance(report.get("summary"), dict),
                isinstance(report.get("system_report"), dict),
            ]
        ),
        "checks": {
            "schema_present": report["schema"] == REPORT_SCHEMA,
            "core_memory_schema_ok": report["core_memory_schema_ok"],
            "memory_context_present": isinstance(report.get("memory_context"), dict),
            "signals_present": isinstance(report.get("signals"), dict),
            "summary_present": isinstance(report.get("summary"), dict),
            "system_report_present": isinstance(report.get("system_report"), dict),
        },
    }
    report["elapsed_ms"] = round((time.perf_counter() - started) * 1000, 2)
    return report


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ANA MAX memory consolidation engine")
    parser.add_argument("--cycle", action="store_true", help="Run a consolidation cycle.")
    parser.add_argument("--dry-run", action="store_true", help="Compute without writing core memory.")
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    if not args.cycle:
        return 0
    result = consolidate(dry_run=args.dry_run)
    print_raw_json(result)
    return 0 if result.get("verification", {}).get("passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
