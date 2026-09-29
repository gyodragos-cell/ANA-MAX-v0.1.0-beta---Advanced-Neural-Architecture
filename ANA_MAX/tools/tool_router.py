"""ANA MAX OS-22 tool router with confidence-gated decisions."""

from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence


CONFIDENCE_THRESHOLD = 0.60
CONFIRMATION_RISK_THRESHOLD = 0.55

DEFAULT_WEIGHTS: dict[str, float] = {
    "relevance": 0.40,
    "risk": -0.25,
    "cost": -0.15,
    "context_fit": 0.15,
    "latency": -0.05,
}

DEFAULT_RISKY_TOOLS: set[str] = {
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

DEFAULT_READ_ONLY_HINTS: tuple[str, ...] = (
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
    """Complete score for one candidate tool."""

    tool: str
    relevance: float
    risk: float
    cost: float
    context_fit: float
    latency: float
    raw_total: float
    confidence: float
    requires_confirmation: bool
    rationale: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @property
    def total(self) -> float:
        """Backward-compatible alias for raw_total."""
        return self.raw_total

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe score payload."""
        return {
            "tool": self.tool,
            "relevance": self.relevance,
            "risk": self.risk,
            "cost": self.cost,
            "context_fit": self.context_fit,
            "latency": self.latency,
            "raw_total": self.raw_total,
            "total": self.total,
            "confidence": self.confidence,
            "requires_confirmation": self.requires_confirmation,
            "rationale": self.rationale,
            "metadata": dict(self.metadata),
        }


@dataclass
class ToolDecision:
    """Final router decision for a task."""

    action: str
    tool: str | None
    score: ToolScore | None
    reason: str
    workspace_hint: str | None = None
    timestamp: float = field(default_factory=time.time)
    audit: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe decision payload."""
        return {
            "action": self.action,
            "tool": self.tool,
            "score": self.score.to_dict() if self.score else None,
            "reason": self.reason,
            "workspace_hint": self.workspace_hint,
            "timestamp": self.timestamp,
            "audit": self.audit,
        }


@dataclass(frozen=True)
class ToolRouteDecision:
    """Backward-compatible selected tool and ranked alternatives."""

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


class WorkspaceOracle:
    """Look up relevant workspace context from workspace/context/ and workspace/tasks/."""

    def __init__(self, workspace_root: Path | str | None = None) -> None:
        if workspace_root is None:
            workspace_root = Path(__file__).resolve().parents[2] / "workspace"
        self.root = Path(workspace_root)

    def lookup(self, task: str, tool: str) -> str | None:
        """Return a workspace hint or None when nothing matches."""
        if not self.root.exists():
            return None

        task_lower = task.lower()
        tool_lower = tool.lower()
        keywords = set(task_lower.split() + tool_lower.split("_"))

        hint = self._search_folder(self.root / "context", keywords)
        if hint:
            return hint

        return self._search_folder(self.root / "tasks", keywords)

    def _search_folder(self, folder: Path, keywords: set[str]) -> str | None:
        if not folder.exists():
            return None

        for path in sorted(folder.iterdir()):
            if not path.is_file():
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue

            if path.suffix == ".json":
                try:
                    data = json.loads(text)
                    flat = json.dumps(data, ensure_ascii=False).lower()
                except Exception:
                    flat = text.lower()
            else:
                flat = text.lower()

            matches = sum(1 for kw in keywords if len(kw) > 3 and kw in flat)
            if matches >= 2:
                snippet = text[:200].strip().replace("\n", " ")
                return f"[workspace/{path.parent.name}/{path.name}] {snippet}"

        return None


class ToolRouter:
    """OS-22 tool router with real scoring, sigmoid confidence, and decision layer."""

    def __init__(
        self,
        policies: Mapping[str, Any] | None = None,
        scoring_config: Mapping[str, float] | None = None,
        workspace_root: Path | str | None = None,
        confidence_threshold: float = CONFIDENCE_THRESHOLD,
    ) -> None:
        self.policies = dict(policies or {})
        self.weights = dict(DEFAULT_WEIGHTS)
        if scoring_config:
            self.weights.update(scoring_config)

        self.risky_tools = set(self.policies.get("risky_tools", DEFAULT_RISKY_TOOLS))
        self.confirmation_threshold = float(
            self.policies.get("confirmation_threshold", CONFIRMATION_RISK_THRESHOLD)
        )
        self.confidence_threshold = float(
            self.policies.get("confidence_threshold", confidence_threshold)
        )
        self.tool_feedback: dict[str, Any] = dict(self.policies.get("tool_feedback", {}))
        self.workspace = WorkspaceOracle(workspace_root)

    def decide(
        self,
        candidate_tools: Sequence[str],
        task_envelope: Any,
        context: Any,
    ) -> ToolDecision:
        """Choose execute, confirm, workspace_lookup, ask_clarification, or no_tool."""
        if not candidate_tools:
            return ToolDecision(
                action="no_tool",
                tool=None,
                score=None,
                reason="no candidate tools provided",
            )

        task_str = self._extract_task_str(task_envelope)
        scores = self._rank_tools(candidate_tools, task_envelope, context)
        best = scores[0]

        audit = {
            "decision_layer": "confidence_threshold",
            "candidates_scored": len(scores),
            "best_tool": best.tool,
            "confidence": best.confidence,
            "threshold": self.confidence_threshold,
            "all_scores": [score.to_dict() for score in scores],
        }

        if best.confidence < self.confidence_threshold:
            hint = self.workspace.lookup(task_str, best.tool)
            if hint:
                return ToolDecision(
                    action="workspace_lookup",
                    tool=best.tool,
                    score=best,
                    reason=(
                        f"confidence {best.confidence:.2f} < {self.confidence_threshold} "
                        "— found in workspace"
                    ),
                    workspace_hint=hint,
                    audit=audit,
                )
            return ToolDecision(
                action="ask_clarification",
                tool=best.tool,
                score=best,
                reason=(
                    f"confidence {best.confidence:.2f} < {self.confidence_threshold} "
                    "— workspace miss"
                ),
                workspace_hint=None,
                audit=audit,
            )

        if best.requires_confirmation:
            return ToolDecision(
                action="confirm",
                tool=best.tool,
                score=best,
                reason=f"confidence {best.confidence:.2f} OK but tool '{best.tool}' requires confirmation",
                audit=audit,
            )

        return ToolDecision(
            action="execute",
            tool=best.tool,
            score=best,
            reason=f"confidence {best.confidence:.2f} >= {self.confidence_threshold}",
            audit=audit,
        )

    def score_tool(self, tool_name: str, task_envelope: Any, context: Any) -> ToolScore:
        """Score one candidate tool and return a ToolScore with real confidence."""
        normalized = self._normalize_tool_name(tool_name)

        relevance = self._score_relevance(normalized, task_envelope, context)
        risk = self._score_risk(normalized, task_envelope, context)
        cost = self._score_cost(normalized, task_envelope, context)
        context_fit = self._score_context_fit(normalized, task_envelope, context)
        latency = self._estimate_latency(normalized)
        feedback_adjustment = self._score_observability_feedback(normalized)

        raw_total = self._weighted_total(relevance, risk, cost, context_fit, latency) + feedback_adjustment
        confidence = self._sigmoid(raw_total)
        needs_confirmation = self.requires_confirmation(normalized, risk)

        score_data = {
            "relevance": relevance,
            "risk": risk,
            "cost": cost,
            "context_fit": context_fit,
            "latency": latency,
            "feedback_adjustment": feedback_adjustment,
            "raw_total": raw_total,
            "confidence": confidence,
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
            raw_total=raw_total,
            confidence=confidence,
            requires_confirmation=needs_confirmation,
            rationale=rationale,
            metadata={"feedback_adjustment": feedback_adjustment},
        )

    def select_tool(
        self,
        candidate_tools: Sequence[str],
        task_envelope: Any,
        context: Any,
    ) -> ToolRouteDecision:
        """Select the highest-confidence candidate from available tools."""
        scores = tuple(self._rank_tools(candidate_tools, task_envelope, context))
        if not scores:
            return ToolRouteDecision(
                selected_tool=None,
                selected_score=None,
                candidates=(),
                rationale="no candidate tools provided",
            )
        selected = scores[0]
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

    def _rank_tools(
        self,
        candidate_tools: Sequence[str],
        task_envelope: Any,
        context: Any,
    ) -> list[ToolScore]:
        scores = [self.score_tool(tool, task_envelope, context) for tool in candidate_tools]
        return sorted(scores, key=lambda score: score.confidence, reverse=True)

    def _weighted_total(
        self,
        relevance: float,
        risk: float,
        cost: float,
        context_fit: float,
        latency: float,
    ) -> float:
        return (
            relevance * self.weights["relevance"]
            + risk * self.weights["risk"]
            + cost * self.weights["cost"]
            + context_fit * self.weights["context_fit"]
            + latency * self.weights["latency"]
        )

    @staticmethod
    def _sigmoid(x: float) -> float:
        """Convert linear score to probability in [0, 1]."""
        try:
            return 1.0 / (1.0 + math.exp(-5.0 * x))
        except OverflowError:
            return 0.0 if x < 0 else 1.0

    def _score_relevance(self, tool_name: str, task_envelope: Any, context: Any) -> float:
        task = str(self._read_value(task_envelope, "task", "")).lower()
        intent = str(self._read_value(task_envelope, "intent", "")).lower()
        combined = f"{task} {intent}".strip()

        if not combined:
            return 0.25
        if tool_name in combined:
            return 0.90

        parts = [part for part in tool_name.split("_") if len(part) > 2]
        matched = sum(1 for part in parts if part in combined)
        if matched >= 2:
            return 0.75
        if matched == 1:
            return 0.55
        if any(hint in tool_name for hint in DEFAULT_READ_ONLY_HINTS):
            return 0.50
        return 0.35

    def _score_risk(self, tool_name: str, task_envelope: Any, context: Any) -> float:
        if tool_name in self.risky_tools:
            return 0.80
        if any(term in tool_name for term in ("control", "write", "patch", "exec", "pentest", "delete")):
            return 0.65
        if any(term in tool_name for term in ("create", "update", "send", "post")):
            return 0.45
        return 0.20

    def _score_cost(self, tool_name: str, task_envelope: Any, context: Any) -> float:
        if any(term in tool_name for term in ("desktop", "vision", "scraper", "web_search", "browser")):
            return 0.55
        if any(term in tool_name for term in ("llm", "embed", "rerank", "inference")):
            return 0.45
        return 0.20

    def _score_context_fit(self, tool_name: str, task_envelope: Any, context: Any) -> float:
        raw_confidence = self._read_value(context, "confidence", 0.35)
        try:
            base = float(raw_confidence)
        except (TypeError, ValueError):
            base = 0.35
        base = max(0.0, min(1.0, base))

        if any(hint in tool_name for hint in DEFAULT_READ_ONLY_HINTS):
            return min(0.95, base + 0.20)
        return min(0.95, base + 0.05)

    def _estimate_latency(self, tool_name: str) -> float:
        if any(term in tool_name for term in ("desktop", "vision", "browser", "web", "network", "pentest")):
            return 0.65
        if any(term in tool_name for term in ("scraper", "search", "llm", "embed")):
            return 0.45
        return 0.20

    def _score_observability_feedback(self, tool_name: str) -> float:
        """Apply real feedback adjustment from audit/observability metrics."""
        feedback = self.tool_feedback.get(tool_name, {})
        if not isinstance(feedback, Mapping):
            return 0.0

        failure_rate = self._safe_float(feedback.get("failure_rate"), 0.0)
        avg_output = self._safe_float(feedback.get("avg_output_bytes"), 0.0)
        avg_latency = self._safe_float(feedback.get("avg_latency_ms"), 0.0)
        scenario_success = self._safe_float(feedback.get("scenario_success_rate"), 0.0)
        noisy_score = self._safe_float(feedback.get("noisy_tool_score"), 0.0)
        recent_success = feedback.get("recent_success")

        adjustment = 0.0
        adjustment -= min(0.12, failure_rate * 0.12)
        adjustment -= min(0.08, avg_output / 200_000)
        adjustment -= min(0.08, noisy_score * 0.08)
        adjustment -= min(0.05, avg_latency / 20_000)
        adjustment += min(0.08, scenario_success * 0.08)
        if recent_success is True:
            adjustment += 0.05
        elif recent_success is False:
            adjustment -= 0.05
        return adjustment

    def build_rationale(self, tool_name: str, score_data: Mapping[str, Any]) -> str:
        """Build a compact human-readable rationale for a route score."""
        confidence = float(score_data.get("confidence", 0.0))
        relevance = float(score_data.get("relevance", 0.0))
        risk = float(score_data.get("risk", 0.0))
        cost = float(score_data.get("cost", 0.0))
        context_fit = float(score_data.get("context_fit", 0.0))
        feedback = float(score_data.get("feedback_adjustment", 0.0))
        return (
            f"confidence={confidence:.2f} | relevance={relevance:.2f} risk={risk:.2f} "
            f"cost={cost:.2f} context_fit={context_fit:.2f} feedback={feedback:+.2f}"
        )

    @staticmethod
    def _extract_task_str(task_envelope: Any) -> str:
        if isinstance(task_envelope, str):
            return task_envelope
        if isinstance(task_envelope, Mapping):
            return str(task_envelope.get("task", task_envelope.get("description", "")))
        return str(task_envelope or "")

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
