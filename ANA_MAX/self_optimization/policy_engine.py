#!/usr/bin/env python3
"""ANA MAX OS-9 Policy Engine."""

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

ENGINE_NAME = "policy_engine"
LEVEL_SCHEMA = "ana.os9.policy_engine.v1"
SYSTEM_POLICIES_SCHEMA = "ana.os9.system_policies.v1"
SYSTEM_POLICIES_PATH = MEMORY_DIR / "system_policies.json"

INPUTS = {
    "evaluation": MEMORY_DIR / "self_evaluation_report.json",
    "daemon": MEMORY_DIR / "os4_daemon_report.json",
    "goals": MEMORY_DIR / "self_goals.json",
    "strategy": MEMORY_DIR / "evolution_strategy.json",
    "meta_history": MEMORY_DIR / "evolution_strategy_history",
    "registry": MEMORY_DIR / "agent_registry.json",
    "proposals": MEMORY_DIR / "architecture_proposals.json",
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


def _build_policies(inputs: dict[str, Any]) -> list[dict[str, Any]]:
    evaluation = inputs.get("evaluation", {}) if isinstance(inputs.get("evaluation", {}), dict) else {}
    daemon = inputs.get("daemon", {}) if isinstance(inputs.get("daemon", {}), dict) else {}
    goals = inputs.get("goals", {}) if isinstance(inputs.get("goals", {}), dict) else {}
    strategy = inputs.get("strategy", {}) if isinstance(inputs.get("strategy", {}), dict) else {}
    registry = inputs.get("registry", {}) if isinstance(inputs.get("registry", {}), dict) else {}
    proposals = inputs.get("proposals", {}) if isinstance(inputs.get("proposals", {}), dict) else {}

    eval_summary = evaluation.get("summary", {}) if isinstance(evaluation.get("summary", {}), dict) else {}
    daemon_overall = bool(daemon.get("overall_success", True))
    daemon_cycles = len(daemon.get("cycles", [])) if isinstance(daemon.get("cycles", []), list) else 0
    goal_count = len(goals.get("goals", [])) if isinstance(goals.get("goals", []), list) else 0
    phase_order = list(strategy.get("phase_order", [])) if isinstance(strategy.get("phase_order", []), list) else []
    registry_agents = registry.get("agents", {}) if isinstance(registry.get("agents", {}), dict) else {}
    proposal_count = len(proposals.get("proposals", [])) if isinstance(proposals.get("proposals", []), list) else 0

    policies: list[dict[str, Any]] = [
        {
            "id": "preserve_baseline_health",
            "priority": "critical",
            "source": "evaluation + daemon",
            "constraint": "health_score must remain 100 and warning_count must remain 0.",
            "status": "enabled",
            "enforcement": "fail_closed_on_warning",
            "evidence": [
                f"health_score={_to_int(eval_summary.get('health_score'), 0)}",
                f"warning_count={_to_int(eval_summary.get('warning_count'), 0)}",
                f"daemon_overall_success={daemon_overall}",
                f"daemon_cycles={daemon_cycles}",
            ],
        },
        {
            "id": "respect_phase_order",
            "priority": "high",
            "source": "os5 strategy",
            "constraint": "Downstream orchestration must follow the deterministic OS-5 phase_order.",
            "status": "enabled",
            "enforcement": "read_only_phase_order",
            "evidence": [f"phase_order_count={len(phase_order)}"],
        },
        {
            "id": "maintain_goal_feedback",
            "priority": "high",
            "source": "os5 goals",
            "constraint": "Goals remain the source of truth for OS-6+ adaptation decisions.",
            "status": "enabled",
            "enforcement": "goal_to_policy_bridge",
            "evidence": [f"goal_count={goal_count}"],
        },
        {
            "id": "keep_agent_registry_healthy",
            "priority": "medium",
            "source": "os7 registry",
            "constraint": "Agent registry failure_count must stay at zero during the baseline ladder.",
            "status": "enabled",
            "enforcement": "registry_health_gate",
            "evidence": [f"registry_agent_count={len(registry_agents)}"],
        },
        {
            "id": "review_architecture_proposals",
            "priority": "medium",
            "source": "os8 proposals",
            "constraint": "Architecture proposals are review-only until explicitly promoted by a later layer.",
            "status": "enabled",
            "enforcement": "proposal_review_gate",
            "evidence": [f"proposal_count={proposal_count}"],
        },
        {
            "id": "track_meta_history",
            "priority": "medium",
            "source": "os6 history",
            "constraint": "Meta-adaptation history should be read-only input for policy composition.",
            "status": "enabled",
            "enforcement": "history_read_only",
            "evidence": [f"meta_history_count={inputs.get('meta_history_count', 0)}"],
        },
    ]
    return policies


def _system_policies_payload(inputs: dict[str, Any], policies: list[dict[str, Any]]) -> dict[str, Any]:
    critical = sum(1 for policy in policies if policy.get("priority") == "critical")
    return {
        "schema": SYSTEM_POLICIES_SCHEMA,
        "generated_at": utc_now(),
        "engine": ENGINE_NAME,
        "workspace_root": str(WORKSPACE_ROOT),
        "source_reports": {name: str(path) for name, path in INPUTS.items()},
        "policies": policies,
        "summary": {
            "policy_count": len(policies),
            "critical_count": critical,
            "enabled_count": sum(1 for policy in policies if policy.get("status") == "enabled"),
            "daemon_overall_success": bool(inputs.get("daemon", {}).get("overall_success", True)) if isinstance(inputs.get("daemon", {}), dict) else True,
        },
    }


def _verification(report: dict[str, Any]) -> dict[str, Any]:
    checks = {
        "schema_present": report.get("schema") == LEVEL_SCHEMA,
        "policies_present": isinstance(report.get("policies"), list) and len(report["policies"]) > 0,
        "system_payload_present": isinstance(report.get("system_policies"), dict),
        "summary_present": isinstance(report.get("summary"), dict),
    }
    return {"passed": all(checks.values()), "checks": checks}


def run_cycle(*, dry_run: bool = True) -> dict[str, Any]:
    started = time.perf_counter()
    inputs = _load_inputs()
    policies = _build_policies(inputs)
    system_payload = _system_policies_payload(inputs, policies)
    report = {
        "schema": LEVEL_SCHEMA,
        "generated_at": utc_now(),
        "engine": ENGINE_NAME,
        "workspace_root": str(WORKSPACE_ROOT),
        "dry_run": dry_run,
        "inputs": {name: str(path) for name, path in INPUTS.items()},
        "policies": policies,
        "system_policies": system_payload,
        "summary": {
            "policy_count": len(policies),
            "critical_count": sum(1 for policy in policies if policy.get("priority") == "critical"),
            "proposal_count": len(inputs.get("proposals", {}).get("proposals", [])) if isinstance(inputs.get("proposals", {}), dict) else 0,
        },
    }
    report["verification"] = _verification(report)
    report["elapsed_ms"] = round((time.perf_counter() - started) * 1000, 2)
    report["policies_path"] = str(SYSTEM_POLICIES_PATH)

    if not dry_run:
        ensure_dir(SYSTEM_POLICIES_PATH.parent)
        write_json(SYSTEM_POLICIES_PATH, system_payload)

    return report


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ANA MAX OS-9 Policy Engine")
    parser.add_argument("--cycle", action="store_true", help="Run the policy composition cycle.")
    parser.add_argument("--dry-run", action="store_true", help="Compute without writing system policies.")
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
