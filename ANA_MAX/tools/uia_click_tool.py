"""UI Automation click tool."""

from __future__ import annotations

from typing import Any

from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus


class UiaClickTool(Tool):
    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="uia_click",
            description="Click a visible UI element using Microsoft UI Automation selectors.",
            parameters=[
                ToolParameter("window_title", "Partial window title", "string", True),
                ToolParameter("element_title", "Element title/name", "string", False),
                ToolParameter("auto_id", "AutomationId", "string", False),
                ToolParameter("control_type", "Control type such as Button or Edit", "string", False),
                ToolParameter("confirm", "Required confirmation for UI mutation", "boolean", False, False),
            ],
            category="desktop",
            requires_confirmation=True,
        )

    def execute(self, **kwargs: Any) -> ToolResult:
        from tools.windows_uia_bridge import WindowsUiaBridgeTool

        if not kwargs.get("element_title") and not kwargs.get("auto_id"):
            return ToolResult(status=ToolStatus.ERROR, error="element_title or auto_id is required")

        bridge = WindowsUiaBridgeTool()
        return bridge.execute(
            action="click_element",
            window_title=kwargs.get("window_title"),
            element_title=kwargs.get("element_title"),
            auto_id=kwargs.get("auto_id"),
            control_type=kwargs.get("control_type"),
        )
