#!/usr/bin/env python3
"""ANA MAX OS-11 Distributed Orchestrator (local simulation only)."""

from __future__ import annotations

import argparse
import time
from typing import Any

from ANA_MAX.self_optimization.osx_level_common import (
    WORKSPACE_ROOT,
    agent_registry_snapshot,
    baseline_metrics,
    build_level_report,
    build_memory_snapshot,
    emit_raw_json,
    level_report_path,
    load_memory_context,
    memory_context_summary,
    read_json,
    write_json,
    write_level_report,
    utc_now,
)

ENGINE_NAME = "distributed_orchestrator"
LEVEL = 11
LEVEL_SCHEMA = "ana.os11.distributed_orchestrator.v1"
TOPOLOGY_SCHEMA = "ana.os11.distributed_topology.v1"
TOPOLOGY_PATH = level_report_path(LEVEL).with_name("distributed_topology.json")

INPUTS = {
    "agent_registry": TOPOLOGY_PATH.parent / "agent_registry.json",
    "shared_state": TOPOLOGY_PATH.parent / "multi_agent_shared_state.json",
    "evolution": TOPOLOGY_PATH.parent / "evolution_report.json",
    "daemon": TOPOLOGY_PATH.parent / "os4_daemon_report.json",
    "consistency": TOPOLOGY_PATH.parent / "self_consistency_report.json",
}


def _node_templates(agent_count: int, health_score: int) -> list[dict[str, Any]]:
    roles = ["coordinator", "optimizer", "tester", "observer"]
    nodes: list[dict[str, Any]] = []
    for index, role in enumerate(roles, start=1):
        nodes.append(
            {
                "id": f"node-{index}",
                "role": role,
                "status": "healthy" if health_score == 100 else "degraded",
                "transport": "local-loopback",
                "agent_slots": max(1, min(3, agent_count or 1)),
            }
        )
    return nodes


def _edge_templates(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    edges: list[dict[str, Any]] = []
    if not nodes:
        return edges
    root = nodes[0]["id"]
    for node in nodes[1:]:
        edges.append(
            {
                "source": root,
                "target": node["id"],
                "type": "simulated",
                "transport": "in-memory",
            }
        )
    return edges


def run_cycle(*, dry_run: bool = True, node_count: int = 4) -> dict[str, Any]:
    started = time.perf_counter()
    memory_snapshot = build_memory_snapshot()
    baseline = baseline_metrics()
    agent_snapshot = agent_registry_snapshot()
    registry_agents = agent_snapshot.get("agents", {}) if isinstance(agent_snapshot, dict) else {}
    agent_count = len(registry_agents) if isinstance(registry_agents, dict) else 0
    healthy_agents = sum(1 for entry in registry_agents.values() if int(entry.get("failure_count", 0) or 0) == 0) if isinstance(registry_agents, dict) else 0
    failure_count_total = sum(int(entry.get("failure_count", 0) or 0) for entry in registry_agents.values()) if isinstance(registry_agents, dict) else 0

    nodes = _node_templates(agent_count, baseline.get("health_score", 0))[: max(3, node_count)]
    edges = _edge_templates(nodes)

    topology = {
        "schema": TOPOLOGY_SCHEMA,
        "generated_at": utc_now(),
        "engine": ENGINE_NAME,
        "workspace_root": str(WORKSPACE_ROOT),
        "local_only": True,
        "simulated": True,
        "dry_run": dry_run,
        "memory_context": memory_context_summary(load_memory_context()),
        "nodes": nodes,
        "edges": edges,
        "summary": {
            "node_count": len(nodes),
            "edge_count": len(edges),
            "agent_count": agent_count,
            "healthy_agent_count": healthy_agents,
            "agent_failure_count": failure_count_total,
            "health_score": baseline.get("health_score", 0),
            "warnings": baseline.get("warnings", 0),
            "parse_error_count": baseline.get("parse_error_count", 0),
        },
    }

    write_json(TOPOLOGY_PATH, topology)

    level_payload = {
        "schema": LEVEL_SCHEMA,
        "generated_at": utc_now(),
        "engine": ENGINE_NAME,
        "workspace_root": str(WORKSPACE_ROOT),
        "dry_run": dry_run,
        "inputs": {name: str(path) for name, path in INPUTS.items()},
        "topology": topology,
        "agent_registry": agent_snapshot,
        "memory_snapshot": memory_snapshot,
        "summary": topology["summary"],
    }

    overall_success = (
        topology["summary"]["health_score"] == 100
        and topology["summary"]["warnings"] == 0
        and topology["summary"]["parse_error_count"] == 0
        and topology["summary"]["agent_failure_count"] == 0
    )

    report = {
        "schema": LEVEL_SCHEMA,
        "generated_at": level_payload["generated_at"],
        "engine": ENGINE_NAME,
        "dry_run": dry_run,
        "overall_success": overall_success,
        "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
        "report_path": str(TOPOLOGY_PATH),
        "level_report_path": str(level_report_path(LEVEL)),
        "topology": topology,
        "summary": {
            **topology["summary"],
            "overall_success": overall_success,
        },
    }

    level_report = build_level_report(
        os_level=LEVEL,
        engine=ENGINE_NAME,
        status="PASS" if overall_success else "WARN",
        next_level="OS-12",
        summary=report["summary"],
        payload=level_payload,
        dry_run=dry_run,
        memory_snapshot=memory_snapshot,
    )
    write_level_report(LEVEL, level_report)

    return report


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ANA MAX OS-11 Distributed Orchestrator")
    parser.add_argument("--cycle", action="store_true", help="Run a bounded distributed simulation cycle.")
    parser.add_argument("--dry-run", action="store_true", help="Compute topology without changing agent registry state.")
    parser.add_argument("--nodes", type=int, default=4, help="Number of local nodes to simulate.")
    return parser


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()
    dry_run = args.dry_run or not args.cycle
    result = run_cycle(dry_run=dry_run, node_count=max(3, args.nodes))
    emit_raw_json(result)
    return 0 if result.get("overall_success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
