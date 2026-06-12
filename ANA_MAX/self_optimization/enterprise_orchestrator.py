#!/usr/bin/env python3
"""ANA MAX OS-10 Enterprise Orchestrator."""

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

ENGINE_NAME = "enterprise_orchestrator"
LEVEL_SCHEMA = "ana.os10.enterprise_orchestrator.v1"
LEVEL_REPORT_SCHEMA = "ana.os10.level_report.v1"
ENTERPRISE_POLICIES_SCHEMA = "ana.os10.enterprise_policies.v1"
LEVEL_REPORT_PATH = MEMORY_DIR / "os_level_OS10_report.json"
ENTERPRISE_POLICIES_PATH = MEMORY_DIR / "enterprise_policies.json"

INPUTS = {
    "global_orchestrator": MEMORY_DIR / "os_level_OS9_report.json",
    "policy_engine": MEMORY_DIR / "system_policies.json",
    "compliance": MEMORY_DIR / "compliance_report.json",
    "security": MEMORY_DIR / "security_report.json",
    "evaluation": MEMORY_DIR / "self_evaluation_report.json",
    "goals": MEMORY_DIR / "self_goals.json",
    "strategy": MEMORY_DIR / "evolution_strategy.json",
    "registry": MEMORY_DIR / "agent_registry.json",
    "proposals": MEMORY_DIR / "architecture_proposals.json",
}


def _load_inputs() -> dict[str, Any]:
    payload = {name: read_json(path, {}) for name, path in INPUTS.items()}
    if not payload.get("global_orchestrator"):
        payload["global_orchestrator"] = {}
    return payload


def _unwrap_level_report(report: dict[str, Any]) -> dict[str, Any]:
    payload = report.get("payload")
    if isinstance(report, dict) and report.get("schema") == "ana.os9.level_report.v1" and isinstance(payload, dict):
        return payload
    return report


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _enterprise_policies(inputs: dict[str, Any]) -> list[dict[str, Any]]:
    base_policies = inputs.get("policy_engine", {}).get("system_policies", {}).get("policies", [])
    if not isinstance(base_policies, list):
        base_policies = []
    policies = [policy for policy in base_policies if isinstance(policy, dict)]
    policies.extend(
        [
            {
                "id": "local_only_execution",
                "priority": "critical",
                "source": "enterprise",
                "constraint": "All OS-6+ execution stays local-only with no remote/cloud dependency.",
                "status": "enabled",
                "enforcement": "local_only_gate",
            },
            {
                "id": "protect_os3_os4_schemas",
                "priority": "critical",
                "source": "enterprise",
                "constraint": "OS-3 and OS-4 schemas remain unchanged and RAW markers stay intact.",
                "status": "enabled",
                "enforcement": "schema_stability_gate",
            },
            {
                "id": "bounded_cycles_required",
                "priority": "high",
                "source": "enterprise",
                "constraint": "Long-running agents must remain bounded unless an operator explicitly opts in.",
                "status": "enabled",
                "enforcement": "bounded_cycle_gate",
            },
            {
                "id": "dangerous_tools_explicit_enable",
                "priority": "high",
                "source": "enterprise",
                "constraint": "Risky tools remain report-only unless explicitly enabled.",
                "status": "enabled",
                "enforcement": "explicit_enable_gate",
            },
            {
                "id": "no_archive_edits",
                "priority": "medium",
                "source": "enterprise",
                "constraint": "Archive contents stay read-only for OS-6+ layers.",
                "status": "enabled",
                "enforcement": "read_only_archive_gate",
            },
            {
                "id": "raw_output_required",
                "priority": "medium",
                "source": "enterprise",
                "constraint": "Enterprise engines keep RAW-tagged JSON output for shell safety.",
                "status": "enabled",
                "enforcement": "raw_output_gate",
            },
        ]
    )
    return policies


def _snapshot(inputs: dict[str, Any]) -> dict[str, Any]:
    global_report = inputs.get("global_orchestrator", {}) if isinstance(inputs.get("global_orchestrator", {}), dict) else {}
    global_report = _unwrap_level_report(global_report)
    compliance = inputs.get("compliance", {}) if isinstance(inputs.get("compliance", {}), dict) else {}
    security = inputs.get("security", {}) if isinstance(inputs.get("security", {}), dict) else {}
    goals = inputs.get("goals", {}) if isinstance(inputs.get("goals", {}), dict) else {}
    strategy = inputs.get("strategy", {}) if isinstance(inputs.get("strategy", {}), dict) else {}
    registry = inputs.get("registry", {}) if isinstance(inputs.get("registry", {}), dict) else {}
    proposals = inputs.get("proposals", {}) if isinstance(inputs.get("proposals", {}), dict) else {}

    health_score = _to_int(inputs.get("evaluation", {}).get("summary", {}).get("health_score"), 0) if isinstance(inputs.get("evaluation", {}), dict) else 0
    warning_count = _to_int(inputs.get("evaluation", {}).get("summary", {}).get("warning_count"), 0) if isinstance(inputs.get("evaluation", {}), dict) else 0
    parse_error_count = _to_int(inputs.get("evaluation", {}).get("summary", {}).get("parse_error_count"), 0) if isinstance(inputs.get("evaluation", {}), dict) else 0
    goal_count = len(goals.get("goals", [])) if isinstance(goals.get("goals", []), list) else 0
    strategy_phase_count = len(strategy.get("phase_order", [])) if isinstance(strategy.get("phase_order", []), list) else 0
    agent_failure_count = sum(
        int(entry.get("failure_count", 0) or 0)
        for entry in (registry.get("agents", {}) if isinstance(registry.get("agents", {}), dict) else {}).values()
    )
    proposal_count = len(proposals.get("proposals", [])) if isinstance(proposals.get("proposals", []), list) else 0

    return {
        "global_orchestrator": global_report,
        "compliance": compliance,
        "security": security,
        "metrics": {
            "health_score": health_score,
            "warning_count": warning_count,
            "parse_error_count": parse_error_count,
            "goal_count": goal_count,
            "strategy_phase_count": strategy_phase_count,
            "agent_failure_count": agent_failure_count,
            "proposal_count": proposal_count,
            "compliance_ok": bool(compliance.get("compliant", True)),
            "security_ok": bool(security.get("secure", True)),
            "global_ok": bool(global_report.get("overall_success", True)),
        },
    }


def _verification(report: dict[str, Any]) -> dict[str, Any]:
    checks = {
        "schema_present": report.get("schema") == LEVEL_SCHEMA,
        "enterprise_policies_present": isinstance(report.get("enterprise_policies"), dict),
        "summary_present": isinstance(report.get("summary"), dict),
        "overall_success_present": "overall_success" in report,
    }
    return {"passed": all(checks.values()), "checks": checks}


def _level_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": LEVEL_REPORT_SCHEMA,
        "generated_at": report.get("generated_at", utc_now()),
        "engine": ENGINE_NAME,
        "os_level": "OS-10",
        "status": "PASS" if report.get("verification", {}).get("passed") and report.get("overall_success") else "WARN",
        "next": "COMPLETE",
        "summary": report.get("summary", {}),
        "payload": report,
    }


def run_cycle(*, dry_run: bool = True) -> dict[str, Any]:
    started = time.perf_counter()
    inputs = _load_inputs()
    snapshot = _snapshot(inputs)
    metrics = snapshot["metrics"]
    enterprise_policies = _enterprise_policies(inputs)
    enterprise_payload = {
        "schema": ENTERPRISE_POLICIES_SCHEMA,
        "generated_at": utc_now(),
        "engine": ENGINE_NAME,
        "workspace_root": str(WORKSPACE_ROOT),
        "source_reports": {name: str(path) for name, path in INPUTS.items()},
        "policies": enterprise_policies,
        "summary": {
            "policy_count": len(enterprise_policies),
            "critical_count": sum(1 for item in enterprise_policies if item.get("priority") == "critical"),
        },
    }
    overall_success = metrics["compliance_ok"] and metrics["security_ok"] and metrics["global_ok"] and metrics["warning_count"] == 0 and metrics["parse_error_count"] == 0 and metrics["agent_failure_count"] == 0

    report = {
        "schema": LEVEL_SCHEMA,
        "generated_at": utc_now(),
        "engine": ENGINE_NAME,
        "workspace_root": str(WORKSPACE_ROOT),
        "dry_run": dry_run,
        "inputs": {name: str(path) for name, path in INPUTS.items()},
        "enterprise_policies": enterprise_payload,
        "compliance": snapshot["compliance"],
        "security": snapshot["security"],
        "global_orchestrator": snapshot["global_orchestrator"],
        "summary": {
            "policy_count": len(enterprise_policies),
            "health_score": metrics["health_score"],
            "warning_count": metrics["warning_count"],
            "parse_error_count": metrics["parse_error_count"],
            "agent_failure_count": metrics["agent_failure_count"],
            "proposal_count": metrics["proposal_count"],
            "compliance_ok": metrics["compliance_ok"],
            "security_ok": metrics["security_ok"],
            "global_ok": metrics["global_ok"],
        },
        "overall_success": overall_success,
    }
    report["verification"] = _verification(report)
    report["elapsed_ms"] = round((time.perf_counter() - started) * 1000, 2)
    report["report_path"] = str(LEVEL_REPORT_PATH)
    report["enterprise_policies_path"] = str(ENTERPRISE_POLICIES_PATH)

    ensure_dir(ENTERPRISE_POLICIES_PATH.parent)
    if not dry_run:
        write_json(ENTERPRISE_POLICIES_PATH, enterprise_payload)
    write_json(LEVEL_REPORT_PATH, _level_report(report))

    return report


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ANA MAX OS-10 Enterprise Orchestrator")
    parser.add_argument("--cycle", action="store_true", help="Run the enterprise cycle.")
    parser.add_argument("--dry-run", action="store_true", help="Compute without writing enterprise artifacts.")
    return parser


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()
    dry_run = args.dry_run or not args.cycle
    result = run_cycle(dry_run=dry_run)
    print_raw_json(result)
    return 0 if result.get("verification", {}).get("passed") and result.get("overall_success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
