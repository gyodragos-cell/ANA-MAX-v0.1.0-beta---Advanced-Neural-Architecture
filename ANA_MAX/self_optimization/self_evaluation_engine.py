#!/usr/bin/env python3
"""
ANA MAX OS-3 Self-Evaluation Engine.

Evaluates overall system state based on artifacts produced by the other
OS-3 engines. Uses only local filesystem reads and standard library code.
"""

from __future__ import annotations

import argparse
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ANA_MAX.self_optimization.os3_common import print_raw_json

ENGINE_NAME = "self_evaluation_engine"
REPORT_FILENAME = "self_evaluation_report.json"
LOG_FILENAME = "self_evaluation_engine.log"

ANA_MAX_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[2]
MEMORY_DIR = ANA_MAX_ROOT / "memory"
LOGS_DIR = ANA_MAX_ROOT / "logs"
REPORT_PATH = MEMORY_DIR / REPORT_FILENAME
LOG_PATH = LOGS_DIR / LOG_FILENAME

INPUT_REPORTS = {
    "profiling": MEMORY_DIR / "self_profiling_report.json",
    "structuring": MEMORY_DIR / "self_structuring_report.json",
    "healing": MEMORY_DIR / "self_healing_report.json",
    "skills": MEMORY_DIR / "self_skills_report.json",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def setup_logger() -> logging.Logger:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(ENGINE_NAME)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    if logger.handlers:
        return logger
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    logger.addHandler(console)
    file_handler = logging.FileHandler(LOG_PATH, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def observe(memory_dir: Path) -> dict[str, Any]:
    """Read upstream engine reports, handling missing files gracefully."""
    loaded: dict[str, Any] = {}
    missing: list[str] = []
    invalid: list[str] = []

    for name, path in INPUT_REPORTS.items():
        if not path.exists():
            missing.append(name)
            continue
        data = _read_json(path)
        if data is None:
            invalid.append(name)
        else:
            loaded[name] = {
                "path": str(path),
                "schema": data.get("schema"),
                "generated_at": data.get("generated_at"),
                "summary": data.get("summary", {}),
                "verification": data.get("verification", {}),
                "raw": data,
            }

    return {
        "memory_dir": str(memory_dir),
        "loaded_reports": loaded,
        "missing_reports": missing,
        "invalid_reports": invalid,
        "loaded_count": len(loaded),
        "expected_count": len(INPUT_REPORTS),
    }


def analyze(observation: dict[str, Any]) -> dict[str, Any]:
    """Derive health indicators from upstream reports."""
    loaded = observation["loaded_reports"]
    indicators: dict[str, Any] = {}
    warnings: list[str] = []
    suggestions: list[str] = []

    if observation["missing_reports"]:
        warnings.append(
            "Missing upstream reports: " + ", ".join(sorted(observation["missing_reports"]))
        )
        suggestions.append("Run the missing OS-3 engines with --cycle before evaluation.")

    if observation["invalid_reports"]:
        warnings.append(
            "Invalid upstream reports: " + ", ".join(sorted(observation["invalid_reports"]))
        )
        suggestions.append("Regenerate invalid report JSON files.")

    profiling = loaded.get("profiling", {}).get("raw", {})
    if profiling:
        summary = profiling.get("summary", {})
        indicators["profiling_total_files"] = summary.get("total_files")
        indicators["profiling_python_files"] = summary.get("python_file_count")
        if summary.get("total_files", 0) == 0:
            warnings.append("Profiling report shows zero files scanned.")
    else:
        indicators["profiling_status"] = "missing"

    structuring = loaded.get("structuring", {}).get("raw", {})
    if structuring:
        summary = structuring.get("summary", {})
        indicators["structuring_health"] = summary.get("structure_health")
        indicators["missing_init_total"] = summary.get("missing_init_total")
        indicators["important_missing_init_count"] = summary.get("important_missing_init_count")
        if summary.get("important_missing_init_count", 0) > 0:
            warnings.append(
                "Package structure has missing __init__.py markers in important directories."
            )
            suggestions.append("Run self_structuring_engine with --fix-init after review.")
    else:
        indicators["structuring_status"] = "missing"

    healing = loaded.get("healing", {}).get("raw", {})
    if healing:
        summary = healing.get("summary", {})
        indicators["healing_health"] = summary.get("health")
        indicators["syntax_failures"] = summary.get("failed_count")
        failed = healing.get("failed_files", [])
        if failed:
            warnings.append(f"Syntax failures detected in {len(failed)} Python files.")
            suggestions.append("Inspect failed_files in self_healing_report.json and fix syntax errors.")
    else:
        indicators["healing_status"] = "missing"

    skills = loaded.get("skills", {}).get("raw", {})
    if skills:
        summary = skills.get("summary", {})
        indicators["skills_module_count"] = summary.get("module_count")
        indicators["skills_function_count"] = summary.get("total_functions")
        indicators["skills_entrypoint_count"] = summary.get("entrypoint_count")
        if summary.get("parse_error_count", 0) > 0:
            warnings.append("Skills discovery encountered parse errors in some modules.")
    else:
        indicators["skills_status"] = "missing"

    score = 100
    score -= 15 * len(observation["missing_reports"])
    score -= 10 * len(observation["invalid_reports"])
    if indicators.get("syntax_failures", 0):
        score -= min(40, 2 * int(indicators["syntax_failures"]))
    if indicators.get("important_missing_init_count", indicators.get("missing_init_total", 0)):
        score -= 10
    score = max(0, min(100, score))

    if score >= 85:
        overall = "healthy"
    elif score >= 60:
        overall = "warning"
    else:
        overall = "critical"

    return {
        "health_indicators": indicators,
        "warnings": warnings,
        "suggestions": suggestions,
        "health_score": score,
        "overall_status": overall,
    }


def plan(analysis: dict[str, Any]) -> list[str]:
    """Decide what to include in the evaluation summary."""
    actions = [
        "include_health_score",
        "include_overall_status",
        "include_health_indicators",
        "include_warnings",
        "include_suggestions",
        "include_input_report_status",
    ]
    if analysis["overall_status"] != "healthy":
        actions.append("flag_follow_up_required")
    return actions


def act(
    observation: dict[str, Any],
    analysis: dict[str, Any],
    planned_actions: list[str],
) -> dict[str, Any]:
    """Build the evaluation report dictionary."""
    return {
        "schema": "ana.os3.self_evaluation.v1",
        "engine": ENGINE_NAME,
        "generated_at": _utc_now(),
        "project_root": str(PROJECT_ROOT),
        "ana_max_root": str(ANA_MAX_ROOT),
        "planned_actions": planned_actions,
        "input_reports": {
            name: {
                "path": str(path),
                "present": path.exists(),
            }
            for name, path in INPUT_REPORTS.items()
        },
        "summary": {
            "overall_status": analysis["overall_status"],
            "health_score": analysis["health_score"],
            "loaded_report_count": observation["loaded_count"],
            "missing_report_count": len(observation["missing_reports"]),
            "warning_count": len(analysis["warnings"]),
            "suggestion_count": len(analysis["suggestions"]),
        },
        "health_indicators": analysis["health_indicators"],
        "warnings": analysis["warnings"],
        "suggestions": analysis["suggestions"],
        "observation_snapshot": {
            "missing_reports": observation["missing_reports"],
            "invalid_reports": observation["invalid_reports"],
            "loaded_report_names": sorted(observation["loaded_reports"].keys()),
        },
    }


def verify(report: dict[str, Any]) -> dict[str, Any]:
    """Ensure the evaluation dict is JSON-serializable and consistent."""
    try:
        json.dumps(report)
        serializable = True
    except TypeError:
        serializable = False

    summary = report.get("summary", {})
    checks = {
        "report_non_empty": bool(report),
        "schema_present": report.get("schema") == "ana.os3.self_evaluation.v1",
        "json_serializable": serializable,
        "overall_status_present": bool(summary.get("overall_status")),
        "health_score_in_range": 0 <= int(summary.get("health_score", -1)) <= 100,
        "warnings_is_list": isinstance(report.get("warnings"), list),
        "suggestions_is_list": isinstance(report.get("suggestions"), list),
    }
    return {"passed": all(checks.values()), "checks": checks}


def document(report: dict[str, Any], verification: dict[str, Any], *, dry_run: bool) -> None:
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    final_report = {
        **report,
        "verification": verification,
        "pipeline": {
            "observe": "complete",
            "analyze": "complete",
            "plan": "complete",
            "act": "complete",
            "verify": "complete",
            "document": "skipped" if dry_run else "complete",
        },
    }
    if not dry_run:
        REPORT_PATH.write_text(
            json.dumps(final_report, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    logger = setup_logger()
    status = "dry-run" if dry_run else "written"
    logger.info(
        "cycle complete status=%s report=%s verify_passed=%s overall=%s score=%s warnings=%s",
        status,
        REPORT_PATH,
        verification.get("passed"),
        report.get("summary", {}).get("overall_status"),
        report.get("summary", {}).get("health_score"),
        report.get("summary", {}).get("warning_count"),
    )


def run_cycle(*, dry_run: bool = False) -> dict[str, Any]:
    started = time.perf_counter()
    observation = observe(MEMORY_DIR)
    analysis = analyze(observation)
    planned = plan(analysis)
    report = act(observation, analysis, planned)
    verification = verify(report)
    document(report, verification, dry_run=dry_run)
    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    return {
        "engine": ENGINE_NAME,
        "dry_run": dry_run,
        "elapsed_ms": elapsed_ms,
        "verification": verification,
        "report_path": str(REPORT_PATH),
        "summary": report.get("summary", {}),
    }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ANA MAX OS-3 Self-Evaluation Engine")
    parser.add_argument("--cycle", action="store_true", help="Run the full OS-3 pipeline.")
    parser.add_argument("--dry-run", action="store_true", help="Do not write the JSON report file.")
    return parser


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()
    if not args.cycle:
        parser.print_help()
        return 0
    result = run_cycle(dry_run=args.dry_run)
    print_raw_json(result)
    return 0 if result.get("verification", {}).get("passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
