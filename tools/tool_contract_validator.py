# PATCH_START v19_phase1
"""Read-only ANA MAX tool contract validator.

Phase 1 keeps this diagnostic intentionally conservative. It imports modules and
only runs probes from a small allowlist known to be read-only.
"""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any


SAFE_PROBES: dict[str, dict[str, Any]] = {
    "context_engine": {"action": "get_context"},
    "ana_runtime_inspector": {"action": "snapshot"},
    "schema_diff": {
        "expected_schema": {"properties": {"success": {"type": "boolean", "required": True}}},
        "actual_response": {"success": True},
    },
}


def _status_from_response(response: Any) -> tuple[str, str]:
    if not isinstance(response, dict):
        return "FAIL", "response is not a dict"
    if response.get("success") is False:
        return "FAIL", str(response.get("error") or "success=false")
    if response.get("success") is True:
        return "PASS", str(response.get("message") or "ok")
    return "WARN", "response has no success field"


def _tool_module_name(tool_name: str) -> str:
    safe_name = tool_name.replace("-", "_").strip()
    if not safe_name or any(ch in safe_name for ch in "\\/.:"):
        raise ValueError("invalid tool_name")
    return f"tools.{safe_name}"


def validate_tool(tool_name: str) -> dict[str, Any]:
    try:
        module = importlib.import_module(_tool_module_name(tool_name))
    except Exception as exc:
        return {"tool": tool_name, "status": "FAIL", "reason": f"import failed: {exc}"}

    run_func = getattr(module, "run", None)
    if not callable(run_func):
        return {"tool": tool_name, "status": "WARN", "reason": "module has no callable run(args)"}

    if tool_name not in SAFE_PROBES:
        return {"tool": tool_name, "status": "WARN", "reason": "no read-only safe probe registered"}

    try:
        response = run_func(dict(SAFE_PROBES[tool_name]))
    except Exception as exc:
        return {"tool": tool_name, "status": "FAIL", "reason": f"probe raised: {exc}"}

    status, reason = _status_from_response(response)
    return {"tool": tool_name, "status": status, "reason": reason, "response": response}


def _candidate_tools() -> list[str]:
    tools_dir = Path(__file__).resolve().parent
    names = []
    for path in tools_dir.glob("*.py"):
        if path.name.startswith("_") or path.name == "__init__.py":
            continue
        names.append(path.stem)
    return sorted(names)


def validate_all() -> dict[str, Any]:
    results = [validate_tool(name) for name in _candidate_tools()]
    counts = {
        "PASS": sum(1 for item in results if item["status"] == "PASS"),
        "WARN": sum(1 for item in results if item["status"] == "WARN"),
        "FAIL": sum(1 for item in results if item["status"] == "FAIL"),
    }
    return {"success": True, "counts": counts, "results": results}


def run(args: dict[str, Any] | None = None) -> dict[str, Any]:
    args = args or {}
    action = str(args.get("action", "validate_all"))
    if action == "validate_tool":
        tool_name = str(args.get("tool_name", ""))
        if not tool_name:
            return {"success": False, "error": "tool_name is required"}
        result = validate_tool(tool_name)
        return {"success": result["status"] != "FAIL", "result": result}
    if action == "validate_all":
        return validate_all()
    return {"success": False, "error": f"unknown action: {action}"}


# PATCH_END v19_phase1
