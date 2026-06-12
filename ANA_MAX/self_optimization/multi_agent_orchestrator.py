#!/usr/bin/env python3
"""
ANA MAX OS-3 Multi-Agent Orchestrator
Autonomy Zone: This module operates with maximum autonomy inside the project workspace.
It may analyze, modify, and extend project components as needed.
It must remain safe and operate only within project boundaries.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

# Add workspace root to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ANA_MAX.self_optimization.os3_common import RAW_END, RAW_START, print_raw_json


WORKSPACE_ROOT = Path(__file__).parent.parent.parent
DOCS_DIR = WORKSPACE_ROOT / "docs"
SHARED_STATE_FILE = WORKSPACE_ROOT / "ANA_MAX" / "memory" / "multi_agent_shared_state.json"
MEMORY_DIR = WORKSPACE_ROOT / "ANA_MAX" / "memory"
AGENT_REGISTRY_FILE = MEMORY_DIR / "agent_registry.json"
LEVEL_REPORT_FILE = MEMORY_DIR / "os_level_OS7_report.json"

TASK_COMMANDS: dict[str, tuple[str, list[str]]] = {
    "profiling": ("ANA_MAX.self_optimization.self_profiling_engine", ["--cycle"]),
    "structuring": ("ANA_MAX.self_optimization.self_structuring_engine", ["--cycle", "--dry-run"]),
    "skills": ("ANA_MAX.self_optimization.self_skills_engine", ["--cycle"]),
    "healing": ("ANA_MAX.self_optimization.self_healing_engine", ["--cycle", "--dry-run"]),
    "knowledge_graph": ("ANA_MAX.self_optimization.knowledge_graph_engine", ["--cycle"]),
}

REPORT_FILES: dict[str, Path] = {
    "performance": MEMORY_DIR / "self_profiling_report.json",
    "structure": MEMORY_DIR / "self_structuring_report.json",
    "tests": MEMORY_DIR / "self_healing_report.json",
    "skills": MEMORY_DIR / "self_skills_report.json",
    "graph": MEMORY_DIR / "knowledge_graph.json",
}

DEFAULT_AGENT_REGISTRY: dict[str, dict[str, Any]] = {
    "optimizer": {
        "role": "optimizer",
        "status": "active",
        "health_score": 100,
        "failure_count": 0,
        "success_count": 0,
        "last_success_at": None,
        "last_failure_at": None,
        "last_task": None,
    },
    "tester": {
        "role": "tester",
        "status": "active",
        "health_score": 100,
        "failure_count": 0,
        "success_count": 0,
        "last_success_at": None,
        "last_failure_at": None,
        "last_task": None,
    },
    "documenter": {
        "role": "documenter",
        "status": "active",
        "health_score": 100,
        "failure_count": 0,
        "success_count": 0,
        "last_success_at": None,
        "last_failure_at": None,
        "last_task": None,
    },
    "structurer": {
        "role": "structurer",
        "status": "active",
        "health_score": 100,
        "failure_count": 0,
        "success_count": 0,
        "last_success_at": None,
        "last_failure_at": None,
        "last_task": None,
    },
    "extractor": {
        "role": "extractor",
        "status": "active",
        "health_score": 100,
        "failure_count": 0,
        "success_count": 0,
        "last_success_at": None,
        "last_failure_at": None,
        "last_task": None,
        "requires_explicit_enable": True,
    },
}


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {"value": data}
    except Exception as exc:
        return {"error": str(exc), "path": str(path)}


def _extract_payload(stdout: str) -> dict[str, Any]:
    text = stdout.strip()
    if RAW_START in text and RAW_END in text:
        text = text.split(RAW_START, 1)[1].split(RAW_END, 1)[0].strip()
    if not text:
        return {"error": "empty_stdout"}
    data = json.loads(text)
    return data if isinstance(data, dict) else {"value": data}


def _run_module(module: str, args: list[str], timeout_seconds: int = 180) -> dict[str, Any]:
    completed = subprocess.run(
        [sys.executable, "-m", module, *args],
        cwd=str(WORKSPACE_ROOT),
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        check=False,
    )
    try:
        result = _extract_payload(completed.stdout)
    except Exception as exc:
        result = {
            "error": "invalid_json_output",
            "parse_error": str(exc),
            "stdout_excerpt": completed.stdout[:2000],
        }
    result["_runner"] = {
        "module": module,
        "args": args,
        "returncode": completed.returncode,
    }
    if completed.returncode != 0:
        result.setdefault("error", "module_returncode_nonzero")
        result["_runner"]["stderr_excerpt"] = completed.stderr[:2000]
    return result


@dataclass
class AgentTask:
    """Task assigned to an agent."""
    agent: str
    task_type: str
    description: str
    priority: str
    status: str  # "pending", "in_progress", "completed", "failed"
    result: Dict[str, Any] | None
    timestamp: str


@dataclass
class SharedState:
    """Shared state for multi-agent coordination."""
    timestamp: str
    performance: Dict[str, Any]
    structure: Dict[str, Any]
    tests: Dict[str, Any]
    skills: Dict[str, Any]
    graph: Dict[str, Any]
    agent_tasks: List[AgentTask]


class MultiAgentOrchestrator:
    """Coordinates multiple agents with different roles for OS-3 execution."""

    def __init__(
        self,
        *,
        workspace_root: Path = WORKSPACE_ROOT,
        shared_state_file: Path = SHARED_STATE_FILE,
    ) -> None:
        self.workspace_root = workspace_root
        self.shared_state_file = shared_state_file
        self.shared_state: SharedState | None = None
        self.agent_tasks: List[AgentTask] = []
        self.agent_registry: dict[str, dict[str, Any]] = self._load_agent_registry()
        self._load_shared_state()

    def _load_shared_state(self) -> None:
        """Load shared state from file."""
        if self.shared_state_file.exists():
            try:
                with self.shared_state_file.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.shared_state = SharedState(**data)
                    self.agent_tasks = [
                        AgentTask(**task) for task in data.get("agent_tasks", [])
                    ]
            except Exception:
                self.shared_state = None
                self.agent_tasks = []

    def _load_agent_registry(self) -> dict[str, dict[str, Any]]:
        if not AGENT_REGISTRY_FILE.exists():
            return json.loads(json.dumps(DEFAULT_AGENT_REGISTRY))
        try:
            with AGENT_REGISTRY_FILE.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
        except Exception:
            return json.loads(json.dumps(DEFAULT_AGENT_REGISTRY))
        agents = data.get("agents", {}) if isinstance(data, dict) else {}
        registry = json.loads(json.dumps(DEFAULT_AGENT_REGISTRY))
        if isinstance(agents, dict):
            for name, entry in agents.items():
                if not isinstance(entry, dict):
                    continue
                registry.setdefault(name, {}).update(entry)
        return registry

    def _save_agent_registry(self) -> None:
        AGENT_REGISTRY_FILE.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema": "ana.os7.agent_registry.v1",
            "generated_at": datetime.now().isoformat(),
            "agents": self.agent_registry,
            "summary": {
                "agent_count": len(self.agent_registry),
                "healthy_count": sum(1 for entry in self.agent_registry.values() if entry.get("failure_count", 0) == 0),
                "failure_count_total": sum(int(entry.get("failure_count", 0) or 0) for entry in self.agent_registry.values()),
                "success_count_total": sum(int(entry.get("success_count", 0) or 0) for entry in self.agent_registry.values()),
            },
        }
        with AGENT_REGISTRY_FILE.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, default=str)

    def _touch_agent_registry(self, task: AgentTask) -> None:
        entry = self.agent_registry.setdefault(
            task.agent,
            {
                "role": task.agent,
                "status": "active",
                "health_score": 100,
                "failure_count": 0,
                "success_count": 0,
                "last_success_at": None,
                "last_failure_at": None,
                "last_task": None,
            },
        )
        entry["last_task"] = {
            "task_type": task.task_type,
            "status": task.status,
            "timestamp": task.timestamp,
        }
        if task.status == "completed":
            entry["success_count"] = int(entry.get("success_count", 0) or 0) + 1
            entry["last_success_at"] = task.timestamp
        elif task.status == "failed":
            entry["failure_count"] = int(entry.get("failure_count", 0) or 0) + 1
            entry["last_failure_at"] = task.timestamp
        failure_count = int(entry.get("failure_count", 0) or 0)
        success_count = int(entry.get("success_count", 0) or 0)
        if failure_count == 0 and success_count > 0:
            entry["health_score"] = 100
        else:
            entry["health_score"] = max(0, 100 - failure_count * 20)

    def _save_shared_state(self) -> None:
        """Save shared state to file."""
        self.shared_state_file.parent.mkdir(parents=True, exist_ok=True)

        state_data = {
            "timestamp": datetime.now().isoformat(),
            "performance": self.shared_state.performance if self.shared_state else {},
            "structure": self.shared_state.structure if self.shared_state else {},
            "tests": self.shared_state.tests if self.shared_state else {},
            "skills": self.shared_state.skills if self.shared_state else {},
            "graph": self.shared_state.graph if self.shared_state else {},
            "agent_tasks": [asdict(task) for task in self.agent_tasks],
        }

        with self.shared_state_file.open("w", encoding="utf-8") as f:
            json.dump(state_data, f, indent=2, default=str)

    def assign_tasks(self, task_type: str = "full_cycle") -> List[AgentTask]:
        """Assign tasks to agents based on their roles."""
        tasks: List[AgentTask] = []
        timestamp = datetime.now().isoformat()

        if task_type == "full_cycle":
            # Optimizer Agent tasks
            tasks.append(AgentTask(
                agent="optimizer",
                task_type="profiling",
                description="Run performance profiling cycle",
                priority="high",
                status="pending",
                result=None,
                timestamp=timestamp,
            ))
            tasks.append(AgentTask(
                agent="optimizer",
                task_type="structuring",
                description="Analyze and propose structure improvements",
                priority="medium",
                status="pending",
                result=None,
                timestamp=timestamp,
            ))
            tasks.append(AgentTask(
                agent="optimizer",
                task_type="skills",
                description="Expand skills and capabilities",
                priority="medium",
                status="pending",
                result=None,
                timestamp=timestamp,
            ))

            # Tester Agent tasks
            tasks.append(AgentTask(
                agent="tester",
                task_type="healing",
                description="Run healing and test cycle",
                priority="high",
                status="pending",
                result=None,
                timestamp=timestamp,
            ))

            # Documenter Agent tasks
            tasks.append(AgentTask(
                agent="documenter",
                task_type="knowledge_graph",
                description="Update knowledge graph",
                priority="medium",
                status="pending",
                result=None,
                timestamp=timestamp,
            ))

            # Structurer Agent tasks
            tasks.append(AgentTask(
                agent="structurer",
                task_type="canonical_layout",
                description="Verify and enforce canonical layout",
                priority="low",
                status="pending",
                result=None,
                timestamp=timestamp,
            ))

            # Extractor Agent tasks (only if repo input available)
            # This agent is user-triggered only, so it's not in the auto cycle
            tasks.append(AgentTask(
                agent="extractor",
                task_type="github_patterns",
                description="Extract GitHub patterns (user-triggered only)",
                priority="low",
                status="pending",
                result=None,
                timestamp=timestamp,
            ))

        elif task_type == "optimization":
            tasks.append(AgentTask(
                agent="optimizer",
                task_type="profiling",
                description="Run performance profiling",
                priority="high",
                status="pending",
                result=None,
                timestamp=timestamp,
            ))

        elif task_type == "testing":
            tasks.append(AgentTask(
                agent="tester",
                task_type="healing",
                description="Run healing and tests",
                priority="high",
                status="pending",
                result=None,
                timestamp=timestamp,
            ))

        self.agent_tasks = tasks
        return tasks

    def sync_state(self) -> SharedState:
        """Synchronize shared state across all agents."""
        performance_report = _load_json(REPORT_FILES["performance"])
        structure_report = _load_json(REPORT_FILES["structure"])
        tests_report = _load_json(REPORT_FILES["tests"])
        skills_report = _load_json(REPORT_FILES["skills"])
        graph_report = _load_json(REPORT_FILES["graph"])

        self.shared_state = SharedState(
            timestamp=datetime.now().isoformat(),
            performance=performance_report.get("summary", performance_report),
            structure=structure_report.get("summary", structure_report),
            tests=tests_report.get("summary", tests_report),
            skills=skills_report.get("summary", skills_report),
            graph=graph_report.get("metadata", graph_report),
            agent_tasks=self.agent_tasks,
        )

        self._save_shared_state()
        return self.shared_state

    def merge_results(self) -> Dict[str, Any]:
        """Merge results from all agents into unified output."""
        merged = {
            "timestamp": datetime.now().isoformat(),
            "agents": {},
            "agent_registry": self.agent_registry,
            "summary": {
                "total_tasks": len(self.agent_tasks),
                "completed": sum(1 for t in self.agent_tasks if t.status == "completed"),
                "failed": sum(1 for t in self.agent_tasks if t.status == "failed"),
                "pending": sum(1 for t in self.agent_tasks if t.status == "pending"),
                "agent_failure_count": sum(
                    int(entry.get("failure_count", 0) or 0) for entry in self.agent_registry.values()
                ),
                "healthy_agents": sum(
                    1 for entry in self.agent_registry.values() if int(entry.get("failure_count", 0) or 0) == 0
                ),
            },
            "shared_state": asdict(self.shared_state) if self.shared_state else {},
        }

        # Group results by agent
        for task in self.agent_tasks:
            if task.agent not in merged["agents"]:
                merged["agents"][task.agent] = {
                    "tasks": [],
                    "results": [],
                }
            merged["agents"][task.agent]["tasks"].append({
                "type": task.task_type,
                "status": task.status,
                "description": task.description,
            })
            if task.result:
                merged["agents"][task.agent]["results"].append(task.result)

        return merged

    def execute_agent_task(self, task: AgentTask) -> AgentTask:
        """Execute a single agent task."""
        task.status = "in_progress"

        try:
            if task.task_type in TASK_COMMANDS:
                module, args = TASK_COMMANDS[task.task_type]
                result = _run_module(module, args)
                task.result = result
                task.status = "failed" if "error" in result else "completed"

            elif task.agent == "structurer" and task.task_type == "canonical_layout":
                structure_report = _load_json(REPORT_FILES["structure"])
                result = {
                    "source": str(REPORT_FILES["structure"]),
                    "summary": structure_report.get("summary", {}),
                    "planned_actions": structure_report.get("planned_actions", []),
                }
                task.result = result
                task.status = "completed" if structure_report else "failed"

            elif task.agent == "extractor" and task.task_type == "github_patterns":
                task.result = {
                    "skipped": True,
                    "reason": "github_pattern_extractor requires an explicit repo_path",
                }
                task.status = "completed"

            else:
                task.status = "failed"
                task.result = {"error": "Unknown task type"}

        except Exception as exc:
            task.status = "failed"
            task.result = {"error": str(exc)}

        self._touch_agent_registry(task)
        return task

    def run_orchestration_cycle(self) -> Dict[str, Any]:
        """Run complete multi-agent orchestration cycle."""
        # Assign tasks
        tasks = self.assign_tasks(task_type="full_cycle")

        # Execute tasks
        for task in tasks:
            self.execute_agent_task(task)

        # Sync state
        self.sync_state()

        # Merge results
        merged = self.merge_results()
        self._save_agent_registry()

        level_report = {
            "schema": "ana.os7.level_report.v1",
            "generated_at": datetime.now().isoformat(),
            "os_level": "OS-7",
            "status": "PASS" if merged["summary"]["failed"] == 0 else "WARN",
            "next": "OS-8",
            "summary": merged["summary"],
            "agent_registry": self.agent_registry,
            "orchestration": merged,
        }
        LEVEL_REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
        with LEVEL_REPORT_FILE.open("w", encoding="utf-8") as handle:
            json.dump(level_report, handle, indent=2, default=str)
        return level_report


def main() -> int:
    """CLI entry point for multi-agent orchestrator."""
    import argparse

    parser = argparse.ArgumentParser(description="ANA MAX OS-3 Multi-Agent Orchestrator")
    parser.add_argument("--assign", default="full_cycle", help="Task type to assign (full_cycle, optimization, testing)")
    parser.add_argument("--sync", action="store_true", help="Synchronize shared state")
    parser.add_argument("--merge", action="store_true", help="Merge agent results")
    parser.add_argument("--cycle", action="store_true", help="Run complete orchestration cycle")
    args = parser.parse_args()

    orchestrator = MultiAgentOrchestrator()

    if args.sync:
        state = orchestrator.sync_state()
        print_raw_json(asdict(state))
        return 0

    if args.merge:
        result = orchestrator.merge_results()
        print_raw_json(result)
        return 0

    if args.cycle:
        result = orchestrator.run_orchestration_cycle()
        print_raw_json(result)
        return 0

    # Default: assign and show tasks
    tasks = orchestrator.assign_tasks(task_type=args.assign)
    print_raw_json([asdict(t) for t in tasks])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
