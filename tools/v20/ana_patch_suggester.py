# PATCH_START v20_phase1
"""Read-only patch suggestion helper for ANA MAX v20 foundation."""

from __future__ import annotations

from typing import Any


def _risk_for(issue: dict[str, Any]) -> str:
    severity = str(issue.get("severity", "low")).lower()
    file_path = str(issue.get("file", ""))
    if severity in {"high", "critical"}:
        return "high"
    if any(part in file_path for part in ("core/", "main.py", "bridge", "registry")):
        return "medium"
    return "low"


def _diff_for_issue(issue: dict[str, Any]) -> str:
    file_path = str(issue.get("file", "UNKNOWN"))
    old = str(issue.get("old", ""))
    new = str(issue.get("new", ""))
    if not old and not new:
        return ""
    return f"--- a/{file_path}\n+++ b/{file_path}\n@@\n-{old}\n+{new}\n"


def run(args: dict[str, Any] | None = None) -> dict[str, Any]:
    args = args or {}
    issues = args.get("issues", [])
    if isinstance(args.get("issue"), dict):
        issues = [args["issue"]]
    if not isinstance(issues, list):
        return {"success": False, "error": "issues must be a list"}

    suggestions = []
    for issue in issues:
        if not isinstance(issue, dict):
            continue
        suggestion = {
            "title": str(issue.get("title", "runtime consistency issue")),
            "risk": _risk_for(issue),
            "explanation": str(issue.get("explanation", "Review before applying any patch.")),
            "patch_suggestion": _diff_for_issue(issue),
        }
        suggestions.append(suggestion)

    return {
        "success": True,
        "suggestions": suggestions,
        "applied": False,
    }


# PATCH_END v20_phase1
