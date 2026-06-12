#!/usr/bin/env python3
"""
ANA MAX OS-3 Self-Evolution Engine (Procedural + Subprocess Version)

This orchestrator is fully compatible with OS-3 procedural engines.
It does NOT import engine classes. It executes each engine as a module
via subprocess, captures JSON output, and writes evolution artifacts.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List

try:
    from ANA_MAX.self_optimization import memory_context
except Exception:
    memory_context = None

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

WORKSPACE_ROOT = ROOT
DOCS_DIR = WORKSPACE_ROOT / "docs"
ROADMAP = DOCS_DIR / "ROADMAP.md"
ARTIFACT_DIR = WORKSPACE_ROOT / "ANA_MAX" / "memory"
EVOLUTION_REPORT = ARTIFACT_DIR / "evolution_report.json"

OS4_REPORTS: Dict[str, Path] = {
    "self_reasoning": ARTIFACT_DIR / "self_reasoning_report.json",
    "toolchain_manifest": ARTIFACT_DIR / "toolchain_manifest.json",
    "daemon_report": ARTIFACT_DIR / "os4_daemon_report.json",
    "knowledge_graph_history": ARTIFACT_DIR / "knowledge_graph_history",
}

OS5_REPORTS: Dict[str, Path] = {
    "self_goals": ARTIFACT_DIR / "self_goals.json",
    "evolution_strategy": ARTIFACT_DIR / "evolution_strategy.json",
    "evolution_strategy_history": ARTIFACT_DIR / "evolution_strategy_history",
}

OS6_REPORTS: Dict[str, Path] = {
    "meta_adaptation_history": ARTIFACT_DIR / "evolution_strategy_history",
}

OS7_REPORTS: Dict[str, Path] = {
    "agent_registry": ARTIFACT_DIR / "agent_registry.json",
}

OS8_REPORTS: Dict[str, Path] = {
    "architecture_proposals": ARTIFACT_DIR / "architecture_proposals.json",
}

OS9_REPORTS: Dict[str, Path] = {
    "system_policies": ARTIFACT_DIR / "system_policies.json",
}

OS10_REPORTS: Dict[str, Path] = {
    "enterprise_policies": ARTIFACT_DIR / "enterprise_policies.json",
}

CONSISTENCY_REPORT = ARTIFACT_DIR / "self_consistency_report.json"
MEMORY_SYSTEM_REPORT = ARTIFACT_DIR / "memory_system_report.json"

RAW_START = "::OS3_RAW_OUTPUT_START::"
RAW_END = "::OS3_RAW_OUTPUT_END::"

ENGINE_COMMANDS: Dict[str, tuple[str, List[str]]] = {
    "profiling": ("ANA_MAX.self_optimization.self_profiling_engine", ["--cycle"]),
    "structuring": ("ANA_MAX.self_optimization.self_structuring_engine", ["--cycle", "--dry-run"]),
    "skills": ("ANA_MAX.self_optimization.self_skills_engine", ["--cycle"]),
    "healing": ("ANA_MAX.self_optimization.self_healing_engine", ["--cycle", "--dry-run"]),
    "knowledge_graph": ("ANA_MAX.self_optimization.knowledge_graph_engine", ["--cycle"]),
}

HEALTH_ENGINE_COMMANDS: Dict[str, tuple[str, List[str]]] = {
    "profiling": ("ANA_MAX.self_optimization.self_profiling_engine", ["--cycle", "--dry-run"]),
    "structuring": ("ANA_MAX.self_optimization.self_structuring_engine", ["--cycle", "--dry-run"]),
    "skills": ("ANA_MAX.self_optimization.self_skills_engine", ["--cycle", "--dry-run"]),
    "healing": ("ANA_MAX.self_optimization.self_healing_engine", ["--cycle", "--dry-run"]),
    "evaluation": ("ANA_MAX.self_optimization.self_evaluation_engine", ["--cycle", "--dry-run"]),
}


def _clean_text(value: Any, limit: int = 4000) -> str:
    text = "" if value is None else str(value)
    return text.replace("TOOL " "END", "[SUPPRESSED_MARKER]")[:limit]


def _extract_json_output(stdout: str) -> Dict[str, Any] | None:
    if RAW_START in stdout and RAW_END in stdout:
        raw = stdout.split(RAW_START, 1)[1].split(RAW_END, 1)[0].strip()
        return json.loads(raw)
    stripped = stdout.strip()
    if not stripped:
        return None
    loaded = json.loads(stripped)
    return loaded if isinstance(loaded, dict) else {"value": loaded}


def _print_raw_json(result: Dict[str, Any]) -> None:
    print(RAW_START)
    print(json.dumps(result, indent=2, default=str, ensure_ascii=False))
    print(RAW_END)


def _load_json_file(path: Path) -> Dict[str, Any]:
    if not path.exists() or path.is_dir():
        return {}
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"error": str(exc), "path": str(path)}
    return loaded if isinstance(loaded, dict) else {"value": loaded}


def _load_memory_context() -> Dict[str, Any]:
    if memory_context is None:
        return {"schema": "ana.memory.context.v1", "error": "module_missing"}
    try:
        return memory_context.build_memory_context()
    except Exception:
        return {"schema": "ana.memory.context.v1", "error": "failed_to_load"}


def _memory_context_summary(context: Dict[str, Any]) -> Dict[str, Any]:
    if memory_context is not None:
        try:
            return memory_context.memory_context_summary(context)
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


def _priority_rank(priority: str) -> int:
    return {
        "critical": 0,
        "high": 1,
        "medium": 2,
        "low": 3,
    }.get(priority, 4)


def _memory_phase_order(memory_snapshot: Dict[str, Any]) -> List[str]:
    preferences = memory_snapshot.get("preferences", {}) if isinstance(memory_snapshot.get("preferences", {}), dict) else {}
    consistency = memory_snapshot.get("consistency", {}) if isinstance(memory_snapshot.get("consistency", {}), dict) else {}
    contradictions = int(consistency.get("contradiction_count", 0) or 0)
    regressions = int(consistency.get("regression_count", 0) or 0)
    stability_priority = str(preferences.get("stability_priority", "high"))
    evolution_aggressiveness = str(preferences.get("evolution_aggressiveness", "low"))

    if contradictions > 0 or regressions > 0:
        return [
            "profiling",
            "structuring",
            "healing",
            "evaluation",
            "reasoning",
            "goals",
            "strategy_refresh",
            "knowledge_graph",
            "toolchain_discovery",
            "daemon_loop",
        ]
    if stability_priority == "high" and evolution_aggressiveness != "high":
        return [
            "profiling",
            "structuring",
            "healing",
            "skills",
            "evaluation",
            "reasoning",
            "goals",
            "strategy_refresh",
            "knowledge_graph",
            "toolchain_discovery",
            "daemon_loop",
        ]
    return [
        "profiling",
        "skills",
        "structuring",
        "healing",
        "evaluation",
        "reasoning",
        "goals",
        "strategy_refresh",
        "knowledge_graph",
        "toolchain_discovery",
        "daemon_loop",
    ]


def _order_plan_steps(steps: List[Dict[str, Any]], memory_snapshot: Dict[str, Any]) -> List[Dict[str, Any]]:
    phase_order = {phase: index for index, phase in enumerate(_memory_phase_order(memory_snapshot))}
    return sorted(
        steps,
        key=lambda step: (
            _priority_rank(str(step.get("priority", "medium"))),
            phase_order.get(str(step.get("phase", "")), 99),
            str(step.get("phase", "")),
        ),
    )


def _run_engine(module: str, args: List[str], timeout_seconds: int = 120) -> Dict[str, Any]:
    """Run an OS-3 engine via subprocess and capture JSON output."""
    cmd = [sys.executable, "-m", module] + args
    started = time.perf_counter()
    try:
        completed = subprocess.run(
            cmd,
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "error": "engine_timeout",
            "module": module,
            "args": args,
            "timeout_seconds": timeout_seconds,
            "stdout_excerpt": _clean_text(exc.stdout),
            "stderr_excerpt": _clean_text(exc.stderr),
        }

    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    try:
        result = _extract_json_output(completed.stdout)
    except Exception as exc:
        return {
            "error": "invalid_json_output",
            "module": module,
            "args": args,
            "returncode": completed.returncode,
            "elapsed_ms": elapsed_ms,
            "parse_error": str(exc),
            "stdout_excerpt": _clean_text(completed.stdout),
            "stderr_excerpt": _clean_text(completed.stderr),
        }

    if result is None:
        return {
            "error": "no_json_output",
            "module": module,
            "args": args,
            "returncode": completed.returncode,
            "elapsed_ms": elapsed_ms,
            "stdout_excerpt": _clean_text(completed.stdout),
            "stderr_excerpt": _clean_text(completed.stderr),
        }

    result["_runner"] = {
        "module": module,
        "args": args,
        "returncode": completed.returncode,
        "elapsed_ms": elapsed_ms,
    }
    if completed.returncode != 0:
        result.setdefault("error", "engine_returncode_nonzero")
        result["_runner"]["stderr_excerpt"] = _clean_text(completed.stderr)
    return result


@dataclass
class EvolutionStep:
    phase: str
    action: str
    result: Dict[str, Any]
    timestamp: str
    success: bool


@dataclass
class EvolutionPlan:
    timestamp: str
    horizon_hours: int
    steps: List[Dict[str, Any]]
    priorities: List[str]
    estimated_completion: str
    memory_snapshot: Dict[str, Any] | None = None


class SelfEvolutionEngine:
    """Coordinates OS-3 procedural engines via subprocess."""

    def __init__(
        self,
        *,
        workspace_root: Path = WORKSPACE_ROOT,
        roadmap: Path = ROADMAP,
        report_path: Path = EVOLUTION_REPORT,
    ) -> None:
        self.workspace_root = workspace_root.resolve()
        self.roadmap = roadmap
        self.report_path = report_path
        self.evolution_history: List[EvolutionStep] = []
        self.current_plan: EvolutionPlan | None = None

        self.report_path.parent.mkdir(parents=True, exist_ok=True)
        self.roadmap.parent.mkdir(parents=True, exist_ok=True)

    def run_cycle(self, *, os5: bool = False) -> Dict[str, Any]:
        memory_snapshot = self.memory_snapshot()
        cycle = {
            "schema": "ana.os3.self_evolution.run_cycle.v1",
            "mode": "sequential",
            "timestamp": datetime.now().isoformat(),
            "workspace_root": str(self.workspace_root),
            "phases": {},
            "overall_success": True,
            "artifacts": {
                "evolution_report": str(self.report_path),
                "roadmap": str(self.roadmap),
                "os5": str(OS5_REPORTS["self_goals"]),
                "strategy": str(OS5_REPORTS["evolution_strategy"]),
            },
            "additive_layers": self.additive_snapshot(),
            "memory_snapshot": memory_snapshot,
        }

        self._run_phase(
            cycle,
            "structuring",
            lambda: _run_engine(
                "ANA_MAX.self_optimization.self_structuring_engine",
                ["--cycle", "--dry-run"],
            ),
        )

        self._run_phase(
            cycle,
            "skills",
            lambda: _run_engine(
                "ANA_MAX.self_optimization.self_skills_engine",
                ["--cycle"],
            ),
        )

        if os5:
            self._run_phase(
                cycle,
                "reasoning",
                lambda: _run_engine(
                    "ANA_MAX.self_optimization.self_reasoning_engine",
                    ["--cycle"],
                ),
            )
            self._run_phase(
                cycle,
                "goals",
                lambda: _run_engine(
                    "ANA_MAX.self_optimization.self_goals_engine",
                    ["--cycle"],
                ),
            )
            self._run_phase(
                cycle,
                "strategy_refresh",
                lambda: _run_engine(
                    "ANA_MAX.self_optimization.self_goals_engine",
                    ["--cycle", "--dry-run"],
                ),
            )

        self._run_phase(
            cycle,
            "knowledge_graph",
            lambda: _run_engine(
                "ANA_MAX.self_optimization.knowledge_graph_engine",
                ["--cycle"],
            ),
        )

        if os5:
            self._run_phase(
                cycle,
                "toolchain_discovery",
                lambda: _run_engine(
                    "ANA_MAX.tools.toolchain_discovery",
                    ["--cycle"],
                ),
            )

        try:
            plan = self.plan_next_steps(horizon_hours=24, memory_snapshot=memory_snapshot)
            self.current_plan = plan
            cycle["phases"]["planning"] = asdict(plan)
        except Exception as exc:
            cycle["phases"]["planning"] = {"error": str(exc)}
            cycle["overall_success"] = False

        self.update_roadmap(cycle)
        self._write_report(cycle)
        return cycle

    def fast_parallel_cycle(
        self,
        *,
        timeout_seconds: int = 120,
        max_workers: int | None = None,
        os5: bool = False,
    ) -> Dict[str, Any]:
        """Run independent OS-3 engines concurrently, then evaluate once."""
        memory_snapshot = self.memory_snapshot()
        commands = ENGINE_COMMANDS if not os5 else {
            "profiling": ENGINE_COMMANDS["profiling"],
            "structuring": ENGINE_COMMANDS["structuring"],
            "skills": ENGINE_COMMANDS["skills"],
            "healing": ENGINE_COMMANDS["healing"],
        }
        workers = max_workers or min(len(commands), 5)
        cycle: Dict[str, Any] = {
            "schema": "ana.os3.self_evolution.fast_parallel.v1",
            "mode": "fast_parallel",
            "timestamp": datetime.now().isoformat(),
            "workspace_root": str(self.workspace_root),
            "timeout_seconds": timeout_seconds,
            "max_workers": workers,
            "phases": {},
            "overall_success": True,
            "artifacts": {
                "evolution_report": str(self.report_path),
                "roadmap": str(self.roadmap),
                "os5": str(OS5_REPORTS["self_goals"]),
                "strategy": str(OS5_REPORTS["evolution_strategy"]),
            },
            "additive_layers": self.additive_snapshot(),
            "memory_snapshot": memory_snapshot,
        }

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(_run_engine, module, args, timeout_seconds): phase
                for phase, (module, args) in commands.items()
            }
            for future in as_completed(futures):
                phase = futures[future]
                try:
                    result = future.result()
                except Exception as exc:
                    result = {"error": str(exc)}
                cycle["phases"][phase] = result
                success = isinstance(result, dict) and "error" not in result
                cycle["overall_success"] = cycle["overall_success"] and success
                self.evolution_history.append(
                    EvolutionStep(
                        phase=phase,
                        action="fast_parallel_cycle",
                        result=result,
                        timestamp=datetime.now().isoformat(),
                        success=success,
                    )
                )

        evaluation = _run_engine(
            "ANA_MAX.self_optimization.self_evaluation_engine",
            ["--cycle"],
            timeout_seconds,
        )
        cycle["phases"]["evaluation"] = evaluation
        cycle["overall_success"] = cycle["overall_success"] and "error" not in evaluation

        if os5:
            for phase_name, module, module_args in [
                (
                    "reasoning",
                    "ANA_MAX.self_optimization.self_reasoning_engine",
                    ["--cycle"],
                ),
                (
                    "goals",
                    "ANA_MAX.self_optimization.self_goals_engine",
                    ["--cycle"],
                ),
                (
                    "strategy_refresh",
                    "ANA_MAX.self_optimization.self_goals_engine",
                    ["--cycle", "--dry-run"],
                ),
                (
                    "knowledge_graph",
                    "ANA_MAX.self_optimization.knowledge_graph_engine",
                    ["--cycle"],
                ),
                (
                    "toolchain_discovery",
                    "ANA_MAX.tools.toolchain_discovery",
                    ["--cycle"],
                ),
            ]:
                result = _run_engine(module, module_args, timeout_seconds)
                cycle["phases"][phase_name] = result
                cycle["overall_success"] = cycle["overall_success"] and "error" not in result

        try:
            plan = self.plan_next_steps(horizon_hours=24, memory_snapshot=memory_snapshot)
            self.current_plan = plan
            cycle["phases"]["planning"] = asdict(plan)
        except Exception as exc:
            cycle["phases"]["planning"] = {"error": str(exc)}
            cycle["overall_success"] = False

        self.update_roadmap(cycle)
        self._write_report(cycle)
        return cycle

    def health_snapshot(self) -> Dict[str, Any]:
        """Read-only local health snapshot for continuous monitoring."""
        package_checks = {
            "ANA_MAX_init": (self.workspace_root / "ANA_MAX" / "__init__.py").exists(),
            "self_optimization_init": (
                self.workspace_root / "ANA_MAX" / "self_optimization" / "__init__.py"
            ).exists(),
            "cascade_init": (self.workspace_root / "cascade_integration" / "__init__.py").exists(),
        }
        disk = shutil.disk_usage(self.workspace_root)
        report_exists = self.report_path.exists()
        last_report: Dict[str, Any] = {}
        if report_exists:
            try:
                last_report = json.loads(self.report_path.read_text(encoding="utf-8"))
            except Exception as exc:
                last_report = {"error": f"invalid_report_json: {exc}"}

        warnings: List[str] = []
        if not all(package_checks.values()):
            warnings.append("missing_package_marker")
        if disk.free < 1024 * 1024 * 1024:
            warnings.append("low_disk_space_under_1gb")
        if isinstance(last_report, dict) and last_report.get("overall_success") is False:
            warnings.append("last_evolution_cycle_failed")

        return {
            "schema": "ana.os3.self_evolution.health_snapshot.v1",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "workspace_root": str(self.workspace_root),
            "status": "healthy" if not warnings else "warning",
            "warnings": warnings,
            "package_checks": package_checks,
            "disk": {
                "total_gb": round(disk.total / (1024 ** 3), 2),
                "used_gb": round(disk.used / (1024 ** 3), 2),
                "free_gb": round(disk.free / (1024 ** 3), 2),
            },
            "last_report": {
                "exists": report_exists,
                "schema": last_report.get("schema") if isinstance(last_report, dict) else None,
                "overall_success": last_report.get("overall_success")
                if isinstance(last_report, dict)
                else None,
            },
            "os4": self.os4_snapshot(),
            "additive": self.additive_snapshot(),
            "memory_snapshot": self.memory_snapshot(),
        }

    def os4_snapshot(self) -> Dict[str, Any]:
        reports: Dict[str, Any] = {}
        for name, path in OS4_REPORTS.items():
            if path.is_dir():
                reports[name] = {
                    "exists": True,
                    "path": str(path),
                    "snapshots": len(list(path.glob("*.json"))),
                }
            else:
                reports[name] = {
                    "exists": path.exists(),
                    "path": str(path),
                    "bytes": path.stat().st_size if path.exists() else 0,
                }
        ready = all(
            reports[name]["exists"]
            for name in ("self_reasoning", "toolchain_manifest", "knowledge_graph_history")
        )
        return {
            "schema": "ana.os4.evolution_snapshot.v1",
            "ready": ready,
            "reports": reports,
        }

    def additive_snapshot(self) -> Dict[str, Any]:
        layers: Dict[str, Any] = {}
        layer_maps = {
            "os5": OS5_REPORTS,
            "os6": OS6_REPORTS,
            "os7": OS7_REPORTS,
            "os8": OS8_REPORTS,
            "os9": OS9_REPORTS,
            "os10": OS10_REPORTS,
        }
        for layer, reports in layer_maps.items():
            layer_reports: Dict[str, Any] = {}
            for name, path in reports.items():
                if path.is_dir():
                    layer_reports[name] = {
                        "exists": True,
                        "path": str(path),
                        "snapshots": len(list(path.glob("*.json"))),
                    }
                else:
                    layer_reports[name] = {
                        "exists": path.exists(),
                        "path": str(path),
                        "bytes": path.stat().st_size if path.exists() else 0,
                    }
            layers[layer] = {
                "ready": all(item.get("exists") for item in layer_reports.values()) if layer_reports else False,
                "reports": layer_reports,
            }
        return {
            "schema": "ana.osX.additive_snapshot.v1",
            "layers": layers,
            "memory": self.memory_snapshot(),
        }

    def memory_snapshot(self) -> Dict[str, Any]:
        context = _load_memory_context()
        consistency = _load_json_file(CONSISTENCY_REPORT)
        system_report = _load_json_file(MEMORY_SYSTEM_REPORT)
        context_summary = _memory_context_summary(context)
        phase_order_hint = _memory_phase_order(
            {
                "preferences": context_summary.get("preferences", {}),
                "consistency": {
                    "contradiction_count": len(consistency.get("contradictions", [])) if isinstance(consistency.get("contradictions", []), list) else 0,
                    "regression_count": len(consistency.get("regressions", [])) if isinstance(consistency.get("regressions", []), list) else 0,
                },
            }
        )
        return {
            "schema": "ana.memory.evolution_snapshot.v1",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "core_memory_present": context_summary.get("core_memory_present", False),
            "core_memory_schema_ok": context_summary.get("core_memory_schema_ok", False),
            "history_length": context_summary.get("history_length", 0),
            "preferences": context_summary.get("preferences", {}),
            "patterns": context_summary.get("patterns", {}),
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
            "phase_order_hint": phase_order_hint,
        }

    def health_monitor(
        self,
        *,
        interval_seconds: int = 60,
        max_cycles: int = 3,
        timeout_seconds: int = 120,
    ) -> Dict[str, Any]:
        """Run bounded read-only health checks; max_cycles=0 means until interrupted."""
        report: Dict[str, Any] = {
            "schema": "ana.os3.self_evolution.health_monitor.v1",
            "mode": "health_monitor",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "interval_seconds": interval_seconds,
            "max_cycles": max_cycles,
            "cycles": [],
            "overall_success": True,
        }
        count = 0
        try:
            while max_cycles == 0 or count < max_cycles:
                memory_snapshot = self.memory_snapshot()
                snapshot = self.health_snapshot()
                evaluation = _run_engine(
                    *HEALTH_ENGINE_COMMANDS["evaluation"],
                    timeout_seconds=timeout_seconds,
                )
                status = snapshot["status"] == "healthy" and "error" not in evaluation
                report["cycles"].append(
                    {
                        "index": count + 1,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "memory_snapshot": memory_snapshot,
                        "snapshot": snapshot,
                        "evaluation": evaluation,
                        "success": status,
                    }
                )
                report["overall_success"] = report["overall_success"] and status
                self._write_report(report)
                count += 1
                if max_cycles != 0 and count >= max_cycles:
                    break
                time.sleep(max(1, interval_seconds))
        except KeyboardInterrupt:
            report["stopped"] = "keyboard_interrupt"

        report["finished_at"] = datetime.now(timezone.utc).isoformat()
        report["memory_snapshot"] = self.memory_snapshot()
        self._write_report(report)
        return report

    def auto_evolution(
        self,
        *,
        interval_seconds: int = 300,
        max_cycles: int = 3,
        fast_parallel: bool = True,
        timeout_seconds: int = 120,
        os5: bool = False,
    ) -> Dict[str, Any]:
        """Run periodic bounded evolution cycles; max_cycles=0 means until interrupted."""
        report: Dict[str, Any] = {
            "schema": "ana.os3.self_evolution.auto_evolution.v1",
            "mode": "auto_evolution",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "interval_seconds": interval_seconds,
            "max_cycles": max_cycles,
            "fast_parallel": fast_parallel,
            "cycles": [],
            "overall_success": True,
        }
        count = 0
        try:
            while max_cycles == 0 or count < max_cycles:
                memory_snapshot = self.memory_snapshot()
                cycle = (
                    self.fast_parallel_cycle(timeout_seconds=timeout_seconds, os5=os5)
                    if fast_parallel
                    else self.run_cycle(os5=os5)
                )
                report["cycles"].append(
                    {
                        "index": count + 1,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "memory_snapshot": memory_snapshot,
                        "mode": cycle.get("mode"),
                        "overall_success": cycle.get("overall_success"),
                        "phase_count": len(cycle.get("phases", {})),
                    }
                )
                report["overall_success"] = report["overall_success"] and bool(
                    cycle.get("overall_success")
                )
                self._write_report(report)
                count += 1
                if max_cycles != 0 and count >= max_cycles:
                    break
                time.sleep(max(1, interval_seconds))
        except KeyboardInterrupt:
            report["stopped"] = "keyboard_interrupt"

        report["finished_at"] = datetime.now(timezone.utc).isoformat()
        report["memory_snapshot"] = self.memory_snapshot()
        self._write_report(report)
        return report

    def coordinate_modules(self) -> Dict[str, Any]:
        return {
            "schema": "ana.os3.self_evolution.coordinate.v1",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "safe_default": "sequential_cycle",
            "recommended_order": [
                "health_monitor",
                "fast_parallel",
                "auto_evolution",
            ],
            "parallel_engines": sorted(ENGINE_COMMANDS),
            "health_engines": sorted(HEALTH_ENGINE_COMMANDS),
            "notes": [
                "structuring and healing stay dry-run inside automated modes",
                "github_pattern_extractor is excluded because it requires an explicit repo path",
                "max_cycles=0 is explicit continuous mode",
                "os5 mode adds reasoning, goals, strategy refresh, knowledge graph, and toolchain phases",
            ],
            "health_snapshot": self.health_snapshot(),
            "os4_snapshot": self.os4_snapshot(),
            "additive_snapshot": self.additive_snapshot(),
            "memory_snapshot": self.memory_snapshot(),
        }

    def _run_phase(self, cycle: Dict[str, Any], phase: str, callback) -> None:
        try:
            result = callback()
            cycle["phases"][phase] = result
            self.evolution_history.append(
                EvolutionStep(
                    phase=phase,
                    action="run_cycle",
                    result=result,
                    timestamp=datetime.now().isoformat(),
                    success="error" not in result,
                )
            )
        except Exception as exc:
            error = {"error": str(exc)}
            cycle["phases"][phase] = error
            cycle["overall_success"] = False
            self.evolution_history.append(
                EvolutionStep(
                    phase=phase,
                    action="run_cycle",
                    result=error,
                    timestamp=datetime.now().isoformat(),
                    success=False,
                )
            )

    def plan_next_steps(
        self,
        horizon_hours: int = 24,
        *,
        memory_snapshot: Dict[str, Any] | None = None,
    ) -> EvolutionPlan:
        recent_failures = [s for s in self.evolution_history[-10:] if not s.success]
        steps: List[Dict[str, Any]] = []
        memory_snapshot = memory_snapshot or self.memory_snapshot()

        if recent_failures:
            for f in recent_failures:
                steps.append(
                    {
                        "phase": f.phase,
                        "action": "repair_and_retry",
                        "priority": "critical",
                        "estimated_minutes": 10,
                        "context": f.result,
                    }
                )
            if int(memory_snapshot.get("consistency", {}).get("contradiction_count", 0) or 0) > 0 or int(memory_snapshot.get("consistency", {}).get("regression_count", 0) or 0) > 0:
                steps.append(
                    {
                        "phase": "memory_consistency",
                        "action": "reconcile_core_memory",
                        "priority": "high",
                        "estimated_minutes": 10,
                        "context": memory_snapshot.get("consistency", {}),
                    }
                )
            steps = _order_plan_steps(steps, memory_snapshot)
            priorities = []
            for step in steps:
                if step["phase"] not in priorities:
                    priorities.append(step["phase"])
        else:
            steps = [
                {"phase": "structuring", "action": "dry_run_cycle", "priority": "high", "estimated_minutes": 5},
                {"phase": "skills", "action": "manifest_refresh", "priority": "medium", "estimated_minutes": 5},
                {"phase": "knowledge_graph", "action": "graph_refresh", "priority": "medium", "estimated_minutes": 10},
            ]
            if int(memory_snapshot.get("consistency", {}).get("contradiction_count", 0) or 0) > 0 or int(memory_snapshot.get("consistency", {}).get("regression_count", 0) or 0) > 0:
                steps.append(
                    {
                        "phase": "memory_consistency",
                        "action": "reconcile_core_memory",
                        "priority": "high",
                        "estimated_minutes": 10,
                        "context": memory_snapshot.get("consistency", {}),
                    }
                )
            steps = _order_plan_steps(steps, memory_snapshot)
            priorities = []
            for step in steps:
                if step["phase"] not in priorities:
                    priorities.append(step["phase"])

        total_minutes = sum(int(s.get("estimated_minutes", 5)) for s in steps)

        return EvolutionPlan(
            timestamp=datetime.now().isoformat(),
            horizon_hours=horizon_hours,
            steps=steps,
            priorities=priorities,
            estimated_completion=(datetime.now() + timedelta(minutes=total_minutes)).isoformat(),
            memory_snapshot=memory_snapshot,
        )

    def update_roadmap(self, cycle: Dict[str, Any]) -> None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        lines = [
            f"\n## Evolution Cycle - {timestamp}",
            "",
            f"- Overall Success: {cycle['overall_success']}",
            f"- Phases Executed: {len(cycle['phases'])}",
            "",
        ]

        for phase, result in cycle["phases"].items():
            status = "FAILED" if isinstance(result, dict) and "error" in result else "SUCCESS"
            detail = f" - {result['error']}" if status == "FAILED" else ""
            lines.append(f"- **{phase}**: {status}{detail}")

        if self.current_plan:
            lines.extend(["", "### Next Steps (24h horizon)", ""])
            for step in self.current_plan.steps:
                lines.append(f"- **{step['phase']}**: {step['action']} (priority: {step['priority']})")

        lines.append("")
        with self.roadmap.open("a", encoding="utf-8") as f:
            f.write("\n".join(lines))

    def _write_report(self, cycle: Dict[str, Any]) -> None:
        self.report_path.write_text(json.dumps(cycle, indent=2, default=str), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="ANA MAX OS-3 Self-Evolution Engine")
    parser.add_argument("--cycle", action="store_true")
    parser.add_argument("--fast-parallel", action="store_true")
    parser.add_argument("--auto-evolution", action="store_true")
    parser.add_argument("--health-monitor", action="store_true")
    parser.add_argument("--plan", action="store_true")
    parser.add_argument("--coordinate", action="store_true")
    parser.add_argument("--horizon", type=int, default=24)
    parser.add_argument("--interval", type=int, default=300)
    parser.add_argument("--max-cycles", type=int, default=3)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--max-workers", type=int, default=0)
    parser.add_argument("--sequential", action="store_true")
    parser.add_argument("--os5", action="store_true")
    args = parser.parse_args()

    engine = SelfEvolutionEngine()

    if args.plan:
        _print_raw_json(asdict(engine.plan_next_steps(horizon_hours=args.horizon)))
        return 0

    if args.coordinate:
        _print_raw_json(engine.coordinate_modules())
        return 0

    if args.health_monitor:
        _print_raw_json(
            engine.health_monitor(
                interval_seconds=args.interval,
                max_cycles=args.max_cycles,
                timeout_seconds=args.timeout,
            )
        )
        return 0

    if args.auto_evolution:
        _print_raw_json(
            engine.auto_evolution(
                interval_seconds=args.interval,
                max_cycles=args.max_cycles,
                fast_parallel=not args.sequential,
                timeout_seconds=args.timeout,
                os5=args.os5,
            )
        )
        return 0

    if args.fast_parallel:
        _print_raw_json(
            engine.fast_parallel_cycle(
                timeout_seconds=args.timeout,
                max_workers=args.max_workers or None,
                os5=args.os5,
            )
        )
        return 0

    _print_raw_json(engine.run_cycle(os5=args.os5))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
