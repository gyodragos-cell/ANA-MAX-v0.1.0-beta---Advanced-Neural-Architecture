"""
Authorized Engineer platform for controlled security work.
"""

from __future__ import annotations

import ipaddress
import logging
import re
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Set

from core.autonomous_agent import AutonomousAgent
from core.bot_factory import BotFactory
from core.lab import LocalLearningLab
from core.repair_controller import RepairController

logger = logging.getLogger(__name__)

_BLOCKED_TASK_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\bexploit\b",
        r"\bpersistence\b",
        r"\bexfil(?:tration)?\b",
        r"\bc2\b",
        r"command\s+and\s+control",
        r"reverse\s+shell",
        r"\bpayload\b",
        r"\bphish(?:ing)?\b",
        r"credential\s+(?:dump|theft|harvest)",
        r"lateral\s+movement",
        r"\bransom(?:ware)?\b",
    )
]
_URL_RE = re.compile(r"https?://([^/\s:]+)")
_IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")


class AssessmentScope:
    """Legal-by-default scope guardrails for security tasks."""

    def __init__(self, workspace_root: str | Path,
                 approved_targets: Optional[Sequence[str]] = None):
        self.workspace_root = Path(workspace_root).resolve()
        self.approved_targets = self._normalize_targets(approved_targets or [])
        self.approved_targets.update({"127.0.0.1", "localhost", "::1"})

    def describe(self) -> Dict[str, Any]:
        return {
            "workspace_root": str(self.workspace_root),
            "approved_targets": sorted(self.approved_targets),
            "mode": "authorized_whitehat",
            "restrictions": [
                "controlled_non_destructive_only",
                "no_exploitation",
                "no_persistence",
                "no_exfiltration",
                "no_command_and_control",
            ],
        }

    def validate_task(self, task: str) -> None:
        task = (task or "").strip()
        if not task:
            raise ValueError("Task-ul este gol.")

        for pattern in _BLOCKED_TASK_PATTERNS:
            if pattern.search(task):
                raise ValueError(
                    "Task-ul cere capacitati ofensive nepermise. "
                    "Platforma accepta doar evaluari autorizate, controlate si nedistructive."
                )

        unauthorized_targets = [
            target for target in self.extract_targets(task)
            if not self.is_target_allowed(target)
        ]
        if unauthorized_targets:
            joined = ", ".join(sorted(set(unauthorized_targets)))
            raise ValueError(
                f"Target in afara scope-ului autorizat: {joined}. "
                "Adauga explicit scope aprobat in platforma daca evaluarea este legala si controlata."
            )

    def build_guarded_task(self, task: str) -> str:
        self.validate_task(task)
        approved_targets = ", ".join(sorted(self.approved_targets)) or "workspace only"
        return (
            "Operate in authorized white-hat security assessment mode.\n"
            f"Workspace scope: {self.workspace_root}\n"
            f"Approved targets: {approved_targets}\n"
            "Rules:\n"
            "- Only controlled, non-destructive validation and verification.\n"
            "- No exploitation, persistence, exfiltration, credential theft, phishing, or command-and-control.\n"
            "- Prefer code review, configuration review, hardening, detection checks, evidence gathering, and reporting.\n"
            f"Task: {task}"
        )

    def extract_targets(self, task: str) -> List[str]:
        targets: Set[str] = set()
        for match in _URL_RE.findall(task):
            targets.add(match.strip().lower())
        for match in _IPV4_RE.findall(task):
            targets.add(match.strip().lower())
        return sorted(targets)

    def is_target_allowed(self, target: str) -> bool:
        normalized = target.strip().strip("[]").lower()
        if not normalized:
            return True
        if normalized in self.approved_targets:
            return True
        try:
            ip = ipaddress.ip_address(normalized)
        except ValueError:
            return False
        return ip.is_loopback

    @staticmethod
    def _normalize_targets(targets: Iterable[str]) -> Set[str]:
        normalized: Set[str] = set()
        for target in targets:
            value = (target or "").strip().strip("[]").lower()
            if value:
                normalized.add(value)
        return normalized


class EngineerPlatform:
    """Controlled platform for repair, audit, validation, and local automation."""

    def __init__(self, agent, workspace_root: str = ".",
                 generated_projects_dir: Optional[str] = None,
                 backup_root: Optional[str] = None,
                 autonomous_factory: Optional[Callable[[Any], Any]] = None,
                 approved_targets: Optional[Sequence[str]] = None,
                 engagement_name: str = "authorized_security_engineer"):
        self.agent = agent
        self.memory = agent.memory
        self.workspace_root = Path(workspace_root).resolve()
        self.generated_projects_dir = Path(
            generated_projects_dir or (self.workspace_root / "generated_bots")
        ).resolve()
        self.generated_projects_dir.mkdir(parents=True, exist_ok=True)

        self.engagement_name = engagement_name
        self.scope = AssessmentScope(self.workspace_root, approved_targets=approved_targets)
        self.autonomous_factory = autonomous_factory or (lambda ana_agent: AutonomousAgent(ana_agent))
        self.repair_controller = RepairController(
            agent=agent,
            memory=self.memory,
            workspace_root=str(self.workspace_root),
            backup_root=backup_root,
        )
        self.bot_factory = BotFactory(
            output_root=str(self.generated_projects_dir),
            default_model=self._default_model(),
        )
        self.lab = LocalLearningLab(self.memory)

    def get_scope(self) -> Dict[str, Any]:
        return self.scope.describe()

    def authorize_targets(self, targets: Sequence[str]) -> Dict[str, Any]:
        self.scope.approved_targets.update(self.scope._normalize_targets(targets))
        return self.get_scope()

    def run_task(self, task: str, max_steps: Optional[int] = None) -> Dict[str, Any]:
        guarded_task = self.scope.build_guarded_task(task)
        run_id = self.memory.create_engineer_run(
            profile="security_engineer",
            task=task,
            workspace=str(self.workspace_root),
            metadata={
                "engagement_name": self.engagement_name,
                "scope": self.get_scope(),
                "max_steps": max_steps,
            },
        )

        engine = self.autonomous_factory(self.agent)
        engine._project_root = self.workspace_root
        raw_result = engine.execute_task(guarded_task, max_iterations=max_steps or 10)

        plan = raw_result.get("plan")
        steps_payload: List[Dict[str, Any]] = []
        modified_files: List[str] = []
        step_order = 1

        if plan and getattr(plan, "steps", None):
            for step in plan.steps:
                details = {
                    "action": step.action,
                    "thought": step.thought,
                    "params": step.params,
                    "result": step.result,
                    "error": step.error,
                }
                steps_payload.append({
                    "action": step.action,
                    "status": step.status,
                    "thought": step.thought,
                    "result": step.result,
                    "error": step.error,
                    "description": step.description,
                })
                modified_files.extend(self._extract_modified_files(step.result))
                self.memory.log_engineer_step(
                    run_id,
                    stage=step.action,
                    title=step.description,
                    status=step.status,
                    details=details,
                    step_order=step_order,
                )
                step_order += 1
        else:
            self.memory.log_engineer_step(
                run_id,
                stage="execute",
                title="Execute guarded task",
                status="completed" if raw_result.get("success", False) else "failed",
                details={"raw_result": raw_result},
                step_order=step_order,
            )

        normalized_files = self._normalize_modified_files(modified_files)
        result = {
            "run_id": run_id,
            "success": raw_result.get("success", True),
            "task": task,
            "guarded_task": guarded_task,
            "iterations": raw_result.get("iterations", raw_result.get("completed_steps", 0)),
            "completed_steps": raw_result.get("completed_steps", len(steps_payload)),
            "total_steps": raw_result.get("total_steps", len(steps_payload)),
            "elapsed_time": raw_result.get("elapsed_time", 0.0),
            "output": raw_result.get("output", ""),
            "steps": steps_payload,
            "modified_files": normalized_files,
        }
        summary = (
            f"Authorized run finished with {result['completed_steps']}/{result['total_steps']} "
            f"steps and {len(normalized_files)} modified files."
        )
        self.memory.finalize_engineer_run(
            run_id,
            "completed" if result["success"] else "failed",
            summary,
            result,
        )
        return result

    def repair_project(self, target: str = ".",
                       test_command: Optional[Sequence[str] | str] = None,
                       error_text: str = "") -> Dict[str, Any]:
        resolved = self._resolve_workspace_path(target)
        return self.repair_controller.repair_project(
            target=resolved,
            test_command=test_command,
            error_text=error_text,
        )

    def create_bot(self, spec: str, name: str = "",
                   output_dir: str = "") -> Dict[str, Any]:
        run_id = self.memory.create_engineer_run(
            profile="bot_factory",
            task=f"create_bot:{spec}",
            workspace=str(self.workspace_root),
            metadata={"name": name, "output_dir": output_dir},
        )
        result = self.bot_factory.create_bot(spec, name=name, output_dir=output_dir)
        self.memory.record_generated_project(
            project_name=result["name"],
            project_path=result["project_dir"],
            project_type="cli_bot",
            spec={"spec": spec},
            metadata={"run_id": run_id},
        )
        self.memory.finalize_engineer_run(
            run_id,
            "completed",
            f"Created bot {result['name']}",
            result,
        )
        return result

    def show_run(self, run_id: str) -> Dict[str, Any]:
        run = self.memory.get_engineer_run(run_id)
        if not run:
            raise ValueError(f"Run not found: {run_id}")
        return run

    def learn_from_run(self, run_id: str) -> Dict[str, Any]:
        return self.lab.learn_from_run(run_id)

    def list_runs(self, limit: int = 20) -> List[Dict[str, Any]]:
        return self.memory.list_engineer_runs(limit=limit)

    def _resolve_workspace_path(self, candidate: str) -> str:
        path = Path(candidate)
        if not path.is_absolute():
            path = (self.workspace_root / path).resolve()
        else:
            path = path.resolve()

        try:
            path.relative_to(self.workspace_root)
        except ValueError as exc:
            raise ValueError(
                f"Path in afara workspace-ului autorizat: {path}"
            ) from exc
        return str(path)

    def _default_model(self) -> str:
        try:
            from core.config import config
            return config.get("ai.ollama.model", "codellama")
        except Exception:
            return "codellama"

    def _extract_modified_files(self, result: Any) -> List[str]:
        if not isinstance(result, dict):
            return []

        discovered: List[str] = []
        for key in ("file", "file_path", "path"):
            value = result.get(key)
            if isinstance(value, str) and value.strip():
                discovered.append(value.strip())

        for key in ("files", "modified_files", "changed_files"):
            value = result.get(key)
            if isinstance(value, list):
                discovered.extend(str(item).strip() for item in value if str(item).strip())

        return discovered

    def _normalize_modified_files(self, files: Sequence[str]) -> List[str]:
        normalized: List[str] = []
        seen: Set[str] = set()

        for item in files:
            value = (item or "").strip()
            if not value:
                continue

            candidate = Path(value)
            if candidate.is_absolute():
                try:
                    display = str(candidate.resolve().relative_to(self.workspace_root))
                except ValueError:
                    display = str(candidate.resolve())
            else:
                display = value.replace("\\", "/")

            if display not in seen:
                seen.add(display)
                normalized.append(display)
        return normalized


EngineerPlatformMax = EngineerPlatform


def launch_max_engineer(agent):
    """Compatibility launcher for a safe authorized local assessment profile."""
    return EngineerPlatform(
        agent=agent,
        workspace_root=".",
        approved_targets=["127.0.0.1", "localhost"],
        engagement_name="authorized_lab_assessment",
    )


__all__ = ["EngineerPlatform", "EngineerPlatformMax", "launch_max_engineer"]
