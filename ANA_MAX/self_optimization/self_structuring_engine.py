#!/usr/bin/env python3
"""
ANA MAX OS-3 Self-Structuring Engine.

Inspects package structure and reports or optionally fixes missing __init__.py
markers using only the Python standard library.
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

ENGINE_NAME = "self_structuring_engine"
REPORT_FILENAME = "self_structuring_report.json"
LOG_FILENAME = "self_structuring_engine.log"

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


def _iter_package_dirs(root: Path) -> list[Path]:
    """Return directories that look like Python packages or package parents."""
    package_dirs: list[Path] = []
    for path in sorted(root.rglob("*")):
        if not path.is_dir():
            continue
        if any(part in SKIP_DIR_NAMES for part in path.parts):
            continue
        if path == root:
            continue
        py_files = [child for child in path.iterdir() if child.is_file() and child.suffix == ".py"]
        py_subdirs = [
            child
            for child in path.iterdir()
            if child.is_dir() and not _should_skip_dir(child) and any(child.rglob("*.py"))
        ]
        if py_files or py_subdirs:
            package_dirs.append(path)
    return package_dirs


def _should_skip_dir(path: Path) -> bool:
    return path.name in SKIP_DIR_NAMES


def observe(root: Path) -> dict[str, Any]:
    """Scan ANA_MAX for Python packages and modules."""
    modules: list[str] = []
    package_dirs: list[str] = []
    missing_init: list[str] = []
    existing_init: list[str] = []

    for path in root.rglob("*.py"):
        if any(part in SKIP_DIR_NAMES for part in path.parts):
            continue
        rel = path.relative_to(root)
        modules.append(str(rel).replace("\\", "/"))
        if path.name == "__init__.py":
            existing_init.append(str(rel.parent).replace("\\", "/"))

    for directory in _iter_package_dirs(root):
        rel_dir = directory.relative_to(root)
        rel_text = str(rel_dir).replace("\\", "/") if rel_dir != Path(".") else "."
        package_dirs.append(rel_text)
        init_file = directory / "__init__.py"
        if not init_file.exists():
            missing_init.append(rel_text)

    return {
        "root": str(root),
        "module_count": len(modules),
        "modules_sample": sorted(modules)[:50],
        "package_dir_count": len(package_dirs),
        "package_dirs": sorted(package_dirs),
        "existing_init_packages": sorted(set(existing_init)),
        "missing_init_packages": sorted(set(missing_init)),
    }


def analyze(observation: dict[str, Any]) -> dict[str, Any]:
    """Decide which missing package markers matter."""
    missing = observation["missing_init_packages"]
    important: list[str] = []
    optional: list[str] = []

    for package in missing:
        if package in {".", "sandbox", "logs", "memory"}:
            optional.append(package)
        else:
            important.append(package)

    return {
        "missing_init_total": len(missing),
        "important_missing_init": important,
        "optional_missing_init": optional,
        "structure_health": "good" if not important else "needs_attention",
    }


def plan(
    analysis: dict[str, Any],
    *,
    fix_init: bool,
    dry_run: bool,
) -> list[dict[str, Any]]:
    """Plan reporting or creation of missing __init__.py files."""
    actions: list[dict[str, Any]] = [
        {"action": "report_structure", "targets": analysis["important_missing_init"]},
    ]
    if fix_init:
        for package in analysis["important_missing_init"]:
            actions.append(
                {
                    "action": "create_init_py",
                    "target": package,
                    "mode": "dry-run" if dry_run else "apply",
                }
            )
    return actions


def act(
    observation: dict[str, Any],
    analysis: dict[str, Any],
    planned_actions: list[dict[str, Any]],
    *,
    fix_init: bool,
    dry_run: bool,
) -> dict[str, Any]:
    """Report structure issues and optionally create __init__.py files."""
    created: list[str] = []
    skipped: list[str] = []

    if fix_init and not dry_run:
        for package in analysis["important_missing_init"]:
            if package == ".":
                target_dir = ANA_MAX_ROOT
            else:
                target_dir = ANA_MAX_ROOT / package.replace("/", "\\")
            init_path = target_dir / "__init__.py"
            if init_path.exists():
                skipped.append(str(init_path.relative_to(ANA_MAX_ROOT)).replace("\\", "/"))
                continue
            target_dir.mkdir(parents=True, exist_ok=True)
            init_path.write_text("", encoding="utf-8")
            created.append(str(init_path.relative_to(ANA_MAX_ROOT)).replace("\\", "/"))

    return {
        "schema": "ana.os3.self_structuring.v1",
        "engine": ENGINE_NAME,
        "generated_at": _utc_now(),
        "project_root": str(PROJECT_ROOT),
        "ana_max_root": str(ANA_MAX_ROOT),
        "fix_init_requested": fix_init,
        "dry_run": dry_run,
        "planned_actions": planned_actions,
        "summary": {
            "module_count": observation["module_count"],
            "package_dir_count": observation["package_dir_count"],
            "missing_init_total": analysis["missing_init_total"],
            "important_missing_init_count": len(analysis["important_missing_init"]),
            "structure_health": analysis["structure_health"],
        },
        "analysis": analysis,
        "created_init_files": created,
        "skipped_init_files": skipped,
        "observation_snapshot": {
            "missing_init_packages": observation["missing_init_packages"],
            "existing_init_packages": observation["existing_init_packages"],
        },
    }


def verify(
    report: dict[str, Any],
    *,
    fix_init: bool,
    dry_run: bool,
) -> dict[str, Any]:
    """Re-scan to confirm structure is consistent with the plan."""
    rescanned = observe(ANA_MAX_ROOT)
    remaining_important = []
    for package in rescanned["missing_init_packages"]:
        if package not in {".", "sandbox", "logs", "memory"}:
            remaining_important.append(package)

    checks = {
        "report_non_empty": bool(report),
        "schema_present": report.get("schema") == "ana.os3.self_structuring.v1",
        "module_count_positive": report.get("summary", {}).get("module_count", 0) > 0,
    }
    if fix_init and not dry_run:
        checks["important_missing_init_resolved"] = len(remaining_important) == 0
    else:
        checks["rescanned_missing_init_count_matches"] = (
            len(remaining_important) == len(report.get("analysis", {}).get("important_missing_init", []))
        )

    return {
        "passed": all(checks.values()),
        "checks": checks,
        "remaining_important_missing_init": remaining_important,
    }


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
        "cycle complete status=%s report=%s verify_passed=%s missing_init=%s health=%s",
        status,
        REPORT_PATH,
        verification.get("passed"),
        report.get("summary", {}).get("missing_init_total"),
        report.get("summary", {}).get("structure_health"),
    )


def run_cycle(*, dry_run: bool = False, fix_init: bool = False) -> dict[str, Any]:
    started = time.perf_counter()
    observation = observe(ANA_MAX_ROOT)
    analysis = analyze(observation)
    planned = plan(analysis, fix_init=fix_init, dry_run=dry_run)
    report = act(
        observation,
        analysis,
        planned,
        fix_init=fix_init,
        dry_run=dry_run,
    )
    verification = verify(report, fix_init=fix_init, dry_run=dry_run)
    document(report, verification, dry_run=dry_run)
    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    return {
        "engine": ENGINE_NAME,
        "dry_run": dry_run,
        "fix_init": fix_init,
        "elapsed_ms": elapsed_ms,
        "verification": verification,
        "report_path": str(REPORT_PATH),
        "summary": report.get("summary", {}),
    }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ANA MAX OS-3 Self-Structuring Engine")
    parser.add_argument("--cycle", action="store_true", help="Run the full OS-3 pipeline.")
    parser.add_argument("--dry-run", action="store_true", help="Do not write report or create files.")
    parser.add_argument(
        "--fix-init",
        action="store_true",
        help="Create missing __init__.py files for important package directories.",
    )
    return parser


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()
    if not args.cycle:
        parser.print_help()
        return 0
    result = run_cycle(dry_run=args.dry_run, fix_init=args.fix_init)
    print_raw_json(result)
    return 0 if result.get("verification", {}).get("passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
