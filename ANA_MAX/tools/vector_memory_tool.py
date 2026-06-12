#!/usr/bin/env python3
"""
ANA MAX - Vector Memory Tool
==============================
Tool pentru acces la Vector Memory Cortex cu search semantic.

Features:
- Store memories with embeddings
- Semantic search (150x+ faster)
- Memory consolidation
- Statistics and analytics

Author: ANA MAX Team (2026-05-19)
"""

import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus
from core.vector_memory import get_vector_memory


class VectorMemoryTool(Tool):
    """Vector Memory Tool pentru ANA MAX."""
    
    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="vector_memory",
            description=(
                "Vector Memory System cu search semantic ultra-rapid (150x+). "
                " stocheaza si cauta memorii cu AI embeddings. "
                "Actions: store, search, stats, consolidate"
            ),
            parameters=[
                ToolParameter(
                    name="action",
                    description="Actiunea: store, search, stats, consolidate",
                    type="string",
                    required=True,
                    choices=["store", "search", "stats", "consolidate"]
                ),
                ToolParameter(
                    name="content",
                    description="Continutul memoriei (pentru store)",
                    type="string",
                    required=False
                ),
                ToolParameter(
                    name="query",
                    description="Query de cautare (pentru search)",
                    type="string",
                    required=False
                ),
                ToolParameter(
                    name="memory_type",
                    description="Tipul memoriei: episodic, semantic, procedural, error_log",
                    type="string",
                    required=False,
                    choices=["episodic", "semantic", "procedural", "error_log"]
                ),
                ToolParameter(
                    name="top_k",
                    description="Numar de rezultate (pentru search)",
                    type="integer",
                    required=False,
                    default=10
                ),
                ToolParameter(
                    name="tags",
                    description="Tag-uri pentru filtrare (JSON array)",
                    type="string",
                    required=False
                ),
                ToolParameter(
                    name="min_importance",
                    description="Importanta minima (0.0-1.0)",
                    type="number",
                    required=False,
                    default=0.0
                )
            ],
            category="memory"
        )
    
    def execute(self, action: str, **kwargs) -> ToolResult:
        try:
            vm = get_vector_memory()
            
            if action == "store":
                return self._store(vm, **kwargs)
            elif action == "search":
                return self._search(vm, **kwargs)
            elif action == "stats":
                return self._stats(vm)
            elif action == "consolidate":
                return self._consolidate(vm, **kwargs)
            else:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error=f"Unknown action: {action}"
                )
        
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Vector memory error: {e}"
            )
    
    def _store(self, vm, content: str = None, memory_type: str = "episodic",
               tags: str = None, **kwargs) -> ToolResult:
        """Store memory."""
        if not content:
            return ToolResult(
                status=ToolStatus.ERROR,
                error="Content is required for store action"
            )
        
        import json
        tags_list = json.loads(tags) if tags else []
        
        memory_id = vm.store(
            content=content,
            memory_type=memory_type,
            tags=tags_list
        )
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={
                "memory_id": memory_id,
                "content_preview": content[:100],
                "memory_type": memory_type,
                "tags": tags_list
            },
            message=f"Memory stored: {memory_id}"
        )
    
    def _search(self, vm, query: str = None, top_k: int = 10,
                memory_type: str = None, tags: str = None,
                min_importance: float = 0.0, **kwargs) -> ToolResult:
        """Search memories."""
        if not query:
            return ToolResult(
                status=ToolStatus.ERROR,
                error="Query is required for search action"
            )
        
        import json
        tags_list = json.loads(tags) if tags else None
        
        results = vm.search(
            query=query,
            top_k=top_k,
            memory_type=memory_type,
            tags=tags_list,
            min_importance=min_importance
        )
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={
                "query": query,
                "results_count": len(results),
                "memories": results
            },
            message=f"Found {len(results)} memories"
        )
    
    def _stats(self, vm) -> ToolResult:
        """Get memory statistics."""
        stats = vm.get_stats()
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data=stats,
            message=f"Total memories: {stats['total']}"
        )
    
    def _consolidate(self, vm, min_importance: float = 0.1, **kwargs) -> ToolResult:
        """Consolidate memories."""
        deleted = vm.consolidate(min_importance=min_importance)
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={
                "deleted_count": deleted,
                "min_importance": min_importance
            },
            message=f"Removed {deleted} low-importance memories"
        )


if __name__ == "__main__":
    # Test tool
    tool = VectorMemoryTool()
    
    # Store
    result = tool.execute("store", content="Test memory for vector search")
    print(f"Store: {result.message}")
    
    # Search
    result = tool.execute("search", query="vector search test")
    print(f"Search: {result.message} ({len(result.data['memories'])} results)")
    
    # Stats
    result = tool.execute("stats")
    print(f"Stats: {result.message}")
    print(result.data)
