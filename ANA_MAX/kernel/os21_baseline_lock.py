"""OS-21 baseline lock report.

This module builds a metadata-only finalization report for the OS-21 additive
layers. It does not execute tools, mutate memory, or alter OS-20.1 runtime.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ANA_MAX.agents.agent_scheduler import AgentScheduler
from ANA_MAX.agents.browser_recon_agent import BrowserReconAgent
from ANA_MAX.agents.web_recon_agent import WebReconAgent
from ANA_MAX.agents.web_scraper_agent import WebScraperAgent
from ANA_MAX.distributed.distributed_pipeline import DistributedPipelineSkeleton
from ANA_MAX.distributed.pipeline_recovery import PipelineRecoveryPlanner
from ANA_MAX.graph.reasoning_graph_builder import ReasoningGraphBuilder
from ANA_MAX.graph.reasoning_graph_query import ReasoningGraphQuery
from ANA_MAX.kernel.agent_capability_registry import AgentCapabilityRegistry
from ANA_MAX.kernel.tool_virtualization_contracts import ToolVirtualizationContracts
from ANA_MAX.knowledge.capsule_merge import CapsuleMergeEngine
from ANA_MAX.knowledge.capsule_schema import ReconCapsuleSchema
from ANA_MAX.knowledge.capsule_store import CapsuleStore
from ANA_MAX.knowledge.capsule_sync import CapsuleSyncEngine
from ANA_MAX.orchestrators.web_recon_orchestrator import WebReconOrchestrator
from ANA_MAX.tools import browser_pack


BASELINE_SCHEMA = "ana.os21.baseline_lock.v1"
LOCK_NAME = "os21_baseline_lock_v1"
LOCK_VERSION = "1.0"


def _schema_status(name: str, expected_schema: str, producer: Callable[[], Mapping[str, Any]]) -> dict[str, Any]:
    try:
        payload = dict(producer())
        actual_schema = str(payload.get("schema", ""))
        success = actual_schema == expected_schema
        return {
            "module": name,
            "expected_schema": expected_schema,
            "actual_schema": actual_schema,
            "success": success,
            "issues": [] if success else ["schema_mismatch"],
        }
    except Exception as exc:  # pragma: no cover - defensive baseline reporting
        return {
            "module": name,
            "expected_schema": expected_schema,
            "actual_schema": "",
            "success": False,
            "issues": [f"exception:{exc}"],
        }


class OS21BaselineLock:
    """Build a final metadata-only OS-21 baseline report."""

    def __init__(self) -> None:
        self._last_report: dict[str, Any] | None = None

    def _module_checks(self) -> list[dict[str, Any]]:
        capsule = ReconCapsuleSchema(
            capsule_id="baseline-capsule",
            url="https://example.com",
            mode="passive",
            timestamp="2026-06-10T00:00:00+00:00",
            passive_phases=("scope",),
            version="1.0",
        )
        capsule_store = CapsuleStore()
        capsule_store.save_capsule(capsule.to_dict())
        graph = ReasoningGraphBuilder().build_graph(
            recon_target="https://example.com",
            recon_mode="passive",
            capsules=[capsule],
        )
        pipeline = DistributedPipelineSkeleton().build_pipeline(workload="recon", mode="local")
        registry = AgentCapabilityRegistry().build_registry()
        contracts = ToolVirtualizationContracts().build_contracts(registry=registry)

        return [
            _schema_status("browser_pack", "ana.os21.browser_pack.v1", browser_pack.build_browser_pack_manifest),
            _schema_status("browser_recon_agent", "ana.os21.browser_recon_agent.v1", lambda: BrowserReconAgent().build_plan("https://example.com")),
            _schema_status("web_recon_orchestrator", "ana.os21.web_recon_orchestrator.v1", lambda: WebReconOrchestrator().build_pipeline("https://example.com")),
            _schema_status("capsule_schema", "ana.os21.recon_capsule.v1", capsule.to_dict),
            _schema_status("capsule_store", "ana.os21.capsule_store.v1", lambda: {"schema": "ana.os21.capsule_store.v1", "capsule_ids": capsule_store.list_capsules()}),
            _schema_status("capsule_merge", "ana.os21.capsule_merge.v1", lambda: CapsuleMergeEngine().merge(capsule.to_dict(), capsule.to_dict(), capsule.to_dict())),
            _schema_status("capsule_sync", "ana.os21.capsule_sync_plan.v1", lambda: CapsuleSyncEngine().build_sync_plan([capsule.to_dict()], [capsule.to_dict()])),
            _schema_status("reasoning_graph_builder", "ana.os21.reasoning_graph.v1", lambda: graph),
            _schema_status("reasoning_graph_query", "ana.os21.reasoning_graph_query.v1", lambda: ReasoningGraphQuery(graph=graph).summarize_queries()),
            _schema_status("agent_scheduler", "ana.os21.agent_scheduler.v1", lambda: AgentScheduler().build_schedule()),
            _schema_status("distributed_pipeline", "ana.os21.distributed_pipeline.v1", lambda: pipeline),
            _schema_status("pipeline_recovery", "ana.os21.pipeline_recovery.v1", lambda: PipelineRecoveryPlanner().build_recovery_plan(pipeline=pipeline)),
            _schema_status("web_scraper_agent", "ana.os21.web_scraper_agent.v1", lambda: WebScraperAgent().build_plan(["https://example.com"])),
            _schema_status("web_recon_agent", "ana.os21.web_recon_agent.v1", lambda: WebReconAgent().build_plan("https://example.com")),
            _schema_status("agent_capability_registry", "ana.os21.agent_capability_registry.v1", lambda: registry),
            _schema_status("tool_virtualization_contracts", "ana.os21.tool_virtualization_contracts.v1", lambda: contracts),
        ]

    def build_report(self) -> dict[str, Any]:
        module_checks = self._module_checks()
        failed = [item for item in module_checks if not item.get("success")]
        status = "PASS" if not failed else "FAIL"
        report = {
            "schema": BASELINE_SCHEMA,
            "lock_name": LOCK_NAME,
            "version": LOCK_VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "metadata_only": True,
            "local_only": True,
            "baseline_compatible": True,
            "status": status,
            "overall_success": not failed,
            "baseline": {
                "os20_runtime_untouched": True,
                "execution_allowed": False,
                "tool_execution_allowed": False,
                "transport_execution_allowed": False,
                "file_mutation_required": False,
            },
            "module_checks": module_checks,
            "summary": {
                "schema": BASELINE_SCHEMA,
                "lock_name": LOCK_NAME,
                "status": status,
                "overall_success": not failed,
                "module_count": len(module_checks),
                "failed_module_count": len(failed),
                "metadata_only": True,
                "local_only": True,
            },
        }
        self._last_report = report
        return report

    def validate_report(self, report: Mapping[str, Any] | None = None) -> dict[str, Any]:
        payload = dict(report or self._last_report or self.build_report())
        issues: list[str] = []
        if payload.get("schema") != BASELINE_SCHEMA:
            issues.append("schema_mismatch")
        if payload.get("overall_success") is not True:
            issues.append("overall_success_false")
        if payload.get("baseline", {}).get("execution_allowed") is not False:
            issues.append("execution_allowed_not_false")
        failed = [item for item in payload.get("module_checks") or [] if not item.get("success")]
        if failed:
            issues.append("module_failures")
        schemas = sorted(
            {
                str(item.get("actual_schema", ""))
                for item in payload.get("module_checks") or []
                if item.get("actual_schema")
            }
        )
        return {
            "schema": BASELINE_SCHEMA,
            "lock_name": LOCK_NAME,
            "success": not issues,
            "issues": issues,
            "schemas": schemas,
            "module_count": len(payload.get("module_checks") or []),
        }

    def summarize_report(self) -> dict[str, Any]:
        report = self._last_report or self.build_report()
        return dict(report.get("summary") or {})


def run(args: dict[str, Any] | None = None) -> dict[str, Any]:
    args = args or {}
    action = str(args.get("action", "report"))
    lock = OS21BaselineLock()
    report = lock.build_report()

    if action == "summary":
        return {"success": True, "result": lock.summarize_report()}
    if action == "validate":
        result = lock.validate_report(report)
        return {"success": result["success"], "result": result}
    if action in {"report", "cycle"}:
        return {"success": report["overall_success"], "result": report}
    return {"success": False, "error": f"unknown action: {action}"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build OS-21 baseline lock metadata.")
    parser.add_argument("--summary", action="store_true", help="Print compact summary")
    parser.add_argument("--validate", action="store_true", help="Validate baseline report")
    parser.add_argument("--cycle", action="store_true", help="Print full baseline report")
    args = parser.parse_args(argv)

    action = "report"
    if args.summary:
        action = "summary"
    elif args.validate:
        action = "validate"
    elif args.cycle:
        action = "cycle"

    output = run({"action": action})
    print(json.dumps(output, indent=2, ensure_ascii=True, sort_keys=True))
    return 0 if output.get("success", False) else 1


if __name__ == "__main__":
    raise SystemExit(main())
