# PATCH_START v20_phase1
"""Read-only documentation text generator for ANA MAX v20 foundation."""

from __future__ import annotations

from typing import Any


def _registry_tools() -> list[dict[str, Any]]:
    try:
        from tools.base import registry

        items = []
        for name in sorted(registry.list_tools()):
            tool = registry.get(name)
            if tool is None:
                continue
            definition = tool.get_definition()
            items.append(
                {
                    "name": definition.name,
                    "description": definition.description,
                    "category": definition.category,
                }
            )
        return items
    except Exception:
        return []


def _tools_md(tools: list[dict[str, Any]]) -> str:
    lines = ["# ANA MAX Tools", "", "Generated documentation preview.", ""]
    if not tools:
        lines.append("No tools are currently registered in the in-process registry.")
        return "\n".join(lines) + "\n"
    for item in tools:
        lines.append(f"- `{item['name']}` ({item['category']}) - {item['description']}")
    return "\n".join(lines) + "\n"


def _diagnostics_layer_md() -> str:
    return """# ANA MAX Diagnostics Layer

The diagnostics layer is read-only and manual-call only.

- `ana_runtime_inspector`
- `tool_contract_validator`
- `schema_diff`
- `ana_health_check`
- `baseline_update_suggester`
- `docs_generator`
- `ana_patch_suggester`
- `runtime_guard`

No diagnostics component applies patches or writes files.
"""


def _summary_md(tool_count: int, generated_at: str) -> str:
    return f"""# ANA MAX Runtime Summary

Generated: {generated_at}

Tools visible in current in-process registry: {tool_count}

This is generated text only. It has not been written to disk.
"""


def _release_notes_template() -> str:
    return """# ANA MAX Release Notes Template

## Highlights

- Runtime diagnostics
- Contract validation
- Schema comparison
- Patch suggestions without patch application

## Verification

- Run compile checks
- Run unit tests
- Run tool listing
"""


def run(args: dict[str, Any] | None = None) -> dict[str, Any]:
    args = args or {}
    tools = _registry_tools()
    generated_at = str(args.get("generated_at", "static-preview"))
    generated = {
        "docs/tools.md": _tools_md(tools),
        "docs/DIAGNOSTICS_LAYER.md": _diagnostics_layer_md(),
        "SUMMARY.md": _summary_md(len(tools), generated_at),
        "RELEASE_NOTES_template.md": _release_notes_template(),
    }
    selected = args.get("document")
    if selected:
        text = generated.get(str(selected))
        if text is None:
            return {"success": False, "error": f"unknown document: {selected}"}
        return {"success": True, "document": selected, "text": text}
    return {"success": True, "generated": generated}


# PATCH_END v20_phase1
