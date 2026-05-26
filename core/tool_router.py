"""ANA MAX v22 tool router scaffolding.

The tool router chooses the smallest useful tool for a planned step. This first
version is intentionally deterministic and lightweight: it exposes the scoring
shape, confirmation checks, and rationale builder without calling live tools or
hard-coding public release behavior.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence


DEFAULT_WEIGHTS = {
    "relevance": 0.4,
    "risk": -0.25,
    "cost": -0.15,
    "context_fit": 0.15,
    "latency": -0.05,
}

DEFAULT_RISKY_TOOLS = {
    "terminal",
    "bash_exec",
    "desktop_control",
    "desktop_control_tool",
    "uia_click",
    "uia_type",
    "git_operations",
    "file_operations",
    "file_patch",
    "network_pentest",
    "mitm_analyzer",
}

DEFAULT_READ_ONLY_HINTS = (
    "read",
    "grep",
    "search",
    "list",
    "inspect",
    "snapshot",
    "health",
    "radar",
    "navigator",
)


@dataclass(frozen=True)
class ToolScore:
    """Scoring details for one candidate tool."""

    tool: str
    relevance: float
    risk: float
    cost: float
    context_fit: float
    latency: float
    total: float
    requires_confirmation: bool
    rationale: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe score payload."""
        return {
            "tool": self.tool,
            "relevance": self.relevance,
            "risk": self.risk,
            "cost": self.cost,
            "context_fit": self.context_fit,
            "latency": self.latency,
            "total": self.total,
            "requires_confirmation": self.requires_confirmation,
            "rationale": self.rationale,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class ToolRouteDecision:
    """Selected tool and ranked alternatives for a planned step."""

    selected_tool: str | None
    selected_score: ToolScore | None
    candidates: tuple[ToolScore, ...] = field(default_factory=tuple)
    rationale: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe route decision."""
        return {
            "selected_tool": self.selected_tool,
            "selected_score": self.selected_score.to_dict() if self.selected_score else None,
            "candidates": [score.to_dict() for score in self.candidates],
            "rationale": self.rationale,
        }


class ToolRouter:
    """Score and select ANA MAX tools for v22 orchestrator steps."""

    def __init__(self, policies: Mapping[str, Any] | None = None, scoring_config: Mapping[str, float] | None = None) -> None:
        """Initialize router policies and scoring weights."""
        self.policies = dict(policies or {})
        self.weights = dict(DEFAULT_WEIGHTS)
        if scoring_config:
            self.weights.update(scoring_config)
        self.risky_tools = set(self.policies.get("risky_tools", DEFAULT_RISKY_TOOLS))
        self.confirmation_threshold = float(self.policies.get("confirmation_threshold", 0.55))
        self.tool_feedback = dict(self.policies.get("tool_feedback", {}))
        # TODO(v22): load dynamic scoring weights from observability metrics.
        # TODO(v22): add premium/internal tool gating from license policy.

    def score_tool(self, tool_name: str, task_envelope: Any, context: Any) -> ToolScore:
        """Score one candidate tool for a task and compact context."""
        normalized = self._normalize_tool_name(tool_name)
        relevance = self._score_relevance(normalized, task_envelope, context)
        risk = self._score_risk(normalized, task_envelope, context)
        cost = self._score_cost(normalized, task_envelope, context)
        context_fit = self._score_context_fit(normalized, task_envelope, context)
        latency = self._estimate_latency(normalized)
        feedback_adjustment = self._score_observability_feedback(normalized)
        total = self._weighted_total(relevance, risk, cost, context_fit, latency) + feedback_adjustment
        needs_confirmation = self.requires_confirmation(normalized, risk)
        score_data = {
            "relevance": relevance,
            "risk": risk,
            "cost": cost,
            "context_fit": context_fit,
            "latency": latency,
            "feedback_adjustment": feedback_adjustment,
            "total": total,
            "requires_confirmation": needs_confirmation,
        }
        rationale = self.build_rationale(normalized, score_data)
        return ToolScore(
            tool=normalized,
            relevance=relevance,
            risk=risk,
            cost=cost,
            context_fit=context_fit,
            latency=latency,
            total=total,
            requires_confirmation=needs_confirmation,
            rationale=rationale,
            metadata={"scoring": "placeholder", "feedback_adjustment": feedback_adjustment},
        )

    def select_tool(self, candidate_tools: Sequence[str], task_envelope: Any, context: Any) -> ToolRouteDecision:
        """Select the highest-scoring tool from candidate tools."""
        scores = tuple(
            sorted(
                (self.score_tool(tool, task_envelope, context) for tool in candidate_tools),
                key=lambda item: item.total,
                reverse=True,
            )
        )
        if not scores:
            return ToolRouteDecision(
                selected_tool=None,
                selected_score=None,
                candidates=(),
                rationale="no candidate tools provided",
            )
        selected = scores[0]
        # TODO(v22): add fallback logic when selected tool is unavailable.
        # TODO(v22): avoid noisy tools using observability failure/output metrics.
        return ToolRouteDecision(
            selected_tool=selected.tool,
            selected_score=selected,
            candidates=scores,
            rationale=f"selected {selected.tool}: {selected.rationale}",
        )

    def requires_confirmation(self, tool_name: str, risk_score: float) -> bool:
        """Return whether a candidate requires confirmation before execution."""
        normalized = self._normalize_tool_name(tool_name)
        if normalized in self.risky_tools:
            return True
        return risk_score >= self.confirmation_threshold

    def build_rationale(self, tool_name: str, score_data: Mapping[str, Any]) -> str:
        """Build a compact human-readable rationale for a route score."""
        total = float(score_data.get("total", 0.0))
        relevance = float(score_data.get("relevance", 0.0))
        risk = float(score_data.get("risk", 0.0))
        cost = float(score_data.get("cost", 0.0))
        context_fit = float(score_data.get("context_fit", 0.0))
        feedback = float(score_data.get("feedback_adjustment", 0.0))
        return (
            f"total={total:.2f}, relevance={relevance:.2f}, risk={risk:.2f}, "
            f"cost={cost:.2f}, context_fit={context_fit:.2f}, feedback={feedback:.2f}"
        )

    def _score_relevance(self, tool_name: str, task_envelope: Any, context: Any) -> float:
        """Placeholder relevance score using task text and tool-name hints."""
        task = str(self._read_value(task_envelope, "task", "")).lower()
        if not task:
            return 0.25
        if tool_name in task or any(part and part in task for part in tool_name.split("_")):
            return 0.75
        if any(hint in tool_name for hint in DEFAULT_READ_ONLY_HINTS):
            return 0.55
        return 0.4

    def _score_risk(self, tool_name: str, task_envelope: Any, context: Any) -> float:
        """Placeholder risk score based on known mutating or powerful tools."""
        if tool_name in self.risky_tools:
            return 0.75
        if any(term in tool_name for term in ("control", "write", "patch", "exec", "pentest")):
            return 0.65
        return 0.2

    def _score_cost(self, tool_name: str, task_envelope: Any, context: Any) -> float:
        """Placeholder cost score for expected token and runtime expense."""
        if any(term in tool_name for term in ("desktop", "vision", "scraper", "search")):
            return 0.45
        return 0.2

    def _score_context_fit(self, tool_name: str, task_envelope: Any, context: Any) -> float:
        """Placeholder context-fit score from available context confidence."""
        confidence = self._read_value(context, "confidence", 0.35)
        try:
            base = float(confidence)
        except (TypeError, ValueError):
            base = 0.35
        if any(hint in tool_name for hint in DEFAULT_READ_ONLY_HINTS):
            return min(0.95, base + 0.2)
        return min(0.95, base + 0.05)

    def _estimate_latency(self, tool_name: str) -> float:
        """Placeholder latency estimate normalized from 0.0 fast to 1.0 slow."""
        if any(term in tool_name for term in ("desktop", "vision", "browser", "web", "network")):
            return 0.55
        return 0.2

    def _score_observability_feedback(self, tool_name: str) -> float:
        """Return a small score adjustment from placeholder observability data."""
        feedback = self.tool_feedback.get(tool_name, {})
        if not isinstance(feedback, Mapping):
            return 0.0

        failure_rate = self._safe_float(feedback.get("failure_rate"), 0.0)
        avg_output = self._safe_float(feedback.get("avg_output_bytes"), 0.0)
        avg_latency = self._safe_float(feedback.get("avg_latency_ms"), 0.0)
        scenario_success_rate = self._safe_float(feedback.get("scenario_success_rate"), 0.0)
        noisy_tool_score = self._safe_float(feedback.get("noisy_tool_score"), 0.0)
        recent_success = feedback.get("recent_success")

        adjustment = 0.0
        adjustment -= min(0.12, failure_rate * 0.12)
        adjustment -= min(0.08, avg_output / 200_000)
        adjustment -= min(0.08, noisy_tool_score * 0.08)
        adjustment -= min(0.05, avg_latency / 20_000)
        adjustment += min(0.08, scenario_success_rate * 0.08)
        if recent_success is True:
            adjustment += 0.05
        elif recent_success is False:
            adjustment -= 0.05
        return adjustment

    def _weighted_total(self, relevance: float, risk: float, cost: float, context_fit: float, latency: float) -> float:
        """Combine score components using current router weights."""
        return (
            relevance * self.weights["relevance"]
            + risk * self.weights["risk"]
            + cost * self.weights["cost"]
            + context_fit * self.weights["context_fit"]
            + latency * self.weights["latency"]
        )

    @staticmethod
    def _safe_float(value: Any, default: float) -> float:
        """Convert a value to float for scoring, falling back safely."""
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _normalize_tool_name(tool_name: str) -> str:
        """Normalize a tool name for consistent scoring."""
        if not isinstance(tool_name, str) or not tool_name.strip():
            raise ValueError("tool_name must be a non-empty string")
        return tool_name.strip().lower()

    @staticmethod
    def _read_value(obj: Any, name: str, default: Any = None) -> Any:
        """Read a named field from a mapping or object."""
        if isinstance(obj, Mapping):
            return obj.get(name, default)
        return getattr(obj, name, default)
