"""Compact UI + code-map context pack for agent routing."""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any

from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus
from tools.foreground_ui_snapshot import ForegroundUISnapshotTool


ANA_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ANA_ROOT.parent
CODE_MAP_SCRIPT = ANA_ROOT / "dev_artifacts" / "scripts" / "ana_code_map.py"
GRAPH_MAP_SCRIPT = ANA_ROOT / "dev_artifacts" / "scripts" / "ana_graph_map.py"
CODE_MAP_OUT = ANA_ROOT / "memory" / "code_map"
GRAPH_MAP_OUT = ANA_ROOT / "memory" / "graph_map"


def _load_code_map_module():
    spec = importlib.util.spec_from_file_location("ana_code_map_runtime", CODE_MAP_SCRIPT)
    if not spec or not spec.loader:
        raise RuntimeError(f"Code map script not found: {CODE_MAP_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _load_graph_map_module():
    spec = importlib.util.spec_from_file_location("ana_graph_map_runtime", GRAPH_MAP_SCRIPT)
    if not spec or not spec.loader:
        raise RuntimeError(f"Graph map script not found: {GRAPH_MAP_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _text(value: Any, limit: int = 240) -> str:
    return str(value or "").replace("\r", " ").replace("\n", " ").strip()[:limit]


def _tokens(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9_.-]{3,}", text or "")


def _candidate_terms(snapshot: dict[str, Any], task: str, include_snapshot_terms: bool = True) -> str:
    if not include_snapshot_terms:
        return task.strip()
    parts = [
        task,
        _text(snapshot.get("active_app")),
        _text(snapshot.get("title")),
    ]
    for key in ("visible_text", "detected_errors", "buttons"):
        values = snapshot.get(key) or []
        if isinstance(values, list):
            parts.extend(_text(item, 120) for item in values[:12])
    candidates = []
    for token in _tokens(" ".join(parts)):
        lower = token.lower()
        if lower.endswith((".py", ".js", ".ts", ".tsx", ".md", ".json", ".ps1")):
            candidates.append(token)
        elif "_" in token or "." in token:
            candidates.append(token)
    focused = " ".join(candidates[:30])
    return f"{task} {focused}".strip() or " ".join(parts)


def _compact_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    return {
        "active_app": _text(snapshot.get("active_app"), 80) or None,
        "title": _text(snapshot.get("title"), 160) or None,
        "visible_text": [_text(item, 160) for item in (snapshot.get("visible_text") or [])[:8]],
        "detected_errors": [_text(item, 180) for item in (snapshot.get("detected_errors") or [])[:5]],
        "suggested_actions": (snapshot.get("suggested_actions") or [])[:5],
        "reason": _text(snapshot.get("reason"), 160) or None,
    }


class CodeContextPackTool(Tool):
    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="code_context_pack",
            description=(
                "Build a compact observation-first context pack by combining foreground UI "
                "state with ANA code map search results. Read-only."
            ),
            parameters=[
                ToolParameter("task", "Current user task or question", "string", False, ""),
                ToolParameter("query", "Alias for task; kept for agent/tool compatibility", "string", False, ""),
                ToolParameter("limit", "Maximum code map matches", "integer", False, 5),
                ToolParameter("refresh_if_empty", "Refresh code map if index is empty", "boolean", False, True),
                ToolParameter("include_text", "Include visible UI text in snapshot", "boolean", False, True),
                ToolParameter("include_graph", "Include graph-map query results and neighbors", "boolean", False, True),
            ],
            category="ai_core",
        )

    def execute(self, **kwargs: Any) -> ToolResult:
        task = str(kwargs.get("task") or kwargs.get("query") or "")
        limit = max(1, min(int(kwargs.get("limit") or 5), 10))
        refresh_if_empty = self._bool(kwargs.get("refresh_if_empty", True))
        include_text = self._bool(kwargs.get("include_text", True))
        include_graph = self._bool(kwargs.get("include_graph", True))

        try:
            snapshot_result = ForegroundUISnapshotTool().execute(
                include_text=include_text,
                max_elements=40,
            )
            snapshot = snapshot_result.data if snapshot_result.is_success and isinstance(snapshot_result.data, dict) else {}

            code_map = _load_code_map_module()
            stats = code_map.stats(CODE_MAP_OUT)
            if refresh_if_empty and int(stats.get("summaries") or 0) == 0:
                code_map.refresh(REPO_ROOT, CODE_MAP_OUT, force=False)
                stats = code_map.stats(CODE_MAP_OUT)

            query_text = _candidate_terms(snapshot, task, include_snapshot_terms=include_text)
            query_limit = max(limit, min(limit * 3, 10)) if include_graph else limit
            query = code_map.query(CODE_MAP_OUT, query_text, limit=query_limit)
            results = query.get("results", [])
            graph_query = self._graph_query(query_text, limit) if include_graph else None
            results = _prefer_graph_files(results, graph_query)[:limit]

            compressed_state = {
                "goal": _text(task, 220) or "Observe current workspace and route next action.",
                "current_ui": {
                    "app": _text(snapshot.get("active_app"), 80) or None,
                    "title": _text(snapshot.get("title"), 160) or None,
                },
                "evidence": [
                    "foreground_ui_snapshot",
                    "ana_code_map",
                ] + (["ana_graph_map"] if graph_query else []),
                "current_file_candidates": [item.get("file") for item in results[:3]],
                "next_action": "Open the top candidate only, inspect nearby symbols, then patch or diagnose.",
            }

            data = {
                "schema": "ana.code_context_pack.v1",
                "snapshot": _compact_snapshot(snapshot),
                "code_map": {
                    "updated_at": stats.get("updated_at"),
                    "summaries": stats.get("summaries"),
                    "query": query_text[:500],
                    "results": results,
                },
                "compressed_state": compressed_state,
            }
            if graph_query:
                data["graph_map"] = {
                    "updated_at": graph_query.get("updated_at"),
                    "results": graph_query.get("results", []),
                    "next_step": graph_query.get("next_step"),
                }
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data=data,
                message=f"Built context pack with {len(results)} code-map matches.",
            )
        except Exception as exc:
            return ToolResult(status=ToolStatus.ERROR, error=f"code_context_pack failed: {exc}")

    def _bool(self, value: Any) -> bool:
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() not in {"", "0", "false", "no", "off"}

    def _graph_query(self, query_text: str, limit: int) -> dict[str, Any] | None:
        try:
            graph_map = _load_graph_map_module()
            code_map = _load_code_map_module()
            code_stats = code_map.stats(CODE_MAP_OUT)
            graph_json = GRAPH_MAP_OUT / graph_map.GRAPH_JSON
            graph_stale = True
            if graph_json.exists():
                try:
                    graph = json.loads(graph_json.read_text(encoding="utf-8"))
                    graph_stale = graph.get("code_map_updated_at") != code_stats.get("updated_at")
                except (OSError, json.JSONDecodeError):
                    graph_stale = True
            if graph_stale:
                graph_map.build_graph(CODE_MAP_OUT, GRAPH_MAP_OUT)
            return graph_map.query_graph(GRAPH_MAP_OUT, query_text, limit=min(limit, 8))
        except Exception:
            return None


def _prefer_graph_files(results: list[dict[str, Any]], graph_query: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Prefer code-map file candidates that Graph Map also ranks highly."""
    if not graph_query or not results:
        return results
    graph_files: list[str] = []
    for item in graph_query.get("results") or []:
        name = str(item.get("name") or "")
        if item.get("kind") == "file" and name:
            graph_files.append(name)
    if not graph_files:
        return results
    rank = {name: index for index, name in enumerate(graph_files)}

    def key(item: dict[str, Any]) -> tuple[int, int]:
        file_name = str(item.get("file") or "")
        if file_name in rank:
            return (0, rank[file_name])
        return (1, 0)

    return sorted(results, key=key)
