"""Minimal ANA graph map runtime built on top of ANA code map."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


GRAPH_JSON = "graph_map.json"
GRAPH_HTML = "graph_map.html"
GRAPH_REPORT = "graph_map_report.md"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_code_map(code_map_out: str | Path) -> dict[str, Any]:
    path = Path(code_map_out) / "code_map.json"
    if not path.exists():
        return {"updated_at": None, "summaries": []}
    return json.loads(path.read_text(encoding="utf-8"))


def build_graph(code_map_out: str | Path, graph_out: str | Path) -> dict[str, Any]:
    graph_out = Path(graph_out)
    graph_out.mkdir(parents=True, exist_ok=True)
    code_map = _load_code_map(code_map_out)
    nodes = []
    edges = []
    for item in code_map.get("summaries") or []:
        file_node = item.get("file")
        if not file_node:
            continue
        nodes.append({"id": file_node, "type": "file", "symbols": item.get("symbols", [])})
        for symbol in item.get("symbols") or []:
            symbol_id = f"{file_node}::{symbol}"
            nodes.append({"id": symbol_id, "type": "symbol"})
            edges.append({"source": file_node, "target": symbol_id, "type": "defines"})
    payload = {
        "schema": "ana.graph_map.v1",
        "updated_at": _now(),
        "code_map_updated_at": code_map.get("updated_at"),
        "nodes": nodes,
        "edges": edges,
        "stats": {"nodes": len(nodes), "edges": len(edges)},
    }
    (graph_out / GRAPH_JSON).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    (graph_out / GRAPH_REPORT).write_text(
        f"# ANA Graph Map\n\n- Nodes: {len(nodes)}\n- Edges: {len(edges)}\n",
        encoding="utf-8",
    )
    (graph_out / GRAPH_HTML).write_text("<!doctype html><title>ANA Graph Map</title><pre>Graph built.</pre>", encoding="utf-8")
    return payload


def _load_graph(graph_out: str | Path) -> dict[str, Any]:
    path = Path(graph_out) / GRAPH_JSON
    if not path.exists():
        return {"schema": "ana.graph_map.v1", "updated_at": None, "nodes": [], "edges": [], "stats": {"nodes": 0, "edges": 0}}
    return json.loads(path.read_text(encoding="utf-8"))


def stats(graph_out: str | Path) -> dict[str, Any]:
    graph = _load_graph(graph_out)
    return {
        "schema": graph.get("schema", "ana.graph_map.v1"),
        "updated_at": graph.get("updated_at"),
        **(graph.get("stats") or {"nodes": 0, "edges": 0}),
    }


def query_graph(graph_out: str | Path, query: str, limit: int = 8) -> dict[str, Any]:
    graph = _load_graph(graph_out)
    terms = [part.lower() for part in str(query or "").split() if len(part) >= 3]
    results = []
    for node in graph.get("nodes") or []:
        haystack = json.dumps(node, ensure_ascii=False).lower()
        score = sum(1 for term in terms if term in haystack)
        if score or not terms:
            item = dict(node)
            item["score"] = score
            results.append(item)
    results.sort(key=lambda item: (-int(item.get("score") or 0), item.get("id", "")))
    return {"schema": "ana.graph_map.query.v1", "results_count": len(results), "results": results[: max(1, int(limit or 8))], "next_step": "Open the highest scoring file node."}


def path_query(graph_out: str | Path, source: str, target: str, max_depth: int = 4) -> dict[str, Any]:
    graph = _load_graph(graph_out)
    direct = any(edge.get("source") == source and edge.get("target") == target for edge in graph.get("edges") or [])
    return {"schema": "ana.graph_map.path.v1", "found": direct, "path": [source, target] if direct else []}


def blast_radius(graph_out: str | Path, changed: str, limit: int = 8) -> dict[str, Any]:
    query = query_graph(graph_out, changed, limit)
    return {"schema": "ana.graph_map.blast.v1", "affected_count": query.get("results_count", 0), "affected": query.get("results", [])}
