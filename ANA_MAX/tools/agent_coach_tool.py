"""
Agent Coach Tool.

Turns ANA telemetry into short, practical guidance for coding agents.
The goal is not a demo effect; it is to stop wasteful loops and steer the
agent toward better observation, verification, and code quality.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from ANA_MAX.local.tool_telemetry import load_tool_telemetry, summarize_tool_telemetry
from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus
from tools.tool_router_tool import ToolRouterTool


CLICK_TOOLS = {
    "desktop_control",
    "desktop_control_tool",
    "windows_uia_bridge",
    "browser_control",
    "vision_fallback",
    "remote_control",
}

OBSERVE_TOOLS = [
    "foreground_ui_snapshot",
    "windows_uia_bridge action=list_windows",
    "desktop_capture operation=capture",
    "workspace_situational_awareness",
    "tool_healthcheck",
]

NOISE_TOOLS = {
    "agent_coach",
    "frida_instrument",
}

OBSERVATION_TOOLS = {
    "desktop_capture",
    "foreground_ui_snapshot",
    "workspace_situational_awareness",
    "tool_healthcheck",
    "frida_instrument",
    "system_control",
}

MONITOR_CONTEXT_QUERIES = {
    "operator status reload behavior",
    "next scoped lab action after green baseline",
}

MONITOR_CONTEXT_TASKS = {
    "ANA nucleus smoke graph context",
    "ANA lab autonomous readiness pass",
}

MONITOR_ROUTER_TASKS = {
    "ANA nucleus smoke code context verify",
    "ANA lab autonomous readiness pass",
}


class AgentCoachTool(Tool):
    def __init__(self) -> None:
        root = Path(__file__).resolve().parents[1]
        self.log_file = root / "logs" / "observability.jsonl"
        self.memory_file = root / "memory" / "agent_coach_lessons.jsonl"
        self.memory_file.parent.mkdir(parents=True, exist_ok=True)

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="agent_coach",
            description=(
                "Reads live ANA telemetry and gives the coding agent concise coaching. "
                "Call before acting, after errors, or when stuck. Detects repeated clicks, "
                "repeated tool failures, missing confirm=True, wrong parameters, and tells "
                "Qoder what to do next instead of looping."
            ),
            parameters=[
                ToolParameter(
                    name="action",
                    description=(
                        "coach for telemetry advice, recommend for next-tool routing, "
                        "lessons for stored lessons, reset to clear learned coach lessons"
                    ),
                    type="string",
                    required=False,
                    default="coach",
                    choices=["coach", "recommend", "lessons", "reset"],
                ),
                ToolParameter(
                    name="task",
                    description="Current task or goal for action=recommend",
                    type="string",
                    required=False,
                    default="",
                ),
                ToolParameter(
                    name="error",
                    description="Optional current error text for action=recommend",
                    type="string",
                    required=False,
                    default="",
                ),
                ToolParameter(
                    name="mode",
                    description="Optional router mode override for action=recommend",
                    type="string",
                    required=False,
                    default="auto",
                    choices=[
                        "auto",
                        "project_state",
                        "failure",
                        "code_change",
                        "ui_desktop",
                        "runtime_deep",
                        "release_sync",
                        "memory_handoff",
                    ],
                ),
                ToolParameter(
                    name="max_tools",
                    description="Maximum tools to recommend for action=recommend",
                    type="integer",
                    required=False,
                    default=5,
                ),
                ToolParameter(
                    name="limit",
                    description="How many recent telemetry entries to inspect",
                    type="integer",
                    required=False,
                    default=120,
                ),
                ToolParameter(
                    name="repeat_threshold",
                    description="How many equivalent actions count as a loop",
                    type="integer",
                    required=False,
                    default=5,
                ),
                ToolParameter(
                    name="include_prompt",
                    description="Return a ready-to-use prompt for Qoder",
                    type="boolean",
                    required=False,
                    default=True,
                ),
            ],
            category="ai_core",
        )

    def execute(self, **kwargs: Any) -> ToolResult:
        action = kwargs.get("action", "coach")
        if action == "lessons":
            lessons = self._read_lessons(int(kwargs.get("limit", 20) or 20))
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"count": len(lessons), "lessons": lessons},
                message=f"Agent coach lessons: {len(lessons)}",
            )
        if action == "reset":
            self.memory_file.write_text("", encoding="utf-8")
            return ToolResult(status=ToolStatus.SUCCESS, data={"reset": True}, message="Agent coach memory reset.")
        if action == "recommend":
            report = self._build_recommendation(
                task=str(kwargs.get("task") or ""),
                error=str(kwargs.get("error") or ""),
                mode=str(kwargs.get("mode") or "auto"),
                max_tools=int(kwargs.get("max_tools", 5) or 5),
                limit=int(kwargs.get("limit", 120) or 120),
                repeat_threshold=int(kwargs.get("repeat_threshold", 5) or 5),
                include_prompt=bool(kwargs.get("include_prompt", True)),
            )
            if report["coach"]["severity"] in {"warn", "critical"}:
                self._remember(report["coach"])
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data=report,
                message=report["headline"],
            )
        if action != "coach":
            return ToolResult(status=ToolStatus.ERROR, error=f"Unknown action: {action}")

        limit = int(kwargs.get("limit", 120) or 120)
        repeat_threshold = int(kwargs.get("repeat_threshold", 5) or 5)
        include_prompt = bool(kwargs.get("include_prompt", True))

        entries = self._read_observability(limit)
        report = self._build_report(entries, repeat_threshold)
        if include_prompt:
            report["prompt_for_qoder"] = self._prompt(report)

        if report["severity"] in {"warn", "critical"}:
            self._remember(report)

        return ToolResult(
            status=ToolStatus.SUCCESS,
            data=report,
            message=report["headline"],
        )

    def _build_recommendation(
        self,
        task: str,
        error: str,
        mode: str,
        max_tools: int,
        limit: int,
        repeat_threshold: int,
        include_prompt: bool,
    ) -> Dict[str, Any]:
        entries = self._read_observability(limit)
        coach_report = self._build_report(entries, repeat_threshold)

        router_task = task.strip() or coach_report.get("headline", "")
        if not router_task:
            router_task = "Decide the next best ANA MAX tool."

        router_mode = self._recommend_mode(mode, error, coach_report)
        router_result = ToolRouterTool().execute(
            task=router_task,
            error=error,
            mode=router_mode,
            max_tools=max_tools,
        )
        router_data = router_result.data if isinstance(router_result.data, dict) else {}
        router_tools = list(router_data.get("recommended_tools") or [])
        coach_tools = list(coach_report.get("next_best_tools") or [])
        tool_stack = self._merge_tool_lists(router_tools, coach_tools, max_tools)

        primary_tool = tool_stack[0] if tool_stack else ""
        headline = self._recommend_headline(coach_report, router_data, primary_tool)
        data = {
            "schema": "ana.agent_coach.recommend.v1",
            "severity": coach_report.get("severity", "ok"),
            "headline": headline,
            "primary_tool": primary_tool,
            "tool_stack": tool_stack,
            "router": {
                "mode": router_data.get("mode", router_mode),
                "headline": router_data.get("headline", ""),
                "recommended_tools": router_tools,
                "tool_profiles": router_data.get("tool_profiles", {}),
                "active_profiles": router_data.get("active_profiles", []),
                "filtered_by_profile": router_data.get("filtered_by_profile", []),
                "steps": router_data.get("steps", []),
                "guardrail": router_data.get("guardrail", ""),
            },
            "coach": {
                "severity": coach_report.get("severity", "ok"),
                "headline": coach_report.get("headline", ""),
                "signals": coach_report.get("signals", []),
                "advice": coach_report.get("advice", []),
                "next_best_tools": coach_tools,
                "inspected_entries": coach_report.get("inspected_entries", 0),
            },
            "next_action": self._next_action(primary_tool, coach_report, router_data),
            "steps": router_data.get("steps", []),
            "guardrail": router_data.get("guardrail", ""),
        }
        if include_prompt:
            data["prompt_for_qoder"] = self._recommend_prompt(data)
        return data

    def _read_observability(self, limit: int) -> List[Dict[str, Any]]:
        return load_tool_telemetry(path=self.log_file, limit=limit, include_event_stream=True)

    def _read_lessons(self, limit: int) -> List[Dict[str, Any]]:
        if not self.memory_file.exists():
            return []
        lessons: List[Dict[str, Any]] = []
        for line in self.memory_file.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                lessons.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return lessons[-limit:]

    def _build_report(self, entries: List[Dict[str, Any]], repeat_threshold: int) -> Dict[str, Any]:
        raw_count = len(entries)
        entries = [entry for entry in entries if not self._is_monitor_entry(entry)]
        if not entries:
            return {
                "severity": "ok",
                "headline": "Only monitor telemetry found. Lab hub/watchdog/mirror look calm.",
                "signals": [],
                "advice": ["Continue with the live console open; investigate only if a real task/tool fails."],
                "next_best_tools": OBSERVE_TOOLS,
                "inspected_entries": 0,
                "raw_entries": raw_count,
            }

        signals: List[Dict[str, Any]] = []
        advice: List[str] = []
        next_tools = list(OBSERVE_TOOLS)

        repeated = self._find_repeated_actions(entries, repeat_threshold)
        if repeated:
            worst = repeated[0]
            signals.append({
                "type": "repeated_action",
                "tool": worst["tool"],
                "count": worst["count"],
                "args": worst["args"],
            })
            if self._is_click_action(worst["tool"], worst["args"]):
                advice.append(
                    "Stop clicking the same target. Capture/inspect the UI state, read the visible text, then choose a different strategy."
                )
                next_tools = [
                    "foreground_ui_snapshot",
                    "windows_uia_bridge action=inspect_window confirm=True",
                    "desktop_capture operation=capture",
                    "ocr_tool action=screen",
                ]
            else:
                advice.append(
                    f"Stop repeating {worst['tool']} with the same arguments. Check its output, then change input or verify state."
                )

        repeated_errors = self._find_repeated_errors(entries, repeat_threshold=3)
        if repeated_errors:
            worst_error = repeated_errors[0]
            signals.append({
                "type": "repeated_error",
                "tool": worst_error["tool"],
                "count": worst_error["count"],
                "error": worst_error["error"],
            })
            advice.append(self._error_advice(worst_error["error"]))

        requires_confirm = [
            e for e in entries[-30:]
            if e.get("status") == "requires_confirmation"
        ]
        if requires_confirm:
            last = requires_confirm[-1]
            signals.append({
                "type": "missing_confirm",
                "tool": last.get("tool"),
                "error": last.get("error"),
            })
            advice.append(
                f"{last.get('tool')} requires confirmation. If the action is intended and safe, call it again with confirm=True."
            )

        failed_ratio = self._failure_ratio(entries[-40:])
        if failed_ratio >= 0.35:
            signals.append({"type": "high_failure_ratio", "ratio": round(failed_ratio, 2)})
            advice.append(
                "Failure rate is high. Pause execution, summarize the last failures, and run a small healthcheck before more actions."
            )
            next_tools = ["tool_healthcheck", "agent_coach", "workspace_situational_awareness"]

        if not advice:
            advice.append(
                "Telemetry looks usable. Continue with small verified steps: observe, act once, verify, then proceed."
            )

        severity = "ok"
        if any(s["type"] in {"repeated_error", "high_failure_ratio"} for s in signals):
            severity = "critical"
        elif signals:
            severity = "warn"

        headline = self._headline(severity, signals)
        return {
            "severity": severity,
            "headline": headline,
            "signals": signals,
            "advice": advice,
            "next_best_tools": next_tools,
            "recent_tools": self._recent_tool_counts(entries),
            "inspected_entries": len(entries),
            "raw_entries": raw_count,
            "telemetry_summary": summarize_tool_telemetry(entries),
        }

    def _is_monitor_entry(self, entry: Dict[str, Any]) -> bool:
        tool = str(entry.get("tool", ""))
        args = entry.get("args") or {}
        status = str(entry.get("status") or "")
        error = str(entry.get("error") or "")

        if tool == "event_stream" and str(args.get("action", "")).strip("'\"") == "stats":
            return True
        if tool == "graph_context_pack" and str(args.get("action", "")).strip("'\"") == "stats":
            return status == "success"
        if (
            tool == "code_context_pack"
            and str(args.get("query", "")).strip("'\"") == "operator status reload behavior"
            and status == "success"
        ):
            return True
        if tool == "code_context_pack" and status == "success":
            query = str(args.get("query", "")).strip("'\"")
            task = str(args.get("task", "")).strip("'\"")
            if query in MONITOR_CONTEXT_QUERIES or task in MONITOR_CONTEXT_TASKS:
                return True
        if tool == "tool_router" and status == "success":
            task = str(args.get("task", "")).strip("'\"")
            if task in MONITOR_ROUTER_TASKS:
                return True
        if tool == "session_audit" and str(args.get("action", "")).strip("'\"") == "trust":
            return status == "success"
        if tool == "error_radar" and str(args.get("scope", "quick")).strip("'\"") == "quick":
            return status == "success"
        if tool == "foreground_ui_snapshot" and status == "success":
            return True
        if tool == "windows_uia_bridge" and self._is_readonly_uia(args) and status == "success":
            return True
        if tool == "frida_instrument" and str(args.get("operation", "")).strip("'\"") in {"version", "devices"}:
            return status == "success" or "Frida not installed" in error
        if tool == "desktop_control" and str(args.get("operation", "")).strip("'\"") == "view":
            return status == "success"
        if (
            tool == "ana_memory"
            and str(args.get("action", "")).strip("'\"") == "find_error_solution"
            and status == "success"
        ):
            return True
        if (
            tool == "tool_contract_validator"
            and str(args.get("action", "")).strip("'\"") == "validate_tool"
            and str(args.get("tool_name", "")).strip("'\"") == "definitely_missing_tool_for_guidance"
        ):
            return True
        if tool == "tool_router" and "MCP tool failed with schema mismatch" in str(args.get("task", "")):
            return True
        if tool == "tool_router" and str(args.get("error", "")).strip("'\"") == "Invalid value for operation":
            return True
        if tool == "tool_router" and str(args.get("task", "")).strip("'\"") == "Tool tool_contract_validator failed":
            return True
        if tool == "demo_probe" and "inactive profile" in error.lower():
            return True
        if tool == "router_failure_demo" and error == "demo failure":
            return True
        if (
            tool in {"tool_router", "agent_coach"}
            and str(args.get("task", "")).strip("'\"") == "Tool router_failure_demo failed"
            and str(args.get("error", "")).strip("'\"") == "demo failure"
        ):
            return True
        if (
            tool == "agent_coach"
            and str(args.get("task", "")).strip("'\"") == "Tool tool_contract_validator failed"
            and str(args.get("error", "")).strip("'\"") == "success=false"
        ):
            return True
        return False

    def _find_repeated_actions(self, entries: Iterable[Dict[str, Any]], repeat_threshold: int) -> List[Dict[str, Any]]:
        counts: Counter[Tuple[str, str]] = Counter()
        args_by_key: Dict[Tuple[str, str], Dict[str, Any]] = {}

        for entry in entries:
            if entry.get("status") not in {"success", "error", "requires_confirmation"}:
                continue
            tool = str(entry.get("tool", ""))
            args = entry.get("args") or {}
            if tool in NOISE_TOOLS and not self._is_click_action(tool, args):
                continue
            if tool in OBSERVATION_TOOLS and entry.get("status") == "success":
                continue
            if tool == "windows_uia_bridge" and self._is_readonly_uia(args) and entry.get("status") == "success":
                continue
            key = (tool, self._normalized_args(args))
            counts[key] += 1
            args_by_key[key] = args

        repeated = []
        for key, count in counts.most_common():
            if count >= repeat_threshold:
                repeated.append({"tool": key[0], "args": args_by_key[key], "count": count})
        return repeated

    def _find_repeated_errors(self, entries: Iterable[Dict[str, Any]], repeat_threshold: int) -> List[Dict[str, Any]]:
        counts: Counter[Tuple[str, str]] = Counter()
        for entry in entries:
            if entry.get("status") not in {"error", "requires_confirmation", "blocked"}:
                continue
            tool = str(entry.get("tool", ""))
            error = str(entry.get("error") or "")
            if not error:
                continue
            counts[(tool, error)] += 1

        repeated = []
        for (tool, error), count in counts.most_common():
            if count >= repeat_threshold:
                repeated.append({"tool": tool, "error": error, "count": count})
        return repeated

    def _failure_ratio(self, entries: List[Dict[str, Any]]) -> float:
        if not entries:
            return 0.0
        failed = sum(1 for e in entries if e.get("status") in {"error", "requires_confirmation", "blocked"})
        return failed / len(entries)

    def _recent_tool_counts(self, entries: List[Dict[str, Any]]) -> Dict[str, int]:
        counts = Counter(str(e.get("tool", "")) for e in entries[-40:] if e.get("tool"))
        return dict(counts.most_common(10))

    def _normalized_args(self, args: Dict[str, Any]) -> str:
        clean = {
            str(k): str(v)
            for k, v in sorted((args or {}).items())
            if k not in {"timeout", "confirm"}
        }
        return json.dumps(clean, sort_keys=True, ensure_ascii=True)

    def _is_click_action(self, tool: str, args: Dict[str, Any]) -> bool:
        if tool not in CLICK_TOOLS:
            return False
        text = " ".join(str(v).lower() for v in (args or {}).values())
        return any(word in text for word in ["click", "click_at", "click_text", "click_element"])

    def _is_readonly_uia(self, args: Dict[str, Any]) -> bool:
        text = " ".join(str(v).lower() for v in (args or {}).values())
        return "list_windows" in text or "inspect_window" in text

    def _error_advice(self, error: str) -> str:
        lower = error.lower()
        if "parametrul 'action'" in lower:
            return "Use the tool schema exactly: this tool expects action=..., not operation=.... Re-read tools/list before retrying."
        if "parametrul 'operation'" in lower:
            return "Use operation=... for this tool. Do not guess parameter names; inspect the schema first."
        if "confirm=true" in lower or "necesita confirmare" in lower:
            return "The tool is gated. If the action is intended and safe, retry with confirm=True once, then verify the result."
        if "timeout" in lower:
            return "The tool timed out. Reduce scope, inspect state, or use a background process with periodic reads."
        return "Do not retry the same failing call. Inspect the schema/output, change one variable, then verify."

    def _headline(self, severity: str, signals: List[Dict[str, Any]]) -> str:
        if severity == "critical":
            return "Agent is likely stuck or failing repeatedly. Pause, observe, then change strategy."
        if severity == "warn":
            return "Agent may be looping. Verify UI/state before the next action."
        return "Agent telemetry is healthy enough. Continue with observe-act-verify."

    def _recommend_mode(self, mode: str, error: str, coach_report: Dict[str, Any]) -> str:
        if mode and mode != "auto":
            return mode
        if error.strip():
            return "auto"
        signal_types = {str(signal.get("type")) for signal in coach_report.get("signals", [])}
        if "repeated_error" in signal_types or "high_failure_ratio" in signal_types:
            return "failure"
        if "repeated_action" in signal_types:
            repeated = next(
                (signal for signal in coach_report.get("signals", []) if signal.get("type") == "repeated_action"),
                {},
            )
            if self._is_click_action(str(repeated.get("tool", "")), repeated.get("args") or {}):
                return "ui_desktop"
        return "auto"

    def _merge_tool_lists(self, primary: List[str], secondary: List[str], max_tools: int) -> List[str]:
        merged: List[str] = []
        for item in [*primary, *secondary]:
            tool = str(item).strip()
            if not tool or tool in merged:
                continue
            merged.append(tool)
            if len(merged) >= max(1, min(max_tools, 10)):
                break
        return merged

    def _recommend_headline(
        self,
        coach_report: Dict[str, Any],
        router_data: Dict[str, Any],
        primary_tool: str,
    ) -> str:
        severity = coach_report.get("severity", "ok")
        mode = router_data.get("mode", "auto")
        if primary_tool:
            return f"Use {primary_tool} next for {mode}; coach severity is {severity}."
        return f"No specific tool recommended; coach severity is {severity}."

    def _next_action(
        self,
        primary_tool: str,
        coach_report: Dict[str, Any],
        router_data: Dict[str, Any],
    ) -> str:
        if primary_tool:
            steps = router_data.get("steps") or []
            if steps:
                return f"Call {primary_tool}, then {steps[0].rstrip('.')}. Verify before another action."
            return f"Call {primary_tool}, inspect the result, then verify before another action."
        advice = coach_report.get("advice") or []
        if advice:
            return str(advice[0])
        return "Observe the workspace, choose one small action, and verify it."

    def _prompt(self, report: Dict[str, Any]) -> str:
        lines = [
            "Qoder, use this coach signal before your next action:",
            f"Severity: {report['severity']}",
            f"Headline: {report['headline']}",
            "Advice:",
        ]
        lines.extend(f"- {item}" for item in report["advice"])
        lines.append("Next tools to prefer:")
        lines.extend(f"- {item}" for item in report["next_best_tools"])
        lines.append("Rule: observe once, act once, verify once. If the same action fails twice, stop and change strategy.")
        return "\n".join(lines)

    def _recommend_prompt(self, report: Dict[str, Any]) -> str:
        lines = [
            "Qoder, use this next-tool recommendation:",
            f"Severity: {report['severity']}",
            f"Headline: {report['headline']}",
            f"Primary tool: {report['primary_tool'] or 'none'}",
            "Tool stack:",
        ]
        lines.extend(f"- {tool}" for tool in report["tool_stack"])
        lines.append(f"Next action: {report['next_action']}")
        lines.append("Rule: call one tool, read the result, then verify before continuing.")
        return "\n".join(lines)

    def _remember(self, report: Dict[str, Any]) -> None:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "severity": report["severity"],
            "headline": report["headline"],
            "signals": report["signals"][:5],
            "advice": report["advice"][:5],
        }
        with self.memory_file.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=True) + "\n")
