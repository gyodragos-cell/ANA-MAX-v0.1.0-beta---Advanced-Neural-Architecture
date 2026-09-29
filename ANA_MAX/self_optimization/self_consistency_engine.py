#!/usr/bin/env python3
"""ANA MAX memory consistency engine."""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ANA_MAX.self_optimization.memory_context import (
    CORE_MEMORY_PATH,
    SYSTEM_REPORT_PATH,
    build_memory_context,
    get_preference,
    load_core_memory,
    memory_context_summary,
    update_memory_system_report,
)
from ANA_MAX.self_optimization.os3_common import print_raw_json
from ANA_MAX.self_optimization.osx_common import MEMORY_DIR, WORKSPACE_ROOT, read_json, utc_now, write_json

ENGINE_NAME = "self_consistency_engine"
REPORT_SCHEMA = "ana.memory.self_consistency.v1"
REPORT_PATH = MEMORY_DIR / "self_consistency_report.json"

INPUTS = {
    "core_memory": CORE_MEMORY_PATH,
    "evaluation": MEMORY_DIR / "self_evaluation_report.json",
    "reasoning": MEMORY_DIR / "self_reasoning_report.json",
    "evolution": MEMORY_DIR / "evolution_report.json",
    "goals": MEMORY_DIR / "self_goals.json",
    "strategy": MEMORY_DIR / "evolution_strategy.json",
}


def _load_inputs() -> dict[str, dict[str, Any]]:
    return {name: read_json(path, {}) for name, path in INPUTS.items()}


def _summary(report: Any) -> dict[str, Any]:
    summary = report.get("summary", {}) if isinstance(report, dict) else {}
    return summary if isinstance(summary, dict) else {}


def _recent_history(core_memory: dict[str, Any], limit: int = 5) -> list[dict[str, Any]]:
    history = core_memory.get("history", []) if isinstance(core_memory, dict) else []
    return [item for item in history[-limit:] if isinstance(item, dict)] if isinstance(history, list) else []


def _latest_metrics(inputs: dict[str, dict[str, Any]]) -> dict[str, Any]:
    evaluation = _summary(inputs["evaluation"])
    reasoning = inputs["reasoning"] if isinstance(inputs["reasoning"], dict) else {}
    evolution = inputs["evolution"] if isinstance(inputs["evolution"], dict) else {}
    goals = inputs["goals"] if isinstance(inputs["goals"], dict) else {}
    strategy = inputs["strategy"] if isinstance(inputs["strategy"], dict) else {}

    strategy_phase_order = strategy.get("phase_order", []) if isinstance(strategy.get("phase_order", []), list) else []
    goal_status = goals.get("status", {}) if isinstance(goals.get("status", {}), dict) else {}
    reasoning_strategy_count = len(reasoning.get("strategies", [])) if isinstance(reasoning.get("strategies", []), list) else 0
    reasoning_hypothesis_count = len(reasoning.get("hypotheses", [])) if isinstance(reasoning.get("hypotheses", []), list) else 0

    return {
        "health_score": int(evaluation.get("health_score", 0) or 0),
        "warning_count": int(evaluation.get("warning_count", 0) or 0),
        "parse_error_count": int(_summary(inputs["evaluation"]).get("parse_error_count", 0) or 0),
        "evolution_overall_success": bool(evolution.get("overall_success", True)),
        "goal_status_overall": goal_status.get("overall"),
        "goal_count": len(goals.get("goals", [])) if isinstance(goals.get("goals", []), list) else 0,
        "strategy_phase_order": [str(item) for item in strategy_phase_order],
        "strategy_phase_count": len(strategy_phase_order),
        "reasoning_strategy_count": reasoning_strategy_count,
        "reasoning_hypothesis_count": reasoning_hypothesis_count,
    }


def _contradictions(core_memory: dict[str, Any], metrics: dict[str, Any], context: dict[str, Any]) -> list[dict[str, Any]]:
    contradictions: list[dict[str, Any]] = []
    long_term = core_memory.get("long_term", {}) if isinstance(core_memory.get("long_term", {}), dict) else {}
    preferences = core_memory.get("preferences", {}) if isinstance(core_memory.get("preferences", {}), dict) else {}
    previous_health = int(long_term.get("last_health_score", metrics["health_score"]) or metrics["health_score"])
    previous_warning_count = int(long_term.get("last_warning_count", metrics["warning_count"]) or metrics["warning_count"])
    previous_parse_errors = int(long_term.get("last_parse_error_count", metrics["parse_error_count"]) or metrics["parse_error_count"])
    previous_success = bool(long_term.get("last_overall_success", metrics["evolution_overall_success"]))
    previous_strategy_order = long_term.get("last_strategy_phase_order", [])

    if get_preference(context, "warnings_tolerance", "zero") == "zero" and metrics["warning_count"] > 0:
        contradictions.append(
            {
                "id": "warnings_tolerance_broken",
                "severity": "high",
                "evidence": [f"warnings_tolerance=zero", f"warning_count={metrics['warning_count']}"],
            }
        )
    if previous_health >= 100 and metrics["health_score"] < 100:
        contradictions.append(
            {
                "id": "health_score_regression",
                "severity": "high",
                "evidence": [f"previous_health={previous_health}", f"current_health={metrics['health_score']}"],
            }
        )
    if previous_warning_count == 0 and metrics["warning_count"] > 0:
        contradictions.append(
            {
                "id": "warning_regression",
                "severity": "medium",
                "evidence": [f"previous_warning_count={previous_warning_count}", f"current_warning_count={metrics['warning_count']}"],
            }
        )
    if previous_parse_errors == 0 and metrics["parse_error_count"] > 0:
        contradictions.append(
            {
                "id": "parse_error_regression",
                "severity": "high",
                "evidence": [f"previous_parse_errors={previous_parse_errors}", f"current_parse_errors={metrics['parse_error_count']}"],
            }
        )
    if previous_success and not metrics["evolution_overall_success"]:
        contradictions.append(
            {
                "id": "evolution_failure_regression",
                "severity": "high",
                "evidence": ["core_memory marked overall_success=true", "latest evolution_overall_success=false"],
            }
        )
    if isinstance(previous_strategy_order, list) and previous_strategy_order and previous_strategy_order != metrics["strategy_phase_order"]:
        contradictions.append(
            {
                "id": "strategy_phase_order_changed",
                "severity": "low",
                "evidence": [
                    f"previous_phase_order={previous_strategy_order}",
                    f"current_phase_order={metrics['strategy_phase_order']}",
                ],
            }
        )
    return contradictions


def _regressions(history: list[dict[str, Any]]) -> list[dict[str, Any]]:
    regressions: list[dict[str, Any]] = []
    recent = history[-5:]
    warning_cycles = sum(1 for item in recent if int(item.get("signals", {}).get("warning_count", 0) or 0) > 0)
    parse_error_cycles = sum(1 for item in recent if int(item.get("signals", {}).get("parse_error_count", 0) or 0) > 0)
    failure_cycles = sum(1 for item in recent if not bool(item.get("signals", {}).get("overall_success", True)))

    if warning_cycles >= 2:
        regressions.append(
            {
                "id": "repeated_warning_cycles",
                "severity": "medium",
                "evidence": [f"warning_cycles_in_last_5={warning_cycles}"],
            }
        )
    if parse_error_cycles >= 2:
        regressions.append(
            {
                "id": "repeated_parse_error_cycles",
                "severity": "high",
                "evidence": [f"parse_error_cycles_in_last_5={parse_error_cycles}"],
            }
        )
    if failure_cycles >= 2:
        regressions.append(
            {
                "id": "repeated_evolution_failures",
                "severity": "high",
                "evidence": [f"failure_cycles_in_last_5={failure_cycles}"],
            }
        )
    return regressions


def _recommendations(contradictions: list[dict[str, Any]], regressions: list[dict[str, Any]], context: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    if not contradictions and not regressions:
        return {
            "goals": [
                {
                    "id": "maintain_current_goals",
                    "priority": "low",
                    "action": "Keep current goal alignment and continue bounded consolidation.",
                }
            ],
            "strategy": [
                {
                    "id": "preserve_current_strategy",
                    "priority": "low",
                    "action": "Keep current phase order and weights because the memory layer is consistent.",
                }
            ],
            "adaptation": [
                {
                    "id": "continue_memory_consolidation",
                    "priority": "low",
                    "action": "Continue bounded consolidation cycles and capture stable history snapshots.",
                }
            ],
        }

    recommendations = {
        "goals": [
            {
                "id": "stabilize_baseline",
                "priority": "critical" if any(item.get("severity") == "high" for item in contradictions) else "high",
                "action": "Prioritize health_score 100, warning_count 0, and parse_error_count 0.",
            }
        ],
        "strategy": [
            {
                "id": "prefer_low_aggression",
                "priority": "high",
                "action": f"Bias strategies toward safety because evolution_aggressiveness={get_preference(context, 'evolution_aggressiveness', 'low')}.",
            }
        ],
        "adaptation": [
            {
                "id": "repair_consistency",
                "priority": "high",
                "action": "Run consolidation again after repair and verify contradictions disappear before expanding.",
            }
        ],
    }
    return recommendations


def _verification(report: dict[str, Any]) -> dict[str, Any]:
    checks = {
        "schema_present": report.get("schema") == REPORT_SCHEMA,
        "contradictions_present": isinstance(report.get("contradictions"), list),
        "regressions_present": isinstance(report.get("regressions"), list),
        "recommendations_present": isinstance(report.get("recommendations"), dict),
        "summary_present": isinstance(report.get("summary"), dict),
    }
    return {"passed": all(checks.values()), "checks": checks}


def run_cycle(*, dry_run: bool = False) -> dict[str, Any]:
    started = time.perf_counter()
    inputs = _load_inputs()
    core_memory = load_core_memory()
    context = build_memory_context(core_memory)
    metrics = _latest_metrics(inputs)
    history = _recent_history(core_memory)
    contradictions = _contradictions(core_memory, metrics, context)
    regressions = _regressions(history)
    recommendations = _recommendations(contradictions, regressions, context)
    overall_consistent = len(contradictions) == 0 and len(regressions) == 0

    report = {
        "schema": REPORT_SCHEMA,
        "engine": ENGINE_NAME,
        "generated_at": utc_now(),
        "dry_run": dry_run,
        "workspace_root": str(WORKSPACE_ROOT),
        "inputs": {name: str(path) for name, path in INPUTS.items()},
        "core_memory_present": CORE_MEMORY_PATH.exists(),
        "memory_context": memory_context_summary(context),
        "latest_metrics": metrics,
        "contradictions": contradictions,
        "regressions": regressions,
        "recommendations": recommendations,
        "overall_consistent": overall_consistent,
        "summary": {
            "contradiction_count": len(contradictions),
            "regression_count": len(regressions),
            "recommendation_count": sum(len(items) for items in recommendations.values()),
            "overall_consistent": overall_consistent,
        },
        "core_memory_path": str(CORE_MEMORY_PATH),
        "report_path": str(REPORT_PATH),
        "system_report_path": str(SYSTEM_REPORT_PATH),
    }
    report["verification"] = _verification(report)
    report["elapsed_ms"] = round((time.perf_counter() - started) * 1000, 2)

    if not dry_run:
        write_json(REPORT_PATH, report)
        update_memory_system_report(
            status="OK" if overall_consistent else "DEGRADED",
            notes=[
                f"contradictions={len(contradictions)}",
                f"regressions={len(regressions)}",
                f"overall_consistent={overall_consistent}",
            ],
            last_consistency_check=report["generated_at"],
            dry_run=False,
        )

    return report


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ANA MAX memory consistency engine")
    parser.add_argument("--cycle", action="store_true", help="Run a consistency cycle.")
    parser.add_argument("--dry-run", action="store_true", help="Compute without writing reports.")
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    if not args.cycle:
        return 0
    result = run_cycle(dry_run=args.dry_run)
    print_raw_json(result)
    return 0 if result.get("verification", {}).get("passed") and result.get("overall_consistent") else 1


if __name__ == "__main__":
    raise SystemExit(main())
