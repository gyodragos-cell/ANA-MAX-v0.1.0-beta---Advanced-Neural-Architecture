# PATCH_START v20_phase1
"""Read-only baseline update suggestions for ANA MAX v20 foundation."""

from __future__ import annotations

from typing import Any


DEFAULT_BASELINE = {
    "tool_count": 74,
    "ai_core_adapters": 7,
    "premium_gated_families": 4,
}


def _suggest_field(name: str, expected: Any, actual: Any) -> dict[str, Any] | None:
    if actual is None or expected == actual:
        return None
    return {
        "field": name,
        "expected": expected,
        "actual": actual,
        "suggestion": f"Update documented {name} from {expected!r} to {actual!r}.",
        "risk": "low",
    }


def _suggest_text_patch(file_path: str, old: str, new: str) -> dict[str, str]:
    return {
        "file": file_path,
        "patch": (
            f"--- a/{file_path}\n"
            f"+++ b/{file_path}\n"
            "@@\n"
            f"-{old}\n"
            f"+{new}\n"
        ),
    }


def run(args: dict[str, Any] | None = None) -> dict[str, Any]:
    args = args or {}
    baseline = dict(DEFAULT_BASELINE)
    if isinstance(args.get("baseline"), dict):
        baseline.update(args["baseline"])
    current = args.get("current", {})
    if not isinstance(current, dict):
        return {"success": False, "error": "current must be a dict when provided"}

    suggestions = []
    for key, expected in baseline.items():
        item = _suggest_field(key, expected, current.get(key))
        if item:
            suggestions.append(item)

    patch_suggestions = []
    current_tool_count = current.get("tool_count")
    if current_tool_count and current_tool_count != baseline.get("tool_count"):
        patch_suggestions.append(
            _suggest_text_patch(
                "README.md",
                f"Tools: {baseline['tool_count']} loaded tools",
                f"Tools: {current_tool_count} loaded tools",
            )
        )

    return {
        "success": True,
        "status": "WARN" if suggestions else "OK",
        "suggestions": suggestions,
        "patch_suggestions": patch_suggestions,
    }


# PATCH_END v20_phase1
