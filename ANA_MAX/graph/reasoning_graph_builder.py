"""OS-21 reasoning graph builder.

This module is metadata-only. It turns local agent, topology, recon, and
capsule metadata into a deterministic reasoning graph without changing OS-20.1
runtime behavior.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ANA_MAX.agents.browser_recon_agent import BrowserReconAgent
from ANA_MAX.knowledge.capsule_schema import ReconCapsuleSchema
from ANA_MAX.knowledge.capsule_store import CapsuleStore
from ANA_MAX.orchestrators.web_recon_orchestrator import WebReconOrchestrator


GRAPH_SCHEMA = "ana.os21.reasoning_graph.v1"
BUILDER_NAME = "reasoning_graph_builder_v1"
BUILDER_VERSION = "1.0"
MEMORY_ROOT = ROOT / "ANA_MAX" / "memory"


def _read_json(path: Path, fallback: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback


def _unique_by_key(items: Iterable[dict[str, Any]], key_name: str = "id") -> list[dict[str, Any]]:
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for item in items:
        key = str(item.get(key_name, ""))
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def _unique_edges(items: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str, str]] = set()
    unique: list[dict[str, Any]] = []
    for item in items:
        signature = (
            str(item.get("source", "")),
            str(item.get("target", "")),
            str(item.get("relation", "")),
        )
        if not signature[0] or not signature[1] or signature in seen:
            continue
        seen.add(signature)
        unique.append(item)
    return unique


def _normalized_capsule(capsule: Any) -> dict[str, Any]:
    if isinstance(capsule, ReconCapsuleSchema):
        return capsule.to_dict()
    if isinstance(capsule, Mapping):
        return ReconCapsuleSchema.from_dict(capsule).to_dict()
    return {}


class ReasoningGraphBuilder:
    """Build a deterministic, metadata-only reasoning graph."""

    def __init__(
        self,
        *,
        capsule_store: CapsuleStore | None = None,
        agent_registry_path: Path | None = None,
        topology_path: Path | None = None,
        knowledge_graph_path: Path | None = None,
        orchestrator: WebReconOrchestrator | None = None,
    ) -> None:
        self.capsule_store = capsule_store or CapsuleStore()
        self.agent_registry_path = agent_registry_path or (MEMORY_ROOT / "agent_registry.json")
        self.topology_path = topology_path or (MEMORY_ROOT / "distributed_topology.json")
        self.knowledge_graph_path = knowledge_graph_path or (MEMORY_ROOT / "knowledge_graph.json")
        self.orchestrator = orchestrator or WebReconOrchestrator(BrowserReconAgent())
        self._last_graph: dict[str, Any] | None = None

    def _load_registry(self) -> dict[str, Any]:
        return _read_json(self.agent_registry_path, {"schema": "ana.os7.agent_registry.v1", "agents": {}, "summary": {}})

    def _load_topology(self) -> dict[str, Any]:
        return _read_json(self.topology_path, {"schema": "ana.os11.distributed_topology.v1", "nodes": [], "edges": [], "summary": {}})

    def _load_knowledge_graph(self) -> dict[str, Any]:
        return _read_json(self.knowledge_graph_path, {"schema": "ana.os5.knowledge_graph.v1", "summary": {}})

    def _agent_nodes(self, registry: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        nodes: list[dict[str, Any]] = [
            {
                "id": "context:agent_registry",
                "type": "context",
                "label": "agent_registry",
                "schema": registry.get("schema", ""),
            }
        ]
        edges: list[dict[str, Any]] = []

        agents = registry.get("agents") or {}
        for agent_id in sorted(agents):
            agent = agents.get(agent_id) or {}
            node_id = f"agent:{agent_id}"
            nodes.append(
                {
                    "id": node_id,
                    "type": "agent",
                    "label": agent_id,
                    "role": agent.get("role", agent_id),
                    "status": agent.get("status", "unknown"),
                    "health_score": agent.get("health_score", 0),
                    "failure_count": agent.get("failure_count", 0),
                    "success_count": agent.get("success_count", 0),
                    "requires_explicit_enable": bool(agent.get("requires_explicit_enable", False)),
                }
            )
            edges.append({"source": "context:agent_registry", "target": node_id, "relation": "describes"})

        return nodes, edges

    def _topology_nodes(self, topology: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        nodes: list[dict[str, Any]] = [
            {
                "id": "context:distributed_topology",
                "type": "context",
                "label": "distributed_topology",
                "schema": topology.get("schema", ""),
            }
        ]
        edges: list[dict[str, Any]] = []

        topology_nodes = topology.get("nodes") or []
        for node in topology_nodes:
            if not isinstance(node, Mapping):
                continue
            node_id = str(node.get("id", "")).strip()
            if not node_id:
                continue
            nodes.append(
                {
                    "id": f"node:{node_id}",
                    "type": "distributed_node",
                    "label": node_id,
                    "role": node.get("role", "unknown"),
                    "status": node.get("status", "unknown"),
                    "transport": node.get("transport", "unknown"),
                    "agent_slots": node.get("agent_slots", 0),
                }
            )
            edges.append({"source": "context:distributed_topology", "target": f"node:{node_id}", "relation": "describes"})

        for edge in topology.get("edges") or []:
            if not isinstance(edge, Mapping):
                continue
            source = str(edge.get("source", "")).strip()
            target = str(edge.get("target", "")).strip()
            if not source or not target:
                continue
            nodes.append(
                {
                    "id": f"edge:{source}->{target}",
                    "type": "distributed_edge",
                    "label": f"{source}->{target}",
                    "transport": edge.get("transport", "unknown"),
                    "edge_type": edge.get("type", "unknown"),
                }
            )
            edges.append({"source": f"node:{source}", "target": f"node:{target}", "relation": edge.get("type", "linked")})

        return nodes, edges

    def _knowledge_graph_nodes(self, knowledge_graph: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        summary = knowledge_graph.get("metadata") or knowledge_graph.get("summary") or {}
        node_count = summary.get("total_nodes") or summary.get("node_count") or 0
        edge_count = summary.get("total_edges") or summary.get("edge_count") or 0
        nodes = [
            {
                "id": "memory:knowledge_graph",
                "type": "memory",
                "label": "knowledge_graph",
                "node_count": node_count,
                "edge_count": edge_count,
            }
        ]
        edges = [{"source": "context:distributed_topology", "target": "memory:knowledge_graph", "relation": "summarizes"}]
        return nodes, edges

    def _capsule_nodes(self, capsules: list[Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        nodes: list[dict[str, Any]] = []
        edges: list[dict[str, Any]] = []
        for capsule in capsules:
            capsule_dict = _normalized_capsule(capsule)
            capsule_id = str(capsule_dict.get("capsule_id", "")).strip()
            if not capsule_id:
                continue
            node_id = f"capsule:{capsule_id}"
            nodes.append(
                {
                    "id": node_id,
                    "type": "capsule",
                    "label": capsule_id,
                    "mode": capsule_dict.get("mode", "passive"),
                    "version": capsule_dict.get("version", "1.0"),
                    "url": capsule_dict.get("url", ""),
                }
            )
            edges.append({"source": "memory:knowledge_graph", "target": node_id, "relation": "tracks"})
        return nodes, edges

    def _recon_nodes(self, recon_target: str, recon_mode: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
        if not recon_target:
            return [], [], {}

        pipeline = self.orchestrator.build_pipeline(recon_target, mode=recon_mode)
        agent_name = str(pipeline.get("agent_plan", {}).get("agent_name", "browser_recon_agent_v1"))
        orchestrator_name = str(pipeline.get("orchestrator_name", "web_recon_orchestrator_v1"))
        pipeline_id = f"pipeline:{pipeline.get('orchestrator_name', 'web_recon_orchestrator_v1')}"
        nodes: list[dict[str, Any]] = [
            {
                "id": f"orchestrator:{orchestrator_name}",
                "type": "orchestrator",
                "label": orchestrator_name,
                "mode": pipeline.get("mode", recon_mode),
            },
            {
                "id": f"agent:{agent_name}",
                "type": "agent",
                "label": agent_name,
                "role": pipeline.get("agent_plan", {}).get("agent_role", "browser_recon"),
                "mode": pipeline.get("mode", recon_mode),
            },
            {
                "id": pipeline_id,
                "type": "pipeline",
                "label": pipeline.get("orchestrator_name", "web_recon_orchestrator_v1"),
                "mode": pipeline.get("mode", recon_mode),
                "url": pipeline.get("url", recon_target),
            }
        ]
        edges: list[dict[str, Any]] = [
            {"source": "context:agent_registry", "target": pipeline_id, "relation": "plans"},
            {"source": "context:distributed_topology", "target": pipeline_id, "relation": "hosts"},
            {"source": f"orchestrator:{orchestrator_name}", "target": pipeline_id, "relation": "builds"},
            {"source": f"orchestrator:{orchestrator_name}", "target": f"agent:{agent_name}", "relation": "delegates"},
            {"source": f"agent:{agent_name}", "target": pipeline_id, "relation": "describes"},
        ]

        previous_phase_id = pipeline_id
        for index, phase in enumerate(pipeline.get("phases") or []):
            if not isinstance(phase, Mapping):
                continue
            phase_name = str(phase.get("name", f"phase_{index}"))
            phase_id = f"phase:{phase_name}"
            nodes.append(
                {
                    "id": phase_id,
                    "type": "phase",
                    "label": phase_name,
                    "phase_kind": phase.get("phase_kind", "passive"),
                    "risk": phase.get("risk", "low"),
                    "requires_confirmation": bool(phase.get("requires_confirmation", False)),
                }
            )
            edges.append({"source": previous_phase_id, "target": phase_id, "relation": "next"})
            previous_phase_id = phase_id

        nodes.append(
            {
                "id": "capsule:recon_seed",
                "type": "capsule_hint",
                "label": "recon_seed",
                "schema": pipeline.get("capsule_hints", {}).get("schema", ""),
            }
        )
        edges.append({"source": previous_phase_id, "target": "capsule:recon_seed", "relation": "handoff"})

        for tool_name in ("web_scraper", "browser_control"):
            nodes.append(
                {
                    "id": f"tool:{tool_name}",
                    "type": "tool",
                    "label": tool_name,
                    "contract": "browser_pack_v1",
                }
            )
            edges.append({"source": f"agent:{agent_name}", "target": f"tool:{tool_name}", "relation": "uses"})

        return nodes, edges, pipeline

    def build_graph(
        self,
        *,
        recon_target: str = "",
        recon_mode: str = "passive",
        capsules: list[Any] | None = None,
    ) -> dict[str, Any]:
        normalized_target = (recon_target or "").strip()
        normalized_mode = (recon_mode or "passive").strip().lower()
        if normalized_mode not in {"passive", "active"}:
            normalized_mode = "passive"

        registry = self._load_registry()
        topology = self._load_topology()
        knowledge_graph = self._load_knowledge_graph()
        capsule_items = list(capsules) if capsules is not None else []
        if capsules is None and self.capsule_store:
            capsule_items = [self.capsule_store.load_capsule(capsule_id) for capsule_id in self.capsule_store.list_capsules()]
        capsule_items = [capsule for capsule in capsule_items if capsule]

        nodes: list[dict[str, Any]] = []
        edges: list[dict[str, Any]] = []

        agent_nodes, agent_edges = self._agent_nodes(registry)
        topology_nodes, topology_edges = self._topology_nodes(topology)
        knowledge_nodes, knowledge_edges = self._knowledge_graph_nodes(knowledge_graph)
        capsule_nodes, capsule_edges = self._capsule_nodes(capsule_items)

        nodes.extend(agent_nodes)
        nodes.extend(topology_nodes)
        nodes.extend(knowledge_nodes)
        nodes.extend(capsule_nodes)
        edges.extend(agent_edges)
        edges.extend(topology_edges)
        edges.extend(knowledge_edges)
        edges.extend(capsule_edges)

        recon_nodes: list[dict[str, Any]] = []
        recon_edges: list[dict[str, Any]] = []
        pipeline: dict[str, Any] = {}
        if normalized_target:
            recon_nodes, recon_edges, pipeline = self._recon_nodes(normalized_target, normalized_mode)
            nodes.extend(recon_nodes)
            edges.extend(recon_edges)

        nodes = _unique_by_key(nodes)
        edges = _unique_edges(edges)

        summary = {
            "schema": GRAPH_SCHEMA,
            "builder_name": BUILDER_NAME,
            "agent_count": len(registry.get("agents") or {}),
            "graph_agent_count": len([node for node in nodes if node.get("type") == "agent"]),
            "orchestrator_count": len([node for node in nodes if node.get("type") == "orchestrator"]),
            "tool_count": len([node for node in nodes if node.get("type") == "tool"]),
            "distributed_node_count": len([node for node in nodes if node.get("type") == "distributed_node"]),
            "capsule_count": len([node for node in nodes if node.get("type") == "capsule"]),
            "phase_count": len([node for node in nodes if node.get("type") == "phase"]),
            "node_count": len(nodes),
            "edge_count": len(edges),
            "recon_enabled": bool(normalized_target),
        }

        graph = {
            "schema": GRAPH_SCHEMA,
            "builder_name": BUILDER_NAME,
            "version": BUILDER_VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "local_only": True,
            "baseline_compatible": True,
            "recon_target": normalized_target,
            "recon_mode": normalized_mode,
            "sources": {
                "agent_registry": {
                    "schema": registry.get("schema", ""),
                    "agent_count": len(registry.get("agents") or {}),
                },
                "distributed_topology": {
                    "schema": topology.get("schema", ""),
                    "node_count": len(topology.get("nodes") or []),
                    "edge_count": len(topology.get("edges") or []),
                    "overall_success": bool(topology.get("overall_success", False)),
                },
                "knowledge_graph": {
                    "schema": knowledge_graph.get("schema", ""),
                    "node_count": knowledge_graph.get("metadata", {}).get("total_nodes", knowledge_graph.get("summary", {}).get("node_count", 0)),
                    "edge_count": knowledge_graph.get("metadata", {}).get("total_edges", knowledge_graph.get("summary", {}).get("edge_count", 0)),
                },
                "capsule_count": len(capsule_items),
            },
            "agents": [node for node in nodes if node.get("type") == "agent"],
            "topology": [node for node in nodes if node.get("type") == "distributed_node"],
            "capsules": [node for node in nodes if node.get("type") == "capsule"],
            "nodes": nodes,
            "edges": edges,
            "reasoning_graph_hints": {
                "nodes": [node["id"] for node in nodes],
                "edges": [edge for edge in edges],
            },
            "summary": summary,
        }

        if pipeline:
            graph["recon_pipeline"] = pipeline

        self._last_graph = graph
        return graph

    def summarize_graph(self) -> dict[str, Any]:
        graph = self._last_graph or self.build_graph()
        return dict(graph.get("summary") or {})


def _run_from_cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a metadata-only reasoning graph.")
    parser.add_argument("--recon-target", default="", help="Optional recon target to fold into the graph")
    parser.add_argument("--mode", default="passive", choices=["passive", "active"], help="Recon mode when a target is provided")
    parser.add_argument("--summary", action="store_true", help="Print a compact summary only")
    parser.add_argument("--cycle", action="store_true", help="Build the graph and print the full JSON payload")
    args = parser.parse_args(argv)

    builder = ReasoningGraphBuilder()
    graph = builder.build_graph(recon_target=args.recon_target, recon_mode=args.mode)
    payload = builder.summarize_graph() if args.summary and not args.cycle else graph

    print(json.dumps(payload, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(_run_from_cli())
