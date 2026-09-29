"""OS-21 distributed pipeline recovery metadata.

This module is metadata-only. It describes checkpoints, retries, shard states,
and migration candidates for a distributed pipeline without executing work.
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

from ANA_MAX.distributed.distributed_pipeline import DistributedPipelineSkeleton


RECOVERY_SCHEMA = "ana.os21.pipeline_recovery.v1"
PLANNER_NAME = "pipeline_recovery_v1"
PLANNER_VERSION = "1.0"


def _as_string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return [str(item) for item in value if str(item)]
    return [str(value)]


def _dedupe_in_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for item in items:
        if not item or item in seen:
            continue
        seen.add(item)
        unique.append(item)
    return unique


def _node_ref_from_shard(shard_id: str) -> str:
    if shard_id.startswith("shard:"):
        return shard_id.split(":", 1)[1]
    return shard_id


def _pipeline_dict(value: Mapping[str, Any] | None) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    return DistributedPipelineSkeleton().build_pipeline()


class PipelineRecoveryPlanner:
    """Build read-only recovery metadata for OS-21 distributed pipelines."""

    def __init__(self, pipeline_builder: DistributedPipelineSkeleton | None = None) -> None:
        self.pipeline_builder = pipeline_builder or DistributedPipelineSkeleton()
        self._last_plan: dict[str, Any] | None = None

    def _task_order(self, pipeline: Mapping[str, Any]) -> list[str]:
        assignments = pipeline.get("schedule", {}).get("assignments") or []
        task_ids = [str(item.get("task_id", "")) for item in assignments if isinstance(item, Mapping)]
        if task_ids:
            return _dedupe_in_order(task_ids)
        tasks = pipeline.get("tasks") or []
        return _dedupe_in_order([str(item.get("task_id", "")) for item in tasks if isinstance(item, Mapping)])

    def _task_to_shard(self, pipeline: Mapping[str, Any]) -> dict[str, str]:
        mapped = pipeline.get("dispatch_strategy", {}).get("task_to_shard") or {}
        task_to_shard = {str(task_id): str(shard_id) for task_id, shard_id in mapped.items()}
        for shard in pipeline.get("shards") or []:
            if not isinstance(shard, Mapping):
                continue
            shard_id = str(shard.get("shard_id", ""))
            for task_id in shard.get("task_ids") or []:
                task_to_shard.setdefault(str(task_id), shard_id)
        return task_to_shard

    def build_checkpoints(self, pipeline: Mapping[str, Any]) -> list[dict[str, Any]]:
        checkpoints: list[dict[str, Any]] = []
        for phase in pipeline.get("phases") or []:
            if not isinstance(phase, Mapping):
                continue
            phase_name = str(phase.get("name", "")).strip()
            if not phase_name:
                continue
            checkpoints.append(
                {
                    "checkpoint_id": f"checkpoint:phase:{phase_name}",
                    "checkpoint_type": "phase",
                    "phase_name": phase_name,
                    "status": "available",
                    "restore_strategy": "metadata_replay",
                    "artifact_refs": [str(item) for item in phase.get("outputs") or []],
                }
            )

        for shard in pipeline.get("shards") or []:
            if not isinstance(shard, Mapping):
                continue
            shard_id = str(shard.get("shard_id", "")).strip()
            if not shard_id:
                continue
            checkpoints.append(
                {
                    "checkpoint_id": f"checkpoint:shard:{_node_ref_from_shard(shard_id)}",
                    "checkpoint_type": "shard",
                    "shard_id": shard_id,
                    "node_id": str(shard.get("node_id", "")),
                    "status": "available",
                    "restore_strategy": "shard_metadata_replay",
                    "artifact_refs": [f"task:{task_id}" for task_id in shard.get("task_ids") or []],
                }
            )
        return sorted(checkpoints, key=lambda item: item["checkpoint_id"])

    def build_shard_states(
        self,
        pipeline: Mapping[str, Any],
        *,
        failed_task_ids: list[str],
        failed_shard_ids: list[str],
    ) -> list[dict[str, Any]]:
        failed_tasks = set(failed_task_ids)
        failed_shards = set(failed_shard_ids)
        states: list[dict[str, Any]] = []
        for shard in pipeline.get("shards") or []:
            if not isinstance(shard, Mapping):
                continue
            shard_id = str(shard.get("shard_id", "")).strip()
            if not shard_id:
                continue
            task_ids = [str(item) for item in shard.get("task_ids") or []]
            if shard_id in failed_shards:
                status = "failed"
            elif any(task_id in failed_tasks for task_id in task_ids):
                status = "degraded"
            else:
                status = "ready"
            states.append(
                {
                    "shard_id": shard_id,
                    "node_id": str(shard.get("node_id", "")),
                    "status": status,
                    "recoverable": True,
                    "task_ids": task_ids,
                    "failed_task_ids": [task_id for task_id in task_ids if task_id in failed_tasks],
                    "checkpoint_id": f"checkpoint:shard:{_node_ref_from_shard(shard_id)}",
                }
            )
        return sorted(states, key=lambda item: item["shard_id"])

    def build_retry_queue(
        self,
        pipeline: Mapping[str, Any],
        *,
        failed_task_ids: list[str],
        failed_shard_ids: list[str],
        max_retries: int,
    ) -> list[dict[str, Any]]:
        task_to_shard = self._task_to_shard(pipeline)
        failed_tasks = set(failed_task_ids)
        failed_shards = set(failed_shard_ids)
        retry_task_ids: list[str] = []
        for task_id in self._task_order(pipeline):
            shard_id = task_to_shard.get(task_id, "")
            if task_id in failed_tasks or shard_id in failed_shards:
                retry_task_ids.append(task_id)

        retry_queue: list[dict[str, Any]] = []
        for task_id in _dedupe_in_order(retry_task_ids):
            shard_id = task_to_shard.get(task_id, "")
            reasons: list[str] = []
            if task_id in failed_tasks:
                reasons.append("failed_task")
            if shard_id in failed_shards:
                reasons.append("failed_shard")
            retry_queue.append(
                {
                    "task_id": task_id,
                    "current_shard_id": shard_id,
                    "attempt": 0,
                    "max_retries": max(0, int(max_retries)),
                    "status": "planned_retry",
                    "mode": "metadata_only",
                    "requires_migration": bool(shard_id in failed_shards or task_id in failed_tasks),
                    "reasons": reasons,
                }
            )
        return retry_queue

    def build_migration_candidates(
        self,
        pipeline: Mapping[str, Any],
        *,
        retry_queue: list[dict[str, Any]],
        failed_shard_ids: list[str],
    ) -> list[dict[str, Any]]:
        shard_ids = sorted(str(shard.get("shard_id", "")) for shard in pipeline.get("shards") or [] if isinstance(shard, Mapping))
        shard_ids = [item for item in shard_ids if item]
        failed_shards = set(failed_shard_ids)
        healthy_shards = [shard_id for shard_id in shard_ids if shard_id not in failed_shards]
        candidates: list[dict[str, Any]] = []

        for item in retry_queue:
            task_id = str(item.get("task_id", ""))
            from_shard = str(item.get("current_shard_id", ""))
            to_shard = ""
            if healthy_shards:
                if from_shard in healthy_shards and len(healthy_shards) > 1:
                    index = healthy_shards.index(from_shard)
                    to_shard = healthy_shards[(index + 1) % len(healthy_shards)]
                elif from_shard not in healthy_shards:
                    to_shard = healthy_shards[0]
                else:
                    to_shard = healthy_shards[0]
            candidates.append(
                {
                    "migration_id": f"migration:{task_id}",
                    "task_id": task_id,
                    "from_shard_id": from_shard,
                    "to_shard_id": to_shard,
                    "status": "planned_migration" if to_shard else "held",
                    "mode": "metadata_only",
                    "reason": "retry_reassignment",
                }
            )
        return sorted(candidates, key=lambda item: item["task_id"])

    def build_recovery_plan(
        self,
        *,
        pipeline: Mapping[str, Any] | None = None,
        failed_task_ids: list[str] | tuple[str, ...] | None = None,
        failed_shard_ids: list[str] | tuple[str, ...] | None = None,
        max_retries: int = 2,
    ) -> dict[str, Any]:
        pipeline_payload = _pipeline_dict(pipeline) if pipeline is not None else self.pipeline_builder.build_pipeline()
        normalized_failed_tasks = _dedupe_in_order(_as_string_list(failed_task_ids))
        normalized_failed_shards = _dedupe_in_order(_as_string_list(failed_shard_ids))
        retry_limit = max(0, int(max_retries or 0))

        checkpoints = self.build_checkpoints(pipeline_payload)
        shard_states = self.build_shard_states(
            pipeline_payload,
            failed_task_ids=normalized_failed_tasks,
            failed_shard_ids=normalized_failed_shards,
        )
        retry_queue = self.build_retry_queue(
            pipeline_payload,
            failed_task_ids=normalized_failed_tasks,
            failed_shard_ids=normalized_failed_shards,
            max_retries=retry_limit,
        )
        migration_candidates = self.build_migration_candidates(
            pipeline_payload,
            retry_queue=retry_queue,
            failed_shard_ids=normalized_failed_shards,
        )

        failed_shard_count = len([item for item in shard_states if item["status"] == "failed"])
        degraded_shard_count = len([item for item in shard_states if item["status"] == "degraded"])
        plan = {
            "schema": RECOVERY_SCHEMA,
            "planner_name": PLANNER_NAME,
            "version": PLANNER_VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "metadata_only": True,
            "local_only": True,
            "simulated": True,
            "baseline_compatible": True,
            "pipeline_ref": {
                "schema": pipeline_payload.get("schema", ""),
                "pipeline_name": pipeline_payload.get("pipeline_name", ""),
                "workload": pipeline_payload.get("workload", ""),
                "mode": pipeline_payload.get("mode", ""),
                "task_count": len(self._task_order(pipeline_payload)),
                "shard_count": len(pipeline_payload.get("shards") or []),
            },
            "failed_task_ids": normalized_failed_tasks,
            "failed_shard_ids": normalized_failed_shards,
            "retry_policy": {
                "max_retries": retry_limit,
                "backoff": "none",
                "retry_mode": "metadata_only",
            },
            "checkpoints": checkpoints,
            "retry_queue": retry_queue,
            "shard_states": shard_states,
            "migration_candidates": migration_candidates,
            "validation": {
                "schema": RECOVERY_SCHEMA,
                "valid": bool(pipeline_payload.get("schema")),
                "issues": [] if pipeline_payload.get("schema") else ["missing_pipeline_schema"],
            },
            "summary": {
                "schema": RECOVERY_SCHEMA,
                "planner_name": PLANNER_NAME,
                "checkpoint_count": len(checkpoints),
                "retry_count": len(retry_queue),
                "migration_count": len(migration_candidates),
                "failed_shard_count": failed_shard_count,
                "degraded_shard_count": degraded_shard_count,
                "overall_success": bool(pipeline_payload.get("schema")),
            },
        }
        self._last_plan = plan
        return plan

    def summarize_recovery(self) -> dict[str, Any]:
        plan = self._last_plan or self.build_recovery_plan()
        return dict(plan.get("summary") or {})


def _run_from_cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build metadata-only distributed pipeline recovery metadata.")
    parser.add_argument("--workload", default="recon", help="Workload label for the generated pipeline")
    parser.add_argument("--mode", default="local", choices=["local", "hybrid"], help="Pipeline mode")
    parser.add_argument("--failed-task", action="append", default=[], help="Task ID to mark as failed")
    parser.add_argument("--failed-shard", action="append", default=[], help="Shard ID to mark as failed")
    parser.add_argument("--max-retries", type=int, default=2, help="Maximum planned retry attempts")
    parser.add_argument("--summary", action="store_true", help="Print compact summary only")
    parser.add_argument("--cycle", action="store_true", help="Build and print the full recovery plan")
    args = parser.parse_args(argv)

    pipeline = DistributedPipelineSkeleton().build_pipeline(workload=args.workload, mode=args.mode)
    planner = PipelineRecoveryPlanner()
    plan = planner.build_recovery_plan(
        pipeline=pipeline,
        failed_task_ids=args.failed_task,
        failed_shard_ids=args.failed_shard,
        max_retries=args.max_retries,
    )
    payload = planner.summarize_recovery() if args.summary and not args.cycle else plan

    print(json.dumps(payload, indent=2, ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(_run_from_cli())
