"""ANA MAX v22 AI engine abstraction scaffolding.

This module separates orchestration decisions from any specific reasoning
backend. The first version provides small, deterministic placeholders for Codex,
local engines, and cloud engines so later modules can depend on a stable shape
without pulling in provider SDKs or network behavior.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol


DEFAULT_SUMMARY_BUDGET = 1200


@dataclass(frozen=True)
class EnginePlan:
    """Compact plan returned by an AI engine before tool routing."""

    engine: str
    steps: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    rationale: str = ""
    confidence: float = 0.25

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe representation of the planned steps."""
        return {
            "engine": self.engine,
            "steps": [dict(step) for step in self.steps],
            "rationale": self.rationale,
            "confidence": self.confidence,
        }


@dataclass(frozen=True)
class CritiqueResult:
    """Safety-aware review of a proposed plan."""

    approved: bool
    reason: str
    revised_plan: Mapping[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe critique payload."""
        return {
            "approved": self.approved,
            "reason": self.reason,
            "revised_plan": dict(self.revised_plan) if self.revised_plan else None,
        }


class EngineAdapter(Protocol):
    """Protocol implemented by concrete AI engine adapters."""

    name: str

    def plan(self, task_envelope: Any, context: Any) -> EnginePlan:
        """Create candidate steps for a task and compact context."""

    def critique(self, plan: Any, safety_context: Any) -> CritiqueResult:
        """Review a plan against safety and policy context."""

    def summarize(self, tool_result: Any, budget: int) -> str:
        """Condense a tool result to fit a context budget."""


class BaseEngine:
    """Small deterministic base adapter used by v22 placeholder engines."""

    name = "base"

    def plan(self, task_envelope: Any, context: Any) -> EnginePlan:
        """Create a minimal observation-first placeholder plan."""
        task = self._read_value(task_envelope, "task", "unspecified task")
        summary = self._read_value(context, "summary", "context unavailable")
        step = {
            "id": "observe-1",
            "intent": "build_context",
            "description": f"Use compact context before acting on: {task}",
            "context_summary": summary,
            "requires_tool_routing": True,
        }
        # TODO(v22): apply model-specific limits and context-window policies.
        # TODO(v22): generate multi-step plans from real engine responses.
        return EnginePlan(
            engine=self.name,
            steps=(step,),
            rationale="placeholder observation-first plan",
            confidence=0.3,
        )

    def critique(self, plan: Any, safety_context: Any) -> CritiqueResult:
        """Approve placeholder read-only plans and flag unsafe context later."""
        blocked = bool(self._read_value(safety_context, "blocked", False))
        if blocked:
            reason = str(self._read_value(safety_context, "reason", "blocked by safety context"))
            return CritiqueResult(approved=False, reason=reason)
        # TODO(v22): inspect mutating steps, policy tiers, and confirmation needs.
        return CritiqueResult(approved=True, reason="placeholder critique passed")

    def summarize(self, tool_result: Any, budget: int = DEFAULT_SUMMARY_BUDGET) -> str:
        """Return a compact string summary within the requested budget."""
        text = self._result_to_text(tool_result)
        if budget <= 0:
            return ""
        if len(text) <= budget:
            return text
        # TODO(v22): replace truncation with structured summarization.
        return text[: max(0, budget - 15)].rstrip() + "... [truncated]"

    @staticmethod
    def _read_value(obj: Any, name: str, default: Any = None) -> Any:
        """Read a named field from a mapping or object."""
        if isinstance(obj, Mapping):
            return obj.get(name, default)
        return getattr(obj, name, default)

    @staticmethod
    def _result_to_text(tool_result: Any) -> str:
        """Convert a placeholder tool result to text for compact summaries."""
        if tool_result is None:
            return ""
        if isinstance(tool_result, str):
            return tool_result
        if isinstance(tool_result, Mapping):
            summary = tool_result.get("summary")
            if isinstance(summary, str):
                return summary
            return str(dict(tool_result))
        return str(tool_result)


class CodexEngine(BaseEngine):
    """Placeholder adapter for Codex as the primary coding engine."""

    name = "codex"

    # TODO(v22): wire Codex-specific cost profile, limits, and streaming hooks.


class LocalEngine(BaseEngine):
    """Placeholder adapter for offline or local LLM backends."""

    name = "local"

    # TODO(v22): add local model discovery, context limits, and fallback policy.


class CloudEngine(BaseEngine):
    """Placeholder adapter for policy-controlled cloud/provider engines."""

    name = "cloud"

    # TODO(v22): add provider cost profiles, auth policy, and streaming behavior.


class AIEngine:
    """Facade that exposes a stable AI engine interface to the orchestrator."""

    def __init__(self, engine_name: str = "codex") -> None:
        """Initialize the requested engine adapter by name."""
        self.engine_name = engine_name
        self.adapter = self._create_adapter(engine_name)
        # TODO(v22): add fallback chain and health-aware adapter selection.

    def plan(self, task_envelope: Any, context: Any) -> EnginePlan:
        """Create candidate steps for a normalized task and compact context."""
        return self.adapter.plan(task_envelope, context)

    def critique(self, plan: Any, safety_context: Any) -> CritiqueResult:
        """Review a plan against safety context before routing or execution."""
        return self.adapter.critique(plan, safety_context)

    def summarize(self, tool_result: Any, budget: int = DEFAULT_SUMMARY_BUDGET) -> str:
        """Summarize a tool result for reuse inside a bounded context window."""
        return self.adapter.summarize(tool_result, budget)

    @staticmethod
    def _create_adapter(engine_name: str) -> EngineAdapter:
        """Create a placeholder adapter for a supported engine name."""
        normalized = (engine_name or "codex").strip().lower()
        adapters: dict[str, type[BaseEngine]] = {
            "codex": CodexEngine,
            "local": LocalEngine,
            "cloud": CloudEngine,
        }
        adapter_class = adapters.get(normalized)
        if adapter_class is None:
            raise ValueError(f"unsupported engine: {engine_name}")
        return adapter_class()