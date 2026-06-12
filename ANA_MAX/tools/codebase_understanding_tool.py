"""
ANA MAX - Codebase Understanding Tool
"""

from __future__ import annotations

import logging
import os
from typing import Any

from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus

logger = logging.getLogger(__name__)


class CodebaseUnderstandingTool(Tool):
    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="codebase_understanding",
            description="Interogare semantica si analiza de arhitectura pentru codebase.",
            parameters=[
                ToolParameter(name="query", description="Intrebarea sau cautarea", type="string", required=False),
                ToolParameter(
                    name="action",
                    description="Actiunea dorita",
                    type="string",
                    required=True,
                    choices=["ask", "analyze", "semantic_search"],
                ),
                ToolParameter(
                    name="project_path",
                    description="Calea catre proiect",
                    type="string",
                    required=False,
                ),
            ],
            category="code",
        )

    def execute(self, **kwargs: Any) -> ToolResult:
        action = kwargs.get("action", "ask")
        project_path = kwargs.get("project_path") or os.getcwd()

        try:
            from core.codebase_understanding import get_codebase_understanding

            engine = get_codebase_understanding(project_path)

            if action == "ask":
                query = kwargs.get("query")
                if not query:
                    return ToolResult(status=ToolStatus.ERROR, error="Parametrul 'query' este obligatoriu pentru 'ask'")
                engine.analyze_project()
                answer = engine.ask_codebase(query)
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data={"answer": answer},
                    message="Analiza semantica finalizata",
                )

            if action == "analyze":
                stats = engine.analyze_project()
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data=stats,
                    message="Proiect analizat si indexat",
                )

            if action == "semantic_search":
                query = kwargs.get("query")
                if not query:
                    return ToolResult(status=ToolStatus.ERROR, error="Parametrul 'query' este obligatoriu")
                results = engine.semantic_search(query)
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data={"results": results},
                    message=f"Gasite {len(results)} fragmente relevante",
                )

            return ToolResult(status=ToolStatus.ERROR, error=f"Actiune necunoscuta: {action}")
        except Exception as exc:
            logger.error("Codebase understanding failed: %s", exc)
            return ToolResult(status=ToolStatus.ERROR, error=str(exc))
