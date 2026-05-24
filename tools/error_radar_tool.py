"""Multi-source blocker detector for ANA MAX."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List

from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus


ERROR_PATTERNS = [
    ("traceback", re.compile(r"Traceback|Exception|Error:", re.IGNORECASE)),
    ("python_import", re.compile(r"ModuleNotFoundError|ImportError", re.IGNORECASE)),
    ("syntax", re.compile(r"SyntaxError|IndentationError", re.IGNORECASE)),
    ("test_failure", re.compile(r"FAILED|FAIL:|ERROR:", re.IGNORECASE)),
    ("auth", re.compile(r"\b(?:401|403)\b|unauthorized|forbidden|authentication", re.IGNORECASE)),
]
SECRET_RE = re.compile(r"(?i)(api[_-]?key|token|password|secret)\s*[:=]\s*\S+")


class ErrorRadarTool(Tool):
    def __init__(self) -> None:
        self.root = Path(__file__).resolve().parents[1]

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="error_radar",
            description="Detect likely blockers from recent logs, observability, git state, and visible window titles.",
            parameters=[
                ToolParameter("scope", "quick, logs, git, ui, all", "string", False, "quick", choices=["quick", "logs", "git", "ui", "all"]),
                ToolParameter("limit", "Maximum findings", "integer", False, 12),
            ],
            category="diagnostics",
        )

    def execute(self, scope: str = "quick", **kwargs: Any) -> ToolResult:
        limit = int(kwargs.get("limit") or 12)
        findings: List[Dict[str, Any]] = []

        if scope in {"quick", "logs", "all"}:
            findings.extend(self._scan_logs(limit))
        if scope in {"quick", "git", "all"}:
            findings.extend(self._scan_git())
        if scope in {"quick", "ui", "all"}:
            findings.extend(self._scan_windows())

        findings = findings[:limit]
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        findings.sort(key=lambda item: severity_order.get(item.get("severity", "low"), 3))

        data = {
            "schema": "ana.error_radar.v1",
            "scope": scope,
            "findings": findings,
            "count": len(findings),
            "recommended_next_step": self._recommend(findings),
        }
        return ToolResult(status=ToolStatus.SUCCESS, data=data, message=f"{len(findings)} findings")

    def _scan_logs(self, limit: int) -> List[Dict[str, Any]]:
        findings: List[Dict[str, Any]] = []
        for log_name in ["ana_max.log", "observability.jsonl"]:
            path = self.root / "logs" / log_name
            if not path.exists():
                continue
            try:
                lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()[-300:]
            except Exception:
                continue
            for lineno, line in enumerate(lines, 1):
                text = self._redact(line.strip())
                if not text:
                    continue
                if log_name.endswith(".jsonl"):
                    text = self._observability_summary(text)
                for kind, pattern in ERROR_PATTERNS:
                    if pattern.search(text):
                        findings.append({
                            "source": log_name,
                            "kind": kind,
                            "severity": "high" if kind in {"traceback", "syntax"} else "medium",
                            "summary": text[:260],
                            "line_hint": lineno,
                        })
                        break
                if len(findings) >= limit:
                    return findings[-limit:]
        return findings[-limit:]

    def _scan_git(self) -> List[Dict[str, Any]]:
        try:
            result = subprocess.run(
                ["git", "status", "--short"],
                cwd=str(self.root.parent),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                timeout=5,
            )
        except Exception as exc:
            return [{"source": "git", "kind": "git_error", "severity": "low", "summary": str(exc)[:180]}]
        if result.returncode != 0:
            return [{"source": "git", "kind": "git_error", "severity": "medium", "summary": result.stderr.strip()[:180]}]
        lines = [line for line in result.stdout.splitlines() if line.strip()]
        if len(lines) > 40:
            return [{"source": "git", "kind": "large_dirty_tree", "severity": "medium", "summary": f"{len(lines)} changed paths; review before committing"}]
        return []

    def _scan_windows(self) -> List[Dict[str, Any]]:
        findings: List[Dict[str, Any]] = []
        try:
            import win32gui

            def collect(hwnd, _extra):
                if not win32gui.IsWindowVisible(hwnd):
                    return
                title = win32gui.GetWindowText(hwnd)
                if re.search(r"error|failed|exception|warning|crash", title or "", re.IGNORECASE):
                    findings.append({"source": "visible_window", "kind": "visible_error", "severity": "medium", "summary": title[:220]})

            win32gui.EnumWindows(collect, None)
        except Exception:
            pass
        return findings[:5]

    def _observability_summary(self, text: str) -> str:
        try:
            entry = json.loads(text)
            if entry.get("status") in {"error", "blocked", "requires_confirmation"}:
                return f"{entry.get('tool')}: {entry.get('status')} {entry.get('error') or ''}"
        except Exception:
            pass
        return text

    def _redact(self, text: str) -> str:
        return SECRET_RE.sub(lambda m: f"{m.group(1)}=********", text)

    def _recommend(self, findings: List[Dict[str, Any]]) -> str:
        if not findings:
            return "No obvious blockers found. Continue with targeted verification."
        first = findings[0]
        if first.get("kind") in {"syntax", "python_import", "traceback"}:
            return "Inspect the owning Python file, fix the first traceback, then run compile and quick tests."
        if first.get("kind") == "large_dirty_tree":
            return "Separate old dirty work from today's change before editing or committing."
        return "Open the highest-severity finding, reproduce it once, then apply the smallest fix."
