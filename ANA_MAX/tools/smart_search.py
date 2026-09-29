from typing import Any
from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult

class SmartSearchTool(Tool):
    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="ana_smart_search",
            description="Stub for smart search.",
            parameters=[
                ToolParameter(name="query", type="string", required=True),
                ToolParameter(name="project_path", type="string", required=True)
            ]
        )

    def _execute(self, query: str, project_path: str, **kwargs: Any) -> ToolResult:
        return ToolResult(is_success=True, data="Stub success")
