"""
A.N.A. v15.0 - Git Tool
========================
Instrumente pentru controlul versiunilor (Git).
"""

import os
import subprocess
import logging
from typing import Optional, Dict, Any, List, Tuple

from pathlib import Path

from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus

logger = logging.getLogger(__name__)


class GitTool(Tool):
    """
    Tool pentru operațiuni Git.
    """
    
    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="git_operations",
            description="Controlul versiunilor folosind Git (status, commit, log, branch, diff).",
            parameters=[
                ToolParameter(
                    name="operation",
                    description="Operațiunea: status, init, add, commit, log, branch, diff, checkout",
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
                    description="Ținta: fișier, nume branch, etc.",
                    type="string",
                    required=False
                ),
                ToolParameter(
                    name="path",
                    description="Calea către repository (implicit '.')",
                    type="string",
                    required=False,
                    default="."
                )
            ],
            category="code"
        )

    def execute(self, operation: str, **kwargs) -> ToolResult:
        """Execută comanda git."""
        repo_path = kwargs.get('path', '.')
        handler_kwargs = dict(kwargs)
        handler_kwargs.pop('path', None)
        
        # Verificăm dacă git este instalat
        try:
            subprocess.run(["git", "--version"], check=True, capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
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
            return ToolResult(status=ToolStatus.ERROR, error=f"Operațiune necunoscută: {operation}")
            
        return handlers[operation](repo_path, **handler_kwargs)

    def _run_git(self, args: List[str], cwd: str) -> Tuple[int, str, str]:
        """Rulează o comandă git și returnează rezultatul."""
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
            return ToolResult(status=ToolStatus.SUCCESS, data=out, message="Status repository obținut")
        return ToolResult(status=ToolStatus.ERROR, error=err or "Folderul nu este un repository git.")

    def _init(self, path: str, **kwargs) -> ToolResult:
        code, out, err = self._run_git(["init"], path)
        if code == 0:
            return ToolResult(status=ToolStatus.SUCCESS, data=out, message="Repository inițializat")
        return ToolResult(status=ToolStatus.ERROR, error=err)

    def _add(self, path: str, **kwargs) -> ToolResult:
        target = kwargs.get('target', '.')
        code, out, err = self._run_git(["add", target], path)
        if code == 0:
            return ToolResult(status=ToolStatus.SUCCESS, data=out, message=f"Fișiere adăugate: {target}")
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
            return ToolResult(status=ToolStatus.SUCCESS, data=out, message="Istoric commit-uri obținut")
        return ToolResult(status=ToolStatus.ERROR, error=err)

    def _branch(self, path: str, **kwargs) -> ToolResult:
        target = kwargs.get('target')
        args = ["branch"]
        if target:
            args.append(target)
            
        code, out, err = self._run_git(args, path)
        if code == 0:
            return ToolResult(status=ToolStatus.SUCCESS, data=out or f"Branch creat: {target}", message="Operațiune branch finalizată")
        return ToolResult(status=ToolStatus.ERROR, error=err)

    def _diff(self, path: str, **kwargs) -> ToolResult:
        code, out, err = self._run_git(["diff"], path)
        if code == 0:
            return ToolResult(status=ToolStatus.SUCCESS, data=out or "Nicio diferență față de index.", message="Diff obținut")
        return ToolResult(status=ToolStatus.ERROR, error=err)

    def _checkout(self, path: str, **kwargs) -> ToolResult:
        target = kwargs.get('target')
        if not target:
            return ToolResult(status=ToolStatus.ERROR, error="Ținta (branch/commit) este obligatorie pentru checkout.")
            
        code, out, err = self._run_git(["checkout", target], path)
        if code == 0:
            return ToolResult(status=ToolStatus.SUCCESS, data=out, message=f"Checkout la {target} realizat")
        return ToolResult(status=ToolStatus.ERROR, error=err)
