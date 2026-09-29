#!/usr/bin/env python3
"""ANA MAX OS-18 Habit & Routine Engine."""

from __future__ import annotations

import argparse
import re
import time
from collections import Counter
from typing import Any

from ANA_MAX.self_optimization.osx_level_common import (
    MEMORY_DIR,
    WORKSPACE_ROOT,
    baseline_metrics,
    build_level_report,
    build_memory_snapshot,
    emit_raw_json,
    level_report_path,
    write_json,
    write_level_report,
    utc_now,
)

ENGINE_NAME = "habit_routine_engine"
LEVEL = 18
LEVEL_SCHEMA = "ana.os18.habit_routine_engine.v1"
REPORT_PATH = level_report_path(LEVEL).with_name("habit_routine_report.json")


def _scan_text_file(path: str) -> str:
    file_path = WORKSPACE_ROOT / path
    if not file_path.exists():
        return ""
    return file_path.read_text(encoding="utf-8", errors="replace")


def _scan_memory_file(name: str) -> str:
    file_path = MEMORY_DIR / name
    if not file_path.exists() or file_path.is_dir():
        return ""
    return file_path.read_text(encoding="utf-8", errors="replace")


def _extract_commands(*texts: str) -> list[dict[str, Any]]:
    command_counter: Counter[str] = Counter()
    cycle_counter: Counter[str] = Counter()
    tool_counter: Counter[str] = Counter()
    command_pattern = re.compile(r"python\s+-m\s+[A-Za-z0-9_.]+")
    cycle_pattern = re.compile(r"OS-\d+|--cycle|--dry-run|--fast-parallel")
    tool_pattern = re.compile(r'"tool"\s*:\s*"([A-Za-z0-9_]+)"')
    explicit_tool_pattern = re.compile(
        r"\b(agent_coach|tool_router|file_operations|project_navigator|smart_search|code_context_pack|workspace_situational_awareness|session_checkpoint|session_rem_sleep)\b"
    )

    for text in texts:
        for command in command_pattern.findall(text):
            command_counter[command] += 1
        for match in cycle_pattern.findall(text):
            cycle_counter[match] += 1
        for tool_name in tool_pattern.findall(text):
            tool_counter[tool_name] += 1
        for tool_name in explicit_tool_pattern.findall(text):
            tool_counter[tool_name] += 1

    routines = [
        {
            "pattern": command,
            "count": count,
            "type": "command",
        }
        for command, count in command_counter.most_common(8)
    ]
    routines.extend(
        {
            "pattern": pattern,
            "count": count,
            "type": "cycle",
        }
        for pattern, count in cycle_counter.most_common(8)
    )
    routines.extend(
        {
            "pattern": tool_name,
            "count": count,
            "type": "tool",
        }
        for tool_name, count in tool_counter.most_common(8)
    )
    return routines


def run_cycle(*, dry_run: bool = False) -> dict[str, Any]:
    started = time.perf_counter()
    memory_snapshot = build_memory_snapshot()
    baseline = baseline_metrics()
    performance_text = _scan_text_file("docs/PERFORMANCE_LOG.md")
    benchmark_text = _scan_text_file("docs/BENCHMARKS.md")
    test_text = _scan_text_file("docs/TEST_REPORT.md")
    changelog_text = _scan_text_file("docs/CHANGELOG.md")
    ana_memory_text = _scan_text_file("docs/ANA_MEMORY.md")
    agent_lessons_text = _scan_memory_file("agent_coach_lessons.jsonl")
    conversation_learning_text = _scan_memory_file("conversation_learning.jsonl")
    routines = _extract_commands(
        performance_text,
        benchmark_text,
        test_text,
        changelog_text,
        ana_memory_text,
        agent_lessons_text,
        conversation_learning_text,
    )
    overall_success = baseline.get("health_score", 0) == 100 and baseline.get("warnings", 0) == 0 and baseline.get("parse_error_count", 0) == 0 and len(routines) > 0

    report = {
        "schema": LEVEL_SCHEMA,
        "generated_at": utc_now(),
        "engine": ENGINE_NAME,
        "workspace_root": str(WORKSPACE_ROOT),
        "dry_run": dry_run,
        "memory_snapshot": memory_snapshot,
        "routines": routines,
        "sources": {
            "docs_performance_log_bytes": len(performance_text),
            "docs_benchmarks_bytes": len(benchmark_text),
            "docs_test_report_bytes": len(test_text),
            "docs_changelog_bytes": len(changelog_text),
            "docs_ana_memory_bytes": len(ana_memory_text),
            "agent_lessons_bytes": len(agent_lessons_text),
            "conversation_learning_bytes": len(conversation_learning_text),
        },
        "summary": {
            "routine_count": len(routines),
            "command_pattern_count": sum(1 for routine in routines if routine["type"] == "command"),
            "cycle_pattern_count": sum(1 for routine in routines if routine["type"] == "cycle"),
            "tool_pattern_count": sum(1 for routine in routines if routine["type"] == "tool"),
            "health_score": baseline.get("health_score", 0),
            "warnings": baseline.get("warnings", 0),
            "parse_error_count": baseline.get("parse_error_count", 0),
            "overall_success": overall_success,
        },
        "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
        "report_path": str(REPORT_PATH),
    }
    write_json(REPORT_PATH, report)
    level_report = build_level_report(
        os_level=LEVEL,
        engine=ENGINE_NAME,
        status="PASS" if overall_success else "WARN",
        next_level="OS-19",
        summary=report["summary"],
        payload=report,
        dry_run=dry_run,
        memory_snapshot=memory_snapshot,
    )
    write_level_report(LEVEL, level_report)
    return report


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ANA MAX OS-18 Habit & Routine Engine")
    parser.add_argument("--cycle", action="store_true", help="Run the habit analysis cycle.")
    parser.add_argument("--dry-run", action="store_true", help="Keep the analysis read-only.")
    return parser


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()
    dry_run = args.dry_run or not args.cycle
    result = run_cycle(dry_run=dry_run)
    emit_raw_json(result)
    return 0 if result.get("summary", {}).get("overall_success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
