"""
ANA MAX - Autonomous Agent
==========================
AutonomousAgent: agent care descompune task-uri complexe in pasi
si le executa secvential folosind tool-urile ANA.

Acesta este agentul de productivitate al ANA - nu are nicio legatura
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
        self._current_read_only = self._is_read_only_task(task)

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
        if self._is_read_only_task(task):
            return TaskPlan(
                task_description=task,
                steps=[TaskStep(id=1, description="Proceseaza task-ul read-only", action="think", params={"task": task})],
                reasoning="Read-only request: bypass deterministic mutating fallback plans",
                total_steps=1,
            )

        fallback_steps = self._create_fallback_plan(task)
        if fallback_steps:
            return TaskPlan(
                task_description=task,
                steps=fallback_steps,
                reasoning="Plan deterministic bazat pe instructiuni operationale explicite",
                total_steps=len(fallback_steps),
            )

        # Modelele locale mici nu genereaza mereu planuri JSON complexe corect.
        # Folosim intotdeauna _simple_plan care:
        #   1. Incearca fallback deterministic (folder/terminal/web) - fara LLM
        #   2. Altfel trimite la text-injection (ACTION blocks)
        logger.info("AutonomousAgent: Bypass JSON plan, folosim Ollama text-injection.")
        return self._simple_plan(task)

        if self.ana is None or getattr(self.ana, "backend", "none") == "none":
            return self._simple_plan(task)

        prompt = (
            f"Esti un agent de productivitate. Primesti un task si trebuie sa il planifici.\n"
            f"Task: {task}\n\n"
            "Raspunde DOAR cu JSON valid, fara explicatii sau markdown blocks. Structura JSON:\n"
            "{\n"
            "  \"reasoning\": \"Explicatie scurta a planului\",\n"
            "  \"steps\": [\n"
            "    {\n"
            "      \"id\": 1,\n"
            "      \"description\": \"Creeaza folderul proiect\",\n"
            "      \"action\": \"terminal\",\n"
            "      \"params\": {\"command\": \"mkdir proiect\"}\n"
            "    },\n"
            "    {\n"
            "      \"id\": 2,\n"
            "      \"description\": \"Creeaza fisierul index.py cu un salut\",\n"
            "      \"action\": \"file\",\n"
            "      \"params\": {\"operation\": \"write\", \"path\": \"proiect/index.py\", \"content\": \"print('Hello')\"}\n"
            "    },\n"
            "    {\n"
            "      \"id\": 3,\n"
            "      \"description\": \"Cautare pe web despre Python\",\n"
            "      \"action\": \"web\",\n"
            "      \"params\": {\"operation\": \"search\", \"query\": \"Python tutorial\"}\n"
            "    }\n"
            "  ]\n"
            "}\n\n"
            "Actiuni si parametrii lor:\n"
            "- think: {}\n"
            "- code: {\"file_path\": \"...\", \"description\": \"ce cod sa scrie\"}\n"
            "- file: {\"operation\": \"read\"|\"write\"|\"list\", \"path\": \"...\", \"content\": \"...\"}\n"
            "- web: {\"operation\": \"search\", \"query\": \"...\"}\n"
            "- terminal: {\"command\": \"...\"}\n"
            "- search: {\"query\": \"...\"}\n"
            "Fii foarte explicit si populeaza intotdeauna campul 'params' cu argumentele necesare pentru fiecare actiune (de ex. 'command' pentru terminal, 'path'/'operation'/'content' pentru file)."
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
        if self._is_read_only_task(task):
            steps = [
                TaskStep(id=1, description="Proceseaza task-ul read-only", action="think", params={"task": task})
            ]
            return TaskPlan(
                task_description=task,
                steps=steps,
                reasoning="Read-only request: use think/text-injection only",
                total_steps=len(steps),
            )

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

    @staticmethod
    def _is_read_only_task(task: str) -> bool:
        text = task.lower()
        markers = (
            "read-only",
            "read only",
            "doar citire",
            "nu modifica",
            "nu scrie",
            "nu sterge",
            "nu rula comenzi mutante",
            "analizeaza",
            "inspecteaza",
            "fara sa faca nimic",
            "fara modificari",
        )
        return any(marker in text for marker in markers)

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
                # actiune necunoscuta  fallback la think
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
        response = self.ana.send_message(query)
        if isinstance(response, str) and response.startswith("Eroare la procesarea mesajului:"):
            raise RuntimeError(response)
        return response

    def _deduce_params_from_description(self, action: str, description: str) -> Dict[str, Any]:
        """Deduce parametrii din descrierea in limbaj natural daca params este gol."""
        params = {}
        lowered = description.lower()

        # Cauta siruri intre ghilimele sau cuvinte cu extensii de fisier
        quoted = re.findall(r"['\"]([^'\"]+)['\"]", description)
        files = re.findall(r"\b[a-zA-Z0-9_\-\/\\\.]+\.[a-zA-Z0-9_]{1,4}\b", description)

        path = None
        if quoted:
            path = quoted[0]
        elif files:
            path = files[0]

        if action == "file":
            if path:
                params["path"] = path
            # Deducem operatia
            if any(term in lowered for term in ("create", "write", "make", "salveaza", "scrie", "creaza", "creeaza")):
                params["operation"] = "write"
            elif any(term in lowered for term in ("list", "directory", "folder", "afiseaza", "arata", "vezi")):
                params["operation"] = "list"
            elif any(term in lowered for term in ("edit", "replace", "modify", "surgical", "surgical_edit")):
                params["operation"] = "edit"
            else:
                params["operation"] = "read"

        elif action == "code":
            if path:
                params["file_path"] = path
            params["description"] = description

        elif action == "terminal":
            cmd = None
            if quoted:
                for q in quoted:
                    if any(q.strip().startswith(term) for term in ("mkdir ", "cd ", "python ", "pip ", "git ", "npm ", "node ", "rm ", "echo ")):
                        cmd = q
                        break
            if not cmd:
                # Deducem comenzi standard pe baza descrierii
                if "create" in lowered and ("folder" in lowered or "directory" in lowered or "director" in lowered):
                    folder_name = quoted[0] if quoted else (files[0] if files else "compass")
                    if "desktop" in lowered or "descktop" in lowered:
                        desktop = os.path.expanduser("~/Desktop")
                        cmd = f'powershell -NoProfile -Command "New-Item -ItemType Directory -Force -Path \'{desktop}\\{folder_name}\' | Out-Null"'
                    else:
                        cmd = f'powershell -NoProfile -Command "New-Item -ItemType Directory -Force -Path \'{folder_name}\' | Out-Null"'
                elif "navigate" in lowered or "cd " in lowered or "go to" in lowered:
                    folder_name = quoted[0] if quoted else (files[0] if files else "compass")
                    if "desktop" in lowered or "descktop" in lowered:
                        desktop = os.path.expanduser("~/Desktop")
                        cmd = f"cd '{desktop}\\{folder_name}'"
                    else:
                        cmd = f"cd '{folder_name}'"
                elif any(term in lowered for term in ("run ", "execute ", "ruleaza ", "executa ")):
                    script_name = path if path else "compass.py"
                    cmd = f"python {script_name}"
            if not cmd:
                cmd = description
            params["command"] = cmd
            params["operation"] = "run"

        elif action == "web":
            query = quoted[0] if quoted else description.replace("Search", "").replace("search", "").strip()
            params["query"] = query
            params["operation"] = "search"

        elif action == "search":
            query = quoted[0] if quoted else description
            params["query"] = query
            params["action"] = "search"

        return params

    def _action_code(self, step: TaskStep) -> str:
        """Analizeaza sau genereaza cod."""
        params = step.params.copy() if step.params else {}
        if not params:
            params = self._deduce_params_from_description("code", step.description)

        for k in ["path", "filepath", "target", "file"]:
            if k in params and "file_path" not in params:
                params["file_path"] = params.pop(k)

        file_path = params.get("file_path")
        description = params.get("description", step.description)

        generated = self._action_think(
            TaskStep(
                id=step.id,
                description=description,
                action="think",
                params={"task": description},
            )
        )

        # Extrage codul daca exista markdown blocks (ex. ```python ... ```)
        code_to_write = generated
        if "```" in generated:
            pattern = r"```(?:python|py)?\n(.*?)\n```"
            match = re.search(pattern, generated, re.DOTALL | re.IGNORECASE)
            if match:
                code_to_write = match.group(1)
            else:
                code_to_write = re.sub(r"```[a-zA-Z]*\n?", "", generated).strip()

        # Valideaza sintaxa Python doar daca e fisier .py
        if file_path and str(file_path).lower().endswith(".py"):
            syntax_error = self._validate_python_syntax(code_to_write)
            if syntax_error:
                raise ValueError(f"Syntax error in Python code: {syntax_error}")

        if file_path:
            target = Path(file_path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(code_to_write, encoding="utf-8")
            return f"Cod salvat in {target}"

        return code_to_write

    def _action_file(self, step: TaskStep) -> str:
        """Operatii pe fisiere prin tool-ul file_operations."""
        try:
            from tools.base import registry
            params = step.params.copy() if step.params else {}
            if not params:
                params = self._deduce_params_from_description("file", step.description)

            # Map key aliases to standard 'path'
            for k in ["file_path", "filepath", "file", "target"]:
                if k in params and "path" not in params:
                    params["path"] = params.pop(k)

            # Map 'action' to 'operation' if needed
            if "action" in params and "operation" not in params:
                params["operation"] = params.pop("action")

            # Map content aliases
            for k in ["text", "text_content", "data"]:
                if k in params and "content" not in params:
                    params["content"] = params.pop(k)

            # If operation is still missing, infer it
            if "operation" not in params:
                if "content" in params:
                    params["operation"] = "write"
                elif "search_text" in params or "replace_text" in params:
                    params["operation"] = "edit"
                elif "old_block" in params or "new_block" in params:
                    params["operation"] = "surgical_edit"
                elif "pattern" in params:
                    params["operation"] = "search"
                else:
                    params["operation"] = "read"

            # If path is directory and operation is read, default to list
            path = params.get("path")
            if path and os.path.isdir(path) and params.get("operation") == "read":
                params["operation"] = "list"

            # If path is missing, default to current directory
            if not params.get("path"):
                params["path"] = "."

            result = registry.execute("file_operations", **params)
            return result.data if result.is_success else f"Eroare fisier: {result.error}"
        except Exception as e:
            return f"Eroare la operatia pe fisier: {e}"

    def _action_web(self, step: TaskStep) -> str:
        """Cautare web prin tool-ul web_search."""
        try:
            from tools.base import registry
            params = step.params.copy() if step.params else {}
            if not params:
                params = self._deduce_params_from_description("web", step.description)

            # Map 'action' to 'operation'
            if "action" in params and "operation" not in params:
                params["operation"] = params.pop("action")

            # If operation is missing, default to search
            if "operation" not in params:
                params["operation"] = "search"

            # Map query aliases
            for k in ["q", "search_query", "text", "url"]:
                if k in params and "query" not in params:
                    params["query"] = params.pop(k)

            # If query is missing, try to get it from description
            if "query" not in params:
                params["query"] = step.description or "Python"

            result = registry.execute("web_search", **params)
            return result.data if result.is_success else f"Eroare web: {result.error}"
        except Exception as e:
            return f"Eroare la cautarea web: {e}"

    def _action_terminal(self, step: TaskStep) -> str:
        """Executa o comanda de sistem prin tool-ul terminal ANA."""
        params = step.params.copy() if step.params else {}
        if not params:
            params = self._deduce_params_from_description("terminal", step.description)

        # Map command aliases
        for k in ["cmd", "run", "text"]:
            if k in params and "command" not in params:
                params["command"] = params.pop(k)

        command = params.get("command", "")
        if not command:
            command = step.description or ""

        if not command:
            return "Nicio comanda specificata."

        from tools.base import registry

        result = registry.execute(
            "terminal",
            operation="run",
            command=command,
            timeout=params.get("timeout", 30),
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
            params = step.params.copy() if step.params else {}

            # Map 'operation' to 'action'
            if "operation" in params and "action" not in params:
                params["action"] = params.pop("operation")

            # If action is missing, default to search
            if "action" not in params:
                params["action"] = "search"

            # Map query aliases
            for k in ["q", "search_query", "text", "pattern"]:
                if k in params and "query" not in params:
                    params["query"] = params.pop(k)

            # If query is missing, try to get it from description
            if "query" not in params:
                params["query"] = step.description or ""

            result = registry.execute("smart_search", **params)
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
        
        # 1. Folder creation/deletion
        folder_plan = self._create_folder_plan(task, lowered)
        if folder_plan:
            return folder_plan
            
        # 2. Terminal execution
        terminal_plan = self._create_terminal_plan(task, lowered)
        if terminal_plan:
            return terminal_plan
            
        # 3. Web Search
        web_plan = self._create_web_plan(task, lowered)
        if web_plan:
            return web_plan
            
        return []

    def _create_terminal_plan(self, task: str, lowered: str) -> List[TaskStep]:
        if not any(term in lowered for term in ("ruleaza", "ruleaza", "executa", "executa", "run")):
            return []
        match = re.search(r'(?:comanda|comanda|cmd|command)\s+(.+)$', task, re.IGNORECASE)
        if match:
            cmd = match.group(1).strip().strip('"`\'')
            if cmd:
                return [
                    TaskStep(id=1, description=f"Ruleaza comanda: {cmd}", action="terminal", params={"command": cmd})
                ]
        return []

    def _create_web_plan(self, task: str, lowered: str) -> List[TaskStep]:
        if not any(term in lowered for term in ("cauta", "caut?", "google", "search")):
            return []
        match = re.search(r'(?:cauta pe google|caut? pe google|cauta pe net|caut? pe net|cauta|caut?|search)\s+(.+)$', task, re.IGNORECASE)
        if match:
            query = self._normalize_web_query(match.group(1))
            if query:
                return [
                    TaskStep(id=1, description=f"Caut? pe web: {query}", action="web", params={"query": query})
                ]
        return []

    @staticmethod
    def _normalize_web_query(raw_query: str) -> str:
        query = str(raw_query or "").strip().strip('"`\'')
        lowered = query.lower()
        lowered = re.sub(r"\bppe\s+google\b", "pe google", lowered)
        lowered = re.sub(r"\bpe\s+gogle\b", "pe google", lowered)
        lowered = re.sub(r"\b(ana|te rog|deschide|browserul|browser|si|cauta|caut?|search|pe|google|web|internet)\b", " ", lowered)
        lowered = re.sub(r"\s+", " ", lowered).strip(" :-,.;")
        return lowered or query

    def _create_folder_plan(self, task: str, lowered: str) -> List[TaskStep]:
        """Infer folder create/delete/script tasks from natural language."""
        target = self._resolve_folder_target(task, lowered)
        if not target:
            return []

        wants_create = any(term in lowered for term in (
            "create", "cree", "creaza", "creaza", "creeaza", "creaza", "fa ", "fa ", "fa pe", "fa pe"
        ))
        wants_delete = any(term in lowered for term in ("delete", "sterge", "sterge"))

        # ---------------------------------------------------------------
        # Detectam daca se cere si un script Python in acel folder
        # ---------------------------------------------------------------
        wants_script = any(term in lowered for term in (
            "script", ".py", "python", "busola", "busol", "compass",
            "buspla", "fisier py", "fisier py", "script py", "cod py",
            "program py", "program python",
        ))

        if wants_create and not wants_delete:
            target_path = Path(target)
            create_cmd = self._wrap_powershell(
                f"New-Item -ItemType Directory -Force -Path '{target}' | Out-Null"
            )
            verify_exists_cmd = self._wrap_powershell(
                f"if (-not (Test-Path '{target}')) {{ exit 1 }} else "
                f"{{ Write-Output 'Folder creat: {target}' }}"
            )

            if not wants_script:
                return [
                    TaskStep(id=1, description="Create folder", action="terminal",
                             params={"command": create_cmd}),
                    TaskStep(id=2, description="Verify folder exists", action="terminal",
                             params={"command": verify_exists_cmd}),
                ]

            # ------- Plan: folder + script Python -------
            # Determinam numele scriptului
            script_name = self._extract_script_name(task, lowered, target_path.name)
            script_path = target_path / script_name

            # Continut busola/compass Python
            script_content = self._generate_script_content(script_name, lowered)

            # Scriem fisierul direct prin Path (nu mai depindem de tool)
            write_step = TaskStep(
                id=3,
                description=f"Write Python script {script_name}",
                action="file",
                params={
                    "operation": "write",
                    "path": str(script_path),
                    "content": script_content,
                },
            )
            verify_script_cmd = self._wrap_powershell(
                f"if (-not (Test-Path '{script_path}')) {{ exit 1 }} else "
                f"{{ Write-Output 'Script creat: {script_path}' }}"
            )
            return [
                TaskStep(id=1, description="Create folder", action="terminal",
                         params={"command": create_cmd}),
                TaskStep(id=2, description="Verify folder exists", action="terminal",
                         params={"command": verify_exists_cmd}),
                write_step,
                TaskStep(id=4, description="Verify script exists", action="terminal",
                         params={"command": verify_script_cmd}),
            ]

        if wants_delete and not wants_create:
            delete_cmd = self._wrap_powershell(
                f"Remove-Item -LiteralPath '{target}' -Recurse -Force"
            )
            verify_missing_cmd = self._wrap_powershell(
                f"if (Test-Path '{target}') {{ exit 1 }} else "
                f"{{ Write-Output 'Folder sters: {target}' }}"
            )
            return [
                TaskStep(id=1, description="Delete folder", action="terminal",
                         params={"command": delete_cmd}),
                TaskStep(id=2, description="Verify folder missing", action="terminal",
                         params={"command": verify_missing_cmd}),
            ]

        return []

    @staticmethod
    def _extract_script_name(task: str, lowered: str, folder_name: str) -> str:
        """Determina numele scriptului Python din task."""
        # Cauta explicit 'busola', 'compass', etc.
        for kw in ("busola", "busol", "compass", "buspla"):
            if kw in lowered:
                return f"{kw}.py"
        # Cauta pattern 'script numit X' sau 'fisier X.py'
        m = re.search(r'\b([A-Za-z0-9_]+)\.py\b', task, re.IGNORECASE)
        if m:
            return m.group(0)
        # Fallback: folosim numele folderului
        return f"{folder_name}.py"

    @staticmethod
    def _generate_script_content(script_name: str, lowered: str) -> str:
        """Genereaza continut Python relevant pentru tipul de script cerut."""
        is_compass = any(kw in lowered for kw in ("busola", "busol", "compass", "buspla"))
        if is_compass:
            return (
                "#!/usr/bin/env python3\n"
                "# -*- coding: utf-8 -*-\n"
                "\"\"\"Busola simpla in Python - afiseaza directia pe baza unghiului.\"\"\"\n\n"
                "import math\n\n\n"
                "DIRECTII = [\n"
                "    'N', 'NNE', 'NE', 'ENE',\n"
                "    'E', 'ESE', 'SE', 'SSE',\n"
                "    'S', 'SSV', 'SV', 'VSV',\n"
                "    'V', 'VNV', 'NV', 'NNV',\n"
                "]\n\n\n"
                "def unghi_la_directie(unghi: float) -> str:\n"
                "    \"\"\"Converteste un unghi (0-360 grade) in directie cardinala.\"\"\"\n"
                "    unghi = unghi % 360\n"
                "    index = round(unghi / 22.5) % 16\n"
                "    return DIRECTII[index]\n\n\n"
                "def busola_interactiva() -> None:\n"
                "    \"\"\"Mod interactiv: citeste unghiuri de la tastatura.\"\"\"\n"
                "    print('=== BUSOLA ANA MAX ===')\n"
                "    print('Introdu un unghi in grade (0-360) sau \\'exit\\' pentru a iesi.')\n"
                "    while True:\n"
                "        try:\n"
                "            inp = input('Unghi: ').strip()\n"
                "            if inp.lower() in ('exit', 'quit', 'q'):\n"
                "                print('La revedere!')\n"
                "                break\n"
                "            unghi = float(inp)\n"
                "            directie = unghi_la_directie(unghi)\n"
                "            print(f'  -> {unghi:.1f} grade = {directie}')\n"
                "        except ValueError:\n"
                "            print('  [!] Introdu un numar valid.')\n"
                "        except KeyboardInterrupt:\n"
                "            print('\\nOprit.')\n"
                "            break\n\n\n"
                "if __name__ == '__main__':\n"
                "    # Demo rapid\n"
                "    exemple = [0, 45, 90, 135, 180, 225, 270, 315, 360]\n"
                "    print('=== Demo directii ===')\n"
                "    for a in exemple:\n"
                "        print(f'  {a:>3} grade -> {unghi_la_directie(a)}')\n"
                "    print()\n"
                "    busola_interactiva()\n"
            )
        # Generic script
        name = script_name.replace(".py", "")
        return (
            f"#!/usr/bin/env python3\n"
            f"# -*- coding: utf-8 -*-\n"
            f"\"\"\"Script generat de ANA MAX: {name}\"\"\"\n\n\n"
            f"def main():\n"
            f"    print('Hello from {name}!')\n\n\n"
            f"if __name__ == '__main__':\n"
            f"    main()\n"
        )


    def _resolve_folder_target(self, task: str, lowered: str) -> Optional[str]:
        explicit = self._extract_explicit_path(task)
        if explicit:
            return explicit

        if "folder" not in lowered and "director" not in lowered and "directory" not in lowered:
            return None

        folder_name = self._extract_folder_name(task)
        if not folder_name:
            return None

        base_dir = self._project_root
        _desktop_keywords = (
            "desktop", "descktop", "desctop", "desk top", "ecran", "birou",
        )
        if any(kw in lowered for kw in _desktop_keywords):
            base_dir = Path(os.path.expanduser("~")) / "Desktop"
            if not base_dir.exists():
                base_dir = Path.home() / "Desktop"
        elif any(term in lowered for term in ("workspace", "spatiul meu de lucru", "proiect")):
            base_dir = self._project_root

        return str(base_dir / folder_name)

    @staticmethod
    def _extract_folder_name(task: str) -> Optional[str]:
        # Daca are ghilimele, extragem continutul ghilimelelor
        match = re.search(r'["\']([^"\']+)["\']', task)
        if match:
            return match.group(1).strip()
            
        # Daca are cuvantul "numit" sau "cu numele"
        match = re.search(r'(?:numit|cu numele)\s+([A-Za-z0-9._-]+)', task, re.IGNORECASE)
        if match:
            return match.group(1).strip()
            
        # Cautam ultimul cuvant din propozitie
        words = [w.strip() for w in task.split() if w.strip()]
        if words:
            last_word = words[-1].rstrip(".!?")
            if last_word and re.match(r'^[A-Za-z0-9._-]+$', last_word):
                return last_word
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
