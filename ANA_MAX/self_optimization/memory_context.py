#!/usr/bin/env python3
"""Shared local-only helpers for ANA memory layers."""

from __future__ import annotations

import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ANA_MAX.self_optimization.osx_common import MEMORY_DIR, read_json, utc_now, write_json

CORE_MEMORY_SCHEMA = "ana.memory.core.v1"
CONTEXT_SCHEMA = "ana.memory.context.v1"
SYSTEM_REPORT_SCHEMA = "ana.memory.system_report.v1"

CORE_MEMORY_PATH = MEMORY_DIR / "core_memory.json"
SYSTEM_REPORT_PATH = MEMORY_DIR / "memory_system_report.json"

DEFAULT_CORE_MEMORY: dict[str, Any] = {
    "schema": CORE_MEMORY_SCHEMA,
    "long_term": {},
    "short_term": {},
    "preferences": {},
    "patterns": {},
    "history": [],
}

DEFAULT_SYSTEM_REPORT: dict[str, Any] = {
    "schema": SYSTEM_REPORT_SCHEMA,
    "status": "DEGRADED",
    "core_memory_present": False,
    "last_consolidation": None,
    "last_consistency_check": None,
    "notes": [],
}


def _normalize_core_memory(value: Any) -> dict[str, Any]:
    core = deepcopy(DEFAULT_CORE_MEMORY)
    if not isinstance(value, dict):
        return core

    core["schema"] = value.get("schema", CORE_MEMORY_SCHEMA)
    core["long_term"] = deepcopy(value.get("long_term", {})) if isinstance(value.get("long_term", {}), dict) else {}
    core["short_term"] = deepcopy(value.get("short_term", {})) if isinstance(value.get("short_term", {}), dict) else {}
    core["preferences"] = deepcopy(value.get("preferences", {})) if isinstance(value.get("preferences", {}), dict) else {}
    core["patterns"] = deepcopy(value.get("patterns", {})) if isinstance(value.get("patterns", {}), dict) else {}
    core["history"] = deepcopy(value.get("history", [])) if isinstance(value.get("history", []), list) else []

    for key, item in value.items():
        if key not in core:
            core[key] = deepcopy(item)
    return core


def _normalize_system_report(value: Any) -> dict[str, Any]:
    report = deepcopy(DEFAULT_SYSTEM_REPORT)
    if not isinstance(value, dict):
        return report

    report["schema"] = value.get("schema", SYSTEM_REPORT_SCHEMA)
    report["status"] = value.get("status", report["status"])
    report["core_memory_present"] = bool(value.get("core_memory_present", report["core_memory_present"]))
    report["last_consolidation"] = value.get("last_consolidation", report["last_consolidation"])
    report["last_consistency_check"] = value.get("last_consistency_check", report["last_consistency_check"])
    report["notes"] = deepcopy(value.get("notes", [])) if isinstance(value.get("notes", []), list) else []

    for key, item in value.items():
        if key not in report:
            report[key] = deepcopy(item)
    return report


def load_core_memory() -> dict[str, Any]:
    if not CORE_MEMORY_PATH.exists():
        return deepcopy(DEFAULT_CORE_MEMORY)
    loaded = read_json(CORE_MEMORY_PATH, deepcopy(DEFAULT_CORE_MEMORY))
    if not isinstance(loaded, dict) or loaded.get("error"):
        return deepcopy(DEFAULT_CORE_MEMORY)
    return _normalize_core_memory(loaded)


def save_core_memory(core_memory: dict[str, Any], *, dry_run: bool = False) -> Path:
    if dry_run:
        return CORE_MEMORY_PATH
    payload = _normalize_core_memory(core_memory)
    write_json(CORE_MEMORY_PATH, payload)
    return CORE_MEMORY_PATH


def build_memory_context(core_memory: dict[str, Any] | None = None) -> dict[str, Any]:
    core = _normalize_core_memory(core_memory) if core_memory is not None else load_core_memory()
    return {
        "schema": CONTEXT_SCHEMA,
        "generated_at": utc_now(),
        "core_memory_present": CORE_MEMORY_PATH.exists(),
        "core_memory_schema_ok": core.get("schema") == CORE_MEMORY_SCHEMA,
        "core_memory_path": str(CORE_MEMORY_PATH),
        "history_length": len(core.get("history", [])) if isinstance(core.get("history", []), list) else 0,
        "long_term": deepcopy(core.get("long_term", {})),
        "short_term": deepcopy(core.get("short_term", {})),
        "preferences": deepcopy(core.get("preferences", {})),
        "patterns": deepcopy(core.get("patterns", {})),
    }


def memory_context_summary(context: dict[str, Any]) -> dict[str, Any]:
    preferences = context.get("preferences", {}) if isinstance(context.get("preferences", {}), dict) else {}
    patterns = context.get("patterns", {}) if isinstance(context.get("patterns", {}), dict) else {}
    long_term = context.get("long_term", {}) if isinstance(context.get("long_term", {}), dict) else {}
    important_preference_keys = [
        "stability_priority",
        "warnings_tolerance",
        "evolution_aggressiveness",
        "goal_persistence",
        "memory_consolidation",
    ]
    important_pattern_keys = [
        "stable_cycles",
        "warning_cycles",
        "parse_error_cycles",
        "evolution_failure_cycles",
        "daemon_failure_cycles",
    ]
    return {
        "schema": CONTEXT_SCHEMA,
        "core_memory_present": bool(context.get("core_memory_present", False)),
        "core_memory_schema_ok": bool(context.get("core_memory_schema_ok", False)),
        "history_length": int(context.get("history_length", 0) or 0),
        "preferences": {key: preferences.get(key) for key in important_preference_keys if key in preferences},
        "patterns": {key: patterns.get(key) for key in important_pattern_keys if key in patterns},
        "long_term_keys": sorted(list(long_term.keys()))[:12],
    }


def get_preference(context: dict[str, Any], key: str, default: Any = None) -> Any:
    preferences = context.get("preferences", {}) if isinstance(context.get("preferences", {}), dict) else {}
    return preferences.get(key, default)


def get_pattern(context: dict[str, Any], key: str, default: Any = None) -> Any:
    patterns = context.get("patterns", {}) if isinstance(context.get("patterns", {}), dict) else {}
    return patterns.get(key, default)


def get_long_term(context: dict[str, Any], key: str, default: Any = None) -> Any:
    long_term = context.get("long_term", {}) if isinstance(context.get("long_term", {}), dict) else {}
    return long_term.get(key, default)


def load_memory_system_report() -> dict[str, Any]:
    if not SYSTEM_REPORT_PATH.exists():
        return deepcopy(DEFAULT_SYSTEM_REPORT)
    loaded = read_json(SYSTEM_REPORT_PATH, deepcopy(DEFAULT_SYSTEM_REPORT))
    if not isinstance(loaded, dict) or loaded.get("error"):
        return deepcopy(DEFAULT_SYSTEM_REPORT)
    return _normalize_system_report(loaded)


def update_memory_system_report(
    *,
    status: str,
    notes: list[str] | None = None,
    last_consolidation: str | None = None,
    last_consistency_check: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    report = load_memory_system_report()
    report["schema"] = SYSTEM_REPORT_SCHEMA
    report["status"] = status
    report["core_memory_present"] = CORE_MEMORY_PATH.exists()
    if last_consolidation is not None:
        report["last_consolidation"] = last_consolidation
    if last_consistency_check is not None:
        report["last_consistency_check"] = last_consistency_check

    merged_notes = list(report.get("notes", [])) if isinstance(report.get("notes", []), list) else []
    for note in notes or []:
        if note not in merged_notes:
            merged_notes.append(note)
    report["notes"] = merged_notes[:25]

    if not dry_run:
        write_json(SYSTEM_REPORT_PATH, report)
    return report
