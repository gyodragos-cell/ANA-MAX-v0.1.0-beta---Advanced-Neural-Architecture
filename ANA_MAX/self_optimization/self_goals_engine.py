#!/usr/bin/env python3
"""ANA MAX OS-5 Self-Directed Goals + Strategy Engine."""

from __future__ import annotations

import argparse
import time
from copy import deepcopy
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from ANA_MAX.self_optimization.os3_common import print_raw_json
from ANA_MAX.self_optimization.osx_common import (
    DOCS_DIR,
    MEMORY_DIR,
    WORKSPACE_ROOT,
    ensure_dir,
    read_json,
    utc_now,
    write_json,
)

ENGINE_NAME = "self_goals_engine"
GOALS_SCHEMA = "ana.os5.goals.v1"
STRATEGY_SCHEMA = "ana.os5.strategy.v1"
ENGINE_SCHEMA = "ana.os5.goals_engine.v1"
LEVEL_REPORT_SCHEMA = "ana.os5.level_report.v1"

GOALS_PATH = MEMORY_DIR / "self_goals.json"
STRATEGY_PATH = MEMORY_DIR / "evolution_strategy.json"
LEVEL_REPORT_PATH = MEMORY_DIR / "os_level_OS5_report.json"
INPUTS = {
    "reasoning": MEMORY_DIR / "self_reasoning_report.json",
    "evolution": MEMORY_DIR / "evolution_report.json",
    "evaluation": MEMORY_DIR / "self_evaluation_report.json",
    "skills": MEMORY_DIR / "self_skills_report.json",
    "graph": MEMORY_DIR / "knowledge_graph.json",
    "daemon": MEMORY_DIR / "os4_daemon_report.json",
    "consistency": MEMORY_DIR / "self_consistency_report.json",
}

DEFAULT_PHASE_ORDER = [
    "profiling",
    "skills",
    "structuring",
    "healing",
    "evaluation",
    "reasoning",
    "goals",
    "strategy_refresh",
    "knowledge_graph",
    "toolchain_discovery",
    "daemon_loop",
]


@dataclass
class GoalRecord:
    id: str
    objective: str
    priority: str
    status: str
    metric: str
    target: str
    rationale: str
    evidence: list[str]
    progress: int


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _goal_status(current: Any, target: Any, comparator: str = "eq") -> str:
    if comparator == "eq":
        return "stable" if current == target else "active"
    if comparator == "lte":
        return "stable" if _to_float(current) <= _to_float(target) else "at_risk"
    if comparator == "gte":
        return "stable" if _to_float(current) >= _to_float(target) else "active"
    return "active"


def load_inputs() -> dict[str, dict[str, Any]]:
    return {name: read_json(path, {}) for name, path in INPUTS.items()}


def _eval_summary(report: dict[str, Any]) -> dict[str, Any]:
    summary = report.get("summary", {})
    if not isinstance(summary, dict):
        return {}
    return summary


def _daemon_summary(report: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(report, dict):
        return {}
    summary = report.get("cycles", [])
    last_cycle = summary[-1] if summary else {}
    if isinstance(last_cycle, dict):
        return last_cycle.get("summary", {}) if isinstance(last_cycle.get("summary", {}), dict) else {}
    return {}


def _graph_metadata(report: dict[str, Any]) -> dict[str, Any]:
    meta = report.get("metadata", {})
    return meta if isinstance(meta, dict) else {}


def _default_goals(inputs: dict[str, dict[str, Any]]) -> list[GoalRecord]:
    evaluation = _eval_summary(inputs["evaluation"])
    skills = _eval_summary(inputs["skills"])
    graph = _graph_metadata(inputs["graph"])
    reasoning = inputs["reasoning"] if isinstance(inputs["reasoning"], dict) else {}
    evolution = inputs["evolution"] if isinstance(inputs["evolution"], dict) else {}
    daemon = _daemon_summary(inputs["daemon"])

    health_score = _to_int(evaluation.get("health_score"), 0)
    warning_count = _to_int(evaluation.get("warning_count"), 0)
    parse_error_count = _to_int(skills.get("parse_error_count"), 0)
    graph_nodes = _to_int(graph.get("total_nodes"), 0)
    graph_edges = _to_int(graph.get("total_edges"), 0)
    daemon_success = bool(inputs["daemon"].get("overall_success", True))
    daemon_cycles = len(inputs["daemon"].get("cycles", [])) if isinstance(inputs["daemon"].get("cycles", []), list) else 0
    evolution_success = bool(inputs["evolution"].get("overall_success", True))
    reasoning_hypotheses = len(inputs["reasoning"].get("hypotheses", [])) if isinstance(inputs["reasoning"].get("hypotheses", []), list) else 0

    graph_density = round(graph_edges / max(graph_nodes, 1), 3)
    goals: list[GoalRecord] = [
        GoalRecord(
            id="preserve_os_baseline",
            objective="Keep health_score at 100 with warning_count at 0.",
            priority="critical",
            status=_goal_status(health_score, 100),
            metric="health_score",
            target="100",
            rationale="OS-3/OS-4 baseline is the stability contract for every later layer.",
            evidence=[
                f"health_score={health_score}",
                f"warning_count={warning_count}",
            ],
            progress=100 if health_score >= 100 and warning_count == 0 else max(0, 100 - warning_count * 10),
        ),
        GoalRecord(
            id="keep_parse_errors_zero",
            objective="Maintain parse_error_count at 0 across skills and orchestration reports.",
            priority="high",
            status=_goal_status(parse_error_count, 0),
            metric="parse_error_count",
            target="0",
            rationale="Parsed reports must stay clean so later layers can compose safely.",
            evidence=[f"parse_error_count={parse_error_count}"],
            progress=100 if parse_error_count == 0 else max(0, 100 - parse_error_count * 20),
        ),
        GoalRecord(
            id="preserve_daemon_stability",
            objective="Keep daemon cycles bounded and successful.",
            priority="high",
            status="stable" if daemon_success else "at_risk",
            metric="daemon_overall_success",
            target="true",
            rationale="Repeated bounded cycles are the safest local automation contract.",
            evidence=[
                f"daemon_success={daemon_success}",
                f"daemon_cycles={daemon_cycles}",
            ],
            progress=100 if daemon_success else 40,
        ),
        GoalRecord(
            id="preserve_graph_quality",
            objective="Keep knowledge graph dense enough for routing but additive-only.",
            priority="medium",
            status="stable" if graph_nodes and graph_edges else "active",
            metric="graph_density",
            target="maintain",
            rationale="Graph structure should remain analyzable as later layers read it.",
            evidence=[
                f"graph_nodes={graph_nodes}",
                f"graph_edges={graph_edges}",
                f"graph_density={graph_density}",
            ],
            progress=100 if graph_nodes and graph_edges else 50,
        ),
        GoalRecord(
            id="prepare_os6_adaptation",
            objective="Keep the system ready for meta-adaptation, policy, and enterprise layers.",
            priority="medium",
            status="stable" if evolution_success and reasoning_hypotheses >= 0 else "active",
            metric="evolution_success",
            target="true",
            rationale="Later OS layers depend on current reports being readable and additive.",
            evidence=[
                f"evolution_overall_success={evolution_success}",
                f"reasoning_hypotheses={reasoning_hypotheses}",
            ],
            progress=100 if evolution_success else 60,
        ),
    ]

    if graph_density > 8:
        goals.append(
            GoalRecord(
                id="watch_graph_density",
                objective="Track hot nodes and graph density so future refactors stay additive.",
                priority="medium",
                status="monitoring",
                metric="graph_density",
                target="<= 8.0",
                rationale="Dense graphs can become hard to reason about as layers grow.",
                evidence=[f"graph_density={graph_density}"],
                progress=70,
            )
        )

    if reasoning.get("strategies"):
        goals.append(
            GoalRecord(
                id="respect_reasoning_hints",
                objective="Feed reasoning-derived hints into the strategy layer.",
                priority="medium",
                status="stable",
                metric="reasoning_strategy_hints",
                target="present",
                rationale="The reasoning engine already synthesizes signals that the goals layer can reuse.",
                evidence=[f"reasoning_strategies={len(reasoning.get('strategies', []))}"],
                progress=100,
            )
        )

    return goals


def _merge_existing_goals(goals: list[GoalRecord], existing: dict[str, Any]) -> list[GoalRecord]:
    existing_goals = existing.get("goals", [])
    if not isinstance(existing_goals, list):
        return goals
    existing_by_id = {
        item.get("id"): item
        for item in existing_goals
        if isinstance(item, dict) and item.get("id")
    }
    merged: list[GoalRecord] = []
    for goal in goals:
        previous = existing_by_id.get(goal.id, {})
        status = previous.get("status", goal.status)
        progress = _to_int(previous.get("progress", goal.progress), goal.progress)
        evidence = goal.evidence[:]
        if isinstance(previous.get("evidence"), list):
            evidence = list(dict.fromkeys([*evidence, *[str(item) for item in previous["evidence"]]]))
        merged.append(
            GoalRecord(
                id=goal.id,
                objective=goal.objective,
                priority=goal.priority,
                status=status,
                metric=goal.metric,
                target=goal.target,
                rationale=goal.rationale,
                evidence=evidence,
                progress=progress,
            )
        )
    return merged


def _build_metrics(inputs: dict[str, dict[str, Any]]) -> dict[str, Any]:
    evaluation = _eval_summary(inputs["evaluation"])
    skills = _eval_summary(inputs["skills"])
    graph = _graph_metadata(inputs["graph"])
    daemon = _daemon_summary(inputs["daemon"])
    reasoning = inputs["reasoning"] if isinstance(inputs["reasoning"], dict) else {}

    graph_nodes = _to_int(graph.get("total_nodes"), 0)
    graph_edges = _to_int(graph.get("total_edges"), 0)

    return {
        "health_score": _to_int(evaluation.get("health_score"), 0),
        "warning_count": _to_int(evaluation.get("warning_count"), 0),
        "parse_error_count": _to_int(skills.get("parse_error_count"), 0),
        "graph_nodes": graph_nodes,
        "graph_edges": graph_edges,
        "graph_density": round(graph_edges / max(graph_nodes, 1), 3),
        "daemon_cycles": len(inputs["daemon"].get("cycles", [])) if isinstance(inputs["daemon"].get("cycles", []), list) else 0,
        "daemon_success": bool(inputs["daemon"].get("overall_success", True)),
        "daemon_last_cycle_success": bool(daemon.get("success", True)) if daemon else bool(inputs["daemon"].get("overall_success", True)),
        "evolution_overall_success": bool(inputs["evolution"].get("overall_success", True)),
        "reasoning_hypotheses": len(reasoning.get("hypotheses", [])) if isinstance(reasoning.get("hypotheses", []), list) else 0,
        "reasoning_strategies": len(reasoning.get("strategies", [])) if isinstance(reasoning.get("strategies", []), list) else 0,
        "reasoning_priorities": len(reasoning.get("priorities", [])) if isinstance(reasoning.get("priorities", []), list) else 0,
    }


def _build_goal_report(inputs: dict[str, dict[str, Any]], *, existing: dict[str, Any]) -> dict[str, Any]:
    goals = _merge_existing_goals(_default_goals(inputs), existing)
    metrics = _build_metrics(inputs)
    consistency = inputs.get("consistency", {}) if isinstance(inputs.get("consistency", {}), dict) else {}
    consistency_contradictions = len(consistency.get("contradictions", [])) if isinstance(consistency.get("contradictions", []), list) else 0
    consistency_regressions = len(consistency.get("regressions", [])) if isinstance(consistency.get("regressions", []), list) else 0
    consistency_overall = bool(consistency.get("overall_consistent", True))

    if consistency_contradictions or consistency_regressions or not consistency_overall:
        goals.append(
            GoalRecord(
                id="restore_memory_consistency",
                objective="Keep core memory, reports, and latest signals consistent.",
                priority="high",
                status="active",
                metric="memory_consistency",
                target="consistent",
                rationale="The optional self-consistency report flagged drift or contradictions.",
                evidence=[
                    f"contradictions={consistency_contradictions}",
                    f"regressions={consistency_regressions}",
                    f"overall_consistent={consistency_overall}",
                ],
                progress=50,
            )
        )

    satisfied = sum(1 for goal in goals if goal.status in {"stable", "monitoring"})
    active = sum(1 for goal in goals if goal.status not in {"stable", "monitoring"})
    return {
        "schema": GOALS_SCHEMA,
        "generated_at": utc_now(),
        "engine": ENGINE_NAME,
        "workspace_root": str(WORKSPACE_ROOT),
        "source_reports": {name: str(path) for name, path in INPUTS.items()},
        "goals": [asdict(goal) for goal in goals],
        "metrics": metrics,
        "status": {
            "overall": "stable" if metrics["health_score"] >= 100 and metrics["warning_count"] == 0 else "watch",
            "goal_count": len(goals),
            "stable_goal_count": satisfied,
            "active_goal_count": active,
        },
    }


def _build_strategy_report(inputs: dict[str, dict[str, Any]], goals_report: dict[str, Any]) -> dict[str, Any]:
    metrics = goals_report["metrics"]
    consistency = inputs.get("consistency", {}) if isinstance(inputs.get("consistency", {}), dict) else {}
    consistency_contradictions = len(consistency.get("contradictions", [])) if isinstance(consistency.get("contradictions", []), list) else 0
    consistency_regressions = len(consistency.get("regressions", [])) if isinstance(consistency.get("regressions", []), list) else 0
    priorities = [
        {
            "rank": 1,
            "goal_id": "preserve_os_baseline",
            "priority": "critical",
            "reason": "Baseline health must stay at 100 and warnings at 0.",
        },
        {
            "rank": 2,
            "goal_id": "keep_parse_errors_zero",
            "priority": "high",
            "reason": "Parse-free reports keep later OS layers safe and deterministic.",
        },
        {
            "rank": 3,
            "goal_id": "preserve_daemon_stability",
            "priority": "high",
            "reason": "Bounded daemon cycles are the automation control point.",
        },
        {
            "rank": 4,
            "goal_id": "preserve_graph_quality",
            "priority": "medium",
            "reason": "Graph quality drives later routing, policy, and orchestration layers.",
        },
    ]
    if metrics["graph_density"] > 8:
        priorities.append(
            {
                "rank": 5,
                "goal_id": "watch_graph_density",
                "priority": "medium",
                "reason": "The graph is becoming dense enough to watch for refactor candidates.",
            }
        )
    if metrics["reasoning_strategies"]:
        priorities.append(
            {
                "rank": 6,
                "goal_id": "respect_reasoning_hints",
                "priority": "medium",
                "reason": "Reasoning already provides local hints for the goals layer.",
            }
        )
    if consistency_contradictions or consistency_regressions or not bool(consistency.get("overall_consistent", True)):
        priorities.insert(
            0,
            {
                "rank": 0,
                "goal_id": "restore_memory_consistency",
                "priority": "critical",
                "reason": "Memory contradictions should be stabilized before any new adaptation.",
            },
        )

    weights = {
        "stability": 0.40 if metrics["warning_count"] == 0 else 0.55,
        "safety": 0.25,
        "observability": 0.15,
        "automation": 0.10 + (0.05 if metrics["daemon_success"] else 0.0),
        "adaptation": 0.10 + (0.05 if metrics["reasoning_strategies"] else 0.0),
    }
    if consistency_contradictions or consistency_regressions or not bool(consistency.get("overall_consistent", True)):
        weights["stability"] = min(0.65, weights["stability"] + 0.10)
        weights["safety"] = min(0.35, weights["safety"] + 0.05)
    phase_order = [
        "profiling",
        "skills",
        "structuring",
        "healing",
        "evaluation",
        "reasoning",
        "goals",
        "strategy_refresh",
        "knowledge_graph",
        "toolchain_discovery",
        "daemon_loop",
    ]
    return {
        "schema": STRATEGY_SCHEMA,
        "generated_at": utc_now(),
        "engine": ENGINE_NAME,
        "workspace_root": str(WORKSPACE_ROOT),
        "source_reports": {name: str(path) for name, path in INPUTS.items()},
        "priorities": sorted(priorities, key=lambda item: item["rank"]),
        "weights": weights,
        "phase_order": phase_order,
        "last_update": utc_now(),
    }


def _load_existing_goal_artifacts() -> tuple[dict[str, Any], dict[str, Any]]:
    return read_json(GOALS_PATH, {}), read_json(STRATEGY_PATH, {})


def _verify(goal_report: dict[str, Any], strategy_report: dict[str, Any]) -> dict[str, Any]:
    checks = {
        "goals_schema": goal_report.get("schema") == GOALS_SCHEMA,
        "strategy_schema": strategy_report.get("schema") == STRATEGY_SCHEMA,
        "goals_present": isinstance(goal_report.get("goals"), list) and len(goal_report["goals"]) > 0,
        "priorities_present": isinstance(strategy_report.get("priorities"), list) and len(strategy_report["priorities"]) > 0,
        "phase_order_present": isinstance(strategy_report.get("phase_order"), list) and len(strategy_report["phase_order"]) > 0,
        "metrics_present": isinstance(goal_report.get("metrics"), dict),
    }
    return {"passed": all(checks.values()), "checks": checks}


def run_cycle(*, dry_run: bool = False) -> dict[str, Any]:
    started = time.perf_counter()
    inputs = load_inputs()
    existing_goals, existing_strategy = _load_existing_goal_artifacts()
    goal_report = _build_goal_report(inputs, existing=existing_goals)
    strategy_report = _build_strategy_report(inputs, goal_report)

    if isinstance(existing_strategy, dict) and existing_strategy.get("phase_order"):
        strategy_report["phase_order"] = existing_strategy["phase_order"]

    verification = _verify(goal_report, strategy_report)
    if not dry_run:
        write_json(GOALS_PATH, goal_report)
        write_json(STRATEGY_PATH, strategy_report)
        level_report = {
            "schema": LEVEL_REPORT_SCHEMA,
            "os_level": "OS-5",
            "status": "PASS" if verification["passed"] else "WARN",
            "next": "OS-6",
            "summary": {
                "goal_count": len(goal_report["goals"]),
                "stable_goals": goal_report["status"]["stable_goal_count"],
                "active_goals": goal_report["status"]["active_goal_count"],
                "phase_count": len(strategy_report["phase_order"]),
            },
            "goals_path": str(GOALS_PATH),
            "strategy_path": str(STRATEGY_PATH),
            "details": {
                "goals_engine": goal_report,
                "strategy": strategy_report,
            },
        }
        write_json(LEVEL_REPORT_PATH, level_report)

    result = {
        "schema": ENGINE_SCHEMA,
        "engine": ENGINE_NAME,
        "generated_at": utc_now(),
        "dry_run": dry_run,
        "goals_path": str(GOALS_PATH),
        "strategy_path": str(STRATEGY_PATH),
        "goals": goal_report,
        "strategy": strategy_report,
        "verification": verification,
        "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
        "summary": {
            "goal_count": len(goal_report["goals"]),
            "stable_goals": goal_report["status"]["stable_goal_count"],
            "active_goals": goal_report["status"]["active_goal_count"],
            "phase_count": len(strategy_report["phase_order"]),
        },
        "level_report_path": str(LEVEL_REPORT_PATH),
    }
    return result


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ANA MAX OS-5 Self-Directed Goals Engine")
    parser.add_argument("--cycle", action="store_true", help="Run the OS-5 goals cycle.")
    parser.add_argument("--dry-run", action="store_true", help="Compute without writing goal artifacts.")
    return parser


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()
    if not args.cycle:
        parser.print_help()
        return 0
    result = run_cycle(dry_run=args.dry_run)
    print_raw_json(result)
    return 0 if result.get("verification", {}).get("passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
