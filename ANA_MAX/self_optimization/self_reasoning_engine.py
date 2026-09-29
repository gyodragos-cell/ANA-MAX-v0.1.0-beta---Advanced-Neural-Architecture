#!/usr/bin/env python3
"""ANA MAX OS-4 Self-Reasoning Engine.

Builds local hypotheses, strategies, and priorities from existing OS-3
artifacts. Uses only filesystem reads and standard library code.
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ANA_MAX.self_optimization.os3_common import print_raw_json

try:
    from ANA_MAX.self_optimization import memory_context
except Exception:
    memory_context = None

ENGINE_NAME = "self_reasoning_engine"
REPORT_FILENAME = "self_reasoning_report.json"

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ANA_MAX_ROOT = PROJECT_ROOT / "ANA_MAX"
MEMORY_DIR = ANA_MAX_ROOT / "memory"
DOCS_DIR = PROJECT_ROOT / "docs"
REPORT_PATH = MEMORY_DIR / REPORT_FILENAME

INPUTS = {
    "evaluation": MEMORY_DIR / "self_evaluation_report.json",
    "evolution": MEMORY_DIR / "evolution_report.json",
    "performance_log": DOCS_DIR / "PERFORMANCE_LOG.md",
    "skills": MEMORY_DIR / "self_skills_report.json",
    "graph": MEMORY_DIR / "knowledge_graph.json",
    "goals": MEMORY_DIR / "self_goals.json",
    "strategy": MEMORY_DIR / "evolution_strategy.json",
    "meta_history_dir": MEMORY_DIR / "evolution_strategy_history",
    "architecture_proposals": MEMORY_DIR / "architecture_proposals.json",
    "system_policies": MEMORY_DIR / "system_policies.json",
    "enterprise_policies": MEMORY_DIR / "enterprise_policies.json",
    "self_consistency": MEMORY_DIR / "self_consistency_report.json",
}


def _load_memory_context() -> dict[str, Any]:
    if memory_context is None:
        return {"schema": "ana.memory.context.v1", "error": "module_missing"}
    try:
        return memory_context.build_memory_context()
    except Exception:
        return {"schema": "ana.memory.context.v1", "error": "failed_to_load"}


def _memory_context_summary(context: dict[str, Any]) -> dict[str, Any]:
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


def _get_preference(context: dict[str, Any], key: str, default: Any) -> Any:
    if memory_context is not None:
        try:
            return memory_context.get_preference(context, key, default)
        except Exception:
            pass
    preferences = context.get("preferences", {}) if isinstance(context, dict) else {}
    if isinstance(preferences, dict):
        return preferences.get(key, default)
    return default


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"error": str(exc), "path": str(path)}
    return data if isinstance(data, dict) else {"value": data}


def _read_text_summary(path: Path, limit: int = 8000) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "path": str(path)}
    if path.is_dir():
        json_files = sorted(path.glob("*.json"))
        return {
            "exists": True,
            "path": str(path),
            "kind": "directory",
            "bytes": 0,
            "line_count": 0,
            "file_count": len(json_files),
            "tail": [str(item.name) for item in json_files[-10:]],
        }
    text = path.read_text(encoding="utf-8", errors="replace")
    lower = text.lower()
    return {
        "exists": True,
        "path": str(path),
        "bytes": path.stat().st_size,
        "line_count": text.count("\n") + 1,
        "pass_count": lower.count("pass"),
        "warning_count": lower.count("warning") + lower.count("warn"),
        "fail_count": lower.count("fail"),
        "tail": text[-limit:],
    }


def observe() -> dict[str, Any]:
    memory_ctx = _load_memory_context()
    return {
        "schema": "ana.os4.self_reasoning.observation.v1",
        "generated_at": _utc_now(),
        "inputs": {
            "evaluation": _read_json(INPUTS["evaluation"]),
            "evolution": _read_json(INPUTS["evolution"]),
            "skills": _read_json(INPUTS["skills"]),
            "graph": _read_json(INPUTS["graph"]),
            "goals": _read_json(INPUTS["goals"]),
            "strategy": _read_json(INPUTS["strategy"]),
            "architecture_proposals": _read_json(INPUTS["architecture_proposals"]),
            "system_policies": _read_json(INPUTS["system_policies"]),
            "enterprise_policies": _read_json(INPUTS["enterprise_policies"]),
            "self_consistency": _read_json(INPUTS["self_consistency"]),
            "performance_log": _read_text_summary(INPUTS["performance_log"]),
            "meta_history": _read_text_summary(INPUTS["meta_history_dir"]),
            "memory_context": memory_ctx,
        },
    }


def analyze(observation: dict[str, Any]) -> dict[str, Any]:
    inputs = observation["inputs"]
    evaluation = inputs.get("evaluation", {})
    evolution = inputs.get("evolution", {})
    skills = inputs.get("skills", {})
    graph = inputs.get("graph", {})
    goals = inputs.get("goals", {})
    strategy = inputs.get("strategy", {})
    architecture_proposals = inputs.get("architecture_proposals", {})
    system_policies = inputs.get("system_policies", {})
    enterprise_policies = inputs.get("enterprise_policies", {})
    self_consistency = inputs.get("self_consistency", {})
    memory_ctx = inputs.get("memory_context", {})
    performance = inputs.get("performance_log", {})
    meta_history = inputs.get("meta_history", {})
    memory_preferences = memory_ctx.get("preferences", {}) if isinstance(memory_ctx, dict) else {}
    memory_patterns = memory_ctx.get("patterns", {}) if isinstance(memory_ctx, dict) else {}
    memory_history_length = int(memory_ctx.get("history_length", 0) or 0) if isinstance(memory_ctx, dict) else 0
    memory_context_present = bool(memory_ctx.get("core_memory_present", False)) if isinstance(memory_ctx, dict) else False
    consistency_overall = bool(self_consistency.get("overall_consistent", True)) if isinstance(self_consistency, dict) else True
    consistency_contradictions = len(self_consistency.get("contradictions", [])) if isinstance(self_consistency.get("contradictions", []), list) else 0
    consistency_regressions = len(self_consistency.get("regressions", [])) if isinstance(self_consistency.get("regressions", []), list) else 0

    eval_summary = evaluation.get("summary", {})
    skills_summary = skills.get("summary", {})
    graph_meta = graph.get("metadata", {})
    goal_status = goals.get("status", {}) if isinstance(goals, dict) else {}
    strategy_priorities = strategy.get("priorities", []) if isinstance(strategy, dict) else []
    strategy_phase_order = strategy.get("phase_order", []) if isinstance(strategy, dict) else []
    architecture_list = architecture_proposals.get("proposals", []) if isinstance(architecture_proposals, dict) else []
    policies_count = len(system_policies.get("policies", [])) if isinstance(system_policies, dict) else 0
    enterprise_policy_count = len(enterprise_policies.get("policies", [])) if isinstance(enterprise_policies, dict) else 0
    meta_history_exists = bool(meta_history.get("exists"))

    hypotheses: list[dict[str, Any]] = []
    strategies: list[dict[str, Any]] = []

    health_score = int(eval_summary.get("health_score", 0) or 0)
    warning_count = int(eval_summary.get("warning_count", 0) or 0)
    parse_errors = int(skills_summary.get("parse_error_count", 0) or 0)
    graph_edges = int(graph_meta.get("total_edges", 0) or 0)
    graph_nodes = int(graph_meta.get("total_nodes", 0) or 0)
    evolution_ok = bool(evolution.get("overall_success"))

    if health_score >= 100 and warning_count == 0:
        hypotheses.append(
            {
                "id": "stable_baseline",
                "confidence": 0.98,
                "evidence": "OS-3 evaluation reports health_score=100 and warning_count=0.",
                "impact": "OS-4 can stay additive and focus on observability/evolution.",
            }
        )
        strategies.append(
            {
                "id": "protect_baseline",
                "priority": "critical",
                "mode": "guardrail",
                "action": "Run evaluation after every OS-4 cycle and fail closed on warnings.",
            }
        )
    else:
        hypotheses.append(
            {
                "id": "baseline_degraded",
                "confidence": 0.9,
                "evidence": f"health_score={health_score}, warning_count={warning_count}.",
                "impact": "Repair OS-3 before extending OS-4 behavior.",
            }
        )
        strategies.append(
            {
                "id": "repair_first",
                "priority": "critical",
                "mode": "stabilization",
                "action": "Run healing, structuring, and evaluation before daemon cycles.",
            }
        )

    if parse_errors == 0:
        hypotheses.append(
            {
                "id": "skills_parse_clean",
                "confidence": 0.95,
                "evidence": "Self-skills report has parse_error_count=0.",
                "impact": "Toolchain discovery can use static parsing safely.",
            }
        )
    else:
        strategies.append(
            {
                "id": "skills_parse_cleanup",
                "priority": "high",
                "mode": "quality",
                "action": "Resolve parse errors before expanding toolchain registration.",
            }
        )

    if graph_nodes and graph_edges:
        density = round(graph_edges / max(graph_nodes, 1), 3)
        hypotheses.append(
            {
                "id": "graph_connected",
                "confidence": 0.85,
                "evidence": f"Knowledge graph has {graph_nodes} nodes and {graph_edges} edges.",
                "impact": f"Graph density {density} supports hot/cold node analysis.",
            }
        )
        strategies.append(
            {
                "id": "adaptive_graph",
                "priority": "medium",
                "mode": "observability",
                "action": "Track graph diffs and use hot/cold nodes for refactor targeting.",
            }
        )

    if evolution_ok:
        strategies.append(
            {
                "id": "bounded_daemon_cycles",
                "priority": "high",
                "mode": "automation",
                "action": "Use bounded OS-4 daemon cycles for repeated local validation.",
            }
        )

    if isinstance(goals, dict) and goals.get("goals"):
        strategies.append(
            {
                "id": "goal_feedback_loop",
                "priority": "high",
                "mode": "goals",
                "action": "Feed the OS-5 goals report back into later orchestration layers.",
            }
        )

    if strategy_phase_order:
        strategies.append(
            {
                "id": "respect_strategy_phase_order",
                "priority": "medium",
                "mode": "strategy",
                "action": f"Use OS-5 phase order as the deterministic source of truth: {', '.join(strategy_phase_order)}.",
            }
        )

    if performance.get("fail_count", 0) > 0:
        hypotheses.append(
            {
                "id": "historical_failures_present",
                "confidence": 0.6,
                "evidence": "Performance log contains historical failure markers.",
                "impact": "Prioritize current reports over historical log wording.",
            }
        )

    if memory_context_present:
        hypotheses.append(
            {
                "id": "memory_context_loaded",
                "confidence": 0.93,
                "evidence": f"core_memory_history_length={memory_history_length}.",
                "impact": "Current reasoning can bias toward stable, bounded decisions.",
            }
        )
        if _get_preference(memory_ctx, "warnings_tolerance", "zero") == "zero":
            strategies.append(
                {
                    "id": "memory_zero_warning_bias",
                    "priority": "high",
                    "mode": "memory",
                    "action": "Prefer low-risk, bounded actions because the memory model expects zero warning tolerance.",
                }
            )
        if _get_preference(memory_ctx, "evolution_aggressiveness", "low") in {"low", "medium"}:
            strategies.append(
                {
                    "id": "memory_conservative_evolution",
                    "priority": "medium",
                    "mode": "memory",
                    "action": "Favor conservative additive changes until the memory history shows repeated stability.",
                }
            )

    if consistency_contradictions or consistency_regressions or not consistency_overall:
        strategies.append(
            {
                "id": "repair_memory_consistency",
                "priority": "critical" if consistency_contradictions else "high",
                "mode": "memory",
                "action": "Repair memory contradictions before promoting new adaptive signals.",
            }
        )

    architecture_candidates: list[dict[str, Any]] = []
    if health_score >= 100 and warning_count == 0 and graph_nodes >= 100:
        architecture_candidates.append(
            {
                "id": "layered_orchestrator_split",
                "confidence": 0.83,
                "target": "OS-8",
                "risk": "low",
                "benefit": "Make the additive ladder easier to evolve without touching OS-3/OS-4 schemas.",
            }
        )
    if parse_errors == 0 and graph_edges >= 1000:
        architecture_candidates.append(
            {
                "id": "policy_and_compliance_layers",
                "confidence": 0.78,
                "target": "OS-9/OS-10",
                "risk": "low",
                "benefit": "Separate policy composition from enterprise compliance and security checks.",
            }
        )
    if isinstance(goals, dict) and goals.get("goals"):
        architecture_candidates.append(
            {
                "id": "goal_to_policy_bridge",
                "confidence": 0.72,
                "target": "OS-9",
                "risk": "low",
                "benefit": "Bridge goals, strategy, and enterprise policies into one read-only composition flow.",
            }
        )

    meta_adaptation_hints: list[dict[str, Any]] = []
    if meta_history_exists:
        meta_adaptation_hints.append(
            {
                "id": "use_meta_history",
                "confidence": 0.91,
                "action": "Compare the latest meta-adaptation snapshot against earlier strategy history.",
            }
        )
    if isinstance(goal_status, dict) and goal_status.get("overall") == "stable":
        meta_adaptation_hints.append(
            {
                "id": "stable_goals_support_strategy",
                "confidence": 0.88,
                "action": "Keep OS-6 adaptation focused on trend detection rather than immediate repair.",
            }
        )

    priorities = sorted(
        [
            {
                "rank": 1,
                "id": "preserve_os3_health",
                "action": "Keep evaluation health_score at 100 and warning_count at 0.",
                "priority": "critical",
            },
            {
                "rank": 2,
                "id": "run_reasoning_after_evaluation",
                "action": "Run self_reasoning after every evaluation cycle.",
                "priority": "high",
            },
            {
                "rank": 3,
                "id": "refresh_adaptive_graph",
                "action": "Refresh graph history and diff after toolchain or doc changes.",
                "priority": "medium",
            },
            {
                "rank": 4,
                "id": "discover_tools_safely",
                "action": "Report candidate/dangerous tools without auto-registration.",
                "priority": "medium",
            },
        ],
        key=lambda item: item["rank"],
    )

    return {
        "hypotheses": hypotheses,
        "strategies": strategies,
        "priorities": priorities,
        "goal_recommendations": [
            {
                "id": "keep_os5_goals_warm",
                "priority": "high",
                "action": "Keep the OS-5 goals layer synchronized with current reasoning signals.",
            },
            {
                "id": "track_strategy_phase_order",
                "priority": "medium",
                "action": "Use the OS-5 strategy phase order to guide later orchestrators.",
            },
            {
                "id": "respect_memory_context",
                "priority": "medium",
                "action": "Use core memory preferences to keep later decisions stable and additive.",
            },
        ],
        "meta_adaptation_hints": meta_adaptation_hints,
        "architecture_candidates": architecture_candidates,
        "signals": {
            "health_score": health_score,
            "warning_count": warning_count,
            "parse_error_count": parse_errors,
            "graph_nodes": graph_nodes,
            "graph_edges": graph_edges,
            "evolution_overall_success": evolution_ok,
            "strategy_priority_count": len(strategy_priorities),
            "strategy_phase_count": len(strategy_phase_order),
            "architecture_candidate_count": len(architecture_candidates),
            "architecture_proposal_count": len(architecture_list),
            "policy_count": policies_count,
            "enterprise_policy_count": enterprise_policy_count,
            "meta_history_exists": meta_history_exists,
            "memory_context_present": memory_context_present,
            "memory_history_length": memory_history_length,
            "memory_stability_priority": memory_preferences.get("stability_priority"),
            "memory_warnings_tolerance": memory_preferences.get("warnings_tolerance"),
            "memory_evolution_aggressiveness": memory_preferences.get("evolution_aggressiveness"),
            "memory_stable_cycles": memory_patterns.get("stable_cycles", 0),
            "memory_warning_cycles": memory_patterns.get("warning_cycles", 0),
            "memory_parse_error_cycles": memory_patterns.get("parse_error_cycles", 0),
            "memory_consistency_present": bool(self_consistency),
            "memory_consistency_overall_consistent": consistency_overall,
            "memory_consistency_contradiction_count": consistency_contradictions,
            "memory_consistency_regression_count": consistency_regressions,
        },
    }


def verify(report: dict[str, Any]) -> dict[str, Any]:
    checks = {
        "schema_present": report.get("schema") == "ana.os4.self_reasoning.v1",
        "hypotheses_present": isinstance(report.get("hypotheses"), list),
        "strategies_present": isinstance(report.get("strategies"), list),
        "priorities_present": isinstance(report.get("priorities"), list),
        "health_signal_present": "health_score" in report.get("signals", {}),
    }
    return {"passed": all(checks.values()), "checks": checks}


def document(report: dict[str, Any], *, dry_run: bool) -> None:
    if dry_run:
        return
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")


def run_cycle(*, dry_run: bool = False) -> dict[str, Any]:
    started = time.perf_counter()
    observation = observe()
    analysis = analyze(observation)
    report = {
        "schema": "ana.os4.self_reasoning.v1",
        "engine": ENGINE_NAME,
        "generated_at": _utc_now(),
        "dry_run": dry_run,
        "project_root": str(PROJECT_ROOT),
        "inputs": {name: str(path) for name, path in INPUTS.items()},
        "hypotheses": analysis["hypotheses"],
        "strategies": analysis["strategies"],
        "priorities": analysis["priorities"],
        "signals": analysis["signals"],
        "memory_context_summary": _memory_context_summary(observation["inputs"]["memory_context"]),
    }
    verification = verify(report)
    report["verification"] = verification
    report["elapsed_ms"] = round((time.perf_counter() - started) * 1000, 2)
    document(report, dry_run=dry_run)
    return {
        "engine": ENGINE_NAME,
        "dry_run": dry_run,
        "elapsed_ms": report["elapsed_ms"],
        "verification": verification,
        "report_path": str(REPORT_PATH),
        "summary": {
            "hypotheses": len(report["hypotheses"]),
            "strategies": len(report["strategies"]),
            "priorities": len(report["priorities"]),
            "health_score": report["signals"].get("health_score"),
            "warning_count": report["signals"].get("warning_count"),
        },
    }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ANA MAX OS-4 Self-Reasoning Engine")
    parser.add_argument("--cycle", action="store_true", help="Run reasoning cycle.")
    parser.add_argument("--dry-run", action="store_true", help="Do not write report.")
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
