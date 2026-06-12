"""ANA MAX session lifecycle MCP tool."""

from __future__ import annotations

from typing import Any

from core.session_lifecycle import SessionLifecycle
from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus


class SessionLifecycleTool(Tool):
    """Expose start/wake/recommend/rest lifecycle actions through MCP."""

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="session_lifecycle",
            description=(
                "Coordinates ANA MAX session lifecycle: start, wake, recommend, "
                "and rest. Wake has first-run fallback; rest previews REM Sleep "
                "unless consolidate=true."
            ),
            parameters=[
                ToolParameter(
                    name="action",
                    description="Lifecycle action to run",
                    type="string",
                    required=False,
                    default="wake",
                    choices=["start", "wake", "recommend", "rest"],
                ),
                ToolParameter(
                    name="task",
                    description="Current task for action=recommend",
                    type="string",
                    required=False,
                    default="",
                ),
                ToolParameter(
                    name="error",
                    description="Optional current error for action=recommend",
                    type="string",
                    required=False,
                    default="",
                ),
                ToolParameter(
                    name="max_tools",
                    description="Maximum tools for action=recommend",
                    type="integer",
                    required=False,
                    default=5,
                ),
                ToolParameter(
                    name="consolidate",
                    description="For action=rest: write REM Sleep report and memory",
                    type="boolean",
                    required=False,
                    default=False,
                ),
                ToolParameter(
                    name="save_memory",
                    description="For action=rest with consolidate=true: save compact memory lessons",
                    type="boolean",
                    required=False,
                    default=True,
                ),
            ],
            category="memory",
        )

    def execute(self, **kwargs: Any) -> ToolResult:
        action = str(kwargs.get("action") or "wake").strip().lower()
        lifecycle = SessionLifecycle()

        try:
            if action == "start":
                payload = lifecycle.start()
            elif action == "wake":
                payload = lifecycle.wake()
            elif action == "recommend":
                payload = lifecycle.recommend(
                    task=str(kwargs.get("task") or ""),
                    error=str(kwargs.get("error") or ""),
                    max_tools=int(kwargs.get("max_tools", 5) or 5),
                )
            elif action == "rest":
                payload = lifecycle.rest(
                    consolidate=self._to_bool(kwargs.get("consolidate"), False),
                    save_memory=self._to_bool(kwargs.get("save_memory"), True),
                )
            else:
                return ToolResult(status=ToolStatus.ERROR, error=f"Unknown lifecycle action: {action}")
        except Exception as exc:
            return ToolResult(status=ToolStatus.ERROR, error=str(exc))

        status = ToolStatus.SUCCESS if payload.get("success", False) else ToolStatus.ERROR
        return ToolResult(
            status=status,
            data=payload,
            message=f"session_lifecycle {action}: {payload.get('phase', action)}",
            error="" if status == ToolStatus.SUCCESS else payload.get("error", "Lifecycle action failed."),
        )

    def _to_bool(self, value: Any, default: bool) -> bool:
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return value != 0
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"1", "true", "yes", "y", "on"}:
                return True
            if normalized in {"0", "false", "no", "n", "off"}:
                return False
        return default
