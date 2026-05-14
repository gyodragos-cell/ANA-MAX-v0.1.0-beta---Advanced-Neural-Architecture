"""
ANA MAX - Terminal Persistent Tool
===================================
Sesiune shell persistenta cu:
- Stare pastrata intre comenzi (cd, env vars, etc.)
- Output live capturat
- Procese background (npm run dev, server, etc.)
- Citire output din procese long-running
"""

from __future__ import annotations

import os
import queue
import subprocess
import threading
import time
import logging
from typing import Any, Dict, List, Optional

from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus

logger = logging.getLogger(__name__)


class PersistentShellSession:
    """Sesiune shell persistenta care pastreaza starea intre comenzi."""

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        self.created_at = time.time()
        self.cwd = os.getcwd()
        self.env = os.environ.copy()
        self.history: List[Dict[str, Any]] = []
        self._bg_processes: Dict[str, subprocess.Popen] = {}
        self._bg_output: Dict[str, List[str]] = {}

    def run(self, command: str, timeout: int = 30) -> Dict[str, Any]:
        """Executa o comanda in sesiunea curenta."""
        start = time.time()

        # Detectam cd si schimbam cwd-ul sesiunii
        stripped = command.strip()
        if stripped.startswith("cd "):
            new_dir = stripped[3:].strip().strip('"').strip("'")
            try:
                target = os.path.join(self.cwd, new_dir)
                target = os.path.normpath(target)
                if os.path.isdir(target):
                    self.cwd = target
                    result = {"stdout": f"[cd] -> {self.cwd}", "stderr": "", "exit_code": 0,
                              "cwd": self.cwd, "duration_ms": int((time.time() - start) * 1000)}
                else:
                    result = {"stdout": "", "stderr": f"Nu exista directorul: {target}",
                              "exit_code": 1, "cwd": self.cwd,
                              "duration_ms": int((time.time() - start) * 1000)}
            except Exception as exc:
                result = {"stdout": "", "stderr": str(exc), "exit_code": 1,
                          "cwd": self.cwd, "duration_ms": int((time.time() - start) * 1000)}
            self.history.append({"command": command, **result})
            return result

        # Detectam set/export pentru env vars
        if stripped.startswith(("set ", "export ")):
            parts = stripped.split(" ", 1)
            if "=" in parts[1]:
                k, v = parts[1].split("=", 1)
                self.env[k.strip()] = v.strip()
                result = {"stdout": f"[env] {k.strip()} = {v.strip()}", "stderr": "",
                          "exit_code": 0, "cwd": self.cwd,
                          "duration_ms": int((time.time() - start) * 1000)}
                self.history.append({"command": command, **result})
                return result

        try:
            proc = subprocess.run(
                command,
                shell=True,
                cwd=self.cwd,
                env=self.env,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            result = {
                "stdout": proc.stdout[-8000:] if proc.stdout else "",
                "stderr": proc.stderr[-2000:] if proc.stderr else "",
                "exit_code": proc.returncode,
                "cwd": self.cwd,
                "duration_ms": int((time.time() - start) * 1000),
            }
        except subprocess.TimeoutExpired:
            result = {
                "stdout": "",
                "stderr": f"Timeout dupa {timeout}s. Foloseste start_background pentru procese lungi.",
                "exit_code": -1,
                "cwd": self.cwd,
                "duration_ms": timeout * 1000,
            }
        except Exception as exc:
            result = {
                "stdout": "",
                "stderr": str(exc),
                "exit_code": -1,
                "cwd": self.cwd,
                "duration_ms": int((time.time() - start) * 1000),
            }

        self.history.append({"command": command, **result})
        return result

    def start_background(self, name: str, command: str) -> Dict[str, Any]:
        """Porneste un proces in background (npm run dev, server, etc.)."""
        if name in self._bg_processes:
            proc = self._bg_processes[name]
            if proc.poll() is None:
                return {"error": f"Procesul '{name}' ruleaza deja (PID {proc.pid})"}

        self._bg_output[name] = []
        output_buffer = self._bg_output[name]

        try:
            proc = subprocess.Popen(
                command,
                shell=True,
                cwd=self.cwd,
                env=self.env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            self._bg_processes[name] = proc

            def _reader():
                try:
                    for line in proc.stdout:
                        output_buffer.append(line.rstrip())
                        if len(output_buffer) > 500:
                            output_buffer.pop(0)
                except Exception:
                    pass

            t = threading.Thread(target=_reader, daemon=True)
            t.start()

            time.sleep(0.5)
            return {
                "started": True,
                "name": name,
                "pid": proc.pid,
                "command": command,
                "cwd": self.cwd,
                "message": f"Proces '{name}' pornit in background (PID {proc.pid})",
            }
        except Exception as exc:
            return {"started": False, "error": str(exc)}

    def read_background(self, name: str, lines: int = 50) -> Dict[str, Any]:
        """Citeste output-ul recent dintr-un proces background."""
        if name not in self._bg_processes:
            return {"error": f"Nu exista procesul background '{name}'"}

        proc = self._bg_processes[name]
        running = proc.poll() is None
        output = self._bg_output.get(name, [])

        return {
            "name": name,
            "pid": proc.pid,
            "running": running,
            "exit_code": proc.poll(),
            "output_lines": output[-lines:],
            "total_lines": len(output),
        }

    def stop_background(self, name: str) -> Dict[str, Any]:
        """Opreste un proces background."""
        if name not in self._bg_processes:
            return {"error": f"Nu exista procesul '{name}'"}

        proc = self._bg_processes[name]
        if proc.poll() is not None:
            return {"stopped": False, "message": f"Procesul '{name}' deja oprit"}

        try:
            proc.terminate()
            time.sleep(0.5)
            if proc.poll() is None:
                proc.kill()
            self._bg_processes.pop(name, None)
            return {"stopped": True, "name": name}
        except Exception as exc:
            return {"stopped": False, "error": str(exc)}

    def list_background(self) -> Dict[str, Any]:
        """Listeaza toate procesele background."""
        result = []
        for name, proc in self._bg_processes.items():
            running = proc.poll() is None
            result.append({
                "name": name,
                "pid": proc.pid,
                "running": running,
                "exit_code": proc.poll(),
                "output_lines_buffered": len(self._bg_output.get(name, [])),
            })
        return {"processes": result, "count": len(result)}

    def info(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "cwd": self.cwd,
            "created_at": self.created_at,
            "history_count": len(self.history),
            "background_processes": len(self._bg_processes),
            "env_vars_count": len(self.env),
        }


# Sesiuni globale (un dict de sesiuni active)
_SESSIONS: Dict[str, PersistentShellSession] = {}
_DEFAULT_SESSION = "default"


def get_session(session_id: str = _DEFAULT_SESSION) -> PersistentShellSession:
    global _SESSIONS
    if session_id not in _SESSIONS:
        _SESSIONS[session_id] = PersistentShellSession(session_id)
    return _SESSIONS[session_id]


class TerminalTool(Tool):
    """
    Terminal persistent cu sesiune pastrata intre comenzi.
    Suporta: run, start_background, read_background, stop_background,
             list_background, session_info, list_sessions, new_session.
    """

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="terminal",
            description=(
                "Terminal persistent cu sesiune pastrata (cd, env, procese background). "
                "Poate rula npm run dev, servere, comenzi lungi in background si sa citeasca output-ul live."
            ),
            parameters=[
                ToolParameter(
                    name="operation",
                    description="Operatiunea dorita",
                    type="string",
                    required=True,
                    choices=[
                        "run",
                        "start_background",
                        "read_background",
                        "stop_background",
                        "list_background",
                        "session_info",
                        "list_sessions",
                        "new_session",
                        "history",
                    ],
                ),
                ToolParameter(
                    name="command",
                    description="Comanda de executat (pentru run / start_background)",
                    type="string",
                    required=False,
                    default="",
                ),
                ToolParameter(
                    name="session_id",
                    description="ID sesiune (default: 'default')",
                    type="string",
                    required=False,
                    default="default",
                ),
                ToolParameter(
                    name="process_name",
                    description="Numele procesului background (ex: 'dev-server', 'watcher')",
                    type="string",
                    required=False,
                    default="",
                ),
                ToolParameter(
                    name="timeout",
                    description="Timeout in secunde pentru run (default: 30)",
                    type="integer",
                    required=False,
                    default=30,
                ),
                ToolParameter(
                    name="lines",
                    description="Numarul de linii de output returnat din background (default: 50)",
                    type="integer",
                    required=False,
                    default=50,
                ),
            ],
            category="system",
            requires_confirmation=False,
        )

    def execute(self, operation: str, **kwargs) -> ToolResult:
        session_id = kwargs.get("session_id", "default") or "default"
        command = kwargs.get("command", "") or ""
        process_name = kwargs.get("process_name", "") or ""
        timeout = int(kwargs.get("timeout", 30) or 30)
        lines = int(kwargs.get("lines", 50) or 50)

        session = get_session(session_id)

        # ── RUN ───────────────────────────────────────────────────────
        if operation == "run":
            if not command:
                return ToolResult(status=ToolStatus.ERROR, error="Parametrul 'command' este necesar")
            result = session.run(command, timeout=timeout)
            status = ToolStatus.SUCCESS if result["exit_code"] == 0 else ToolStatus.ERROR
            msg = f"[exit {result['exit_code']}] {command[:60]}"
            return ToolResult(status=status, data=result, message=msg)

        # ── BACKGROUND ────────────────────────────────────────────────
        if operation == "start_background":
            if not command:
                return ToolResult(status=ToolStatus.ERROR, error="Parametrul 'command' este necesar")
            if not process_name:
                return ToolResult(status=ToolStatus.ERROR, error="Parametrul 'process_name' este necesar")
            result = session.start_background(process_name, command)
            if result.get("started"):
                return ToolResult(status=ToolStatus.SUCCESS, data=result, message=result["message"])
            return ToolResult(status=ToolStatus.ERROR, error=result.get("error", "Eroare la pornire"))

        if operation == "read_background":
            if not process_name:
                return ToolResult(status=ToolStatus.ERROR, error="Parametrul 'process_name' este necesar")
            result = session.read_background(process_name, lines=lines)
            if "error" in result:
                return ToolResult(status=ToolStatus.ERROR, error=result["error"])
            return ToolResult(status=ToolStatus.SUCCESS, data=result,
                              message=f"Output '{process_name}': {len(result['output_lines'])} linii")

        if operation == "stop_background":
            if not process_name:
                return ToolResult(status=ToolStatus.ERROR, error="Parametrul 'process_name' este necesar")
            result = session.stop_background(process_name)
            if result.get("stopped"):
                return ToolResult(status=ToolStatus.SUCCESS, data=result, message=f"Proces '{process_name}' oprit")
            return ToolResult(status=ToolStatus.ERROR, error=result.get("error", "Nu s-a putut opri"))

        if operation == "list_background":
            result = session.list_background()
            return ToolResult(status=ToolStatus.SUCCESS, data=result,
                              message=f"Procese background: {result['count']}")

        # ── SESSION ───────────────────────────────────────────────────
        if operation == "session_info":
            return ToolResult(status=ToolStatus.SUCCESS, data=session.info(),
                              message=f"Info sesiune '{session_id}'")

        if operation == "new_session":
            new_id = session_id if session_id != "default" else f"session_{int(time.time())}"
            _SESSIONS[new_id] = PersistentShellSession(new_id)
            return ToolResult(status=ToolStatus.SUCCESS,
                              data={"session_id": new_id},
                              message=f"Sesiune noua creata: {new_id}")

        if operation == "list_sessions":
            sessions_info = {sid: s.info() for sid, s in _SESSIONS.items()}
            return ToolResult(status=ToolStatus.SUCCESS, data=sessions_info,
                              message=f"Sesiuni active: {len(_SESSIONS)}")

        if operation == "history":
            hist = session.history[-lines:]
            return ToolResult(status=ToolStatus.SUCCESS, data={"history": hist, "total": len(session.history)},
                              message=f"Ultimele {len(hist)} comenzi din sesiunea '{session_id}'")

        return ToolResult(status=ToolStatus.ERROR, error=f"Operatie necunoscuta: {operation}")
