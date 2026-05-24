# PATCH_START v20_phase1
"""Read-only aggregate health report for ANA MAX v20 foundation."""

from __future__ import annotations

from typing import Any


CRITICAL_RESPONSE_SCHEMA = {
    "properties": {
        "success": {"type": "boolean", "required": True},
    }
}


def _safe_call(label: str, func, args: dict[str, Any]) -> dict[str, Any]:
    try:
        result = func(args)
        if not isinstance(result, dict):
            return {"success": False, "component": label, "error": "non-dict response"}
        return result
    except Exception as exc:
        return {"success": False, "component": label, "error": str(exc)}


def _status_from_sections(sections: dict[str, Any]) -> str:
    failures = []
    warnings = []
    for name, payload in sections.items():
        if not isinstance(payload, dict):
            failures.append(name)
        elif payload.get("success") is False:
            failures.append(name)
        elif payload.get("counts", {}).get("FAIL", 0):
            failures.append(name)
        elif payload.get("counts", {}).get("WARN", 0):
            warnings.append(name)
    if failures:
        return "FAIL"
    if warnings:
        return "WARN"
    return "OK"


def run(args: dict[str, Any] | None = None) -> dict[str, Any]:
    args = args or {}
    include_contracts = bool(args.get("include_contracts", True))

    from tools import ana_runtime_inspector
    from tools import schema_diff
    from tools import tool_contract_validator

    runtime_snapshot = _safe_call(
        "ana_runtime_inspector",
        ana_runtime_inspector.run,
        {"action": "snapshot"},
    )
    schema_check = _safe_call(
        "schema_diff",
        schema_diff.run,
        {
            "expected_schema": CRITICAL_RESPONSE_SCHEMA,
            "actual_response": runtime_snapshot,
        },
    )

    sections: dict[str, Any] = {
        "runtime_snapshot": runtime_snapshot,
        "critical_schema": schema_check,
    }
    if include_contracts:
        sections["tool_contracts"] = _safe_call(
            "tool_contract_validator",
            tool_contract_validator.run,
            {"action": "validate_all"},
        )

    status = _status_from_sections(sections)
    return {
        "success": status != "FAIL",
        "status": status,
        "report": sections,
    }


# PATCH_END v20_phase1
