"""OS-21 reasoning graph query API.

This module is metadata-only. It reads an in-memory reasoning graph or builds
one through ReasoningGraphBuilder, then returns deterministic query payloads.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import deque
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ANA_MAX.graph.reasoning_graph_builder import ReasoningGraphBuilder


QUERY_SCHEMA = "ana.os21.reasoning_graph_query.v1"
QUERY_NAME = "reasoning_graph_query_v1"
QUERY_VERSION = "1.0"


def _as_graph(value: Mapping[str, Any] | None) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    return {}


def _nodes(graph: Mapping[str, Any]) -> list[dict[str, Any]]:
    items = graph.get("nodes") or []
    return [dict(item) for item in items if isinstance(item, Mapping)]


def _edges(graph: Mapping[str, Any]) -> list[dict[str, Any]]:
    items = graph.get("edges") or []
    return [dict(item) for item in items if isinstance(item, Mapping)]


def _normalize_prefixed_id(value: str, prefix: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        return ""
    if ":" in normalized:
        return normalized
    return f"{prefix}:{normalized}"


def _sort_nodes(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(items, key=lambda item: str(item.get("id", "")))


def _sort_edges(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        items,
        key=lambda item: (
            str(item.get("source", "")),
            str(item.get("target", "")),
            str(item.get("relation", "")),
        ),
    )


class ReasoningGraphQuery:
    """Read-only query helper for OS-21 reasoning graph metadata."""

    def __init__(
        self,
        *,
        graph: Mapping[str, Any] | None = None,
        builder: ReasoningGraphBuilder | None = None,
    ) -> None:
        self.builder = builder or ReasoningGraphBuilder()
        self.graph = _as_graph(graph) or self.builder.build_graph()
        self._query_log: list[dict[str, Any]] = []

    def _payload(self, query: dict[str, Any], results: list[Any]) -> dict[str, Any]:
        payload = {
            "schema": QUERY_SCHEMA,
            "query_name": QUERY_NAME,
            "version": QUERY_VERSION,
            "metadata_only": True,
            "local_only": True,
            "baseline_compatible": True,
            "query": query,
            "count": len(results),
            "results": results,
        }
        self._query_log.append(
            {
                "type": query.get("type", ""),
                "count": len(results),
            }
        )
        return payload

    def find_nodes_by_type(self, node_type: str) -> dict[str, Any]:
        normalized_type = str(node_type or "").strip()
        results = [
            node
            for node in _nodes(self.graph)
            if str(node.get("type", "")) == normalized_type
        ]
        return self._payload(
            {
                "type": "find_nodes_by_type",
                "node_type": normalized_type,
            },
            _sort_nodes(results),
        )

    def find_edges_by_agent(self, agent_id: str) -> dict[str, Any]:
        normalized_agent_id = _normalize_prefixed_id(agent_id, "agent")
        results = [
            edge
            for edge in _edges(self.graph)
            if edge.get("source") == normalized_agent_id or edge.get("target") == normalized_agent_id
        ]
        return self._payload(
            {
                "type": "find_edges_by_agent",
                "agent_id": normalized_agent_id,
            },
            _sort_edges(results),
        )

    def find_capsules_by_url(self, url: str) -> dict[str, Any]:
        normalized_url = str(url or "").strip()
        results = [
            node
            for node in _nodes(self.graph)
            if node.get("type") == "capsule" and str(node.get("url", "")) == normalized_url
        ]
        return self._payload(
            {
                "type": "find_capsules_by_url",
                "url": normalized_url,
            },
            _sort_nodes(results),
        )

    def find_tools_by_degree(self, min_degree: int = 1) -> dict[str, Any]:
        threshold = max(0, int(min_degree or 0))
        graph_edges = _edges(self.graph)
        results: list[dict[str, Any]] = []
        for node in _nodes(self.graph):
            if node.get("type") != "tool":
                continue
            node_id = str(node.get("id", ""))
            degree = sum(
                1
                for edge in graph_edges
                if edge.get("source") == node_id or edge.get("target") == node_id
            )
            if degree >= threshold:
                enriched = dict(node)
                enriched["degree"] = degree
                results.append(enriched)

        results = sorted(results, key=lambda item: (-int(item.get("degree", 0)), str(item.get("id", ""))))
        return self._payload(
            {
                "type": "find_tools_by_degree",
                "min_degree": threshold,
            },
            results,
        )

    def find_paths(self, source_id: str, target_id: str, max_depth: int = 4) -> dict[str, Any]:
        source = str(source_id or "").strip()
        target = str(target_id or "").strip()
        depth = max(0, int(max_depth or 0))
        node_ids = {str(node.get("id", "")) for node in _nodes(self.graph)}

        if not source or not target or source not in node_ids or target not in node_ids:
            return self._payload(
                {
                    "type": "find_paths",
                    "source_id": source,
                    "target_id": target,
                    "max_depth": depth,
                },
                [],
            )

        adjacency: dict[str, list[str]] = {}
        for edge in _edges(self.graph):
            edge_source = str(edge.get("source", ""))
            edge_target = str(edge.get("target", ""))
            if not edge_source or not edge_target:
                continue
            adjacency.setdefault(edge_source, [])
            if edge_target not in adjacency[edge_source]:
                adjacency[edge_source].append(edge_target)

        queue: deque[list[str]] = deque([[source]])
        results: list[list[str]] = []
        seen_paths: set[tuple[str, ...]] = set()

        while queue:
            path = queue.popleft()
            current = path[-1]
            if current == target:
                signature = tuple(path)
                if signature not in seen_paths:
                    seen_paths.add(signature)
                    results.append(path)
                continue

            if len(path) - 1 >= depth:
                continue

            for next_node in adjacency.get(current, []):
                if next_node in path:
                    continue
                queue.append([*path, next_node])

        results = sorted(results, key=lambda item: (len(item), item))
        return self._payload(
            {
                "type": "find_paths",
                "source_id": source,
                "target_id": target,
                "max_depth": depth,
            },
            results,
        )

    def summarize_queries(self) -> dict[str, Any]:
        graph_summary = dict(self.graph.get("summary") or {})
        return {
            "schema": QUERY_SCHEMA,
            "query_name": QUERY_NAME,
            "version": QUERY_VERSION,
            "metadata_only": True,
            "local_only": True,
            "baseline_compatible": True,
            "graph_schema": self.graph.get("schema", ""),
            "node_count": len(_nodes(self.graph)),
            "edge_count": len(_edges(self.graph)),
            "query_count": len(self._query_log),
            "queries": list(self._query_log),
            "graph_summary": graph_summary,
        }


def _run_from_cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Query a metadata-only reasoning graph.")
    parser.add_argument("--summary", action="store_true", help="Print query API and graph summary")
    parser.add_argument("--node-type", default="", help="Find nodes by type")
    parser.add_argument("--agent", default="", help="Find edges touching an agent")
    parser.add_argument("--capsule-url", default="", help="Find capsule nodes by URL")
    parser.add_argument("--tools-by-degree", action="store_true", help="Find tool nodes with degree >= min degree")
    parser.add_argument("--min-degree", type=int, default=1, help="Minimum degree for tool query")
    parser.add_argument("--source", default="", help="Source node ID for path query")
    parser.add_argument("--target", default="", help="Target node ID for path query")
    parser.add_argument("--max-depth", type=int, default=4, help="Maximum edge depth for path query")
    args = parser.parse_args(argv)

    query = ReasoningGraphQuery()
    payload: dict[str, Any]

    if args.node_type:
        payload = query.find_nodes_by_type(args.node_type)
    elif args.agent:
        payload = query.find_edges_by_agent(args.agent)
    elif args.capsule_url:
        payload = query.find_capsules_by_url(args.capsule_url)
    elif args.tools_by_degree:
        payload = query.find_tools_by_degree(args.min_degree)
    elif args.source or args.target:
        payload = query.find_paths(args.source, args.target, args.max_depth)
    else:
        payload = query.summarize_queries()

    if args.summary and payload.get("schema") == QUERY_SCHEMA and "results" in payload:
        payload = query.summarize_queries()

    print(json.dumps(payload, indent=2, ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(_run_from_cli())
