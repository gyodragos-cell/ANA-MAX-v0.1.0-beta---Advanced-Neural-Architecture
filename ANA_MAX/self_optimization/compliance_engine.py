#!/usr/bin/env python3
"""ANA MAX OS-10 Compliance Engine."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ANA_MAX.self_optimization.os3_common import print_raw_json
from ANA_MAX.self_optimization.osx_common import MEMORY_DIR, WORKSPACE_ROOT, ensure_dir, read_json, write_json, utc_now

ENGINE_NAME = "compliance_engine"
LEVEL_SCHEMA = "ana.os10.compliance.v1"
REPORT_PATH = MEMORY_DIR / "compliance_report.json"

INPUTS = {
    "evaluation": MEMORY_DIR / "self_evaluation_report.json",
    "skills": MEMORY_DIR / "self_skills_report.json",
    "evolution": MEMORY_DIR / "evolution_report.json",
    "goals": MEMORY_DIR / "self_goals.json",
    "strategy": MEMORY_DIR / "evolution_strategy.json",
    "registry": MEMORY_DIR / "agent_registry.json",
    "policies": MEMORY_DIR / "system_policies.json",
}


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _load_inputs() -> dict[str, Any]:
    return {name: read_json(path, {}) for name, path in INPUTS.items()}


def _violations(inputs: dict[str, Any]) -> list[dict[str, Any]]:
    evaluation = inputs.get("evaluation", {}) if isinstance(inputs.get("evaluation", {}), dict) else {}
    skills = inputs.get("skills", {}) if isinstance(inputs.get("skills", {}), dict) else {}
    evolution = inputs.get("evolution", {}) if isinstance(inputs.get("evolution", {}), dict) else {}
    goals = inputs.get("goals", {}) if isinstance(inputs.get("goals", {}), dict) else {}
    strategy = inputs.get("strategy", {}) if isinstance(inputs.get("strategy", {}), dict) else {}
    registry = inputs.get("registry", {}) if isinstance(inputs.get("registry", {}), dict) else {}
    policies = inputs.get("policies", {}) if isinstance(inputs.get("policies", {}), dict) else {}

    eval_summary = evaluation.get("summary", {}) if isinstance(evaluation.get("summary", {}), dict) else {}
    skill_summary = skills.get("summary", {}) if isinstance(skills.get("summary", {}), dict) else {}
    registry_agents = registry.get("agents", {}) if isinstance(registry.get("agents", {}), dict) else {}
    policy_schema = policies.get("schema")

    violations: list[dict[str, Any]] = []
    if _to_int(eval_summary.get("health_score"), 0) != 100:
        violations.append({"id": "health_score_not_100", "severity": "critical"})
    if _to_int(eval_summary.get("warning_count"), 0) != 0:
        violations.append({"id": "warnings_present", "severity": "critical"})
    if _to_int(skill_summary.get("parse_error_count"), 0) != 0:
        violations.append({"id": "parse_errors_present", "severity": "high"})
    if not bool(evolution.get("overall_success", True)):
        violations.append({"id": "evolution_not_successful", "severity": "high"})
    if goals and not isinstance(goals.get("goals", []), list):
        violations.append({"id": "goals_payload_invalid", "severity": "medium"})
    if strategy and not isinstance(strategy.get("phase_order", []), list):
        violations.append({"id": "strategy_phase_order_invalid", "severity": "medium"})
    if policies and policy_schema != "ana.os9.system_policies.v1":
        violations.append({"id": "system_policies_invalid", "severity": "high"})
    if registry_agents and any(int(entry.get("failure_count", 0) or 0) > 0 for entry in registry_agents.values()):
        violations.append({"id": "agent_failures_present", "severity": "high"})
    return violations


def _verification(report: dict[str, Any]) -> dict[str, Any]:
    checks = {
        "schema_present": report.get("schema") == LEVEL_SCHEMA,
        "violations_present": isinstance(report.get("violations"), list),
        "summary_present": isinstance(report.get("summary"), dict),
        "compliant_field_present": "compliant" in report,
    }
    return {"passed": all(checks.values()), "checks": checks}


def run_cycle(*, dry_run: bool = False) -> dict[str, Any]:
    started = time.perf_counter()
    inputs = _load_inputs()
    violations = _violations(inputs)
    compliant = len(violations) == 0

    report = {
        "schema": LEVEL_SCHEMA,
        "generated_at": utc_now(),
        "engine": ENGINE_NAME,
        "workspace_root": str(WORKSPACE_ROOT),
        "dry_run": dry_run,
        "inputs": {name: str(path) for name, path in INPUTS.items()},
        "violations": violations,
        "compliant": compliant,
        "summary": {
            "violation_count": len(violations),
            "critical_count": sum(1 for item in violations if item.get("severity") == "critical"),
            "high_count": sum(1 for item in violations if item.get("severity") == "high"),
        },
    }
    report["verification"] = _verification(report)
    report["elapsed_ms"] = round((time.perf_counter() - started) * 1000, 2)
    report["report_path"] = str(REPORT_PATH)

    if not dry_run:
        ensure_dir(REPORT_PATH.parent)
        write_json(REPORT_PATH, report)

    return report


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ANA MAX OS-10 Compliance Engine")
    parser.add_argument("--cycle", action="store_true", help="Run the compliance cycle.")
    parser.add_argument("--dry-run", action="store_true", help="Compute without writing the report.")
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
