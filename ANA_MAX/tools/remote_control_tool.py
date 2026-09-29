"""ANA MAX remote control stub."""

from __future__ import annotations
from typing import Any
from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus

class RemoteControlTool(Tool):
    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="remote_control",
            description="Stub for remote_control operations. Currently a no-op.",
            parameters=[
                ToolParameter(name="action", description="Action to perform", type="string", required=False, default="status"),
            ],
            category="system",
        )

    def execute(self, **kwargs: Any) -> ToolResult:
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={"status": "stub_ready"},
            message="remote_control module is currently a stub.",
        )
