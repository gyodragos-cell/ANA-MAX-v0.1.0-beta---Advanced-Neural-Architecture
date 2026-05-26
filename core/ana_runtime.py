"""ANA MAX v22 runtime orchestrator scaffolding.

The runtime orchestrator wires together the v22 input, context, planning,
routing, execution, and observability layers. This module intentionally keeps
execution single-step and predictable until the safety and routing policies are
ready for real multi-tool chains.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping


DEFAULT_CANDIDATE_TOOLS = ("workspace_situational_awareness", "grep_file", "file_operations")


def _utc_now() -> str:
    """Return an ISO-8601 UTC timestamp for runtime records."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass(frozen=True)
class RuntimeSummary:
    """Compact result returned by ANAMaxRuntime.run."""

    success: bool
    task: str
    plan: Mapping[str, Any]
    route: Mapping[str, Any]
    result: Mapping[str, Any]
    audit_events: tuple[Mapping[str, Any], ...] = field(default_factory=tuple)
    created_at: str = field(default_factory=_utc_now)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe runtime summary."""
        return {
            "success": self.success,
            "task": self.task,
            "plan": dict(self.plan),
            "route": dict(self.route),
            "result": dict(self.result),
            "audit_events": [dict(event) for event in self.audit_events],
            "created_at": self.created_at,
        }


class ANAMaxRuntime:
    """Coordinate the ANA MAX v22 runtime layers for one task."""

    def __init__(
        self,
        input_layer: Any,
        context_builder: Any,
        ai_engine: Any,
        tool_router: Any,
        execution_layer: Any,
        observability: Any,
    ) -> None:
        """Initialize runtime dependencies and placeholder state."""
        self.input_layer = input_layer
        self.context_builder = context_builder
        self.ai_engine = ai_engine
        self.tool_router = tool_router
        self.execution_layer = execution_layer
        self.observability = observability
        self.audit_trail: list[dict[str, Any]] = []
        self.safety_envelope: dict[str, Any] = {
            "mode": "scaffold",
            "allow_mutation": False,
            "requires_confirmation": True,
        }
        self.runtime_state: dict[str, Any] = {
            "created_at": _utc_now(),
            "last_stage": None,
            "runs": 0,
        }
        self.fallback_pipeline: tuple[str, ...] = DEFAULT_CANDIDATE_TOOLS
        # TODO(v22): add streaming support for planning and tool output.
        # TODO(v22): add adaptive routing using observability feedback.

    def run(self, task_envelope: Any) -> RuntimeSummary:
        """Run one scaffolded observe-plan-route-execute cycle."""
        normalized = self.input_layer.normalize(task_envelope) if self.input_layer else task_envelope
        self.runtime_state["runs"] += 1
        self._observe("input", self._to_mapping(normalized))

        context = self._build_context(normalized)
        plan = self._plan(normalized, context)
        route = self._route(plan, context)
        selected_tool = self._read_value(route, "selected_tool", None)
        arguments = self._build_arguments(normalized, context, plan)
        result = self._execute(selected_tool, arguments) if selected_tool else self._empty_execution_result()
        summary = self._summarize(plan, route, result)
        self._observe("summary", summary.to_dict())
        return summary

    def _build_context(self, task_envelope: Any) -> Any:
        """Build compact context for the current task."""
        context = self.context_builder.build_context(task_envelope)
        self._observe("context", self._to_mapping(context))
        return context

    def _plan(self, task_envelope: Any, context: Any) -> Any:
        """Create a placeholder engine plan for the task and context."""
        plan = self.ai_engine.plan(task_envelope, context)
        critique = self.ai_engine.critique(plan, self.safety_envelope)
        self._observe("plan", {"plan": self._to_mapping(plan), "critique": self._to_mapping(critique)})
        # TODO(v22): support multi-step planning and revised plans.
        return plan

    def _route(self, plan: Any, context: Any) -> Any:
        """Select a tool for the first scaffolded plan step."""
        candidates = self._candidate_tools_from_plan(plan) or self.fallback_pipeline
        route = self.tool_router.select_tool(candidates, self._to_mapping(plan), context)
        self._observe("route", self._to_mapping(route))
        # TODO(v22): support multi-tool chains and fallback route expansion.
        return route

    def _execute(self, tool_name: str, arguments: Mapping[str, Any]) -> Any:
        """Execute one routed tool through the execution layer."""
        result = self.execution_layer.execute(tool_name, arguments)
        self._observe("execute", self._to_mapping(result))
        return result

    def _observe(self, stage: str, data: Any) -> None:
        """Record a compact audit and observability event for a runtime stage."""
        self.runtime_state["last_stage"] = stage
        event = {
            "stage": stage,
            "created_at": _utc_now(),
            "data_keys": sorted(self._to_mapping(data).keys()),
        }
        self.audit_trail.append(event)
        if self.observability is not None:
            self.observability.record_event(f"runtime_{stage}", event)

    def _summarize(self, plan: Any, route: Any, result: Any) -> RuntimeSummary:
        """Build the final compact runtime summary."""
        result_map = self._to_mapping(result)
        plan_map = self._to_mapping(plan)
        route_map = self._to_mapping(route)
        task = self._extract_task_from_plan(plan_map)
        success = bool(result_map.get("success", False))
        return RuntimeSummary(
            success=success,
            task=task,
            plan=plan_map,
            route=route_map,
            result=result_map,
            audit_events=tuple(self.audit_trail),
        )

    def _candidate_tools_from_plan(self, plan: Any) -> tuple[str, ...]:
        """Extract candidate tool names from a plan if present."""
        plan_map = self._to_mapping(plan)
        steps = plan_map.get("steps", [])
        candidates: list[str] = []
        for step in steps:
            if isinstance(step, Mapping):
                tool = step.get("tool") or step.get("candidate_tool")
                if isinstance(tool, str) and tool.strip():
                    candidates.append(tool.strip())
        return tuple(candidates)

    def _build_arguments(self, task_envelope: Any, context: Any, plan: Any) -> dict[str, Any]:
        """Build placeholder arguments for a selected tool."""
        # TODO(v22): derive tool-specific arguments from plan steps and schemas.
        return {
            "task": self._read_value(task_envelope, "task", ""),
            "context_summary": self._read_value(context, "summary", ""),
            "dry_run": True,
        }

    @staticmethod
    def _empty_execution_result() -> dict[str, Any]:
        """Return a compact result when no route is available."""
        return {
            "tool": None,
            "success": False,
            "summary": "no tool selected",
            "error": "routing did not select a tool",
        }

    @staticmethod
    def _extract_task_from_plan(plan_map: Mapping[str, Any]) -> str:
        """Best-effort task extraction for the runtime summary."""
        steps = plan_map.get("steps", [])
        if steps and isinstance(steps[0], Mapping):
            description = steps[0].get("description")
            if isinstance(description, str) and description.strip():
                return description.strip()
        return "unknown task"

    @staticmethod
    def _to_mapping(value: Any) -> dict[str, Any]:
        """Convert common v22 objects into JSON-safe mappings."""
        if value is None:
            return {}
        if isinstance(value, Mapping):
            return dict(value)
        to_dict = getattr(value, "to_dict", None)
        if callable(to_dict):
            return dict(to_dict())
        return {"value": value}

    @staticmethod
    def _read_value(obj: Any, name: str, default: Any = None) -> Any:
        """Read a named value from a mapping or object."""
        if isinstance(obj, Mapping):
            return obj.get(name, default)
        return getattr(obj, name, default)