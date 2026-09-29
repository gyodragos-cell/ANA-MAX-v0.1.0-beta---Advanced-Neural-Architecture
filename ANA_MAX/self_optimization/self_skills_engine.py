#!/usr/bin/env python3
"""
ANA MAX OS-3 Self-Skills Engine.

Discovers and summarizes available capabilities in the ANA_MAX project using
AST parsing and filesystem inspection only.
"""

from __future__ import annotations

import argparse
import ast
import json
import logging
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ANA_MAX.self_optimization.os3_common import print_raw_json

ENGINE_NAME = "self_skills_engine"
REPORT_FILENAME = "self_skills_report.json"
LOG_FILENAME = "self_skills_engine.log"

ANA_MAX_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[2]
MEMORY_DIR = ANA_MAX_ROOT / "memory"
LOGS_DIR = ANA_MAX_ROOT / "logs"
REPORT_PATH = MEMORY_DIR / REPORT_FILENAME
LOG_PATH = LOGS_DIR / LOG_FILENAME

SKIP_DIR_NAMES = frozenset(
    {
        "__pycache__",
        ".git",
        "venv",
        ".venv",
        "node_modules",
        "site-packages",
        ".mypy_cache",
        ".pytest_cache",
        "archives",
        "logs",
        "memory",
        "sandbox",
        "screenshots",
        "voice_temp",
    }
)


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


def _area_for_path(rel_path: str) -> str:
    parts = rel_path.replace("\\", "/").split("/")
    return parts[0] if parts else "root"


def _parse_python_file(path: Path) -> dict[str, Any]:
    """Parse a Python file and extract top-level symbols without importing it."""
    source = path.read_text(encoding="utf-8-sig", errors="replace")
    tree = ast.parse(source, filename=str(path))
    functions: list[str] = []
    classes: list[str] = []
    has_main_guard = False

    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            functions.append(node.name)
        elif isinstance(node, ast.AsyncFunctionDef):
            functions.append(node.name)
        elif isinstance(node, ast.ClassDef):
            classes.append(node.name)
        elif isinstance(node, ast.If):
            test = node.test
            if (
                isinstance(test, ast.Compare)
                and isinstance(test.left, ast.Name)
                and test.left.id == "__name__"
            ):
                has_main_guard = True

    return {
        "functions": functions,
        "classes": classes,
        "has_main_guard": has_main_guard,
        "line_count": len(source.splitlines()),
    }


def observe(root: Path) -> dict[str, Any]:
    """Scan ANA_MAX modules and collect parseable capability metadata."""
    modules: list[dict[str, Any]] = []
    parse_errors: list[dict[str, str]] = []

    for path in sorted(root.rglob("*.py")):
        if any(part in SKIP_DIR_NAMES for part in path.parts):
            continue
        rel = str(path.relative_to(root)).replace("\\", "/")
        try:
            parsed = _parse_python_file(path)
            modules.append(
                {
                    "module": rel,
                    "area": _area_for_path(rel),
                    **parsed,
                }
            )
        except SyntaxError as exc:
            parse_errors.append({"module": rel, "error": str(exc)})

    return {
        "root": str(root),
        "modules": modules,
        "module_count": len(modules),
        "parse_errors": parse_errors,
    }


def analyze(observation: dict[str, Any]) -> dict[str, Any]:
    """Group capabilities by module area."""
    by_area: dict[str, list[dict[str, Any]]] = defaultdict(list)
    entrypoints: list[str] = []
    total_functions = 0
    total_classes = 0

    for module in observation["modules"]:
        by_area[module["area"]].append(
            {
                "module": module["module"],
                "functions": module["functions"],
                "classes": module["classes"],
                "has_main_guard": module["has_main_guard"],
            }
        )
        total_functions += len(module["functions"])
        total_classes += len(module["classes"])
        if module["has_main_guard"]:
            entrypoints.append(module["module"])

    area_summary = []
    for area, items in sorted(by_area.items()):
        area_summary.append(
            {
                "area": area,
                "module_count": len(items),
                "function_count": sum(len(item["functions"]) for item in items),
                "class_count": sum(len(item["classes"]) for item in items),
                "entrypoint_count": sum(1 for item in items if item["has_main_guard"]),
            }
        )

    return {
        "areas": area_summary,
        "by_area": {area: items for area, items in by_area.items()},
        "entrypoints": sorted(entrypoints),
        "total_functions": total_functions,
        "total_classes": total_classes,
        "parse_error_count": len(observation["parse_errors"]),
    }


def plan(analysis: dict[str, Any]) -> list[str]:
    """Decide how to represent discovered skills."""
    actions = [
        "include_area_summary",
        "include_entrypoints",
        "include_per_module_capabilities",
        "include_function_and_class_totals",
    ]
    if analysis["parse_error_count"] > 0:
        actions.append("include_parse_errors")
    return actions


def act(
    observation: dict[str, Any],
    analysis: dict[str, Any],
    planned_actions: list[str],
) -> dict[str, Any]:
    """Build the skills report dictionary."""
    skills: list[dict[str, Any]] = []
    for module in observation["modules"]:
        skills.append(
            {
                "module": module["module"],
                "area": module["area"],
                "functions": module["functions"],
                "classes": module["classes"],
                "entrypoint": module["has_main_guard"],
                "line_count": module["line_count"],
            }
        )

    return {
        "schema": "ana.os3.self_skills.v1",
        "engine": ENGINE_NAME,
        "generated_at": _utc_now(),
        "project_root": str(PROJECT_ROOT),
        "ana_max_root": str(ANA_MAX_ROOT),
        "planned_actions": planned_actions,
        "summary": {
            "module_count": observation["module_count"],
            "area_count": len(analysis["areas"]),
            "total_functions": analysis["total_functions"],
            "total_classes": analysis["total_classes"],
            "entrypoint_count": len(analysis["entrypoints"]),
            "parse_error_count": analysis["parse_error_count"],
        },
        "areas": analysis["areas"],
        "entrypoints": analysis["entrypoints"],
        "skills": skills,
        "parse_errors": observation["parse_errors"],
    }


def verify(report: dict[str, Any]) -> dict[str, Any]:
    """Ensure the skills structure is valid and non-empty when possible."""
    summary = report.get("summary", {})
    checks = {
        "report_non_empty": bool(report),
        "schema_present": report.get("schema") == "ana.os3.self_skills.v1",
        "skills_is_list": isinstance(report.get("skills"), list),
        "summary_counts_non_negative": (
            summary.get("module_count", -1) >= 0
            and summary.get("total_functions", -1) >= 0
            and summary.get("total_classes", -1) >= 0
        ),
        "skills_count_matches_summary": len(report.get("skills", [])) == summary.get("module_count", -1),
    }
    if summary.get("module_count", 0) > 0:
        checks["skills_non_empty"] = len(report.get("skills", [])) > 0
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
        "cycle complete status=%s report=%s verify_passed=%s modules=%s functions=%s classes=%s",
        status,
        REPORT_PATH,
        verification.get("passed"),
        report.get("summary", {}).get("module_count"),
        report.get("summary", {}).get("total_functions"),
        report.get("summary", {}).get("total_classes"),
    )


def run_cycle(*, dry_run: bool = False) -> dict[str, Any]:
    started = time.perf_counter()
    observation = observe(ANA_MAX_ROOT)
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
    parser = argparse.ArgumentParser(description="ANA MAX OS-3 Self-Skills Engine")
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
