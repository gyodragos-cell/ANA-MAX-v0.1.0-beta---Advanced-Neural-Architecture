"""
ANA MAX - Smart Search Tool
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from core.smart_search import get_search_engine
from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus

logger = logging.getLogger(__name__)


class SmartSearchTool(Tool):
    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="smart_search",
            description="Cautare ultra-rapida in proiecte mari.",
            parameters=[
                ToolParameter(name="query", description="Cuvinte cheie", type="string", required=False),
                ToolParameter(
                    name="action",
                    description="Actiunea dorita",
                    type="string",
                    required=True,
                    choices=["search", "index", "find_definition", "stats"],
                ),
                ToolParameter(name="project_path", description="Calea catre proiect", type="string", required=False),
                ToolParameter(name="symbol", description="Simbol pentru find_definition", type="string", required=False),
            ],
            category="code",
        )

    def execute(self, **kwargs: Any) -> ToolResult:
        action = kwargs.get("action", "search")
        if action == "search":
            res = self._search(**kwargs)
        elif action == "index":
            res = self._index_project(**kwargs)
        elif action == "find_definition":
            res = self._find_definition(**kwargs)
        elif action == "stats":
            res = self._get_stats(**kwargs)
        else:
            return ToolResult(status=ToolStatus.ERROR, error=f"Unknown action: {action}")

        if res.get("success"):
            return ToolResult(status=ToolStatus.SUCCESS, data=res, message=res.get("message", ""))
        return ToolResult(status=ToolStatus.ERROR, error=res.get("error", "Unknown error"))

    def _search(self, **kwargs: Any) -> Dict[str, Any]:
        query = kwargs.get("query")
        if not query:
            return {"error": "Missing 'query' parameter"}

        project_path = kwargs.get("project_path")
        file_types = kwargs.get("file_types")
        limit = kwargs.get("limit", 10)

        try:
            search_engine = get_search_engine(project_path)
            results = search_engine.search(query, limit=limit, file_types=file_types)
            debug_info = getattr(search_engine, "last_query_debug", {})
            formatted = [
                {
                    "file": r["file_path"],
                    "language": r["language"],
                    "lines": f"{r['start_line']}-{r['end_line']}",
                    "preview": r["match_content"][:200] + "..." if len(r["match_content"]) > 200 else r["match_content"],
                    "relevance": f"{r['relevance']:.2f}",
                }
                for r in results
            ]
            return {
                "success": True,
                "query": query,
                "normalized_query": debug_info.get("normalized_query", query),
                "results_count": len(results),
                "results": formatted,
                "message": f"Gasite {len(results)} rezultate",
            }
        except Exception as exc:
            logger.error("Search failed for query %r: %s", query, exc)
            return {"success": False, "error": str(exc), "query": query}

    def _index_project(self, **kwargs: Any) -> Dict[str, Any]:
        project_path = kwargs.get("project_path")
        force = kwargs.get("force", False)

        try:
            search_engine = get_search_engine(project_path)
            stats = search_engine.index_project(force=force)
            return {
                "success": True,
                "message": f"Indexare completa in {stats['elapsed_time']:.2f}s",
                "files_processed": stats["files_processed"],
                "files_updated": stats["files_updated"],
                "files_skipped": stats["files_skipped"],
                "speed": f"{stats['files_per_second']:.0f} files/sec",
            }
        except Exception as exc:
            logger.error("Indexing failed: %s", exc)
            return {"success": False, "error": str(exc)}

    def _find_definition(self, **kwargs: Any) -> Dict[str, Any]:
        symbol = kwargs.get("symbol")
        if not symbol:
            return {"error": "Missing 'symbol' parameter"}

        project_path = kwargs.get("project_path")
        language = kwargs.get("language")

        try:
            search_engine = get_search_engine(project_path)
            results = search_engine.find_definition(symbol, language)
            formatted = [
                {
                    "file": r["file_path"],
                    "line": r["start_line"],
                    "preview": r["match_content"][:150] + "...",
                }
                for r in results
            ]
            return {
                "success": True,
                "symbol": symbol,
                "definitions_found": len(results),
                "results": formatted,
            }
        except Exception as exc:
            logger.error("Find definition failed: %s", exc)
            return {"success": False, "error": str(exc)}

    def _get_stats(self, **kwargs: Any) -> Dict[str, Any]:
        project_path = kwargs.get("project_path")
        try:
            search_engine = get_search_engine(project_path)
            stats = search_engine.get_stats()
            return {"success": True, **stats}
        except Exception as exc:
            logger.error("Get stats failed: %s", exc)
            return {"success": False, "error": str(exc)}
