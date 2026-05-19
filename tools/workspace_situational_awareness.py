"""
ANA MAX - Workspace Situational Awareness

Observation-only WorkGraph snapshot for agents. The tool returns compact JSON
so an agent can see repo, git, active window, and likely blockers before acting.
"""

from __future__ import annotations

import ctypes
import os
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List

from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _run_git(args: List[str], cwd: Path, timeout: float = 3.0) -> Dict[str, Any]:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
        return {
            "ok": completed.returncode == 0,
            "stdout": completed.stdout.strip(),
            "stderr": completed.stderr.strip(),
            "returncode": completed.returncode,
        }
    except Exception as exc:
        return {"ok": False, "stdout": "", "stderr": str(exc), "returncode": -1}


def _git_state(path: Path, max_files: int) -> Dict[str, Any]:
    git_cwd = path if path.is_dir() else path.parent
    root_result = _run_git(["rev-parse", "--show-toplevel"], path)
    if not root_result["ok"] and git_cwd != path:
        root_result = _run_git(["rev-parse", "--show-toplevel"], git_cwd)
    if not root_result["ok"]:
        return {
            "available": False,
            "repo": None,
            "branch": None,
            "git_clean": None,
            "modified_files": [],
            "error": root_result["stderr"][:200],
        }

    repo = Path(root_result["stdout"])
    branch_result = _run_git(["branch", "--show-current"], repo)
    status_result = _run_git(["status", "--short"], repo)
    files = [line.strip() for line in status_result["stdout"].splitlines() if line.strip()]

    return {
        "available": True,
        "repo": repo.name,
        "repo_root": repo.name,
        "branch": branch_result["stdout"] or "detached",
        "git_clean": len(files) == 0,
        "modified_files": files[:max_files],
        "truncated": len(files) > max_files,
    }


def _active_window() -> Dict[str, Any]:
    if os.name != "nt":
        return {
            "available": False,
            "app": None,
            "title": "",
            "visibility_quality": "unknown",
            "error": "Active window inspection is Windows-only",
        }

    try:
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        length = user32.GetWindowTextLengthW(hwnd)
        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buffer, length + 1)
        title = buffer.value
        return {
            "available": bool(title),
            "handle": int(hwnd),
            "app": None,
            "title": title,
            "visibility_quality": "good" if title else "partial",
        }
    except Exception as exc:
        return {
            "available": False,
            "app": None,
            "title": "",
            "visibility_quality": "unknown",
            "error": str(exc)[:200],
        }


def _visible_error_signals(texts: List[str]) -> Dict[str, List[str]]:
    needles = ("error", "failed", "exception", "traceback", "warning", "unauthorized")
    matches = []
    for text in texts:
        lower = text.lower()
        if any(needle in lower for needle in needles):
            matches.append(text[:180])
    return {"errors": matches[:10], "warnings": []}


def _recommendation(git: Dict[str, Any], signals: Dict[str, List[str]]) -> str:
    if signals["errors"]:
        return "Investigate visible errors before editing or committing."
    if git.get("available") and not git.get("git_clean"):
        return "Review modified files, then run verification before commit."
    if git.get("available"):
        return "Workspace looks stable. Run task-specific checks before handoff."
    return "Git state is unavailable. Confirm workspace path before acting."


class WorkspaceSituationalAwarenessTool(Tool):
    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="workspace_situational_awareness",
            description=(
                "Observation-only WorkGraph snapshot: active window, git state, "
                "signals, confidence, and next step."
            ),
            parameters=[
                ToolParameter(
                    name="path",
                    description="Workspace path to inspect. Defaults to repo root.",
                    type="string",
                    required=False,
                    default=".",
                ),
                ToolParameter(
                    name="max_files",
                    description="Maximum changed files to include.",
                    type="integer",
                    required=False,
                    default=30,
                ),
            ],
            category="workgraph",
        )

    def execute(self, path: str = ".", max_files: int = 30, **kwargs) -> ToolResult:
        try:
            target = Path(path)
            if not target.is_absolute():
                target = PROJECT_ROOT / target
            target = target.resolve()
            try:
                max_files_int = int(max_files)
            except (TypeError, ValueError):
                max_files_int = 30
            max_files_int = max(1, min(max_files_int, 50))

            active_window = _active_window()
            git = _git_state(target, max_files_int)
            text_sources = [active_window.get("title") or "", git.get("error") or ""]
            signals = _visible_error_signals(text_sources)
            blind_spots = []
            if not active_window.get("available"):
                blind_spots.append("active_window")
            if not git.get("available"):
                blind_spots.append("git")

            confidence = 0.95
            if blind_spots:
                confidence -= 0.2 * len(blind_spots)
            if signals["errors"]:
                confidence -= 0.15
            confidence = max(0.1, round(confidence, 2))

            data = {
                "schema": "ana.workgraph.workspace_state.v1",
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "active_window": active_window,
                "workspace": git,
                "signals": signals,
                "recommended_next_step": _recommendation(git, signals),
                "confidence": confidence,
                "blind_spots": blind_spots,
                "mode": "observe_only",
            }
            return ToolResult(status=ToolStatus.SUCCESS, data=data, message="Workspace snapshot ready")
        except Exception as exc:
            return ToolResult(status=ToolStatus.ERROR, error=str(exc))
