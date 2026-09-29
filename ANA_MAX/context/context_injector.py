#!/usr/bin/env python3
"""Build bounded ANA MAX context bundles for execution agents."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from ANA_MAX.self_optimization.os3_common import print_raw_json

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

ANA_MAX_ROOT = ROOT / "ANA_MAX"
MEMORY_DIR = ANA_MAX_ROOT / "memory"

BUNDLE_SCHEMA = "ana.context.bundle.v1"
EXPORT_SCHEMA = "ana.context.export.v1"
OS_LEVEL_RE = re.compile(r"os_level_OS(\d+)_report\.json$")

REPORT_FILES = {
    "core_memory": "core_memory.json",
    "emergent": "emergent_intelligence_report.json",
    "consistency": "self_consistency_report.json",
    "evolution_report": "evolution_report.json",
    "self_goals": "self_goals.json",
    "evolution_strategy": "evolution_strategy.json",
}


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists() or path.is_dir():
        return {}
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"error": str(exc), "path": str(path)}
    return loaded if isinstance(loaded, dict) else {"value": loaded}


def _report_summary(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": report.get("schema"),
        "generated_at": report.get("generated_at"),
        "engine": report.get("engine"),
        "os_level": report.get("os_level"),
        "status": report.get("status"),
        "next": report.get("next"),
        "summary": report.get("summary", {}),
    }


def _load_os_level_reports() -> dict[str, dict[str, Any]]:
    reports: dict[str, dict[str, Any]] = {}
    if not MEMORY_DIR.exists():
        return reports
    for path in sorted(MEMORY_DIR.glob("os_level_OS*_report.json"), key=_os_level_sort_key):
        reports[path.name] = {
            "path": str(path),
            "level": _level_from_name(path.name),
            "report": _report_summary(_load_json(path)),
        }
    return reports


def _level_from_name(name: str) -> int:
    match = OS_LEVEL_RE.match(name)
    return int(match.group(1)) if match else -1


def _os_level_sort_key(path: Path) -> tuple[int, str]:
    return (_level_from_name(path.name), path.name)


def _current_os_level(os_level_reports: dict[str, dict[str, Any]]) -> str:
    current_level = -1
    current_name = "unknown"
    pass_statuses = {"PASS", "PASS (auto-healed)"}
    for item in os_level_reports.values():
        report = item.get("report", {})
        level = int(item.get("level", -1) or -1)
        if report.get("status") in pass_statuses and level > current_level:
            current_level = level
            current_name = str(report.get("os_level") or f"OS-{level}")
    return current_name


def _bundle_summary(
    core_memory: dict[str, Any],
    os_level_reports: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    long_term = core_memory.get("long_term", {}) if isinstance(core_memory, dict) else {}
    preferences = core_memory.get("preferences", {}) if isinstance(core_memory, dict) else {}
    patterns = core_memory.get("patterns", {}) if isinstance(core_memory, dict) else {}
    return {
        "current_os_level": _current_os_level(os_level_reports),
        "os_report_count": len(os_level_reports),
        "health_score": long_term.get("last_health_score"),
        "overall_success": long_term.get("last_overall_success"),
        "stability_priority": preferences.get("stability_priority", "high"),
        "warnings_tolerance": preferences.get("warnings_tolerance", "zero"),
        "stable_cycles": patterns.get("stable_cycles", 0),
        "warning_cycles": patterns.get("warning_cycles", 0),
        "parse_error_cycles": patterns.get("parse_error_cycles", 0),
    }


def build_context_bundle() -> dict[str, Any]:
    loaded = {
        key: _load_json(MEMORY_DIR / filename)
        for key, filename in REPORT_FILES.items()
    }
    os_level_reports = _load_os_level_reports()
    summary = _bundle_summary(loaded["core_memory"], os_level_reports)
    return {
        "schema": BUNDLE_SCHEMA,
        "workspace_root": str(ROOT),
        "memory_dir": str(MEMORY_DIR),
        "summary": summary,
        **loaded,
        "os_level_reports": os_level_reports,
    }


def export_agent_bootstrap_prompt() -> str:
    bundle = build_context_bundle()
    core = bundle.get("core_memory", {})
    preferences = core.get("preferences", {}) if isinstance(core, dict) else {}
    patterns = core.get("patterns", {}) if isinstance(core, dict) else {}
    long_term = core.get("long_term", {}) if isinstance(core, dict) else {}
    summary = bundle.get("summary", {})

    lines = [
        "You are an EXECUTION AGENT working under ANA MAX OS.",
        "",
        "ANA MAX provides you with:",
        f"- current_os_level: {summary.get('current_os_level', 'unknown')}",
        f"- stability_priority: {preferences.get('stability_priority', 'high')}",
        f"- warnings_tolerance: {preferences.get('warnings_tolerance', 'zero')}",
        "",
        "You MUST:",
        "- respect ANA MAX memory and reports",
        "- keep all changes additive",
        "- avoid breaking existing schemas",
        "- keep execution local-only unless the operator explicitly says otherwise",
        "",
        "Long-term signals:",
        f"- health_score: {long_term.get('last_health_score', 'unknown')}",
        f"- overall_success: {long_term.get('last_overall_success', 'unknown')}",
        "",
        "Patterns:",
        f"- stable_cycles: {patterns.get('stable_cycles', 0)}",
        f"- warning_cycles: {patterns.get('warning_cycles', 0)}",
        f"- parse_error_cycles: {patterns.get('parse_error_cycles', 0)}",
        "",
        "Your role:",
        "- implement code according to ANA MAX direction",
        "- use this context as primary guidance",
        "- do not ignore memory, preferences, or patterns",
    ]
    return "\n".join(lines)


def build_export() -> dict[str, Any]:
    return {
        "schema": EXPORT_SCHEMA,
        "bundle": build_context_bundle(),
        "agent_bootstrap_prompt": export_agent_bootstrap_prompt(),
    }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ANA MAX context bundle exporter")
    parser.add_argument(
        "--prompt-only",
        action="store_true",
        help="Emit only the bootstrap prompt inside the RAW JSON envelope.",
    )
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    payload: dict[str, Any]
    if args.prompt_only:
        payload = {
            "schema": EXPORT_SCHEMA,
            "agent_bootstrap_prompt": export_agent_bootstrap_prompt(),
        }
    else:
        payload = build_export()
    print_raw_json(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
