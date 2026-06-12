"""Graph context pack over ANA code map.

Lab-native Graphify-inspired graph layer:
- refresh builds ANA_MAX/memory/graph_map from code_map index
- query returns relevant graph nodes and neighbors
- path finds a short relation path between two concepts
- blast estimates impacted files/tests/symbols from changed files
- stats reports graph health
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus


ANA_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ANA_ROOT.parent
GRAPH_SCRIPT = ANA_ROOT / "dev_artifacts" / "scripts" / "ana_graph_map.py"
CODE_MAP_SCRIPT = ANA_ROOT / "dev_artifacts" / "scripts" / "ana_code_map.py"
CODE_MAP_OUT = ANA_ROOT / "memory" / "code_map"
GRAPH_OUT = ANA_ROOT / "memory" / "graph_map"


def _load_module(script: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, script)
    if not spec or not spec.loader:
        raise RuntimeError(f"Script not found: {script}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() not in {"", "0", "false", "no", "off"}


class GraphContextPackTool(Tool):
    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="graph_context_pack",
            description=(
                "Build/query a local Graphify-inspired knowledge graph over ANA Code Map. "
                "Read-only for source files; writes graph artifacts under ANA_MAX/memory/graph_map."
            ),
            parameters=[
                ToolParameter("action", "refresh, query, path, blast, stats", "string", False, "query", choices=["refresh", "query", "path", "blast", "stats"]),
                ToolParameter("query", "Concept, file, symbol, or task to query", "string", False, ""),
                ToolParameter("source", "Source concept for path action", "string", False, ""),
                ToolParameter("target", "Target concept for path action", "string", False, ""),
                ToolParameter("changed", "Changed file path(s) for blast action; comma/newline separated or list", "string", False, ""),
                ToolParameter("limit", "Maximum query results", "integer", False, 8),
                ToolParameter("max_depth", "Maximum path depth", "integer", False, 4),
                ToolParameter("refresh_code_map_if_empty", "Refresh code map first when empty", "boolean", False, True),
            ],
            category="ai_core",
        )

    def execute(self, action: str = "query", **kwargs: Any) -> ToolResult:
        try:
            graph_map = _load_module(GRAPH_SCRIPT, "ana_graph_map_runtime")
            action = str(action or kwargs.get("action") or "query").strip().lower()
            limit = max(1, min(int(kwargs.get("limit") or 8), 25))
            max_depth = max(1, min(int(kwargs.get("max_depth") or 4), 8))
            code_map_stats = self._ensure_code_map(kwargs)

            if action == "refresh":
                graph = graph_map.build_graph(CODE_MAP_OUT, GRAPH_OUT)
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data={
                        "schema": graph.get("schema"),
                        "graph_out": str(GRAPH_OUT),
                        "graph_json": str(GRAPH_OUT / graph_map.GRAPH_JSON),
                        "graph_html": str(GRAPH_OUT / graph_map.GRAPH_HTML),
                        "report": str(GRAPH_OUT / graph_map.GRAPH_REPORT),
                        "stats": graph.get("stats"),
                    },
                    message=f"Graph map refreshed: {graph.get('stats', {}).get('nodes', 0)} nodes / {graph.get('stats', {}).get('edges', 0)} edges.",
                )

            if action == "stats":
                data = graph_map.stats(GRAPH_OUT)
                data["stale"] = self._graph_is_stale(graph_map, code_map_stats)
                return ToolResult(status=ToolStatus.SUCCESS, data=data, message="Graph map stats loaded.")

            if self._graph_is_stale(graph_map, code_map_stats):
                graph_map.build_graph(CODE_MAP_OUT, GRAPH_OUT)

            if action == "path":
                source = str(kwargs.get("source") or "")
                target = str(kwargs.get("target") or "")
                if not source or not target:
                    return ToolResult(status=ToolStatus.ERROR, error="source and target are required for graph path.")
                data = graph_map.path_query(GRAPH_OUT, source, target, max_depth=max_depth)
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data=data,
                    message="Graph path found." if data.get("found") else "Graph path not found.",
                )

            if action == "blast":
                changed = kwargs.get("changed") or kwargs.get("query") or ""
                if not changed:
                    return ToolResult(status=ToolStatus.ERROR, error="changed or query is required for graph blast.")
                data = graph_map.blast_radius(GRAPH_OUT, changed, limit=limit)
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data=data,
                    message=f"Graph blast-radius returned {data.get('affected_count', 0)} affected nodes.",
                )

            query = str(kwargs.get("query") or "")
            if not query:
                return ToolResult(status=ToolStatus.ERROR, error="query is required for graph query.")
            data = graph_map.query_graph(GRAPH_OUT, query, limit=limit)
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data=data,
                message=f"Graph query returned {data.get('results_count', 0)} nodes.",
            )
        except Exception as exc:
            return ToolResult(status=ToolStatus.ERROR, error=f"graph_context_pack failed: {exc}")

    def _ensure_code_map(self, kwargs: dict[str, Any]) -> dict[str, Any]:
        refresh_if_empty = _bool(kwargs.get("refresh_code_map_if_empty", True))
        code_map = _load_module(CODE_MAP_SCRIPT, "ana_code_map_for_graph_context")
        stats = code_map.stats(CODE_MAP_OUT)
        if refresh_if_empty and int(stats.get("summaries") or 0) == 0:
            code_map.refresh(REPO_ROOT, CODE_MAP_OUT, force=False)
            stats = code_map.stats(CODE_MAP_OUT)
        return stats

    def _graph_is_stale(self, graph_map: Any, code_map_stats: dict[str, Any]) -> bool:
        graph_json = GRAPH_OUT / graph_map.GRAPH_JSON
        if not graph_json.exists():
            return True
        try:
            graph = json.loads(graph_json.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return True
        return graph.get("code_map_updated_at") != code_map_stats.get("updated_at")
