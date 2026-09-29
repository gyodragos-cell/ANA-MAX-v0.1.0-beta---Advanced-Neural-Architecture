"""OS-21 finalizer.

This module marks OS-21 as finalized without entering OS-22. It aggregates the
metadata baseline gate and can write one final report artifact on request.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ANA_MAX.kernel.agent_capability_registry import AgentCapabilityRegistry
from ANA_MAX.kernel.os21_baseline_lock import OS21BaselineLock
from ANA_MAX.kernel.tool_virtualization_contracts import ToolVirtualizationContracts


FINALIZER_SCHEMA = "ana.os21.finalizer.v1"
FINALIZER_NAME = "os21_finalizer_v1"
FINALIZER_VERSION = "1.0"
DEFAULT_OUTPUT_PATH = ROOT / "ANA_MAX" / "memory" / "os21_final_report.json"
DEFAULT_LEVEL_REPORT_PATH = ROOT / "ANA_MAX" / "memory" / "os_level_OS21_report.json"


class OS21Finalizer:
    """Build and optionally persist the final OS-21 metadata report."""

    def __init__(
        self,
        output_path: Path | str | None = None,
        level_report_path: Path | str | None = None,
    ) -> None:
        self.output_path = Path(output_path) if output_path is not None else DEFAULT_OUTPUT_PATH
        self.level_report_path = (
            Path(level_report_path) if level_report_path is not None else DEFAULT_LEVEL_REPORT_PATH
        )
        self._last_report: dict[str, Any] | None = None

    def build_final_report(self) -> dict[str, Any]:
        baseline = OS21BaselineLock().build_report()
        baseline_validation = OS21BaselineLock().validate_report(baseline)
        registry_summary = AgentCapabilityRegistry().build_registry().get("summary", {})
        contract_summary = ToolVirtualizationContracts().build_contracts().get("summary", {})
        overall_success = bool(baseline.get("overall_success") and baseline_validation.get("success"))

        report = {
            "schema": FINALIZER_SCHEMA,
            "finalizer_name": FINALIZER_NAME,
            "version": FINALIZER_VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "os_level": "OS-21",
            "status": "FINALIZED" if overall_success else "BLOCKED",
            "overall_success": overall_success,
            "metadata_only": True,
            "local_only": True,
            "baseline_compatible": True,
            "no_runtime_execution": True,
            "baseline_lock": {
                "schema": baseline.get("schema", ""),
                "status": baseline.get("status", ""),
                "overall_success": baseline.get("overall_success", False),
                "module_count": baseline.get("summary", {}).get("module_count", 0),
                "failed_module_count": baseline.get("summary", {}).get("failed_module_count", 0),
            },
            "baseline_validation": baseline_validation,
            "kernel": {
                "agent_registry": {
                    "schema": registry_summary.get("schema", "ana.os21.agent_capability_registry.v1"),
                    "agent_count": registry_summary.get("agent_count", 0),
                    "capability_count": registry_summary.get("capability_count", 0),
                    "tool_count": registry_summary.get("tool_count", 0),
                },
                "tool_virtualization": {
                    "schema": contract_summary.get("schema", "ana.os21.tool_virtualization_contracts.v1"),
                    "tool_count": contract_summary.get("tool_count", 0),
                    "operation_contract_count": contract_summary.get("operation_contract_count", 0),
                    "execution_allowed": False,
                },
            },
            "boundary": {
                "stop_before": "OS-22",
                "os22_started": False,
                "ready_for_os22": False,
                "next_allowed_phase": "promotion_review_only",
                "reason": "User requested stop at OS-21 finalization.",
            },
            "final_artifacts": [
                "docs/OS21_PLAN.md",
                "docs/OS21_BASELINE_LOCK.md",
                "docs/TOOL_VIRTUALIZATION_CONTRACTS_V1.md",
                "docs/AGENT_CAPABILITY_REGISTRY_V1.md",
                "docs/TEST_REPORT.md",
                "ANA_MAX/memory/os21_final_report.json",
                "ANA_MAX/memory/os_level_OS21_report.json",
            ],
            "summary": {
                "schema": FINALIZER_SCHEMA,
                "finalizer_name": FINALIZER_NAME,
                "os_level": "OS-21",
                "status": "FINALIZED" if overall_success else "BLOCKED",
                "overall_success": overall_success,
                "module_count": baseline.get("summary", {}).get("module_count", 0),
                "failed_module_count": baseline.get("summary", {}).get("failed_module_count", 0),
                "ready_for_os22": False,
                "os22_started": False,
                "metadata_only": True,
                "local_only": True,
            },
        }
        self._last_report = report
        return report

    def build_level_report(self, report: Mapping[str, Any] | None = None) -> dict[str, Any]:
        payload = dict(report or self._last_report or self.build_final_report())
        summary = dict(payload.get("summary") or {})
        return {
            "schema": "ana.os21.level_report.v1",
            "generated_at": payload.get("generated_at"),
            "engine": FINALIZER_NAME,
            "os_level": "OS-21",
            "status": "PASS" if payload.get("overall_success") is True else "BLOCKED",
            "next": None,
            "overall_success": payload.get("overall_success") is True,
            "metadata_only": True,
            "local_only": True,
            "os22_started": False,
            "summary": {
                "finalizer_status": payload.get("status"),
                "module_count": summary.get("module_count", 0),
                "failed_module_count": summary.get("failed_module_count", 0),
                "ready_for_os22": False,
                "os22_started": False,
                "metadata_only": True,
                "local_only": True,
            },
        }

    def validate_final_report(self, report: Mapping[str, Any] | None = None) -> dict[str, Any]:
        payload = dict(report or self._last_report or self.build_final_report())
        issues: list[str] = []
        if payload.get("schema") != FINALIZER_SCHEMA:
            issues.append("schema_mismatch")
        if payload.get("os_level") != "OS-21":
            issues.append("wrong_os_level")
        if payload.get("status") != "FINALIZED":
            issues.append("not_finalized")
        if payload.get("overall_success") is not True:
            issues.append("overall_success_false")
        if payload.get("boundary", {}).get("os22_started") is not False:
            issues.append("os22_started")
        if payload.get("boundary", {}).get("stop_before") != "OS-22":
            issues.append("missing_os22_boundary")
        return {
            "schema": FINALIZER_SCHEMA,
            "finalizer_name": FINALIZER_NAME,
            "success": not issues,
            "issues": issues,
            "os_level": payload.get("os_level", ""),
            "status": payload.get("status", ""),
            "os22_started": bool(payload.get("boundary", {}).get("os22_started", False)),
        }

    def write_final_report(self) -> dict[str, Any]:
        report = self.build_final_report()
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.output_path.write_text(
            json.dumps(report, indent=2, ensure_ascii=True, sort_keys=True),
            encoding="utf-8",
        )
        return report

    def write_level_report(self, report: Mapping[str, Any] | None = None) -> dict[str, Any]:
        level_report = self.build_level_report(report)
        self.level_report_path.parent.mkdir(parents=True, exist_ok=True)
        self.level_report_path.write_text(
            json.dumps(level_report, indent=2, ensure_ascii=True, sort_keys=True),
            encoding="utf-8",
        )
        return level_report

    def summarize_final_report(self) -> dict[str, Any]:
        report = self._last_report or self.build_final_report()
        return dict(report.get("summary") or {})


def run(args: dict[str, Any] | None = None) -> dict[str, Any]:
    args = args or {}
    action = str(args.get("action", "summary"))
    finalizer = OS21Finalizer(output_path=args.get("output_path"))

    if action == "write":
        report = finalizer.write_final_report()
        level_report = finalizer.write_level_report(report)
        return {
            "success": report["overall_success"] and level_report["overall_success"],
            "result": report,
            "level_report": level_report,
        }
    report = finalizer.build_final_report()
    if action == "validate":
        result = finalizer.validate_final_report(report)
        return {"success": result["success"], "result": result}
    if action == "summary":
        return {"success": True, "result": finalizer.summarize_final_report()}
    if action in {"report", "cycle"}:
        return {"success": report["overall_success"], "result": report}
    return {"success": False, "error": f"unknown action: {action}"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Finalize OS-21 metadata baseline without entering OS-22.")
    parser.add_argument("--summary", action="store_true", help="Print compact final summary")
    parser.add_argument("--validate", action="store_true", help="Validate final report")
    parser.add_argument("--write", action="store_true", help="Write OS-21 final and level report artifacts")
    parser.add_argument("--cycle", action="store_true", help="Print full final report")
    parser.add_argument("--output-path", default="", help="Optional output path for --write")
    args = parser.parse_args(argv)

    action = "summary"
    if args.validate:
        action = "validate"
    elif args.write:
        action = "write"
    elif args.cycle:
        action = "cycle"
    elif args.summary:
        action = "summary"

    output = run({"action": action, "output_path": args.output_path or None})
    print(json.dumps(output, indent=2, ensure_ascii=True, sort_keys=True))
    return 0 if output.get("success", False) else 1


if __name__ == "__main__":
    raise SystemExit(main())
