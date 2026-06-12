"""Multi-source blocker detector for ANA MAX."""

from __future__ import annotations

import json
import logging
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List

from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus

logger = logging.getLogger(__name__)


ERROR_PATTERNS = [
    ("traceback", re.compile(r"Traceback|Exception|Error:", re.IGNORECASE)),
    ("python_import", re.compile(r"ModuleNotFoundError|ImportError", re.IGNORECASE)),
    ("syntax", re.compile(r"SyntaxError|IndentationError", re.IGNORECASE)),
    ("test_failure", re.compile(r"FAILED|FAIL:|ERROR:", re.IGNORECASE)),
    (
        "auth",
        re.compile(
            r"(?<![,.\d])(?:401|403)(?![,.\d])|status(?:_code)?\s*[=:]\s*(?:401|403)|unauthorized|forbidden|authentication",
            re.IGNORECASE,
        ),
    ),
]
SECRET_RE = re.compile(r"(?i)(api[_-]?key|token|password|secret)\s*[:=]\s*\S+")


class ErrorRadarTool(Tool):
    def __init__(self) -> None:
        self.root = Path(__file__).resolve().parents[1]

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="error_radar",
            description="Detect likely blockers from recent logs, observability, and visible window titles.",
            parameters=[
                ToolParameter("scope", "quick, logs, ui, all", "string", False, "quick", choices=["quick", "logs", "ui", "all"]),
                ToolParameter("limit", "Maximum findings", "integer", False, 12),
            ],
            category="diagnostics",
        )

    def execute(self, scope: str = "quick", **kwargs: Any) -> ToolResult:
        limit = int(kwargs.get("limit") or 12)
        findings: List[Dict[str, Any]] = []

        if scope in {"quick", "logs", "all"}:
            findings.extend(self._scan_logs(limit))
        if scope in {"quick", "ui", "all"}:
            findings.extend(self._scan_windows())

        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        findings = self._dedupe_findings(findings)
        findings.sort(key=lambda item: severity_order.get(item.get("severity", "low"), 3))
        findings = findings[:limit]

        data = {
            "schema": "ana.error_radar.v1",
            "scope": scope,
            "findings": findings,
            "count": len(findings),
            "summary": self._finding_summary(findings),
            "recommended_next_step": self._recommend(findings),
        }
        return ToolResult(status=ToolStatus.SUCCESS, data=data, message=f"{len(findings)} findings")

    def _dedupe_findings(self, findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
        unique: list[dict[str, Any]] = []
        seen: set[tuple[str, str, str]] = set()
        for finding in findings:
            key = (
                str(finding.get("source") or ""),
                str(finding.get("kind") or ""),
                str(finding.get("summary") or "")[:160],
            )
            if key in seen:
                continue
            seen.add(key)
            unique.append(finding)
        return unique

    def _finding_summary(self, findings: list[dict[str, Any]]) -> dict[str, Any]:
        by_severity: dict[str, int] = {}
        by_kind: dict[str, int] = {}
        by_source: dict[str, int] = {}
        for finding in findings:
            severity = str(finding.get("severity") or "unknown")
            kind = str(finding.get("kind") or "unknown")
            source = str(finding.get("source") or "unknown")
            by_severity[severity] = by_severity.get(severity, 0) + 1
            by_kind[kind] = by_kind.get(kind, 0) + 1
            by_source[source] = by_source.get(source, 0) + 1
        top = findings[0] if findings else None
        return {
            "by_severity": by_severity,
            "by_kind": by_kind,
            "by_source": by_source,
            "top_kind": top.get("kind") if top else None,
            "top_severity": top.get("severity") if top else None,
            "top_source": top.get("source") if top else None,
        }

    def _scan_logs(self, limit: int) -> List[Dict[str, Any]]:
        findings: List[Dict[str, Any]] = []
        for log_name in ["ana_max.log", "observability.jsonl"]:
            path = self.root / "logs" / log_name
            if not path.exists():
                continue
            try:
                lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()[-300:]
            except Exception as exc:
                logger.debug("Skipping unreadable log %s: %s", path, exc)
                continue
            for lineno, line in enumerate(lines, 1):
                text = self._redact(line.strip())
                if not text:
                    continue
                if log_name.endswith(".jsonl"):
                    text = self._observability_summary(text)
                    if not text:
                        continue
                if self._is_monitor_noise(text):
                    continue
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
        except Exception as exc:
            findings.append({"source": "visible_window", "kind": "ui_scan_error", "severity": "low", "summary": str(exc)[:180]})
        return findings[:5]

    def _observability_summary(self, text: str) -> str:
        try:
            entry = json.loads(text)
            if entry.get("status") in {"error", "blocked", "requires_confirmation"}:
                return f"{entry.get('tool')}: {entry.get('status')} {entry.get('error') or ''}"
        except Exception as exc:
            logger.debug("Could not parse observability record: %s", exc)
            return text
        return ""

    def _is_monitor_noise(self, text: str) -> bool:
        markers = [
            "MCP tool failed with schema mismatch action versus operation",
            "Invalid value for operation",
            "definitely_missing_tool_for_guidance",
            "Tool tool_contract_validator failed",
            "tool_contract_validator failed",
            "HTTP /mcp tools/call start name=debugger",
            "TOOL START name=debugger",
        ]
        if any(marker in text for marker in markers):
            return True
        if "traceback_text" in text and "name=debugger" in text:
            return True
        if " - INFO - " in text and "success=True" in text:
            return True
        if " - INFO - " in text and re.search(r"\bfailed\b|\bERROR\b", text, re.IGNORECASE):
            return True
        return False

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
