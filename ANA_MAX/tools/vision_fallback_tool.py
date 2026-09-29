"""ANA MAX vision fallback stub."""

from __future__ import annotations
from typing import Any
from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus

class VisionFallbackTool(Tool):
    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="vision_fallback",
            description="Stub for vision_fallback operations. Currently a no-op.",
            parameters=[
                ToolParameter(name="action", description="Action to perform", type="string", required=False, default="status"),
            ],
            category="system",
        )

    def execute(self, **kwargs: Any) -> ToolResult:
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={"status": "stub_ready"},
            message="vision_fallback module is currently a stub.",
        )
