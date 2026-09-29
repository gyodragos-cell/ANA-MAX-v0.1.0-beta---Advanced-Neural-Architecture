"""OS-21 agent scheduler.

This module is metadata-only. It turns the current agent registry into a
deterministic schedule and does not execute agent work.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


SCHEDULER_SCHEMA = "ana.os21.agent_scheduler.v1"
SCHEDULER_NAME = "agent_scheduler_v1"
SCHEDULER_VERSION = "1.0"
MEMORY_ROOT = ROOT / "ANA_MAX" / "memory"

ROLE_ORDER = ("optimizer", "tester", "documenter", "structurer", "extractor")
TASK_ROLE_HINTS = {
    "optimize": "optimizer",
    "validate": "tester",
    "test": "tester",
    "document": "documenter",
    "structure": "structurer",
    "extract": "extractor",
    "recon": "extractor",
}

DEFAULT_TASKS = (
    {"task_id": "task-1", "task_type": "optimize_workspace", "purpose": "Improve the current workspace baseline", "preferred_role": "optimizer", "priority": 1},
    {"task_id": "task-2", "task_type": "validate_workspace", "purpose": "Validate the current workspace baseline", "preferred_role": "tester", "priority": 2},
    {"task_id": "task-3", "task_type": "document_changes", "purpose": "Summarize durable project notes", "preferred_role": "documenter", "priority": 3},
    {"task_id": "task-4", "task_type": "structure_graph", "purpose": "Keep project structure consistent", "preferred_role": "structurer", "priority": 4},
    {"task_id": "task-5", "task_type": "extract_patterns", "purpose": "Extract external patterns when explicitly enabled", "preferred_role": "extractor", "priority": 5, "requires_explicit_enable": True},
)


def _read_json(path: Path, fallback: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback


def _normalize_task(task: Any, index: int) -> dict[str, Any]:
    if isinstance(task, Mapping):
        payload = dict(task)
    else:
        payload = {"task_type": str(task)}

    task_type = str(payload.get("task_type", "")).strip() or f"task_{index}"
    task_type_lower = task_type.lower()
    preferred_role = str(payload.get("preferred_role", "")).strip().lower()
    if not preferred_role:
        for key, role in TASK_ROLE_HINTS.items():
            if key in task_type_lower:
                preferred_role = role
                break
    if not preferred_role:
        preferred_role = ROLE_ORDER[index % len(ROLE_ORDER)]

    return {
        "task_id": str(payload.get("task_id", f"task-{index + 1}")),
        "task_type": task_type,
        "purpose": str(payload.get("purpose", task_type.replace("_", " "))).strip(),
        "preferred_role": preferred_role,
        "priority": int(payload.get("priority", index + 1) or index + 1),
        "requires_explicit_enable": bool(payload.get("requires_explicit_enable", False)),
    }


class AgentScheduler:
    """Deterministic agent scheduler for OS-21 planning."""

    def __init__(self, registry_path: Path | None = None) -> None:
        self.registry_path = registry_path or (MEMORY_ROOT / "agent_registry.json")
        self._last_schedule: dict[str, Any] | None = None

    def _load_registry(self) -> dict[str, Any]:
        return _read_json(self.registry_path, {"schema": "ana.os7.agent_registry.v1", "agents": {}, "summary": {}})

    def _ordered_agents(self, registry: dict[str, Any]) -> list[dict[str, Any]]:
        agents = registry.get("agents") or {}
        ordered: list[dict[str, Any]] = []
        for role in ROLE_ORDER:
            for agent_id in sorted(agents):
                agent = agents.get(agent_id) or {}
                if str(agent.get("role", "")).strip().lower() != role:
                    continue
                ordered.append(
                    {
                        "agent_id": agent_id,
                        "role": role,
                        "status": agent.get("status", "unknown"),
                        "health_score": agent.get("health_score", 0),
                        "failure_count": agent.get("failure_count", 0),
                        "success_count": agent.get("success_count", 0),
                        "requires_explicit_enable": bool(agent.get("requires_explicit_enable", False)),
                    }
                )
        return ordered

    def _default_tasks(self, tasks: list[Any] | None = None) -> list[dict[str, Any]]:
        if tasks is None:
            return [dict(task) for task in DEFAULT_TASKS]
        return [_normalize_task(task, index) for index, task in enumerate(tasks)]

    def _assign_agent(self, task: dict[str, Any], agents: list[dict[str, Any]]) -> dict[str, Any]:
        preferred_role = str(task.get("preferred_role", "")).strip().lower()
        selected = None
        for agent in agents:
            if agent["role"] == preferred_role and agent.get("status") == "active":
                selected = agent
                break
        if selected is None:
            for agent in agents:
                if agent.get("status") == "active":
                    selected = agent
                    break
        if selected is None and agents:
            selected = agents[0]

        selected = selected or {
            "agent_id": "agent:unassigned",
            "role": "unassigned",
            "status": "missing",
            "health_score": 0,
            "failure_count": 0,
            "success_count": 0,
            "requires_explicit_enable": False,
        }

        gated = bool(task.get("requires_explicit_enable", False) or selected.get("requires_explicit_enable", False))
        return {
            "task_id": task["task_id"],
            "task_type": task["task_type"],
            "agent_id": selected["agent_id"],
            "agent_role": selected["role"],
            "priority": task["priority"],
            "requires_explicit_enable": gated,
            "status": "gated" if gated else "planned",
            "purpose": task["purpose"],
        }

    def build_schedule(self, tasks: list[Any] | None = None, policy: str = "balanced") -> dict[str, Any]:
        normalized_policy = (policy or "balanced").strip().lower()
        if normalized_policy not in {"balanced", "safe", "fast"}:
            normalized_policy = "balanced"

        registry = self._load_registry()
        agents = self._ordered_agents(registry)
        task_queue = self._default_tasks(tasks)
        assignments = [self._assign_agent(task, agents) for task in task_queue]
        round_items = [{"round": 1, "assignments": [assignment["task_id"] for assignment in assignments]}]

        nodes = [f"scheduler:{SCHEDULER_NAME}"]
        edges: list[dict[str, Any]] = []
        for agent in agents:
            nodes.append(f"agent:{agent['agent_id']}")
            edges.append({"source": f"scheduler:{SCHEDULER_NAME}", "target": f"agent:{agent['agent_id']}", "relation": "assigns"})
        for task in task_queue:
            nodes.append(f"task:{task['task_id']}")
            edges.append({"source": f"scheduler:{SCHEDULER_NAME}", "target": f"task:{task['task_id']}", "relation": "queues"})
        for assignment in assignments:
            edges.append({"source": f"agent:{assignment['agent_id']}", "target": f"task:{assignment['task_id']}", "relation": "executes"})

        schedule = {
            "schema": SCHEDULER_SCHEMA,
            "scheduler_name": SCHEDULER_NAME,
            "version": SCHEDULER_VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "local_only": True,
            "baseline_compatible": True,
            "policy": normalized_policy,
            "agents": agents,
            "tasks": task_queue,
            "assignments": assignments,
            "rounds": round_items,
            "reasoning_graph_hints": {
                "nodes": nodes,
                "edges": edges,
            },
            "summary": {
                "schema": SCHEDULER_SCHEMA,
                "scheduler_name": SCHEDULER_NAME,
                "agent_count": len(agents),
                "healthy_agent_count": len([agent for agent in agents if agent.get("status") == "active"]),
                "gated_agent_count": len([agent for agent in agents if agent.get("requires_explicit_enable")]),
                "task_count": len(task_queue),
                "assignment_count": len(assignments),
                "policy": normalized_policy,
            },
        }

        self._last_schedule = schedule
        return schedule

    def summarize_schedule(self) -> dict[str, Any]:
        schedule = self._last_schedule or self.build_schedule()
        return dict(schedule.get("summary") or {})


def _run_from_cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a metadata-only agent schedule.")
    parser.add_argument("--policy", default="balanced", choices=["balanced", "safe", "fast"], help="Scheduling policy")
    parser.add_argument("--task", action="append", default=[], help="Optional task type to include in the schedule")
    parser.add_argument("--summary", action="store_true", help="Print a compact summary only")
    parser.add_argument("--cycle", action="store_true", help="Build and print the full schedule")
    args = parser.parse_args(argv)

    scheduler = AgentScheduler()
    tasks = args.task if args.task else None
    schedule = scheduler.build_schedule(tasks=tasks, policy=args.policy)
    payload = scheduler.summarize_schedule() if args.summary and not args.cycle else schedule

    print(json.dumps(payload, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(_run_from_cli())
