"""
A.N.A. v15.0 - Git Tool (OS27 Hyper++)
========================================
Instrumente pentru controlul versiunilor (Git).

OS27 Hyper++ Features:
- Telemetry tracking for git operations (status, init, add, commit, log, branch, diff, checkout)
- Health monitoring for git operations reliability
- MemoryCortex integration for git errors and state learning
- ContextEngine integration for git state awareness
- SelfEvolvingTool integration for anomaly detection on git failures
- Structured logging with error detection
"""

import os
import subprocess
import logging
import time
from typing import Optional, Dict, Any, List, Tuple

from pathlib import Path

from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus

logger = logging.getLogger(__name__)

# OS27 Hyper++ Telemetry
_git_telemetry: Dict[str, Dict[str, Any]] = {}


def _record_git_telemetry(operation: str, success: bool, execution_time: float) -> None:
    """Record OS27 Hyper++ telemetry for git operations."""
    if operation not in _git_telemetry:
        _git_telemetry[operation] = {
            "operation_count": 0,
            "success_count": 0,
            "failure_count": 0,
            "total_time": 0.0,
            "last_execution_time": 0.0,
            "last_success": False,
        }
    
    _git_telemetry[operation]["operation_count"] += 1
    _git_telemetry[operation]["total_time"] += execution_time
    _git_telemetry[operation]["last_execution_time"] = execution_time
    _git_telemetry[operation]["last_success"] = success
    
    if success:
        _git_telemetry[operation]["success_count"] += 1
    else:
        _git_telemetry[operation]["failure_count"] += 1


def get_git_telemetry(operation: str | None = None) -> Dict[str, Any] | Dict[str, Dict[str, Any]]:
    """Get telemetry for git operations."""
    if operation:
        return _git_telemetry.get(operation, {})
    return _git_telemetry.copy()


def get_git_health() -> str:
    """Get health status for git tool based on telemetry."""
    if not _git_telemetry:
        return "unknown"
    
    total_ops = sum(stats["operation_count"] for stats in _git_telemetry.values())
    total_failures = sum(stats["failure_count"] for stats in _git_telemetry.values())
    
    if total_ops == 0:
        return "unknown"
    
    failure_rate = total_failures / total_ops
    if failure_rate > 0.5:
        return "broken"
    if failure_rate > 0.1:
        return "degraded"
    return "healthy"


class GitTool(Tool):
    """
    Tool pentru operatiuni Git.
    """
    
    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="git_operations",
            description="Controlul versiunilor folosind Git (status, commit, log, branch, diff).",
            parameters=[
                ToolParameter(
                    name="operation",
                    description="Operatiunea: status, init, add, commit, log, branch, diff, checkout",
                    type="string",
                    required=True,
                    choices=["status", "init", "add", "commit", "log", "branch", "diff", "checkout"]
                ),
                ToolParameter(
                    name="message",
                    description="Mesajul de commit",
                    type="string",
                    required=False
                ),
                ToolParameter(
                    name="target",
                    description="Tinta: fisier, nume branch, etc.",
                    type="string",
                    required=False
                ),
                ToolParameter(
                    name="path",
                    description="Calea catre repository (implicit '.')",
                    type="string",
                    required=False,
                    default="."
                )
            ],
            category="code"
        )

    def execute(self, operation: str, **kwargs) -> ToolResult:
        """Executa comanda git."""
        start_time = time.time()
        
        # AI Core hooks (lazy import for safety)
        cortex = None
        context_engine = None
        evolver = None
        try:
            from tools.memory_cortex import MemoryCortex
            cortex = MemoryCortex()
        except Exception:
            pass
        try:
            from tools.context_engine import ContextEngine
            context_engine = ContextEngine()
        except Exception:
            pass
        try:
            from tools.self_evolving_tool import SelfEvolvingTool
            evolver = SelfEvolvingTool()
        except Exception:
            pass
        
        repo_path = kwargs.get('path', '.')
        handler_kwargs = dict(kwargs)
        handler_kwargs.pop('path', None)
        
        # Verificam daca git este instalat
        try:
            subprocess.run(["git", "--version"], check=True, capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            execution_time = time.time() - start_time
            _record_git_telemetry(operation, False, execution_time)
            
            # MemoryCortex integration for git errors
            if cortex:
                try:
                    cortex.remember(
                        "error",
                        f"git.{operation}",
                        "Git nu este instalat pe acest sistem"
                    )
                except Exception:
                    pass
            
            return ToolResult(status=ToolStatus.ERROR, error="Git nu este instalat pe acest sistem.")

        handlers = {
            "status": self._status,
            "init": self._init,
            "add": self._add,
            "commit": self._commit,
            "log": self._log,
            "branch": self._branch,
            "diff": self._diff,
            "checkout": self._checkout
        }
        
        if operation not in handlers:
            execution_time = time.time() - start_time
            _record_git_telemetry(operation, False, execution_time)
            return ToolResult(status=ToolStatus.ERROR, error=f"Operatiune necunoscuta: {operation}")
        
        try:
            result = handlers[operation](repo_path, **handler_kwargs)
            execution_time = time.time() - start_time
            _record_git_telemetry(operation, result.is_success, execution_time)
            
            # ContextEngine integration for git state
            if context_engine and result.is_success:
                try:
                    context_engine.update_context(
                        key="git_state",
                        value={
                            "operation": operation,
                            "repo_path": repo_path,
                            "success": result.is_success,
                            "timestamp": time.time(),
                        }
                    )
                except Exception:
                    pass
            
            # MemoryCortex integration for git errors
            if cortex and not result.is_success:
                try:
                    cortex.remember(
                        "error",
                        f"git.{operation}",
                        f"Git operation failed for {repo_path}: {result.error}"
                    )
                except Exception:
                    pass
            
            return result
        except Exception as exc:
            execution_time = time.time() - start_time
            _record_git_telemetry(operation, False, execution_time)
            
            # MemoryCortex integration for git errors
            if cortex:
                try:
                    cortex.remember(
                        "error",
                        f"git.{operation}",
                        f"Git operation failed for {repo_path}: {str(exc)}"
                    )
                except Exception:
                    pass
            
            return ToolResult(status=ToolStatus.ERROR, error=str(exc))

    def _run_git(self, args: List[str], cwd: str) -> Tuple[int, str, str]:
        """Ruleaza o comanda git si returneaza rezultatul."""
        import subprocess
        try:
            result = subprocess.run(
                ["git"] + args,
                cwd=cwd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='ignore'
            )
            return result.returncode, result.stdout, result.stderr
        except Exception as e:
            return 1, "", str(e)

    def _status(self, path: str, **kwargs) -> ToolResult:
        code, out, err = self._run_git(["status"], path)
        if code == 0:
            return ToolResult(status=ToolStatus.SUCCESS, data=out, message="Status repository obtinut")
        return ToolResult(status=ToolStatus.ERROR, error=err or "Folderul nu este un repository git.")

    def _init(self, path: str, **kwargs) -> ToolResult:
        code, out, err = self._run_git(["init"], path)
        if code == 0:
            return ToolResult(status=ToolStatus.SUCCESS, data=out, message="Repository initializat")
        return ToolResult(status=ToolStatus.ERROR, error=err)

    def _add(self, path: str, **kwargs) -> ToolResult:
        target = kwargs.get('target', '.')
        code, out, err = self._run_git(["add", target], path)
        if code == 0:
            return ToolResult(status=ToolStatus.SUCCESS, data=out, message=f"Fisiere adaugate: {target}")
        return ToolResult(status=ToolStatus.ERROR, error=err)

    def _commit(self, path: str, **kwargs) -> ToolResult:
        message = kwargs.get('message')
        if not message:
            return ToolResult(status=ToolStatus.ERROR, error="Mesajul de commit este obligatoriu.")
        
        code, out, err = self._run_git(["commit", "-m", message], path)
        if code == 0:
            return ToolResult(status=ToolStatus.SUCCESS, data=out, message="Commit realizat cu succes")
        return ToolResult(status=ToolStatus.ERROR, error=err or "Nimic de commit-uit.")

    def _log(self, path: str, **kwargs) -> ToolResult:
        code, out, err = self._run_git(["log", "--oneline", "-n", "10"], path)
        if code == 0:
            return ToolResult(status=ToolStatus.SUCCESS, data=out, message="Istoric commit-uri obtinut")
        return ToolResult(status=ToolStatus.ERROR, error=err)

    def _branch(self, path: str, **kwargs) -> ToolResult:
        target = kwargs.get('target')
        args = ["branch"]
        if target:
            args.append(target)
            
        code, out, err = self._run_git(args, path)
        if code == 0:
            return ToolResult(status=ToolStatus.SUCCESS, data=out or f"Branch creat: {target}", message="Operatiune branch finalizata")
        return ToolResult(status=ToolStatus.ERROR, error=err)

    def _diff(self, path: str, **kwargs) -> ToolResult:
        code, out, err = self._run_git(["diff"], path)
        if code == 0:
            return ToolResult(status=ToolStatus.SUCCESS, data=out or "Nicio diferenta fata de index.", message="Diff obtinut")
        return ToolResult(status=ToolStatus.ERROR, error=err)

    def _checkout(self, path: str, **kwargs) -> ToolResult:
        target = kwargs.get('target')
        if not target:
            return ToolResult(status=ToolStatus.ERROR, error="Tinta (branch/commit) este obligatorie pentru checkout.")
            
        code, out, err = self._run_git(["checkout", target], path)
        if code == 0:
            return ToolResult(status=ToolStatus.SUCCESS, data=out, message=f"Checkout la {target} realizat")
        return ToolResult(status=ToolStatus.ERROR, error=err)
