#!/usr/bin/env python3
"""ANA MAX OS-6 Meta-Adaptation Engine."""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ANA_MAX.self_optimization.os3_common import print_raw_json
from ANA_MAX.self_optimization.osx_common import MEMORY_DIR, WORKSPACE_ROOT, ensure_dir, read_json, write_json, utc_now

ENGINE_NAME = "meta_adaptation_engine"
LEVEL_SCHEMA = "ana.os6.meta_adaptation.v1"
LEVEL_REPORT_SCHEMA = "ana.os6.level_report.v1"
LEVEL_REPORT_PATH = MEMORY_DIR / "os_level_OS6_report.json"
HISTORY_DIR = MEMORY_DIR / "evolution_strategy_history"

INPUTS = {
    "goals": MEMORY_DIR / "self_goals.json",
    "strategy": MEMORY_DIR / "evolution_strategy.json",
    "evolution": MEMORY_DIR / "evolution_report.json",
    "evaluation": MEMORY_DIR / "self_evaluation_report.json",
    "consistency": MEMORY_DIR / "self_consistency_report.json",
}


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _load_inputs() -> dict[str, dict[str, Any]]:
    return {name: read_json(path, {}) for name, path in INPUTS.items()}


def _history_files() -> list[Path]:
    if not HISTORY_DIR.exists():
        return []
    return sorted(
        path
        for path in HISTORY_DIR.glob("os6_meta_*.json")
        if path.is_file()
    )


def _load_history() -> list[dict[str, Any]]:
    snapshots: list[dict[str, Any]] = []
    for path in _history_files():
        data = read_json(path, {})
        if isinstance(data, dict):
            data["_path"] = str(path)
            snapshots.append(data)
    return snapshots


def _current_metrics(inputs: dict[str, dict[str, Any]]) -> dict[str, Any]:
    evaluation = inputs["evaluation"].get("summary", {}) if isinstance(inputs["evaluation"], dict) else {}
    goals = inputs["goals"].get("metrics", {}) if isinstance(inputs["goals"], dict) else {}
    strategy = inputs["strategy"] if isinstance(inputs["strategy"], dict) else {}
    evolution = inputs["evolution"] if isinstance(inputs["evolution"], dict) else {}
    return {
        "health_score": _to_int(evaluation.get("health_score"), 0),
        "warning_count": _to_int(evaluation.get("warning_count"), 0),
        "parse_error_count": _to_int(goals.get("parse_error_count"), 0),
        "graph_nodes": _to_int(goals.get("graph_nodes"), 0),
        "graph_edges": _to_int(goals.get("graph_edges"), 0),
        "graph_density": goals.get("graph_density", 0),
        "evolution_overall_success": bool(evolution.get("overall_success", True)),
        "strategy_priority_count": len(strategy.get("priorities", [])) if isinstance(strategy.get("priorities", []), list) else 0,
        "strategy_phase_count": len(strategy.get("phase_order", [])) if isinstance(strategy.get("phase_order", []), list) else 0,
    }


def _trend_lines(history: list[dict[str, Any]], metrics: dict[str, Any]) -> list[dict[str, Any]]:
    recent = history[-5:]
    lines: list[dict[str, Any]] = []
    for snapshot in recent:
        metrics_snapshot = snapshot.get("metrics", {}) if isinstance(snapshot, dict) else {}
        lines.append(
            {
                "timestamp": snapshot.get("generated_at"),
                "health_score": metrics_snapshot.get("health_score"),
                "warning_count": metrics_snapshot.get("warning_count"),
                "parse_error_count": metrics_snapshot.get("parse_error_count"),
                "graph_density": metrics_snapshot.get("graph_density"),
            }
        )
    lines.append(
        {
            "timestamp": utc_now(),
            "health_score": metrics["health_score"],
            "warning_count": metrics["warning_count"],
            "parse_error_count": metrics["parse_error_count"],
            "graph_density": metrics["graph_density"],
        }
    )
    return lines


def _strategy_delta(current: dict[str, Any], previous: dict[str, Any]) -> dict[str, Any]:
    current_priorities = current.get("priorities", []) if isinstance(current.get("priorities", []), list) else []
    previous_priorities = previous.get("priorities", []) if isinstance(previous.get("priorities", []), list) else []
    current_phase_order = list(current.get("phase_order", [])) if isinstance(current.get("phase_order", []), list) else []
    previous_phase_order = list(previous.get("phase_order", [])) if isinstance(previous.get("phase_order", []), list) else []
    current_weights = current.get("weights", {}) if isinstance(current.get("weights", {}), dict) else {}
    previous_weights = previous.get("weights", {}) if isinstance(previous.get("weights", {}), dict) else {}

    current_priority_ids = [item.get("goal_id") or item.get("id") for item in current_priorities if isinstance(item, dict)]
    previous_priority_ids = [item.get("goal_id") or item.get("id") for item in previous_priorities if isinstance(item, dict)]
    weight_delta_keys = sorted(
        {
            key
            for key in set(current_weights) | set(previous_weights)
            if current_weights.get(key) != previous_weights.get(key)
        }
    )

    return {
        "priority_count_delta": len(current_priority_ids) - len(previous_priority_ids),
        "priority_ids_added": [item for item in current_priority_ids if item not in previous_priority_ids],
        "priority_ids_removed": [item for item in previous_priority_ids if item not in current_priority_ids],
        "phase_order_changed": current_phase_order != previous_phase_order,
        "phase_order_delta": {
            "current": current_phase_order,
            "previous": previous_phase_order,
        },
        "weight_delta_keys": weight_delta_keys,
    }


def _decisions(
    metrics: dict[str, Any],
    strategy_delta: dict[str, Any],
    consistency: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    consistency = consistency if isinstance(consistency, dict) else {}
    decisions: list[dict[str, Any]] = [
        {
            "id": "preserve_baseline",
            "priority": "critical",
            "action": "Keep OS-3/OS-4 health at 100 with warnings at 0.",
        },
        {
            "id": "watch_strategy_delta",
            "priority": "high",
            "action": "Track phase order and weight changes across the OS-5 strategy history.",
        },
    ]
    if metrics["warning_count"] > 0 or metrics["health_score"] < 100:
        decisions.append(
            {
                "id": "stabilize_baseline",
                "priority": "critical",
                "action": "Pause expansion and focus on baseline repair and bounded validation.",
            }
        )
    if metrics["parse_error_count"] > 0:
        decisions.append(
            {
                "id": "repair_parser_chain",
                "priority": "high",
                "action": "Repair parsing and report generation before adding more layers.",
            }
        )
    if strategy_delta["phase_order_changed"]:
        decisions.append(
            {
                "id": "refresh_phase_order",
                "priority": "medium",
                "action": "Refresh downstream orchestrators to respect the new deterministic phase order.",
            }
        )
    if metrics["graph_density"] and float(metrics["graph_density"]) > 8:
        decisions.append(
            {
                "id": "watch_graph_density",
                "priority": "medium",
                "action": "Use graph history to keep the additive ladder from becoming noisy.",
            }
        )
    if consistency and (not bool(consistency.get("overall_consistent", True)) or len(consistency.get("contradictions", [])) > 0 or len(consistency.get("regressions", [])) > 0):
        decisions.append(
            {
                "id": "repair_memory_consistency",
                "priority": "high",
                "action": "Use the self-consistency report to repair contradictions before expanding the adaptive ladder.",
            }
        )
    return decisions


def _verification(report: dict[str, Any]) -> dict[str, Any]:
    checks = {
        "schema_present": report.get("schema") == LEVEL_SCHEMA,
        "goals_present": isinstance(report.get("goals"), dict),
        "strategy_present": isinstance(report.get("strategy"), dict),
        "trend_lines_present": isinstance(report.get("trend_lines"), list),
        "decisions_present": isinstance(report.get("adaptation_decisions"), list),
    }
    return {"passed": all(checks.values()), "checks": checks}


def _level_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": LEVEL_REPORT_SCHEMA,
        "generated_at": report.get("generated_at", utc_now()),
        "engine": ENGINE_NAME,
        "os_level": "OS-6",
        "status": "PASS" if report.get("verification", {}).get("passed") else "WARN",
        "next": "OS-7",
        "summary": report.get("summary", {}),
        "payload": report,
    }


def run_cycle(*, dry_run: bool = False) -> dict[str, Any]:
    started = time.perf_counter()
    inputs = _load_inputs()
    history = _load_history()
    current_strategy = inputs["strategy"] if isinstance(inputs["strategy"], dict) else {}
    previous_strategy = history[-1].get("strategy", {}) if history else {}
    metrics = _current_metrics(inputs)
    delta = _strategy_delta(current_strategy, previous_strategy if isinstance(previous_strategy, dict) else {})
    decisions = _decisions(metrics, delta, inputs.get("consistency", {}))
    history_path = HISTORY_DIR / f"os6_meta_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    report = {
        "schema": LEVEL_SCHEMA,
        "engine": ENGINE_NAME,
        "generated_at": utc_now(),
        "dry_run": dry_run,
        "workspace_root": str(WORKSPACE_ROOT),
        "inputs": {name: str(path) for name, path in INPUTS.items()},
        "history_dir": str(HISTORY_DIR),
        "history_count": len(history),
        "goals": inputs["goals"],
        "strategy": current_strategy,
        "metrics": metrics,
        "trend_lines": _trend_lines(history, metrics),
        "strategy_deltas": delta,
        "adaptation_decisions": decisions,
        "summary": {
            "goal_count": len(inputs["goals"].get("goals", [])) if isinstance(inputs["goals"], dict) else 0,
            "history_count": len(history),
            "decision_count": len(decisions),
            "phase_order_changed": delta["phase_order_changed"],
        },
    }
    report["verification"] = _verification(report)
    report["elapsed_ms"] = round((time.perf_counter() - started) * 1000, 2)
    report["report_path"] = str(history_path)
    report["level_report_path"] = str(LEVEL_REPORT_PATH)

    if not dry_run:
        ensure_dir(HISTORY_DIR)
        write_json(history_path, report)
        write_json(LEVEL_REPORT_PATH, _level_report(report))

    return report


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ANA MAX OS-6 Meta-Adaptation Engine")
    parser.add_argument("--cycle", action="store_true", help="Run a meta-adaptation cycle.")
    parser.add_argument("--dry-run", action="store_true", help="Compute without writing history files.")
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
