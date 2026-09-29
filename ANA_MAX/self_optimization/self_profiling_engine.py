#!/usr/bin/env python3
"""
ANA MAX OS-3 Self-Profiling Engine.

Inspects the ANA_MAX codebase and collects simple profiling-style information
using only the Python standard library and local filesystem operations.
"""

from __future__ import annotations

import argparse
import json
import logging
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ANA_MAX.self_optimization.os3_common import print_raw_json

ENGINE_NAME = "self_profiling_engine"
REPORT_FILENAME = "self_profiling_report.json"
LOG_FILENAME = "self_profiling_engine.log"

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

TOP_N = 15


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _should_skip_dir(path: Path) -> bool:
    return path.name in SKIP_DIR_NAMES


def setup_logger() -> logging.Logger:
    """Configure console and file logging (call only during execution)."""
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


def observe(root: Path) -> dict[str, Any]:
    """Walk ANA_MAX and collect file metadata."""
    files_by_extension: dict[str, int] = defaultdict(int)
    size_by_extension: dict[str, int] = defaultdict(int)
    size_by_top_dir: dict[str, int] = defaultdict(int)
    count_by_top_dir: dict[str, int] = defaultdict(int)
    size_by_relative_dir: dict[str, int] = defaultdict(int)
    count_by_relative_dir: dict[str, int] = defaultdict(int)
    python_files: list[dict[str, Any]] = []
    total_files = 0
    total_bytes = 0

    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIR_NAMES for part in path.parts):
            continue

        size = path.stat().st_size
        suffix = path.suffix.lower() or "(no_ext)"
        rel = path.relative_to(root)
        top = rel.parts[0] if rel.parts else "."
        parent = str(rel.parent).replace("\\", "/") if rel.parent != Path(".") else "."

        total_files += 1
        total_bytes += size
        files_by_extension[suffix] += 1
        size_by_extension[suffix] += size
        size_by_top_dir[top] += size
        count_by_top_dir[top] += 1
        size_by_relative_dir[parent] += size
        count_by_relative_dir[parent] += 1

        if suffix == ".py":
            line_count = 0
            try:
                line_count = len(path.read_text(encoding="utf-8", errors="replace").splitlines())
            except OSError:
                line_count = -1
            python_files.append(
                {
                    "path": str(rel).replace("\\", "/"),
                    "size_bytes": size,
                    "line_count": line_count,
                }
            )

    return {
        "root": str(root),
        "total_files": total_files,
        "total_bytes": total_bytes,
        "files_by_extension": dict(sorted(files_by_extension.items())),
        "size_by_extension": dict(sorted(size_by_extension.items())),
        "size_by_top_dir": dict(size_by_top_dir),
        "count_by_top_dir": dict(count_by_top_dir),
        "size_by_relative_dir": dict(size_by_relative_dir),
        "count_by_relative_dir": dict(count_by_relative_dir),
        "python_files": python_files,
    }


def analyze(observation: dict[str, Any]) -> dict[str, Any]:
    """Summarize largest and most active areas."""
    dir_stats: list[dict[str, Any]] = []
    for directory, size in observation["size_by_relative_dir"].items():
        dir_stats.append(
            {
                "directory": directory,
                "size_bytes": size,
                "file_count": observation["count_by_relative_dir"].get(directory, 0),
            }
        )

    by_size = sorted(dir_stats, key=lambda item: item["size_bytes"], reverse=True)
    by_count = sorted(dir_stats, key=lambda item: item["file_count"], reverse=True)

    python_sorted = sorted(
        observation["python_files"],
        key=lambda item: item.get("line_count", 0),
        reverse=True,
    )

    top_level = sorted(
        (
            {
                "directory": name,
                "size_bytes": observation["size_by_top_dir"].get(name, 0),
                "file_count": observation["count_by_top_dir"].get(name, 0),
            }
            for name in observation["count_by_top_dir"]
        ),
        key=lambda item: item["size_bytes"],
        reverse=True,
    )

    return {
        "largest_directories_by_size": by_size[:TOP_N],
        "most_active_directories_by_count": by_count[:TOP_N],
        "largest_top_level_areas": top_level[:TOP_N],
        "largest_python_files_by_lines": python_sorted[:TOP_N],
        "python_file_count": len(observation["python_files"]),
        "dominant_extensions": sorted(
            observation["files_by_extension"].items(),
            key=lambda item: item[1],
            reverse=True,
        )[:10],
    }


def plan(analysis: dict[str, Any]) -> list[str]:
    """Decide what to include in the final report."""
    actions = [
        "include_summary_totals",
        "include_top_directories_by_size",
        "include_top_directories_by_count",
        "include_top_level_breakdown",
        "include_largest_python_modules",
        "include_extension_breakdown",
    ]
    if analysis["python_file_count"] == 0:
        actions.append("flag_no_python_files_found")
    return actions


def act(
    observation: dict[str, Any],
    analysis: dict[str, Any],
    planned_actions: list[str],
) -> dict[str, Any]:
    """Build the structured profiling report."""
    return {
        "schema": "ana.os3.self_profiling.v1",
        "engine": ENGINE_NAME,
        "generated_at": _utc_now(),
        "project_root": str(PROJECT_ROOT),
        "ana_max_root": str(ANA_MAX_ROOT),
        "planned_actions": planned_actions,
        "summary": {
            "total_files": observation["total_files"],
            "total_bytes": observation["total_bytes"],
            "python_file_count": analysis["python_file_count"],
            "top_level_area_count": len(observation["count_by_top_dir"]),
        },
        "analysis": analysis,
        "observation_snapshot": {
            "files_by_extension": observation["files_by_extension"],
            "size_by_top_dir": observation["size_by_top_dir"],
            "count_by_top_dir": observation["count_by_top_dir"],
        },
    }


def verify(report: dict[str, Any]) -> dict[str, Any]:
    """Ensure the report dict is non-empty and internally consistent."""
    checks: dict[str, bool] = {}
    checks["report_non_empty"] = bool(report)
    summary = report.get("summary", {})
    checks["summary_has_totals"] = (
        isinstance(summary.get("total_files"), int)
        and summary["total_files"] >= 0
        and isinstance(summary.get("total_bytes"), int)
        and summary["total_bytes"] >= 0
    )
    checks["analysis_present"] = bool(report.get("analysis"))
    checks["schema_present"] = report.get("schema") == "ana.os3.self_profiling.v1"
    passed = all(checks.values())
    return {"passed": passed, "checks": checks}


def document(report: dict[str, Any], verification: dict[str, Any], *, dry_run: bool) -> None:
    """Write JSON report and append a log line."""
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
        "cycle complete status=%s report=%s verify_passed=%s files=%s bytes=%s",
        status,
        REPORT_PATH,
        verification.get("passed"),
        report.get("summary", {}).get("total_files"),
        report.get("summary", {}).get("total_bytes"),
    )


def run_cycle(*, dry_run: bool = False) -> dict[str, Any]:
    """Execute the full OS-3 micro pipeline."""
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
    parser = argparse.ArgumentParser(description="ANA MAX OS-3 Self-Profiling Engine")
    parser.add_argument(
        "--cycle",
        action="store_true",
        help="Run the full observe-analyze-plan-act-verify-document pipeline.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run the pipeline without writing the JSON report file.",
    )
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
