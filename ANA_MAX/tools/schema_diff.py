# PATCH_START v19_phase1
"""Read-only schema/response comparison for ANA MAX diagnostics."""

from __future__ import annotations

from typing import Any


TYPE_MAP = {
    "string": str,
    "integer": int,
    "number": (int, float),
    "boolean": bool,
    "object": dict,
    "dict": dict,
    "array": list,
    "list": list,
}


def _schema_properties(schema: dict[str, Any]) -> dict[str, Any]:
    properties = schema.get("properties")
    if isinstance(properties, dict):
        return properties
    return {key: value for key, value in schema.items() if isinstance(value, dict)}


def _required_fields(schema: dict[str, Any], properties: dict[str, Any]) -> set[str]:
    required = schema.get("required", [])
    fields = set(required) if isinstance(required, list) else set()
    for key, spec in properties.items():
        if isinstance(spec, dict) and spec.get("required") is True:
            fields.add(key)
    return fields


def diff(expected_schema: dict[str, Any], actual_response: dict[str, Any]) -> dict[str, list[dict[str, Any]] | list[str]]:
    properties = _schema_properties(expected_schema)
    required = _required_fields(expected_schema, properties)
    actual_keys = set(actual_response)
    expected_keys = set(properties)

    missing = sorted(key for key in required if key not in actual_keys)
    extra = sorted(actual_keys - expected_keys) if expected_keys else []
    type_mismatch: list[dict[str, Any]] = []

    for key, spec in properties.items():
        if key not in actual_response or not isinstance(spec, dict):
            continue
        expected_type = spec.get("type")
        python_type = TYPE_MAP.get(str(expected_type))
        if python_type is None:
            continue
        value = actual_response[key]
        if expected_type == "integer" and isinstance(value, bool):
            ok = False
        elif expected_type == "number" and isinstance(value, bool):
            ok = False
        else:
            ok = isinstance(value, python_type)
        if not ok:
            type_mismatch.append(
                {
                    "field": key,
                    "expected": expected_type,
                    "actual": type(value).__name__,
                }
            )

    return {"missing": missing, "extra": extra, "type_mismatch": type_mismatch}


def run(args: dict[str, Any] | None = None) -> dict[str, Any]:
    args = args or {}
    expected_schema = args.get("expected_schema", {})
    actual_response = args.get("actual_response", {})
    if not isinstance(expected_schema, dict):
        return {"success": False, "error": "expected_schema must be a dict"}
    if not isinstance(actual_response, dict):
        return {"success": False, "error": "actual_response must be a dict"}
    return {"success": True, **diff(expected_schema, actual_response)}


# PATCH_END v19_phase1
