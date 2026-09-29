#!/usr/bin/env python3
"""ANA MAX OS-4 bounded daemon runner."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ANA_MAX.self_optimization.os3_common import RAW_END, RAW_START, print_raw_json

try:
    from ANA_MAX.self_optimization import memory_context
except Exception:
    memory_context = None

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = PROJECT_ROOT / "docs"
MEMORY_DIR = PROJECT_ROOT / "ANA_MAX" / "memory"
DAEMON_LOG = DOCS_DIR / "OS4_DAEMON_LOG.md"
DAEMON_REPORT = MEMORY_DIR / "os4_daemon_report.json"

PHASES: list[tuple[str, str, list[str]]] = [
    ("profiling", "ANA_MAX.self_optimization.self_profiling_engine", ["--cycle"]),
    ("skills", "ANA_MAX.self_optimization.self_skills_engine", ["--cycle"]),
    ("structuring", "ANA_MAX.self_optimization.self_structuring_engine", ["--cycle", "--dry-run"]),
    ("healing", "ANA_MAX.self_optimization.self_healing_engine", ["--cycle", "--dry-run"]),
    ("evaluation", "ANA_MAX.self_optimization.self_evaluation_engine", ["--cycle"]),
    ("reasoning", "ANA_MAX.self_optimization.self_reasoning_engine", ["--cycle"]),
    ("goals", "ANA_MAX.self_optimization.self_goals_engine", ["--cycle"]),
    ("knowledge_graph", "ANA_MAX.self_optimization.knowledge_graph_engine", ["--cycle"]),
    ("toolchain_discovery", "ANA_MAX.tools.toolchain_discovery", ["--cycle"]),
]


def _memory_section() -> dict[str, Any]:
    if memory_context is None:
        return {"schema": "ana.memory.context.v1", "error": "module_missing"}
    try:
        context = memory_context.build_memory_context()
    except Exception:
        return {"schema": "ana.memory.context.v1", "error": "failed_to_load"}
    try:
        return memory_context.memory_context_summary(context)
    except Exception:
        return {
            "schema": "ana.memory.context.v1",
            "core_memory_present": bool(context.get("core_memory_present", False)),
            "core_memory_schema_ok": bool(context.get("core_memory_schema_ok", False)),
            "history_length": int(context.get("history_length", 0) or 0),
            "preferences": context.get("preferences", {}),
            "patterns": context.get("patterns", {}),
            "long_term_keys": sorted((context.get("long_term") or {}).keys()),
        }


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _extract_payload(stdout: str) -> dict[str, Any]:
    text = stdout.strip()
    if RAW_START in text and RAW_END in text:
        text = text.split(RAW_START, 1)[1].split(RAW_END, 1)[0].strip()
    if not text:
        return {"error": "empty_stdout"}
    data = json.loads(text)
    return data if isinstance(data, dict) else {"value": data}


def _run_phase(name: str, module: str, args: list[str], timeout_seconds: int) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        completed = subprocess.run(
            [sys.executable, "-m", module, *args],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "name": name,
            "success": False,
            "error": "timeout",
            "timeout_seconds": timeout_seconds,
            "stdout_excerpt": str(exc.stdout or "")[:1200],
            "stderr_excerpt": str(exc.stderr or "")[:1200],
        }

    try:
        payload = _extract_payload(completed.stdout)
    except Exception as exc:
        payload = {
            "error": "invalid_json_output",
            "parse_error": str(exc),
            "stdout_excerpt": completed.stdout[:1200],
        }

    return {
        "name": name,
        "success": completed.returncode == 0 and "error" not in payload,
        "returncode": completed.returncode,
        "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
        "module": module,
        "args": args,
        "payload": payload,
        "stderr_excerpt": completed.stderr[:1200] if completed.returncode else "",
    }


def _append_heartbeat(cycle: dict[str, Any], *, dry_run: bool) -> None:
    if dry_run:
        return
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    summary = cycle["summary"]
    lines = [
        f"\n## OS-4 Daemon Cycle {cycle['index']} - {cycle['timestamp']}",
        "",
        f"- Success: {summary['success']}",
        f"- Completed phases: {summary['completed']} / {summary['total']}",
        f"- Failed phases: {summary['failed']}",
        f"- Duration ms: {summary['elapsed_ms']}",
        "",
    ]
    DAEMON_LOG.open("a", encoding="utf-8").write("\n".join(lines))


def _write_report(report: dict[str, Any], *, dry_run: bool) -> None:
    if dry_run:
        return
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    DAEMON_REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")


def run_daemon(
    *,
    interval_seconds: int,
    max_cycles: int,
    timeout_seconds: int,
    dry_run: bool,
) -> dict[str, Any]:
    report: dict[str, Any] = {
        "schema": "ana.os4.daemon.v1",
        "engine": "os4_daemon",
        "started_at": _utc_now(),
        "interval_seconds": interval_seconds,
        "max_cycles": max_cycles,
        "timeout_seconds": timeout_seconds,
        "dry_run": dry_run,
        "cycles": [],
        "overall_success": True,
        "report_path": str(DAEMON_REPORT),
        "log_path": str(DAEMON_LOG),
        "memory": _memory_section(),
    }

    count = 0
    try:
        while max_cycles == 0 or count < max_cycles:
            cycle_started = time.perf_counter()
            cycle_memory = _memory_section()
            phases = [
                _run_phase(name, module, args, timeout_seconds)
                for name, module, args in PHASES
            ]
            failed = sum(1 for phase in phases if not phase["success"])
            cycle = {
                "index": count + 1,
                "timestamp": _utc_now(),
                "memory": cycle_memory,
                "phases": phases,
                "summary": {
                    "success": failed == 0,
                    "total": len(phases),
                    "completed": len(phases) - failed,
                    "failed": failed,
                    "elapsed_ms": round((time.perf_counter() - cycle_started) * 1000, 2),
                },
            }
            report["cycles"].append(cycle)
            report["overall_success"] = report["overall_success"] and cycle["summary"]["success"]
            _append_heartbeat(cycle, dry_run=dry_run)
            _write_report(report, dry_run=dry_run)
            count += 1
            if max_cycles != 0 and count >= max_cycles:
                break
            time.sleep(max(1, interval_seconds))
    except KeyboardInterrupt:
        report["stopped"] = "keyboard_interrupt"

    report["finished_at"] = _utc_now()
    _write_report(report, dry_run=dry_run)
    return {
        "engine": "os4_daemon",
        "dry_run": dry_run,
        "overall_success": report["overall_success"],
        "cycles": len(report["cycles"]),
        "report_path": str(DAEMON_REPORT),
        "log_path": str(DAEMON_LOG),
        "memory": report["memory"],
        "summary": {
            "failed_cycles": sum(1 for cycle in report["cycles"] if not cycle["summary"]["success"]),
            "total_phases": sum(cycle["summary"]["total"] for cycle in report["cycles"]),
            "failed_phases": sum(cycle["summary"]["failed"] for cycle in report["cycles"]),
        },
    }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ANA MAX OS-4 Daemon")
    parser.add_argument("--interval-seconds", type=int, default=300)
    parser.add_argument("--max-cycles", type=int, default=3)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    result = run_daemon(
        interval_seconds=args.interval_seconds,
        max_cycles=args.max_cycles,
        timeout_seconds=args.timeout,
        dry_run=args.dry_run,
    )
    print_raw_json(result)
    return 0 if result.get("overall_success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
