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
    # --- MIRROR BRAIN HOOK ---
    # When this function is called without explicit tool specs,
    # we dynamically fetch the full mirror brain context.
    try:
        from ANA_MAX.tools.agent_context_injector import collect_full_context
        ctx = collect_full_context(fast=True)
        mirror_prompt = ctx.get("system_prompt", "")
    except Exception:
        mirror_prompt = ""

    base_prompt = _ascii_text(profile_text).strip()
    spec_block = _ascii_text(tool_specs).strip() if tool_specs is not None else (
        mirror_prompt if mirror_prompt else load_tool_specs().strip()
    )
    context_block = _ascii_text(rag_context).strip()

    sections: list[str] = []
    
    if mirror_prompt and tool_specs is None:
        # If we successfully loaded Mirror Brain, it acts as the primary system prompt.
        sections.append(mirror_prompt)
        if base_prompt:
            # We still append the profile behavior (e.g. language/persona restrictions)
            sections.append("## PROFILE BEHAVIOR\n" + base_prompt)
    else:
        # Legacy fallback
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
