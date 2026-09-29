#!/usr/bin/env python3
"""ANA MAX OS-10 Security Engine."""

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

ENGINE_NAME = "security_engine"
LEVEL_SCHEMA = "ana.os10.security.v1"
REPORT_PATH = MEMORY_DIR / "security_report.json"

INPUTS = {
    "toolchain": MEMORY_DIR / "toolchain_manifest.json",
    "policies": MEMORY_DIR / "system_policies.json",
    "registry": MEMORY_DIR / "agent_registry.json",
    "daemon": MEMORY_DIR / "os4_daemon_report.json",
}

RISKY_TOOL_MARKERS = (
    "project_navigator",
    "smart_search",
    "file_patch",
    "frida",
    "remote_control",
    "network_pentest",
)


def _load_inputs() -> dict[str, Any]:
    return {name: read_json(path, {}) for name, path in INPUTS.items()}


def _violations(inputs: dict[str, Any]) -> list[dict[str, Any]]:
    toolchain = inputs.get("toolchain", {}) if isinstance(inputs.get("toolchain", {}), dict) else {}
    policies = inputs.get("policies", {}) if isinstance(inputs.get("policies", {}), dict) else {}
    registry = inputs.get("registry", {}) if isinstance(inputs.get("registry", {}), dict) else {}
    daemon = inputs.get("daemon", {}) if isinstance(inputs.get("daemon", {}), dict) else {}

    violations: list[dict[str, Any]] = []
    if toolchain.get("policy", {}).get("auto_enable") is True:
        violations.append({"id": "auto_enable_enabled", "severity": "critical"})
    if toolchain.get("policy", {}).get("validation") != "syntax_only_no_import_no_registration":
        violations.append({"id": "toolchain_validation_relaxed", "severity": "high"})

    active_tools = toolchain.get("tools", {}).get("active", []) if isinstance(toolchain.get("tools", {}).get("active", []), list) else []
    for item in active_tools:
        if not isinstance(item, dict):
            continue
        if item.get("dangerous") and not item.get("requires_explicit_enable"):
            violations.append(
                {
                    "id": f"dangerous_tool_without_explicit_enable:{item.get('name')}",
                    "severity": "high",
                }
            )

    registry_agents = registry.get("agents", {}) if isinstance(registry.get("agents", {}), dict) else {}
    if registry_agents and any(int(entry.get("failure_count", 0) or 0) > 0 for entry in registry_agents.values()):
        violations.append({"id": "agent_failures_present", "severity": "high"})

    if daemon and not bool(daemon.get("overall_success", True)):
        violations.append({"id": "daemon_not_successful", "severity": "medium"})
    if daemon and _safe_cycles(daemon) == 0:
        violations.append({"id": "daemon_cycles_unbounded_or_missing", "severity": "medium"})

    if policies and policies.get("schema") != "ana.os9.system_policies.v1":
        violations.append({"id": "system_policies_missing_or_invalid", "severity": "high"})

    return violations


def _safe_cycles(daemon: dict[str, Any]) -> int:
    try:
        max_cycles = int(daemon.get("max_cycles", 0) or 0)
    except Exception:
        max_cycles = 0
    return max_cycles


def _risky_marker_detected() -> bool:
    # Local-only, report-only scan of tool filenames. This does not execute tools.
    tools_dir = WORKSPACE_ROOT / "ANA_MAX" / "tools"
    if not tools_dir.exists():
        return False
    names = [path.stem.lower() for path in tools_dir.glob("*.py") if path.name != "__init__.py"]
    return any(any(marker in name for marker in RISKY_TOOL_MARKERS) for name in names)


def _verification(report: dict[str, Any]) -> dict[str, Any]:
    checks = {
        "schema_present": report.get("schema") == LEVEL_SCHEMA,
        "violations_present": isinstance(report.get("violations"), list),
        "summary_present": isinstance(report.get("summary"), dict),
        "security_state_present": "secure" in report,
    }
    return {"passed": all(checks.values()), "checks": checks}


def run_cycle(*, dry_run: bool = False) -> dict[str, Any]:
    started = time.perf_counter()
    inputs = _load_inputs()
    violations = _violations(inputs)
    secure = len(violations) == 0

    report = {
        "schema": LEVEL_SCHEMA,
        "generated_at": utc_now(),
        "engine": ENGINE_NAME,
        "workspace_root": str(WORKSPACE_ROOT),
        "dry_run": dry_run,
        "inputs": {name: str(path) for name, path in INPUTS.items()},
        "violations": violations,
        "secure": secure,
        "summary": {
            "violation_count": len(violations),
            "critical_count": sum(1 for item in violations if item.get("severity") == "critical"),
            "high_count": sum(1 for item in violations if item.get("severity") == "high"),
            "low_count": sum(1 for item in violations if item.get("severity") == "low"),
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
    parser = argparse.ArgumentParser(description="ANA MAX OS-10 Security Engine")
    parser.add_argument("--cycle", action="store_true", help="Run the security cycle.")
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
