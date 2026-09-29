#!/usr/bin/env python3
"""Shared helpers for ANA MAX OS-11+ additive levels."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ANA_MAX.self_optimization.os3_common import print_raw_json

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

WORKSPACE_ROOT = ROOT
ANA_MAX_ROOT = WORKSPACE_ROOT / "ANA_MAX"
MEMORY_DIR = ANA_MAX_ROOT / "memory"
DOCS_DIR = WORKSPACE_ROOT / "docs"

try:
    from ANA_MAX.self_optimization import memory_context as _memory_context
except Exception:
    _memory_context = None

LEVEL_REPORT_SCHEMA = "ana.osX.level_report.v1"
FINAL_SUMMARY_SCHEMA = "ana.osX.final_summary.v1"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        return {} if default is None else default
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"error": str(exc), "path": str(path)}
    if isinstance(loaded, dict):
        return loaded
    return {"value": loaded}


def write_json(path: Path, data: Any) -> Path:
    ensure_dir(path.parent)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    return path


def emit_raw_json(payload: Any) -> None:
    print_raw_json(payload)


def load_memory_context() -> dict[str, Any]:
    if _memory_context is None:
        return {"schema": "ana.memory.context.v1", "error": "module_missing"}
    try:
        return _memory_context.build_memory_context()
    except Exception:
        return {"schema": "ana.memory.context.v1", "error": "failed_to_load"}


def memory_context_summary(context: dict[str, Any]) -> dict[str, Any]:
    if _memory_context is not None:
        try:
            return _memory_context.memory_context_summary(context)
        except Exception:
            pass
    return {
        "schema": "ana.memory.context.v1",
        "core_memory_present": bool(context.get("core_memory_present", False)),
        "core_memory_schema_ok": bool(context.get("core_memory_schema_ok", False)),
        "history_length": int(context.get("history_length", 0) or 0),
        "preferences": context.get("preferences", {}),
        "patterns": context.get("patterns", {}),
        "long_term_keys": sorted((context.get("long_term") or {}).keys()),
    }


def build_memory_snapshot() -> dict[str, Any]:
    context = load_memory_context()
    summary = memory_context_summary(context)
    consistency = read_json(MEMORY_DIR / "self_consistency_report.json", {})
    system_report = read_json(MEMORY_DIR / "memory_system_report.json", {})
    return {
        "schema": "ana.memory.evolution_snapshot.v1",
        "generated_at": utc_now(),
        "core_memory_present": summary.get("core_memory_present", False),
        "core_memory_schema_ok": summary.get("core_memory_schema_ok", False),
        "history_length": summary.get("history_length", 0),
        "preferences": summary.get("preferences", {}),
        "patterns": summary.get("patterns", {}),
        "consistency": {
            "present": bool(consistency),
            "overall_consistent": bool(consistency.get("overall_consistent", True)) if isinstance(consistency, dict) else True,
            "contradiction_count": len(consistency.get("contradictions", [])) if isinstance(consistency.get("contradictions", []), list) else 0,
            "regression_count": len(consistency.get("regressions", [])) if isinstance(consistency.get("regressions", []), list) else 0,
        },
        "memory_system": {
            "present": bool(system_report),
            "status": system_report.get("status") if isinstance(system_report, dict) else None,
            "last_consolidation": system_report.get("last_consolidation") if isinstance(system_report, dict) else None,
            "last_consistency_check": system_report.get("last_consistency_check") if isinstance(system_report, dict) else None,
        },
        "long_term_keys": summary.get("long_term_keys", []),
    }


def baseline_metrics() -> dict[str, Any]:
    evaluation = read_json(MEMORY_DIR / "self_evaluation_report.json", {})
    skills = read_json(MEMORY_DIR / "self_skills_report.json", {})
    evolution = read_json(MEMORY_DIR / "evolution_report.json", {})
    daemon = read_json(MEMORY_DIR / "os4_daemon_report.json", {})
    evaluation_summary = evaluation.get("summary", {}) if isinstance(evaluation, dict) else {}
    skills_summary = skills.get("summary", {}) if isinstance(skills, dict) else {}
    return {
        "health_score": int(evaluation_summary.get("health_score", 0) or 0),
        "warnings": int(evaluation_summary.get("warning_count", 0) or 0),
        "parse_error_count": int(skills_summary.get("parse_error_count", 0) or 0),
        "overall_success": bool(evolution.get("overall_success", True)) and bool(daemon.get("overall_success", True)),
    }


def agent_registry_snapshot() -> dict[str, Any]:
    registry = read_json(MEMORY_DIR / "agent_registry.json", {})
    agents = registry.get("agents", {}) if isinstance(registry, dict) else {}
    if not isinstance(agents, dict):
        agents = {}
    return {
        "schema": "ana.os7.agent_registry.v1",
        "generated_at": utc_now(),
        "path": str(MEMORY_DIR / "agent_registry.json"),
        "agents": agents,
        "summary": {
            "agent_count": len(agents),
            "healthy_count": sum(1 for entry in agents.values() if int(entry.get("failure_count", 0) or 0) == 0),
            "failure_count_total": sum(int(entry.get("failure_count", 0) or 0) for entry in agents.values()),
            "success_count_total": sum(int(entry.get("success_count", 0) or 0) for entry in agents.values()),
        },
    }


def level_report_path(os_level: int) -> Path:
    return MEMORY_DIR / f"os_level_OS{os_level}_report.json"


def build_level_report(
    *,
    os_level: int,
    engine: str,
    status: str,
    next_level: str | None,
    summary: dict[str, Any],
    payload: dict[str, Any],
    dry_run: bool,
    auto_retry_used: bool = False,
    auto_healing_levels_used: int = 0,
    memory_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "schema": LEVEL_REPORT_SCHEMA,
        "generated_at": utc_now(),
        "engine": engine,
        "os_level": f"OS-{os_level}",
        "status": status,
        "next": next_level,
        "dry_run": dry_run,
        "auto_retry_used": auto_retry_used,
        "auto_healing_levels_used": auto_healing_levels_used,
        "summary": summary,
        "memory_snapshot": memory_snapshot or build_memory_snapshot(),
        "payload": payload,
    }


def write_level_report(os_level: int, report: dict[str, Any]) -> Path:
    path = level_report_path(os_level)
    write_json(path, report)
    return path
