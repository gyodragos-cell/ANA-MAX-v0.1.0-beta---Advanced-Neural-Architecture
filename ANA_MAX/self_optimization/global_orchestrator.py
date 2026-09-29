#!/usr/bin/env python3
"""ANA MAX OS-9 Global Orchestrator."""

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

from ANA_MAX.self_optimization.os3_common import print_raw_json
from ANA_MAX.self_optimization.osx_common import MEMORY_DIR, WORKSPACE_ROOT, ensure_dir, read_json, write_json, utc_now

ENGINE_NAME = "global_orchestrator"
LEVEL_SCHEMA = "ana.os9.global_orchestrator.v1"
LEVEL_REPORT_SCHEMA = "ana.os9.level_report.v1"
LEVEL_REPORT_PATH = MEMORY_DIR / "os_level_OS9_report.json"

INPUTS = {
    "evolution": MEMORY_DIR / "evolution_report.json",
    "daemon": MEMORY_DIR / "os4_daemon_report.json",
    "goals": MEMORY_DIR / "self_goals.json",
    "strategy": MEMORY_DIR / "evolution_strategy.json",
    "meta_history": MEMORY_DIR / "evolution_strategy_history",
    "registry": MEMORY_DIR / "agent_registry.json",
    "proposals": MEMORY_DIR / "architecture_proposals.json",
    "policies": MEMORY_DIR / "system_policies.json",
}


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _load_inputs() -> dict[str, Any]:
    payload = {name: read_json(path, {}) if path.is_file() else {"path": str(path), "exists": path.exists()} for name, path in INPUTS.items()}
    payload["meta_history_count"] = len(list(INPUTS["meta_history"].glob("os6_meta_*.json"))) if INPUTS["meta_history"].exists() else 0
    return payload


def _layer_snapshot(inputs: dict[str, Any]) -> dict[str, Any]:
    evolution = inputs.get("evolution", {}) if isinstance(inputs.get("evolution", {}), dict) else {}
    daemon = inputs.get("daemon", {}) if isinstance(inputs.get("daemon", {}), dict) else {}
    goals = inputs.get("goals", {}) if isinstance(inputs.get("goals", {}), dict) else {}
    strategy = inputs.get("strategy", {}) if isinstance(inputs.get("strategy", {}), dict) else {}
    registry = inputs.get("registry", {}) if isinstance(inputs.get("registry", {}), dict) else {}
    proposals = inputs.get("proposals", {}) if isinstance(inputs.get("proposals", {}), dict) else {}
    policies = inputs.get("policies", {}) if isinstance(inputs.get("policies", {}), dict) else {}

    evo_success = bool(evolution.get("overall_success", True))
    daemon_success = bool(daemon.get("overall_success", True))
    eval_summary = read_json(MEMORY_DIR / "self_evaluation_report.json", {}).get("summary", {})
    health_score = _to_int(eval_summary.get("health_score"), 0) if isinstance(eval_summary, dict) else 0
    warnings = _to_int(eval_summary.get("warning_count"), 0) if isinstance(eval_summary, dict) else 0
    parse_error_count = _to_int(read_json(MEMORY_DIR / "self_skills_report.json", {}).get("summary", {}).get("parse_error_count"), 0)
    agent_failure_count = sum(
        int(entry.get("failure_count", 0) or 0)
        for entry in (registry.get("agents", {}) if isinstance(registry.get("agents", {}), dict) else {}).values()
    )

    return {
        "os4": {
            "health_score": health_score,
            "warning_count": warnings,
            "daemon_success": daemon_success,
            "evolution_success": evo_success,
        },
        "os5": {
            "goal_count": len(goals.get("goals", [])) if isinstance(goals.get("goals", []), list) else 0,
            "strategy_phase_count": len(strategy.get("phase_order", [])) if isinstance(strategy.get("phase_order", []), list) else 0,
        },
        "os6": {
            "history_count": inputs.get("meta_history_count", 0),
        },
        "os7": {
            "agent_count": len(registry.get("agents", {})) if isinstance(registry.get("agents", {}), dict) else 0,
            "agent_failure_count": agent_failure_count,
        },
        "os8": {
            "proposal_count": len(proposals.get("proposals", [])) if isinstance(proposals.get("proposals", []), list) else 0,
        },
        "os9": {
            "policy_count": len(policies.get("policies", [])) if isinstance(policies.get("policies", []), list) else 0,
        },
        "os9_inputs_present": {
            "goals": bool(goals),
            "strategy": bool(strategy),
            "policies": bool(policies),
        },
        "parse_error_count": parse_error_count,
    }


def _detect_drift(layers: dict[str, Any]) -> dict[str, Any]:
    drift_reasons: list[str] = []
    if layers["os4"]["health_score"] < 100 or layers["os4"]["warning_count"] > 0:
        drift_reasons.append("baseline_health_changed")
    if layers["os7"]["agent_failure_count"] > 0:
        drift_reasons.append("agent_failures_present")
    if layers["parse_error_count"] > 0:
        drift_reasons.append("parse_errors_present")
    return {
        "detected": bool(drift_reasons),
        "reasons": drift_reasons,
    }


def _verification(report: dict[str, Any]) -> dict[str, Any]:
    checks = {
        "schema_present": report.get("schema") == LEVEL_SCHEMA,
        "layers_present": isinstance(report.get("layers"), dict),
        "drift_present": isinstance(report.get("drift"), dict),
        "summary_present": isinstance(report.get("summary"), dict),
    }
    return {"passed": all(checks.values()), "checks": checks}


def _level_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": LEVEL_REPORT_SCHEMA,
        "generated_at": report.get("generated_at", utc_now()),
        "engine": ENGINE_NAME,
        "os_level": "OS-9",
        "status": "PASS" if report.get("verification", {}).get("passed") else "WARN",
        "next": "OS-10",
        "summary": report.get("summary", {}),
        "payload": report,
    }


def run_cycle(*, dry_run: bool = True) -> dict[str, Any]:
    started = time.perf_counter()
    inputs = _load_inputs()
    layers = _layer_snapshot(inputs)
    drift = _detect_drift(layers)
    overall_success = not drift["detected"] and layers["os4"]["health_score"] == 100 and layers["os4"]["warning_count"] == 0 and layers["parse_error_count"] == 0

    report = {
        "schema": LEVEL_SCHEMA,
        "generated_at": utc_now(),
        "engine": ENGINE_NAME,
        "workspace_root": str(WORKSPACE_ROOT),
        "dry_run": dry_run,
        "inputs": {name: str(path) for name, path in INPUTS.items()},
        "layers": layers,
        "drift": drift,
        "overall_success": overall_success,
        "summary": {
            "health_score": layers["os4"]["health_score"],
            "warning_count": layers["os4"]["warning_count"],
            "parse_error_count": layers["parse_error_count"],
            "agent_failure_count": layers["os7"]["agent_failure_count"],
            "proposal_count": layers["os8"]["proposal_count"],
            "policy_count": layers["os9"]["policy_count"],
            "drift_detected": drift["detected"],
        },
    }
    report["verification"] = _verification(report)
    report["elapsed_ms"] = round((time.perf_counter() - started) * 1000, 2)
    report["report_path"] = str(LEVEL_REPORT_PATH)

    ensure_dir(LEVEL_REPORT_PATH.parent)
    write_json(LEVEL_REPORT_PATH, _level_report(report))

    return report


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ANA MAX OS-9 Global Orchestrator")
    parser.add_argument("--cycle", action="store_true", help="Run the orchestration cycle.")
    parser.add_argument("--dry-run", action="store_true", help="Compute without writing the level report.")
    return parser


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()
    dry_run = args.dry_run or not args.cycle
    result = run_cycle(dry_run=dry_run)
    print_raw_json(result)
    return 0 if result.get("verification", {}).get("passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
