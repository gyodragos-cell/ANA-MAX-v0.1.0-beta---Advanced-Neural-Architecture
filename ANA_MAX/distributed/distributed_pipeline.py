"""OS-21 distributed pipeline skeleton.

This module is metadata-only. It combines the agent scheduler and reasoning
graph into a local-only distributed runtime plan without executing tasks.
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

from ANA_MAX.agents.agent_scheduler import AgentScheduler
from ANA_MAX.graph.reasoning_graph_builder import ReasoningGraphBuilder


DISTRIBUTED_PIPELINE_SCHEMA = "ana.os21.distributed_pipeline.v1"
PIPELINE_NAME = "distributed_pipeline_v1"
PIPELINE_VERSION = "1.0"
MEMORY_ROOT = ROOT / "ANA_MAX" / "memory"


def _read_json(path: Path, fallback: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback


def _task_blueprint(workload: str) -> list[dict[str, Any]]:
    normalized = (workload or "recon").strip().lower()
    if normalized == "recon":
        return [
            {"task_type": "observe_topology", "purpose": "Inspect the local topology metadata", "preferred_role": "structurer"},
            {"task_type": "build_schedule", "purpose": "Create a deterministic agent schedule", "preferred_role": "optimizer"},
            {"task_type": "dispatch_shards", "purpose": "Plan shard dispatch across nodes", "preferred_role": "tester"},
            {"task_type": "aggregate_results", "purpose": "Combine shard outputs into a single view", "preferred_role": "documenter"},
            {"task_type": "validate_outputs", "purpose": "Validate the pipeline output metadata", "preferred_role": "tester"},
        ]
    return [
        {"task_type": f"{normalized}_observe", "purpose": f"Observe the {normalized} workload", "preferred_role": "structurer"},
        {"task_type": f"{normalized}_schedule", "purpose": f"Schedule the {normalized} workload", "preferred_role": "optimizer"},
        {"task_type": f"{normalized}_dispatch", "purpose": f"Dispatch the {normalized} workload", "preferred_role": "tester"},
        {"task_type": f"{normalized}_aggregate", "purpose": f"Aggregate the {normalized} workload", "preferred_role": "documenter"},
        {"task_type": f"{normalized}_validate", "purpose": f"Validate the {normalized} workload", "preferred_role": "tester"},
    ]


class DistributedPipelineSkeleton:
    """Build a deterministic distributed runtime plan."""

    def __init__(
        self,
        *,
        scheduler: AgentScheduler | None = None,
        graph_builder: ReasoningGraphBuilder | None = None,
        topology_path: Path | None = None,
    ) -> None:
        self.scheduler = scheduler or AgentScheduler()
        self.graph_builder = graph_builder or ReasoningGraphBuilder()
        self.topology_path = topology_path or (MEMORY_ROOT / "distributed_topology.json")
        self._last_pipeline: dict[str, Any] | None = None

    def _load_topology(self) -> dict[str, Any]:
        return _read_json(self.topology_path, {"schema": "ana.os11.distributed_topology.v1", "nodes": [], "edges": [], "summary": {}})

    def _node_profiles(self, topology: dict[str, Any]) -> list[dict[str, Any]]:
        profiles: list[dict[str, Any]] = []
        for node in topology.get("nodes") or []:
            if not isinstance(node, Mapping):
                continue
            node_id = str(node.get("id", "")).strip()
            if not node_id:
                continue
            transport = str(node.get("transport", "local-loopback"))
            profiles.append(
                {
                    "node_id": node_id,
                    "role": str(node.get("role", "unknown")),
                    "status": str(node.get("status", "unknown")),
                    "transport": transport,
                    "execution_tier": "local" if "local" in transport else "hybrid",
                    "agent_slots": int(node.get("agent_slots", 0) or 0),
                }
            )
        return profiles

    def _shards_from_schedule(self, topology_nodes: list[dict[str, Any]], schedule: dict[str, Any]) -> list[dict[str, Any]]:
        if not topology_nodes:
            return []
        assignments = schedule.get("assignments") or []
        shards: dict[str, dict[str, Any]] = {}
        for index, node in enumerate(topology_nodes):
            node_id = node["node_id"]
            shard_id = f"shard:{node_id}"
            shards[shard_id] = {
                "shard_id": shard_id,
                "node_id": node_id,
                "role": node["role"],
                "transport": node["transport"],
                "execution_tier": node["execution_tier"],
                "task_ids": [],
            }
        for index, assignment in enumerate(assignments):
            shard_ids = list(shards)
            shard = shards[shard_ids[index % len(shard_ids)]]
            shard["task_ids"].append(str(assignment.get("task_id", "")))
        return [shards[shard_id] for shard_id in sorted(shards)]

    def build_pipeline(self, workload: str = "recon", mode: str = "local") -> dict[str, Any]:
        normalized_workload = (workload or "recon").strip().lower()
        normalized_mode = (mode or "local").strip().lower()
        if normalized_mode not in {"local", "hybrid"}:
            normalized_mode = "local"

        topology = self._load_topology()
        topology_nodes = self._node_profiles(topology)
        tasks = _task_blueprint(normalized_workload)
        schedule = self.scheduler.build_schedule(tasks=tasks, policy="safe" if normalized_mode == "local" else "balanced")
        graph = self.graph_builder.build_graph(
            recon_target="",
            recon_mode="passive" if normalized_mode == "local" else "active",
        )

        if normalized_mode == "hybrid":
            transport_abstractions = sorted({*(node["transport"] for node in topology_nodes), "hybrid-placeholder"})
        else:
            transport_abstractions = sorted({node["transport"] for node in topology_nodes})

        shards = self._shards_from_schedule(topology_nodes, schedule)
        phases = [
            {
                "name": "topology_ingest",
                "purpose": "Normalize the distributed topology metadata.",
                "outputs": ["topology_profile"],
            },
            {
                "name": "agent_schedule",
                "purpose": "Build a deterministic multi-agent schedule.",
                "outputs": ["schedule"],
            },
            {
                "name": "shard_partition",
                "purpose": "Map planned tasks onto topology shards.",
                "outputs": ["shards"],
            },
            {
                "name": "dispatch_simulation",
                "purpose": "Describe how work would move between nodes without executing it.",
                "outputs": ["dispatch_map"],
            },
            {
                "name": "aggregate_results",
                "purpose": "Combine metadata from all planned shards.",
                "outputs": ["aggregate_view"],
            },
            {
                "name": "validate_outputs",
                "purpose": "Check the pipeline metadata for consistency.",
                "outputs": ["validation_summary"],
            },
        ]

        pipeline = {
            "schema": DISTRIBUTED_PIPELINE_SCHEMA,
            "pipeline_name": PIPELINE_NAME,
            "version": PIPELINE_VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "local_only": True,
            "simulated": True,
            "baseline_compatible": True,
            "workload": normalized_workload,
            "mode": normalized_mode,
            "topology": {
                "schema": topology.get("schema", ""),
                "node_count": len(topology_nodes),
                "edge_count": len(topology.get("edges") or []),
                "health_score": topology.get("summary", {}).get("health_score", 0),
                "warnings": topology.get("summary", {}).get("warnings", 0),
                "parse_error_count": topology.get("summary", {}).get("parse_error_count", 0),
                "overall_success": bool(topology.get("overall_success", False)),
            },
            "transport_abstractions": transport_abstractions,
            "nodes": topology_nodes,
            "edges": list(topology.get("edges") or []),
            "phases": phases,
            "tasks": tasks,
            "schedule": schedule,
            "shards": shards,
            "graph": graph,
            "reasoning_graph_hints": {
                "nodes": list(graph.get("reasoning_graph_hints", {}).get("nodes") or []),
                "edges": list(graph.get("reasoning_graph_hints", {}).get("edges") or []),
            },
            "dispatch_strategy": {
                "type": "round_robin",
                "policy": normalized_mode,
                "task_to_shard": {assignment["task_id"]: shards[index % len(shards)]["shard_id"] for index, assignment in enumerate(schedule.get("assignments") or [])} if shards else {},
            },
            "summary": {
                "schema": DISTRIBUTED_PIPELINE_SCHEMA,
                "pipeline_name": PIPELINE_NAME,
                "workload": normalized_workload,
                "mode": normalized_mode,
                "node_count": len(topology_nodes),
                "transport_count": len(transport_abstractions),
                "task_count": len(tasks),
                "assignment_count": len(schedule.get("assignments") or []),
                "shard_count": len(shards),
                "phase_count": len(phases),
                "graph_node_count": len(graph.get("nodes") or []),
                "graph_edge_count": len(graph.get("edges") or []),
            },
        }

        self._last_pipeline = pipeline
        return pipeline

    def summarize_pipeline(self) -> dict[str, Any]:
        pipeline = self._last_pipeline or self.build_pipeline()
        return dict(pipeline.get("summary") or {})


def _run_from_cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a metadata-only distributed pipeline skeleton.")
    parser.add_argument("--workload", default="recon", help="Workload label for the pipeline")
    parser.add_argument("--mode", default="local", choices=["local", "hybrid"], help="Pipeline mode")
    parser.add_argument("--summary", action="store_true", help="Print a compact summary only")
    parser.add_argument("--cycle", action="store_true", help="Build the pipeline and print the full JSON payload")
    args = parser.parse_args(argv)

    pipeline = DistributedPipelineSkeleton().build_pipeline(workload=args.workload, mode=args.mode)
    payload = DistributedPipelineSkeleton().summarize_pipeline() if args.summary and not args.cycle else pipeline

    print(json.dumps(payload, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(_run_from_cli())

