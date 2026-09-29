import os
import json
import logging
from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus
from core.rag_cpu_engine import get_rag_engine

logger = logging.getLogger(__name__)

class RagSearchFile(Tool):
    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="rag_search_file",
            description="Semantic search (Zero-VRAM RAG) over a massive file. Use this when the file is too large to read entirely and you need to find specific paragraphs, code references, or log lines.",
            parameters=[
                ToolParameter(
                    name="filepath",
                    description="The absolute path to the file you want to search.",
                    type="string",
                    required=True
                ),
                ToolParameter(
                    name="query",
                    description="The search query (keywords, variable names, error messages).",
                    type="string",
                    required=True
                )
            ],
            category="Analysis"
        )

    def execute(self, params: dict, context=None) -> ToolResult:
        filepath = params.get("filepath")
        query = params.get("query")

        if not filepath or not query:
            return ToolResult(
                status=ToolStatus.ERROR,
                message="Missing 'filepath' or 'query' parameters.",
                error="Invalid arguments"
            )

        if not os.path.exists(filepath):
            return ToolResult(
                status=ToolStatus.ERROR,
                message=f"File not found: {filepath}",
                error="FileNotFound"
            )

        logger.info(f"RAG searching '{query}' in {filepath}")
        engine = get_rag_engine()
        
        try:
            results = engine.search_file(filepath, query)
            
            output_msg = f"RAG Search Results for '{query}' in {os.path.basename(filepath)}:\n\n{results}"
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data=output_msg,
                message="RAG Search Completed"
            )
        except Exception as e:
            logger.error(f"RAG Search failed: {e}")
            return ToolResult(
                status=ToolStatus.ERROR,
                message=f"RAG Engine crashed: {str(e)}",
                error=str(e)
            )
