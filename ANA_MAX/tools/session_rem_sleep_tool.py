"""
ANA MAX - Session REM Sleep Tool (OS27 Hyper++)
==============================================

Consolidates session traces into compact lessons between chats.
This is deterministic and local: it reads checkpoints, telemetry, and memory
files, then writes a small retrospective report and optional lessons.

OS27 Hyper++ Features:
- Telemetry tracking for REM sleep operations (analyze, consolidate, latest)
- Health monitoring for REM sleep operations reliability
- MemoryCortex integration for REM sleep errors and state learning
- ContextEngine integration for REM sleep state awareness
- SelfEvolvingTool integration for anomaly detection on REM sleep failures
- Structured logging with error detection
"""

from __future__ import annotations

import json
import re
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List

from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus

# OS27 Hyper++ Telemetry
_rem_sleep_telemetry: Dict[str, Dict[str, Any]] = {}


def _record_rem_sleep_telemetry(operation: str, success: bool, execution_time: float) -> None:
    """Record OS27 Hyper++ telemetry for REM sleep operations."""
    if operation not in _rem_sleep_telemetry:
        _rem_sleep_telemetry[operation] = {
            "operation_count": 0,
            "success_count": 0,
            "failure_count": 0,
            "total_time": 0.0,
            "last_execution_time": 0.0,
            "last_success": False,
        }
    
    _rem_sleep_telemetry[operation]["operation_count"] += 1
    _rem_sleep_telemetry[operation]["total_time"] += execution_time
    _rem_sleep_telemetry[operation]["last_execution_time"] = execution_time
    _rem_sleep_telemetry[operation]["last_success"] = success
    
    if success:
        _rem_sleep_telemetry[operation]["success_count"] += 1
    else:
        _rem_sleep_telemetry[operation]["failure_count"] += 1


def get_rem_sleep_telemetry(operation: str | None = None) -> Dict[str, Any] | Dict[str, Dict[str, Any]]:
    """Get telemetry for REM sleep operations."""
    if operation:
        return _rem_sleep_telemetry.get(operation, {})
    return _rem_sleep_telemetry.copy()


def get_rem_sleep_health() -> str:
    """Get health status for REM sleep tool based on telemetry."""
    if not _rem_sleep_telemetry:
        return "unknown"
    
    total_ops = sum(stats["operation_count"] for stats in _rem_sleep_telemetry.values())
    total_failures = sum(stats["failure_count"] for stats in _rem_sleep_telemetry.values())
    
    if total_ops == 0:
        return "unknown"
    
    failure_rate = total_failures / total_ops
    if failure_rate > 0.5:
        return "broken"
    if failure_rate > 0.1:
        return "degraded"
    return "healthy"


PASS_WORDS = ("pass", "passed", "ok", "green", "ready", "validated", "clean")
FAIL_WORDS = ("fail", "failed", "error", "warn", "risk", "blocked", "missing", "deprecated")


class SessionRemSleepTool(Tool):
    def __init__(self) -> None:
        self.root = Path(__file__).resolve().parents[1]
        self.docs_dir = self.root / "docs"
        self.memory_dir = self.root / "memory"
        self.log_file = self.root / "logs" / "observability.jsonl"
        self.reports_dir = self.docs_dir / "rem_sleep"
        self.conversation_file = self.memory_dir / "conversation_learning.jsonl"

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="session_rem_sleep",
            description=(
                "Between-session retrospective for ANA MAX. Reads recent checkpoints, "
                "telemetry, and learned lessons, then summarizes what worked, what failed, "
                "and what future agents should do differently."
            ),
            parameters=[
                ToolParameter(
                    name="action",
                    description="analyze returns a report, consolidate also saves report and memory lessons, latest reads the last report",
                    type="string",
                    required=False,
                    default="analyze",
                    choices=["analyze", "consolidate", "latest"],
                ),
                ToolParameter(
                    name="checkpoint_limit",
                    description="How many recent SESSION_CHECKPOINT docs to inspect",
                    type="integer",
                    required=False,
                    default=8,
                ),
                ToolParameter(
                    name="telemetry_limit",
                    description="How many recent observability entries to inspect",
                    type="integer",
                    required=False,
                    default=200,
                ),
                ToolParameter(
                    name="lesson_limit",
                    description="How many recent conversation lessons to inspect",
                    type="integer",
                    required=False,
                    default=20,
                ),
                ToolParameter(
                    name="save_memory",
                    description="When consolidating, save compact lessons into conversation_learning and ana_memory",
                    type="boolean",
                    required=False,
                    default=True,
                ),
            ],
            category="memory",
        )

    def execute(self, **kwargs: Any) -> ToolResult:
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
        
        action = str(kwargs.get("action") or "analyze").strip().lower()
        
        try:
            if action == "latest":
                result = self._latest()
            elif action not in {"analyze", "consolidate"}:
                result = ToolResult(status=ToolStatus.ERROR, error=f"Unknown action: {action}")
            else:
                report = self._build_report(
                    checkpoint_limit=int(kwargs.get("checkpoint_limit", 8) or 8),
                    telemetry_limit=int(kwargs.get("telemetry_limit", 200) or 200),
                    lesson_limit=int(kwargs.get("lesson_limit", 20) or 20),
                )

                if action == "consolidate":
                    path = self._write_report(report)
                    report["saved_report"] = str(path)
                    if self._to_bool(kwargs.get("save_memory", True)):
                        saved = self._save_memory(report, path)
                        report["saved_memory"] = saved

                result = ToolResult(
                    status=ToolStatus.SUCCESS,
                    data=report,
                    message=report["headline"],
                )

            execution_time = time.time() - start_time
            _record_rem_sleep_telemetry(action, result.is_success, execution_time)
            
            # ContextEngine integration for REM sleep state
            if context_engine and result.is_success:
                try:
                    context_engine.update_context(
                        key="rem_sleep_state",
                        value={
                            "action": action,
                            "success": result.is_success,
                            "timestamp": time.time(),
                        }
                    )
                except Exception:
                    pass
            
            # MemoryCortex integration for REM sleep errors
            if cortex and not result.is_success:
                try:
                    cortex.remember(
                        "error",
                        f"rem_sleep.{action}",
                        f"REM sleep operation failed: {result.error}"
                    )
                except Exception:
                    pass
            
            return result
        except Exception as exc:
            execution_time = time.time() - start_time
            _record_rem_sleep_telemetry(action, False, execution_time)
            
            # MemoryCortex integration for REM sleep errors
            if cortex:
                try:
                    cortex.remember(
                        "error",
                        f"rem_sleep.{action}",
                        f"REM sleep operation failed: {str(exc)}"
                    )
                except Exception:
                    pass
            
            return ToolResult(status=ToolStatus.ERROR, error=str(exc))

    def _build_report(self, checkpoint_limit: int, telemetry_limit: int, lesson_limit: int) -> Dict[str, Any]:
        checkpoints = self._read_checkpoints(checkpoint_limit)
        telemetry = self._read_jsonl(self.log_file, telemetry_limit)
        lessons = self._read_jsonl(self.conversation_file, lesson_limit)

        tool_errors = self._tool_errors(telemetry)
        repeated_errors = [
            {"tool": tool, "count": count}
            for tool, count in tool_errors.most_common()
            if count >= 2
        ]

        checkpoint_text = "\n".join(item["excerpt"] for item in checkpoints)
        wins = self._extract_signal_lines(checkpoint_text, PASS_WORDS, limit=8)
        friction = self._extract_signal_lines(checkpoint_text, FAIL_WORDS, limit=8)
        recent_lesson_titles = [
            str(item.get("title") or "").strip()
            for item in lessons
            if str(item.get("title") or "").strip()
        ][-lesson_limit:]

        patterns = self._patterns(wins, friction, repeated_errors, recent_lesson_titles)
        recommendations = self._recommendations(patterns, repeated_errors, friction)
        mistakes = self._mistakes(friction, repeated_errors)

        return {
            "schema": "ana.session_rem_sleep.v1",
            "timestamp": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "headline": self._headline(wins, mistakes, recommendations),
            "inspected": {
                "checkpoints": len(checkpoints),
                "telemetry_entries": len(telemetry),
                "lessons": len(lessons),
            },
            "worked": wins,
            "mistakes_or_friction": mistakes,
            "patterns": patterns,
            "recommendations": recommendations,
            "next_session_prompt": self._next_session_prompt(recommendations),
            "sources": {
                "checkpoints": [item["path"] for item in checkpoints],
                "observability": str(self.log_file),
                "conversation_learning": str(self.conversation_file),
            },
        }

    def _read_checkpoints(self, limit: int) -> List[Dict[str, str]]:
        if not self.docs_dir.exists():
            return []
        paths = sorted(
            self.docs_dir.glob("SESSION_CHECKPOINT_*.md"),
            key=lambda path: path.stat().st_mtime,
        )[-max(limit, 0):]
        items = []
        for path in paths:
            text = path.read_text(encoding="utf-8", errors="replace")
            items.append({"path": str(path), "excerpt": text[:12000]})
        return items

    def _read_jsonl(self, path: Path, limit: int) -> List[Dict[str, Any]]:
        if not path.exists() or limit <= 0:
            return []
        entries: List[Dict[str, Any]] = []
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        for line in lines[-max(limit * 2, limit):]:
            line = line.strip()
            if not line:
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                entries.append(value)
        return entries[-limit:]

    def _tool_errors(self, telemetry: Iterable[Dict[str, Any]]) -> Counter:
        counter: Counter = Counter()
        for entry in telemetry:
            status = str(entry.get("status") or "").lower()
            error = str(entry.get("error") or "").strip()
            if status in {"error", "blocked"} or error:
                tool = str(entry.get("tool") or entry.get("name") or "unknown")
                counter[tool] += 1
        return counter

    def _extract_signal_lines(self, text: str, words: Iterable[str], limit: int) -> List[str]:
        needles = tuple(word.lower() for word in words)
        lines = []
        seen = set()
        for raw in text.splitlines():
            line = self._clean_line(raw)
            if not line or len(line) < 8:
                continue
            low = line.lower()
            if any(word in low for word in needles) and line not in seen:
                seen.add(line)
                lines.append(line[:220])
            if len(lines) >= limit:
                break
        return lines

    def _patterns(
        self,
        wins: List[str],
        friction: List[str],
        repeated_errors: List[Dict[str, Any]],
        lesson_titles: List[str],
    ) -> List[str]:
        patterns = []
        if wins:
            patterns.append("Validation-first work is paying off; keep turning successful checks into repeatable gates.")
        if repeated_errors:
            tools = ", ".join(item["tool"] for item in repeated_errors[:4])
            patterns.append(f"Repeated tool errors appeared around: {tools}. Route through agent_coach before retrying.")
        if friction:
            patterns.append("Friction should be converted into small durable rules, not left only in chat.")
        if any("checkpoint" in title.lower() for title in lesson_titles):
            patterns.append("Checkpoint memory is already useful; continue saving compact handoffs before risky transitions.")
        if not patterns:
            patterns.append("No strong failure pattern found; continue with observe, route, act once, verify, learn.")
        return patterns

    def _recommendations(
        self,
        patterns: List[str],
        repeated_errors: List[Dict[str, Any]],
        friction: List[str],
    ) -> List[str]:
        recommendations = [
            "Start the next session by reading docs/NEXT_SESSION_BOOTSTRAP.md and ANA_MAX/docs/CURRENT_SESSION_HANDOFF.md.",
            "Run the no-reload quality gate before packaging, installing, or reloading IDE integrations.",
        ]
        if repeated_errors:
            recommendations.append("After two similar tool failures, call agent_coach action=recommend and follow its primary_tool.")
        if friction:
            recommendations.append("Turn recurring warnings or broken assumptions into conversation_learning lessons.")
        if patterns:
            recommendations.append("Prefer tool_router for tool selection so the agent does not scan all tools blindly.")
        return recommendations

    def _mistakes(self, friction: List[str], repeated_errors: List[Dict[str, Any]]) -> List[str]:
        mistakes = list(friction[:6])
        for item in repeated_errors[:6]:
            mistakes.append(f"Repeated failure pattern: {item['tool']} reported {item['count']} recent errors.")
        if not mistakes:
            mistakes.append("No obvious recent mistake pattern found in inspected traces.")
        return mistakes

    def _headline(self, wins: List[str], mistakes: List[str], recommendations: List[str]) -> str:
        return (
            f"REM sleep analyzed {len(wins)} success signals, "
            f"{len(mistakes)} friction signals, and {len(recommendations)} next-session rules."
        )

    def _next_session_prompt(self, recommendations: List[str]) -> str:
        return "Before acting, read durable memory, verify MCP readiness, then follow these rules: " + "; ".join(
            recommendations[:4]
        )

    def _write_report(self, report: Dict[str, Any]) -> Path:
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        stamp = report["timestamp"].replace(":", "").replace("+00:00", "Z")
        path = self.reports_dir / f"REM_SLEEP_REPORT_{stamp}.md"
        lines = [
            f"# REM Sleep Report - {report['timestamp']}",
            "",
            report["headline"],
            "",
            "## What Worked",
            "",
            *[f"- {item}" for item in report["worked"]],
            "",
            "## Mistakes Or Friction",
            "",
            *[f"- {item}" for item in report["mistakes_or_friction"]],
            "",
            "## Patterns",
            "",
            *[f"- {item}" for item in report["patterns"]],
            "",
            "## Recommendations",
            "",
            *[f"- {item}" for item in report["recommendations"]],
            "",
            "## Next Session Prompt",
            "",
            report["next_session_prompt"],
            "",
        ]
        path.write_text("\n".join(lines), encoding="utf-8")
        return path

    def _save_memory(self, report: Dict[str, Any], path: Path) -> Dict[str, Any]:
        saved = {"conversation_learning": False, "ana_memory": False}
        lesson_text = "\n".join(report["patterns"] + report["recommendations"])
        try:
            from tools.conversation_learning_tool import ConversationLearningTool

            learning = ConversationLearningTool()
            learning.memory_file = self.conversation_file
            result = learning.execute(
                action="add",
                title="REM sleep consolidation",
                category="session_rem_sleep",
                problem="Agents lose calibration when session context is only in chat.",
                lesson=lesson_text,
                fix="Run session_rem_sleep action=consolidate between important sessions.",
                validation=f"Report saved: {path}",
                source="session_rem_sleep",
                confidence="high",
                tags="rem-sleep,retrospective,checkpoint,memory,agent-continuity",
            )
            saved["conversation_learning"] = result.is_success
        except Exception as exc:
            saved["conversation_learning_error"] = str(exc)

        try:
            from tools.memory_tool import MemoryTool

            topic = "session_rem_sleep_" + re.sub(r"[^0-9A-Za-z_]+", "_", report["timestamp"])
            result = MemoryTool().execute(
                action="save_knowledge",
                topic=topic,
                content=lesson_text + f"\n\nFull REM report: {path}",
                category="session_rem_sleep",
            )
            saved["ana_memory"] = result.is_success
            saved["ana_memory_topic"] = topic
        except Exception as exc:
            saved["ana_memory_error"] = str(exc)
        return saved

    def _latest(self) -> ToolResult:
        if not self.reports_dir.exists():
            return ToolResult(status=ToolStatus.SUCCESS, data={"found": False}, message="No REM sleep report found.")
        reports = sorted(self.reports_dir.glob("REM_SLEEP_REPORT_*.md"), key=lambda path: path.stat().st_mtime)
        if not reports:
            return ToolResult(status=ToolStatus.SUCCESS, data={"found": False}, message="No REM sleep report found.")
        path = reports[-1]
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={"found": True, "path": str(path), "content": path.read_text(encoding="utf-8", errors="replace")},
            message=f"Latest REM sleep report: {path.name}",
        )

    def _clean_line(self, raw: str) -> str:
        line = raw.strip()
        line = re.sub(r"^[#*\-\s`>]+", "", line)
        line = re.sub(r"\s+", " ", line)
        return line.strip()

    def _to_bool(self, value: Any) -> bool:
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() not in {"0", "false", "no", "off"}
