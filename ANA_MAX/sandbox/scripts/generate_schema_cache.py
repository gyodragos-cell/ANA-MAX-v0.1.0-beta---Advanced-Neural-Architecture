import sys
import json
import os

ana_manus_root = os.path.dirname(os.path.abspath(__file__))
ANA_MAX_ROOT = os.path.join(ana_manus_root, "ANA_MAX")
for _p in (ANA_MAX_ROOT, ana_manus_root):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from bridge.direct_bridge import DirectBridge
from tools.base import registry

print("Initializing bridge for schema generation...")
bridge = DirectBridge(include_hybrid_tools=True)

def _tool_to_mcp(definition) -> dict:
    properties = {}
    required = []
    for p in getattr(definition, "parameters", []) or []:
        ptype = (getattr(p, "type", "string") or "string").lower()
        if ptype == "any":
            ptype = "string"
        schema = {"type": ptype, "description": p.description or ""}
        if getattr(p, "choices", None):
            schema["enum"] = list(p.choices)
        if getattr(p, "default", None) is not None:
            schema["default"] = p.default
        properties[p.name] = schema
        if getattr(p, "required", False):
            required.append(p.name)

    desc = (definition.description or "ANA MAX tool").strip()
    if getattr(definition, "dangerous", False) or getattr(definition, "requires_confirmation", False):
        desc += " (god-mode: ruleaza fara confirmare)"

    return {
        "name": definition.name,
        "description": desc,
        "inputSchema": {
            "type": "object",
            "properties": properties,
            "required": required,
        }
    }

mcp_tools = []
for name in sorted(registry.list_tools()):
    tool = registry.get(name)
    if tool:
        try:
            mcp_tools.append(_tool_to_mcp(tool.get_definition()))
        except Exception as e:
            print(f"Error on {name}: {e}")

def _fallback_terminal_tool():
    return {
        "name": "ana_terminal",
        "description": "Executa comenzi shell prin ANA Bridge (fallback permanent, god-mode).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Comanda de executat"},
                "timeout": {"type": "integer", "description": "Timeout in secunde", "default": 30},
            },
            "required": ["command"],
        }
    }

mcp_tools.append(_fallback_terminal_tool())

with open("mcp_tools_cache.json", "w") as f:
    json.dump(mcp_tools, f, indent=2)

print(f"Successfully generated mcp_tools_cache.json with {len(mcp_tools)} tools.")

