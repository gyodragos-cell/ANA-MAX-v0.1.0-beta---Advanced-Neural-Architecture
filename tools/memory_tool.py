"""
ANA MAX - Memory Tool
"""

from __future__ import annotations

from typing import Any, Dict
from pathlib import Path

from core.memory import get_memory
from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus


class MemoryTool(Tool):
    def __init__(self) -> None:
        self.db_path = str(Path(__file__).resolve().parents[1] / "memory" / "ana_max_brain.db")

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="ana_memory",
            description="Acces curat la memoria persistenta ANA: knowledge, search, error patterns si stats.",
            parameters=[
                ToolParameter(
                    name="action",
                    description="Actiunea dorita",
                    type="string",
                    required=True,
                    choices=["save_knowledge", "search_knowledge", "list_topics", "stats", "save_error_solution", "find_error_solution"],
                ),
                ToolParameter(name="topic", description="Topic pentru knowledge", type="string", required=False),
                ToolParameter(name="content", description="Continutul knowledge", type="string", required=False),
                ToolParameter(name="category", description="Categoria knowledge", type="string", required=False),
                ToolParameter(name="query", description="Query pentru search", type="string", required=False),
                ToolParameter(name="limit", description="Numar maxim rezultate", type="integer", required=False, default=10),
                ToolParameter(name="error_pattern", description="Pattern de eroare", type="string", required=False),
                ToolParameter(name="solution", description="Solutie asociata erorii", type="string", required=False),
                ToolParameter(name="error_text", description="Text de eroare pentru cautare", type="string", required=False),
            ],
            category="memory",
        )

    def execute(self, **kwargs: Any) -> ToolResult:
        action = kwargs.get("action")
        memory = get_memory(self.db_path)

        try:
            if action == "save_knowledge":
                topic = kwargs.get("topic")
                content = kwargs.get("content")
                if not topic or not content:
                    return ToolResult(status=ToolStatus.ERROR, error="Parametrii 'topic' si 'content' sunt obligatorii.")
                ok = memory.save_knowledge(topic, content, category=kwargs.get("category"))
                return ToolResult(
                    status=ToolStatus.SUCCESS if ok else ToolStatus.ERROR,
                    data={"saved": bool(ok), "topic": topic},
                    message="Knowledge salvata." if ok else "",
                    error=None if ok else "Nu s-a putut salva knowledge.",
                )

            if action == "search_knowledge":
                query = kwargs.get("query")
                if not query:
                    return ToolResult(status=ToolStatus.ERROR, error="Parametrul 'query' este obligatoriu.")
                results = memory.search_knowledge(query, limit=int(kwargs.get("limit", 10)))
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data={"query": query, "count": len(results), "results": results},
                    message=f"Gasite {len(results)} rezultate in memorie.",
                )

            if action == "list_topics":
                topics = memory.list_all_knowledge()
                limit = int(kwargs.get("limit", 50))
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data={"count": len(topics), "topics": topics[:limit]},
                    message=f"Gasite {len(topics)} topicuri in memorie.",
                )

            if action == "stats":
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data=memory.get_stats(),
                    message="Statistici memorie disponibile.",
                )

            if action == "save_error_solution":
                error_pattern = kwargs.get("error_pattern")
                solution = kwargs.get("solution")
                if not error_pattern or not solution:
                    return ToolResult(status=ToolStatus.ERROR, error="Parametrii 'error_pattern' si 'solution' sunt obligatorii.")
                ok = memory.save_error_solution(error_pattern, solution)
                return ToolResult(
                    status=ToolStatus.SUCCESS if ok else ToolStatus.ERROR,
                    data={"saved": bool(ok), "error_pattern": error_pattern},
                    message="Pattern de eroare salvat." if ok else "",
                    error=None if ok else "Nu s-a putut salva pattern-ul de eroare.",
                )

            if action == "find_error_solution":
                error_text = kwargs.get("error_text")
                if not error_text:
                    return ToolResult(status=ToolStatus.ERROR, error="Parametrul 'error_text' este obligatoriu.")
                result = memory.find_error_solution(error_text)
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data={"found": bool(result), "result": result},
                    message="Pattern de eroare verificat.",
                )

            return ToolResult(status=ToolStatus.ERROR, error=f"Unknown action: {action}")
        except Exception as exc:
            return ToolResult(status=ToolStatus.ERROR, error=str(exc))
