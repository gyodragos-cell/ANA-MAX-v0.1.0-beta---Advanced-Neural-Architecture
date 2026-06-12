from __future__ import annotations

from typing import Any

from ANA_MAX.tools.tool_manifest_loader import get_tool_specs as load_tool_specs


TOOL_CALL_INSTRUCTION = "TOOL_CALL: <tool_name> <json_arguments>"


def _ascii_text(value: Any) -> str:
    return str(value or "").encode("ascii", errors="replace").decode("ascii")


def compose_system_prompt(
    profile_text: str,
    *,
    tool_specs: str | None = None,
    rag_context: str = "",
) -> str:
    base_prompt = _ascii_text(profile_text).strip()
    spec_block = _ascii_text(tool_specs).strip() if tool_specs is not None else load_tool_specs().strip()
    context_block = _ascii_text(rag_context).strip()

    sections: list[str] = []
    if base_prompt:
        sections.append(base_prompt)
    if spec_block:
        sections.append(spec_block)
        sections.append(
            "To use a tool, emit exactly:\n"
            f"{TOOL_CALL_INSTRUCTION}"
        )
    if context_block:
        sections.append(f"Retrieved context:\n{context_block}")
    return "\n\n".join(sections).strip()


def get_tool_specs() -> str:
    return load_tool_specs()
