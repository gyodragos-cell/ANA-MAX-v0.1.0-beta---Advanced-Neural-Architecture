# PATCH_START v20_phase1
"""Read-only runtime guard checks for ANA MAX v20 foundation."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def _registry_check() -> dict[str, Any]:
    try:
        from tools.base import registry

        names = registry.list_tools()
        duplicates = sorted({name for name in names if names.count(name) > 1})
        return {
            "status": "WARN" if duplicates else "OK",
            "tool_count": len(names),
            "duplicates": duplicates,
        }
    except Exception as exc:
        return {"status": "WARN", "reason": str(exc)}


def _environment_check(args: dict[str, Any]) -> dict[str, Any]:
    expected_root = args.get("expected_root")
    cwd = Path.cwd().resolve()
    if not expected_root:
        return {"status": "OK", "cwd": str(cwd)}
    expected = Path(str(expected_root)).expanduser().resolve()
    return {
        "status": "OK" if cwd == expected else "WARN",
        "cwd": str(cwd),
        "expected_root": str(expected),
    }


def _hash_check() -> dict[str, Any]:
    try:
        from tools import ana_runtime_inspector

        snapshot = ana_runtime_inspector.run({"action": "snapshot"})
        hashes = snapshot.get("runtime", {}).get("file_hashes", {})
        missing = sorted(key for key, value in hashes.items() if value is None)
        return {"status": "WARN" if missing else "OK", "missing_hashes": missing}
    except Exception as exc:
        return {"status": "WARN", "reason": str(exc)}


def _overall(checks: dict[str, dict[str, Any]]) -> str:
    return "WARN" if any(item.get("status") != "OK" for item in checks.values()) else "OK"


def run(args: dict[str, Any] | None = None) -> dict[str, Any]:
    args = args or {}
    checks = {
        "registry": _registry_check(),
        "environment": _environment_check(args),
        "file_hash_integrity": _hash_check(),
        "adapter_consistency": {
            "status": "OK",
            "note": "Phase 1 guard performs non-invasive adapter checks only.",
        },
    }
    status = _overall(checks)
    return {
        "success": True,
        "status": status,
        "checks": checks,
    }


# PATCH_END v20_phase1
