"""Map ANA MAX tool metadata into Copilot-style HTTP tool definitions."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List


class ToolMapper:
    def __init__(self, config: Dict[str, Any] | None = None):
        self.config = config or {}

    def map_tools(self, tools: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
        mapped = [self.map_tool(tool) for tool in tools]
        return sorted(mapped, key=lambda item: item["name"])

    def map_tool(self, tool: Dict[str, Any]) -> Dict[str, Any]:
        name = str(tool.get("name", "")).strip()
        parameters = tool.get("parameters") or tool.get("inputSchema") or {}
        if "type" not in parameters:
            parameters = {"type": "object", "properties": parameters, "required": []}

        return {
            "name": name,
            "description": str(tool.get("description", "")),
            "category": str(tool.get("category", "ana-max")),
            "method": "POST",
            "endpoint": "/tools/call",
            "request_template": {"tool": name, "params": {}},
            "input_schema": parameters,
        }

    @staticmethod
    def compact_names(tools: Iterable[Dict[str, Any]]) -> List[str]:
        return [str(tool.get("name", "")) for tool in tools if tool.get("name")]
