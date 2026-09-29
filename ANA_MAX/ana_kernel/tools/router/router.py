from __future__ import annotations

from ana.core.error_model.errors import RoutingFailure, ValidationError
from ana.tools.registry.registry import ToolRegistry, ToolSpec


class ToolRouter:
    def route(self, capability: str, registry: ToolRegistry) -> ToolSpec:
        if not capability:
            raise ValidationError("capability is required", source="router")
        tools = registry.tools_for(capability)
        if not tools:
            raise RoutingFailure(
                "no tool registered for capability",
                source="router",
                details={"capability": capability},
            )
        return tools[0] if tools else registry.default_tool()
