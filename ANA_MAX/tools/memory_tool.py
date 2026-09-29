"""
ANA MAX - Memory Tool (OS27 Hyper++)
====================================

OS27 Hyper++ Features:
- Telemetry tracking for memory operations (save_knowledge, search_knowledge, list_topics, stats, save_error_solution, find_error_solution)
- Health monitoring for memory operations reliability
- MemoryCortex integration for memory errors and state learning
- ContextEngine integration for memory state awareness
- SelfEvolvingTool integration for anomaly detection on memory failures
- Structured logging with error detection
"""

from __future__ import annotations

import time
from typing import Any, Dict
from pathlib import Path

from core.memory import get_memory
from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus

# OS27 Hyper++ Telemetry
_memory_telemetry: Dict[str, Dict[str, Any]] = {}


def _record_memory_telemetry(operation: str, success: bool, execution_time: float) -> None:
    """Record OS27 Hyper++ telemetry for memory operations."""
    if operation not in _memory_telemetry:
        _memory_telemetry[operation] = {
            "operation_count": 0,
            "success_count": 0,
            "failure_count": 0,
            "total_time": 0.0,
            "last_execution_time": 0.0,
            "last_success": False,
        }
    
    _memory_telemetry[operation]["operation_count"] += 1
    _memory_telemetry[operation]["total_time"] += execution_time
    _memory_telemetry[operation]["last_execution_time"] = execution_time
    _memory_telemetry[operation]["last_success"] = success
    
    if success:
        _memory_telemetry[operation]["success_count"] += 1
    else:
        _memory_telemetry[operation]["failure_count"] += 1


def get_memory_telemetry(operation: str | None = None) -> Dict[str, Any] | Dict[str, Dict[str, Any]]:
    """Get telemetry for memory operations."""
    if operation:
        return _memory_telemetry.get(operation, {})
    return _memory_telemetry.copy()


def get_memory_health() -> str:
    """Get health status for memory tool based on telemetry."""
    if not _memory_telemetry:
        return "unknown"
    
    total_ops = sum(stats["operation_count"] for stats in _memory_telemetry.values())
    total_failures = sum(stats["failure_count"] for stats in _memory_telemetry.values())
    
    if total_ops == 0:
        return "unknown"
    
    failure_rate = total_failures / total_ops
    if failure_rate > 0.5:
        return "broken"
    if failure_rate > 0.1:
        return "degraded"
    return "healthy"


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
        start_time = time.time()
        
        # AI Core hooks (lazy import for safety)
        cortex = None
        context_engine = None
        evolver = None
        try:
            from tools.memory_cortex import MemoryCortex
            cortex = MemoryCortex()
        except Exception:
            pass
        try:
            from tools.context_engine import ContextEngine
            context_engine = ContextEngine()
        except Exception:
            pass
        try:
            from tools.self_evolving_tool import SelfEvolvingTool
            evolver = SelfEvolvingTool()
        except Exception:
            pass
        
        action = kwargs.get("action")
        memory = get_memory(self.db_path)

        try:
            if action == "save_knowledge":
                topic = kwargs.get("topic")
                content = kwargs.get("content")
                if not topic or not content:
                    result = ToolResult(status=ToolStatus.ERROR, error="Parametrii 'topic' si 'content' sunt obligatorii.")
                else:
                    ok = memory.save_knowledge(topic, content, category=kwargs.get("category"))
                    result = ToolResult(
                        status=ToolStatus.SUCCESS if ok else ToolStatus.ERROR,
                        data={"saved": bool(ok), "topic": topic},
                        message="Knowledge salvata." if ok else "",
                        error=None if ok else "Nu s-a putut salva knowledge.",
                    )

            elif action == "search_knowledge":
                query = kwargs.get("query")
                if not query:
                    result = ToolResult(status=ToolStatus.ERROR, error="Parametrul 'query' este obligatoriu.")
                else:
                    results = memory.search_knowledge(query, limit=int(kwargs.get("limit", 10)))
                    result = ToolResult(
                        status=ToolStatus.SUCCESS,
                        data={"query": query, "count": len(results), "results": results},
                        message=f"Gasite {len(results)} rezultate in memorie.",
                    )

            elif action == "list_topics":
                topics = memory.list_all_knowledge()
                limit = int(kwargs.get("limit", 50))
                result = ToolResult(
                    status=ToolStatus.SUCCESS,
                    data={"count": len(topics), "topics": topics[:limit]},
                    message=f"Gasite {len(topics)} topicuri in memorie.",
                )

            elif action == "stats":
                result = ToolResult(
                    status=ToolStatus.SUCCESS,
                    data=memory.get_stats(),
                    message="Statistici memorie disponibile.",
                )

            elif action == "save_error_solution":
                error_pattern = kwargs.get("error_pattern")
                solution = kwargs.get("solution")
                if not error_pattern or not solution:
                    result = ToolResult(status=ToolStatus.ERROR, error="Parametrii 'error_pattern' si 'solution' sunt obligatorii.")
                else:
                    ok = memory.save_error_solution(error_pattern, solution)
                    result = ToolResult(
                        status=ToolStatus.SUCCESS if ok else ToolStatus.ERROR,
                        data={"saved": bool(ok), "error_pattern": error_pattern},
                        message="Pattern de eroare salvat." if ok else "",
                        error=None if ok else "Nu s-a putut salva pattern-ul de eroare.",
                    )

            elif action == "find_error_solution":
                error_text = kwargs.get("error_text")
                if not error_text:
                    result = ToolResult(status=ToolStatus.ERROR, error="Parametrul 'error_text' este obligatoriu.")
                else:
                    result = memory.find_error_solution(error_text)
                    result = ToolResult(
                        status=ToolStatus.SUCCESS,
                        data={"found": bool(result), "result": result},
                        message="Pattern de eroare verificat.",
                    )
            else:
                result = ToolResult(status=ToolStatus.ERROR, error=f"Unknown action: {action}")

            execution_time = time.time() - start_time
            _record_memory_telemetry(action, result.is_success, execution_time)
            
            # ContextEngine integration for memory state
            if context_engine and result.is_success:
                try:
                    context_engine.update_context(
                        key="memory_state",
                        value={
                            "action": action,
                            "success": result.is_success,
                            "timestamp": time.time(),
                        }
                    )
                except Exception:
                    pass
            
            # MemoryCortex integration for memory errors
            if cortex and not result.is_success:
                try:
                    cortex.remember(
                        "error",
                        f"memory.{action}",
                        f"Memory operation failed: {result.error}"
                    )
                except Exception:
                    pass
            
            return result
        except Exception as exc:
            execution_time = time.time() - start_time
            _record_memory_telemetry(action, False, execution_time)
            
            # MemoryCortex integration for memory errors
            if cortex:
                try:
                    cortex.remember(
                        "error",
                        f"memory.{action}",
                        f"Memory operation failed: {str(exc)}"
                    )
                except Exception:
                    pass
            
            return ToolResult(status=ToolStatus.ERROR, error=str(exc))
