"""
ANA MAX - Autonomous Agent
==========================
AutonomousAgent: agent care descompune task-uri complexe in pasi
si le executa secvential folosind tool-urile ANA.

Acesta este agentul de productivitate al ANA — nu are nicio legatura
cu activitati de tip pentest sau exploatare.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
import os
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums & dataclasses
# ---------------------------------------------------------------------------

class TaskStatus(Enum):
    PENDING = "pending"
    PLANNING = "planning"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    FIXING = "fixing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class TaskStep:
    id: int
    description: str
    action: str          # ex: "code", "file", "web", "terminal", "think"
    thought: str = ""
    params: Dict[str, Any] = field(default_factory=dict)
    status: str = "pending"
    result: Optional[Any] = None
    error: Optional[str] = None
    retries: int = 0
    max_retries: int = 3


@dataclass
class TaskPlan:
    task_description: str
    steps: List[TaskStep]
    reasoning: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    completed_steps: int = 0
    total_steps: int = 0


# ---------------------------------------------------------------------------
# AutonomousAgent
# ---------------------------------------------------------------------------

class AutonomousAgent:
    """
    Agent autonom pentru executia task-urilor complexe.

    Workflow:
    1. PLAN  - descompune task-ul in pasi folosind backend-ul AI
    2. EXEC  - executa fiecare pas cu tool-urile disponibile
    3. VERIFY- verifica rezultatele si repara daca e nevoie
    """

    _SUPPORTED_ACTIONS = {
        "think",      # rationament intern / raspuns text
        "code",       # analiza sau generare cod
        "file",       # operatii pe fisiere
        "web",        # cautare web
        "terminal",   # comenzi sistem (cu sandbox)
        "memory",     # stocare/recuperare din memorie
        "search",     # cautare codebase
    }

    def __init__(self, ana_agent):
        """
        Parametri:
            ana_agent: instanta de ANAAgent cu metoda send_message()
        """
        self.ana = ana_agent
        self.current_plan: Optional[TaskPlan] = None
        self.task_history: List[Dict] = []
        self._max_steps = 50
        self._project_root = Path.cwd()
        logger.info("AutonomousAgent initializat.")

    # ------------------------------------------------------------------
    # API public
    # ------------------------------------------------------------------

    def execute_task(self, task: str, max_iterations: int = 20) -> Dict[str, Any]:
        """
        Executa un task complex.

        Parametri:
            task (str): Descrierea task-ului.
            max_iterations (int): Numarul maxim de iteratii.

        Returneaza:
            dict cu cheile: success, output, completed_steps, total_steps, elapsed_time
        """
        if not task or not task.strip():
            return self._result(False, "Task-ul este gol.", 0, 0, 0.0)

        logger.info(f"AutonomousAgent: task primit: {task[:100]}")
        start_time = time.time()

        # 1. Planificare
        plan = self._create_plan(task)
        self.current_plan = plan

        # 2. Executie pas cu pas
        iterations = 0
        while iterations < max_iterations:
            iterations += 1

            if plan.completed_steps >= plan.total_steps:
                logger.info("Toate pasii au fost completati.")
                break

            step = self._get_next_step(plan)
            if step is None:
                break

            self._execute_step(step)

            if step.status == "completed":
                plan.completed_steps += 1
            elif step.status == "failed" and step.retries >= step.max_retries:
                logger.warning(f"Pasul {step.id} a esuat dupa {step.retries} incercari: {step.error}")
                plan.completed_steps += 1  # trecem mai departe

        elapsed = time.time() - start_time
        success = all(step.status == "completed" for step in plan.steps) if plan.total_steps > 0 else True

        # Construim output-ul din rezultatele pasilor
        output = self._build_output(plan)

        result = self._result(success, output, plan.completed_steps, plan.total_steps, elapsed)
        self.task_history.append(result)
        return result

    # ------------------------------------------------------------------
    # Planificare
    # ------------------------------------------------------------------

    def _create_plan(self, task: str) -> TaskPlan:
        """Cere backend-ului AI sa creeze un plan de executie."""
        fallback_steps = self._create_fallback_plan(task)
        if fallback_steps:
            return TaskPlan(
                task_description=task,
                steps=fallback_steps,
                reasoning="Plan deterministic bazat pe instructiuni operationale explicite",
                total_steps=len(fallback_steps),
            )

        if self.ana is None or getattr(self.ana, "backend", "none") == "none":
            return self._simple_plan(task)

        prompt = (
            f"Esti un agent de productivitate. Primesti un task si trebuie sa il planifici.\n"
            f"Task: {task}\n\n"
            f"Raspunde DOAR cu JSON valid, fara explicatii:\n"
            f'{{"reasoning": "...", "steps": ['
            f'{{"id":1,"description":"...","action":"think","params":{{}}}}'
            f"]}}\n\n"
            f"Actiuni disponibile: think, code, file, web, terminal, memory, search\n"
            f"Pastreaza planul simplu si eficient (max 8 pasi)."
        )

        try:
            response = self.ana.send_message(prompt, allow_auto_tools=False)
            # extrage JSON din raspuns
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                data = json.loads(response[json_start:json_end])
                steps = []
                for s in data.get("steps", []):
                    steps.append(TaskStep(
                        id=s.get("id", len(steps) + 1),
                        description=s.get("description", ""),
                        action=s.get("action", "think"),
                        thought=s.get("thought", ""),
                        params=s.get("params", {})
                    ))
                if steps:
                    return TaskPlan(
                        task_description=task,
                        steps=steps,
                        reasoning=data.get("reasoning", ""),
                        total_steps=len(steps)
                    )
        except Exception as e:
            logger.warning(f"Nu am putut parsa planul AI: {e}. Folosesc plan simplu.")

        return self._simple_plan(task)

    def _simple_plan(self, task: str) -> TaskPlan:
        """Plan fallback cu un singur pas de tip 'think'."""
        fallback_steps = self._create_fallback_plan(task)
        if fallback_steps:
            return TaskPlan(
                task_description=task,
                steps=fallback_steps,
                reasoning="Plan fallback bazat pe instructiuni explicite din task",
                total_steps=len(fallback_steps),
            )
        steps = [
            TaskStep(id=1, description="Proceseaza task-ul", action="think", params={"task": task})
        ]
        return TaskPlan(
            task_description=task,
            steps=steps,
            reasoning="Plan simplu (backend AI indisponibil sau plan invalid)",
            total_steps=1
        )

    # ------------------------------------------------------------------
    # Executie
    # ------------------------------------------------------------------

    def _get_next_step(self, plan: TaskPlan) -> Optional[TaskStep]:
        for step in plan.steps:
            if step.status == "pending":
                return step
        return None

    def _execute_step(self, step: TaskStep) -> bool:
        step.status = "executing"
        logger.info(f"Executie pas {step.id}: {step.description} (actiune: {step.action})")

        try:
            if step.action == "think":
                result = self._action_think(step)
            elif step.action == "code":
                result = self._action_code(step)
            elif step.action == "file":
                result = self._action_file(step)
            elif step.action == "web":
                result = self._action_web(step)
            elif step.action == "terminal":
                result = self._action_terminal(step)
            elif step.action == "memory":
                result = self._action_memory(step)
            elif step.action == "search":
                result = self._action_search(step)
            else:
                # actiune necunoscuta → fallback la think
                result = self._action_think(step)

            if self._result_indicates_failure(step.action, result):
                step.error = str(result)
                step.result = None
                step.status = "failed"
                step.retries += 1
                if step.retries < step.max_retries:
                    step.status = "pending"
                return False

            step.result = result
            step.status = "completed"
            return True

        except Exception as e:
            step.error = str(e)
            step.status = "failed"
            step.retries += 1
            logger.error(f"Pasul {step.id} a esuat: {e}")
            if step.retries < step.max_retries:
                step.status = "pending"  # permite reincercare
            return False

    def _result_indicates_failure(self, action: str, result: Any) -> bool:
        text = str(result or "")
        lowered = text.lower()
        if action == "code":
            return any(marker in lowered for marker in ["syntax error", "eroare", "error:", "traceback"])
        if action == "terminal":
            return any(marker in lowered for marker in ["command exited", "exit code 1", "eroare", "error:"])
        return False

    # ------------------------------------------------------------------
    # Actiuni individuale
    # ------------------------------------------------------------------

    def _action_think(self, step: TaskStep) -> str:
        """Trimite task-ul la AI si returneaza raspunsul."""
        if self.ana is None or getattr(self.ana, "backend", "none") == "none":
            return f"[think] Task procesat local: {step.description}"

        query = step.params.get("task") or step.params.get("query") or step.description
        return self.ana.send_message(query)

    def _action_code(self, step: TaskStep) -> str:
        """Analizeaza sau genereaza cod."""
        file_path = step.params.get("file_path")
        description = step.params.get("description", step.description)

        generated = self._action_think(
            TaskStep(
                id=step.id,
                description=description,
                action="think",
                params={"task": description},
            )
        )

        syntax_error = self._validate_python_syntax(generated)
        if syntax_error:
            raise ValueError(f"Syntax error: {syntax_error}")

        if file_path:
            target = Path(file_path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(generated, encoding="utf-8")
            return f"Cod salvat in {target}"

        return generated

    def _action_file(self, step: TaskStep) -> str:
        """Operatii pe fisiere prin tool-ul file_operations."""
        try:
            from tools.base import registry
            result = registry.execute("file_operations", **step.params)
            return result.data if result.is_success else f"Eroare fisier: {result.error}"
        except Exception as e:
            return f"Eroare la operatia pe fisier: {e}"

    def _action_web(self, step: TaskStep) -> str:
        """Cautare web prin tool-ul web_search."""
        try:
            from tools.base import registry
            result = registry.execute("web_search", **step.params)
            return result.data if result.is_success else f"Eroare web: {result.error}"
        except Exception as e:
            return f"Eroare la cautarea web: {e}"

    def _action_terminal(self, step: TaskStep) -> str:
        """Executa o comanda de sistem prin tool-ul terminal ANA."""
        command = step.params.get("command", "")
        if not command:
            return "Nicio comanda specificata."

        from tools.base import registry

        result = registry.execute(
            "terminal",
            operation="run",
            command=command,
            timeout=step.params.get("timeout", 30),
        )
        if not result.is_success:
            raise RuntimeError(result.error or result.message or "Terminal tool failed")

        payload = result.data or {}
        stdout = str(payload.get("stdout", "")).strip()
        stderr = str(payload.get("stderr", "")).strip()
        cwd = str(payload.get("cwd", "")).strip()
        exit_code = payload.get("exit_code", 0)

        parts = []
        if stdout:
            parts.append(stdout)
        if stderr:
            parts.append(f"stderr: {stderr}")
        if cwd:
            parts.append(f"cwd: {cwd}")
        parts.append(f"exit_code: {exit_code}")
        return "\n".join(parts)

    def _action_memory(self, step: TaskStep) -> str:
        """Acceseaza memoria ANA."""
        try:
            from core.memory import get_memory
            memory = get_memory()
            operation = step.params.get("operation", "get")
            if operation == "save":
                topic = step.params.get("topic", "")
                content = step.params.get("content", "")
                memory.save_knowledge(topic, content)
                return f"Salvat in memorie: {topic}"
            else:
                topic = step.params.get("topic") or step.params.get("query", "")
                result = memory.get_knowledge(topic)
                return result or f"Nu am gasit informatii despre: {topic}"
        except Exception as e:
            return f"Eroare la accesarea memoriei: {e}"

    def _action_search(self, step: TaskStep) -> str:
        """Cauta in codebase."""
        try:
            from tools.base import registry
            result = registry.execute("smart_search", **step.params)
            return result.data if result.is_success else f"Eroare cautare: {result.error}"
        except Exception as e:
            return f"Eroare la cautare: {e}"

    # ------------------------------------------------------------------
    # Utilitare
    # ------------------------------------------------------------------

    def _build_output(self, plan: TaskPlan) -> str:
        """Construieste un output text din rezultatele tuturor pasilor."""
        parts = []
        for step in plan.steps:
            if step.result:
                parts.append(str(step.result))
            elif step.error:
                parts.append(f"[Eroare pas {step.id}]: {step.error}")
        return "\n\n".join(parts) if parts else "Task executat."

    @staticmethod
    def _result(success: bool, output: str, completed: int,
                total: int, elapsed: float) -> Dict[str, Any]:
        return {
            "success": success,
            "output": output,
            "completed_steps": completed,
            "total_steps": total,
            "elapsed_time": elapsed,
        }

    def get_status(self) -> Dict[str, Any]:
        plan = self.current_plan
        if not plan:
            return {"status": "idle"}
        return {
            "status": "running",
            "task": plan.task_description[:80],
            "progress": f"{plan.completed_steps}/{plan.total_steps}",
        }

    def _fix_step(self, step: TaskStep) -> None:
        """Request replacement steps for a failed step and inject them into the plan."""
        if self.current_plan is None or self.ana is None:
            return

        prompt = (
            "Un pas a esuat. Ofera un JSON cu cheile explanation si new_steps pentru remediere.\n"
            f"step={step.description}\nerror={step.error or ''}"
        )
        response = self.ana.send_message(prompt)
        json_start = response.find("{")
        json_end = response.rfind("}") + 1
        if json_start < 0 or json_end <= json_start:
            return

        try:
            data = json.loads(response[json_start:json_end])
        except Exception:
            return

        new_steps: List[TaskStep] = []
        for item in data.get("new_steps", []):
            new_steps.append(
                TaskStep(
                    id=item.get("id", len(new_steps) + 100),
                    description=item.get("description", "Remediere"),
                    action=item.get("action", "think"),
                    params=item.get("params", {}),
                )
            )

        if not new_steps:
            return

        existing = self.current_plan.steps
        try:
            index = existing.index(step)
        except ValueError:
            index = 0
        self.current_plan.steps = existing[:index] + new_steps + existing[index:]
        self.current_plan.total_steps = len(self.current_plan.steps)

    def _create_fallback_plan(self, task: str) -> List[TaskStep]:
        """Build deterministic fallback plans for explicit operational tasks."""
        lowered = task.lower()
        folder_plan = self._create_folder_plan(task, lowered)
        if folder_plan:
            return folder_plan
        return []

    def _create_folder_plan(self, task: str, lowered: str) -> List[TaskStep]:
        """Infer folder create/delete tasks from natural language."""
        target = self._resolve_folder_target(task, lowered)
        if not target:
            return []

        wants_create = any(term in lowered for term in ("create", "cree", "creaza", "creeaza"))
        wants_delete = any(term in lowered for term in ("delete", "sterge", "șterge"))

        if wants_create and not wants_delete:
            create_cmd = self._wrap_powershell(f"New-Item -ItemType Directory -Force -Path '{target}' | Out-Null")
            verify_exists_cmd = self._wrap_powershell(
                f"if (-not (Test-Path '{target}')) {{ exit 1 }} else {{ Write-Output 'Folder creat: {target}' }}"
            )
            return [
                TaskStep(id=1, description="Create folder", action="terminal", params={"command": create_cmd}),
                TaskStep(id=2, description="Verify folder exists", action="terminal", params={"command": verify_exists_cmd}),
            ]

        if wants_delete and not wants_create:
            delete_cmd = self._wrap_powershell(f"Remove-Item -LiteralPath '{target}' -Recurse -Force")
            verify_missing_cmd = self._wrap_powershell(
                f"if (Test-Path '{target}') {{ exit 1 }} else {{ Write-Output 'Folder sters: {target}' }}"
            )
            return [
                TaskStep(id=1, description="Delete folder", action="terminal", params={"command": delete_cmd}),
                TaskStep(id=2, description="Verify folder missing", action="terminal", params={"command": verify_missing_cmd}),
            ]

        return []

    def _resolve_folder_target(self, task: str, lowered: str) -> Optional[str]:
        explicit = self._extract_explicit_path(task)
        if explicit:
            return explicit

        if "folder" not in lowered and "director" not in lowered:
            return None

        folder_name = self._extract_folder_name(task)
        if not folder_name:
            return None

        base_dir = self._project_root
        if "desktop" in lowered:
            base_dir = Path.home() / "Desktop"
        elif any(term in lowered for term in ("workspace", "spatiul meu de lucru", "spațiul meu de lucru", "proiect")):
            base_dir = self._project_root

        return str(base_dir / folder_name)

    @staticmethod
    def _extract_folder_name(task: str) -> Optional[str]:
        patterns = [
            r'folder(?:ul)?\s+(?:cu numele|numit)?\s*"([^"]+)"',
            r"folder(?:ul)?\s+(?:cu numele|numit)?\s+'([^']+)'",
            r"folder(?:ul)?\s+(?:cu numele|numit)?\s+([A-Za-z0-9._-]+)",
            r"director(?:ul)?\s+(?:cu numele|numit)?\s+([A-Za-z0-9._-]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, task, re.IGNORECASE)
            if match:
                candidate = match.group(1).strip().strip(".")
                if candidate:
                    return candidate
        return None

    @staticmethod
    def _wrap_powershell(script: str) -> str:
        escaped = script.replace('"', '`"')
        return f'powershell -NoProfile -Command "{escaped}"'

    @staticmethod
    def _extract_explicit_path(task: str) -> Optional[str]:
        match = re.search(r"([A-Za-z]:\\[^\n,]+|/[^\n,]+)", task)
        if not match:
            return None
        return match.group(1).strip().rstrip(".")

    @staticmethod
    def _run_local_command(command: str) -> Dict[str, Any]:
        import subprocess

        completed = subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            capture_output=True,
            text=True,
        )
        return {
            "returncode": completed.returncode,
            "stdout": completed.stdout.strip(),
            "stderr": completed.stderr.strip(),
            "message": f"Command exited with status {completed.returncode}",
        }

    @staticmethod
    def _validate_python_syntax(code: str) -> Optional[str]:
        import ast

        try:
            ast.parse(code)
            return None
        except SyntaxError as exc:
            return str(exc)


# Backward-compatible aliases expected by tests and older modules.
Step = TaskStep
Plan = TaskPlan
