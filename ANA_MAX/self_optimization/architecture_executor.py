#!/usr/bin/env python3
"""ANA MAX OS-8 Architecture Executor."""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ANA_MAX.self_optimization.os3_common import print_raw_json
from ANA_MAX.self_optimization.osx_common import MEMORY_DIR, WORKSPACE_ROOT, ensure_dir, read_json, write_json, utc_now

ENGINE_NAME = "architecture_executor"
LEVEL_SCHEMA = "ana.os8.architecture_executor.v1"
LEVEL_REPORT_SCHEMA = "ana.os8.level_report.v1"
PROPOSALS_SCHEMA = "ana.os8.architecture_proposals.v1"
LEVEL_REPORT_PATH = MEMORY_DIR / "os_level_OS8_report.json"
PROPOSALS_PATH = MEMORY_DIR / "architecture_proposals.json"

INPUTS = {
    "reasoning": MEMORY_DIR / "self_reasoning_report.json",
    "goals": MEMORY_DIR / "self_goals.json",
    "strategy": MEMORY_DIR / "evolution_strategy.json",
    "meta_adaptation": MEMORY_DIR / "evolution_strategy_history",
    "graph": MEMORY_DIR / "knowledge_graph.json",
}


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _load_inputs() -> dict[str, Any]:
    payload = {
        name: read_json(path, {}) if path.is_file() else {"path": str(path), "exists": path.exists()}
        for name, path in INPUTS.items()
    }
    meta_dir = INPUTS["meta_adaptation"]
    payload["meta_adaptation_history_count"] = len(list(meta_dir.glob("os6_meta_*.json"))) if meta_dir.exists() else 0
    return payload


def _graph_metrics(graph: dict[str, Any]) -> dict[str, Any]:
    metadata = graph.get("metadata", {}) if isinstance(graph, dict) else {}
    return {
        "nodes": _to_int(metadata.get("total_nodes"), 0),
        "edges": _to_int(metadata.get("total_edges"), 0),
        "density": round(_to_int(metadata.get("total_edges"), 0) / max(_to_int(metadata.get("total_nodes"), 0), 1), 3),
    }


def _candidate_proposals(inputs: dict[str, Any]) -> list[dict[str, Any]]:
    reasoning = inputs["reasoning"] if isinstance(inputs.get("reasoning"), dict) else {}
    goals = inputs["goals"] if isinstance(inputs.get("goals"), dict) else {}
    strategy = inputs["strategy"] if isinstance(inputs.get("strategy"), dict) else {}
    graph_metrics = _graph_metrics(inputs.get("graph", {}))
    reasoning_candidates = reasoning.get("architecture_candidates", []) if isinstance(reasoning.get("architecture_candidates", []), list) else []
    goals_list = goals.get("goals", []) if isinstance(goals.get("goals", []), list) else []
    priorities = strategy.get("priorities", []) if isinstance(strategy.get("priorities", []), list) else []

    proposals: list[dict[str, Any]] = []

    for candidate in reasoning_candidates:
        if not isinstance(candidate, dict):
            continue
        proposals.append(
            {
                "id": candidate.get("id", f"candidate_{len(proposals)+1}"),
                "title": candidate.get("id", "architecture_candidate"),
                "confidence": candidate.get("confidence", 0.5),
                "target_layer": candidate.get("target", "OS-8"),
                "risk": candidate.get("risk", "low"),
                "benefit": candidate.get("benefit", "read-only additive improvement"),
                "rationale": "Lifted from the reasoning engine's architecture candidates.",
                "action": "simulate",
            }
        )

    if graph_metrics["nodes"] >= 100 and graph_metrics["edges"] >= 1000:
        proposals.append(
            {
                "id": "split_orchestrator_layers",
                "title": "Split orchestrator layers",
                "confidence": 0.86,
                "target_layer": "OS-8",
                "risk": "low",
                "benefit": "Keep layered orchestration focused and easier to test.",
                "rationale": f"Graph density {graph_metrics['density']} suggests a bounded decomposition point.",
                "action": "simulate",
            }
        )

    if goals_list and priorities:
        proposals.append(
            {
                "id": "goal_to_policy_bridge",
                "title": "Bridge goals to policy composition",
                "confidence": 0.8,
                "target_layer": "OS-9",
                "risk": "low",
                "benefit": "Feed goals and strategy into the policy engine without changing OS-3/OS-4 schemas.",
                "rationale": "The goals and strategy layers are already producing deterministic ordering information.",
                "action": "simulate",
            }
        )

    if inputs.get("meta_adaptation_history_count", 0):
        proposals.append(
            {
                "id": "history_guided_review",
                "title": "Review architecture using meta-adaptation history",
                "confidence": 0.74,
                "target_layer": "OS-6",
                "risk": "low",
                "benefit": "Use prior adaptation snapshots to avoid redundant proposals.",
                "rationale": "OS-6 history provides a trend line for stable additive evolution.",
                "action": "simulate",
            }
        )

    return proposals


def _simulation(proposals: list[dict[str, Any]], *, dry_run: bool) -> list[dict[str, Any]]:
    simulated: list[dict[str, Any]] = []
    for proposal in proposals:
        simulated.append(
            {
                "proposal_id": proposal.get("id"),
                "would_mutate": False,
                "status": "simulated" if dry_run else "planned",
                "notes": "OS-8 executor remains additive and read-only unless an explicit future apply mode is introduced.",
            }
        )
    return simulated


def _verification(report: dict[str, Any]) -> dict[str, Any]:
    checks = {
        "schema_present": report.get("schema") == LEVEL_SCHEMA,
        "proposals_present": isinstance(report.get("proposals"), list),
        "simulation_present": isinstance(report.get("simulation"), list),
        "dry_run_state_present": "dry_run" in report,
    }
    return {"passed": all(checks.values()), "checks": checks}


def _level_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": LEVEL_REPORT_SCHEMA,
        "generated_at": report.get("generated_at", utc_now()),
        "engine": ENGINE_NAME,
        "os_level": "OS-8",
        "status": "PASS" if report.get("verification", {}).get("passed") else "WARN",
        "next": "OS-9",
        "summary": report.get("summary", {}),
        "payload": report,
    }


def run_cycle(*, dry_run: bool = True) -> dict[str, Any]:
    started = time.perf_counter()
    inputs = _load_inputs()
    proposals = _candidate_proposals(inputs)
    simulation = _simulation(proposals, dry_run=dry_run)

    proposals_report = {
        "schema": PROPOSALS_SCHEMA,
        "generated_at": utc_now(),
        "engine": ENGINE_NAME,
        "workspace_root": str(WORKSPACE_ROOT),
        "source_reports": {name: str(path) for name, path in INPUTS.items()},
        "proposals": proposals,
        "summary": {
            "proposal_count": len(proposals),
            "simulation_count": len(simulation),
        },
    }

    report = {
        "schema": LEVEL_SCHEMA,
        "generated_at": utc_now(),
        "engine": ENGINE_NAME,
        "workspace_root": str(WORKSPACE_ROOT),
        "dry_run": dry_run,
        "inputs": {name: str(path) for name, path in INPUTS.items()},
        "proposals": proposals,
        "simulation": simulation,
        "proposal_report": proposals_report,
        "summary": {
            "proposal_count": len(proposals),
            "simulation_count": len(simulation),
            "dry_run": dry_run,
        },
    }
    report["verification"] = _verification(report)
    report["elapsed_ms"] = round((time.perf_counter() - started) * 1000, 2)
    report["proposals_path"] = str(PROPOSALS_PATH)
    report["level_report_path"] = str(LEVEL_REPORT_PATH)

    ensure_dir(PROPOSALS_PATH.parent)
    if not dry_run:
        write_json(PROPOSALS_PATH, proposals_report)
    write_json(LEVEL_REPORT_PATH, _level_report(report))

    return report


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ANA MAX OS-8 Architecture Executor")
    parser.add_argument("--cycle", action="store_true", help="Run the architecture executor cycle.")
    parser.add_argument("--dry-run", action="store_true", help="Compute proposals without writing artifacts.")
    return parser


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()
    dry_run = args.dry_run or not args.cycle
    result = run_cycle(dry_run=dry_run)
    print_raw_json(result)
    return 0 if result.get("verification", {}).get("passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
