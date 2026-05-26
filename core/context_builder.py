"""ANA MAX v22 context builder scaffolding.

The context builder prepares compact, factual context for the v22 orchestrator.
It deliberately avoids heavy scans in this first scaffold and leaves concrete
collection strategies to future integrations with ANA tools such as workspace
situational awareness, error radar, project navigation, and focused file reads.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping


DEFAULT_CONFIDENCE = 0.35


def _utc_now() -> str:
    """Return an ISO-8601 UTC timestamp for cache and context records."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass(frozen=True)
class ContextSnapshot:
    """Compact context passed from the builder to planning and routing."""

    summary: str
    facts: tuple[str, ...] = field(default_factory=tuple)
    workspace_state: Mapping[str, Any] = field(default_factory=dict)
    recent_errors: tuple[Mapping[str, Any], ...] = field(default_factory=tuple)
    docs: tuple[Mapping[str, Any], ...] = field(default_factory=tuple)
    blind_spots: tuple[str, ...] = field(default_factory=tuple)
    confidence: float = DEFAULT_CONFIDENCE
    created_at: str = field(default_factory=_utc_now)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe context representation for engines and tests."""
        return {
            "summary": self.summary,
            "facts": list(self.facts),
            "workspace_state": dict(self.workspace_state),
            "recent_errors": [dict(item) for item in self.recent_errors],
            "docs": [dict(item) for item in self.docs],
            "blind_spots": list(self.blind_spots),
            "confidence": self.confidence,
            "created_at": self.created_at,
        }


class ContextBuilder:
    """Build and cache compact context for ANA MAX v22 tasks."""

    def __init__(self, cache_ttl_seconds: int = 30) -> None:
        """Initialize placeholder caches and freshness settings."""
        self.cache_ttl_seconds = cache_ttl_seconds
        self._cache: dict[str, Any] = {
            "created_at": None,
            "workspace_state": None,
            "recent_errors": None,
            "docs": None,
        }

    def build_context(self, task_envelope: Any) -> ContextSnapshot:
        """Collect and merge the minimum useful context for a task envelope."""
        workspace_state = self._collect_workspace_state(task_envelope)
        recent_errors = self._collect_recent_errors(task_envelope)
        docs = self._collect_docs(task_envelope)
        return self._merge_and_summarize(
            task_envelope=task_envelope,
            workspace_state=workspace_state,
            recent_errors=recent_errors,
            docs=docs,
        )

    def _collect_workspace_state(self, task_envelope: Any) -> dict[str, Any]:
        """Collect a compact workspace state placeholder.

        TODO(v22): call workspace_situational_awareness and cache its compact
        JSON output when the runtime integration is wired in.
        """
        workspace = self._get_envelope_value(task_envelope, "workspace", "")
        state = {
            "workspace": workspace,
            "source": "placeholder",
            "collected_at": _utc_now(),
            "git": {"known": False},
            "active_window": {"known": False},
        }
        self._cache["workspace_state"] = state
        self._cache["created_at"] = state["collected_at"]
        return state

    def _collect_recent_errors(self, task_envelope: Any) -> tuple[dict[str, Any], ...]:
        """Collect recent error signals placeholder.

        TODO(v22): call error_radar and include only prioritized compact errors.
        """
        errors: tuple[dict[str, Any], ...] = ()
        self._cache["recent_errors"] = errors
        return errors

    def _collect_docs(self, task_envelope: Any) -> tuple[dict[str, Any], ...]:
        """Collect relevant documentation pointers placeholder.

        TODO(v22): use project_navigator or focused file reads to identify the
        smallest set of owner docs for the current task.
        """
        docs = (
            {
                "path": "ANA_MAX_V22_ARCHITECTURE.md",
                "reason": "v22 blueprint",
                "loaded": False,
            },
        )
        self._cache["docs"] = docs
        return docs

    def _merge_and_summarize(
        self,
        task_envelope: Any,
        workspace_state: Mapping[str, Any],
        recent_errors: tuple[Mapping[str, Any], ...],
        docs: tuple[Mapping[str, Any], ...],
    ) -> ContextSnapshot:
        """Merge collected context into a compact summary object."""
        task = self._get_envelope_value(task_envelope, "task", "")
        facts = ["ContextBuilder scaffold active"]
        if workspace_state.get("workspace"):
            facts.append(f"Workspace set: {workspace_state['workspace']}")
        if docs:
            facts.append(f"Documentation pointers: {len(docs)}")
        if recent_errors:
            facts.append(f"Recent errors: {len(recent_errors)}")

        blind_spots = [
            "workspace state uses placeholder collection",
            "recent errors are not connected to error_radar yet",
            "docs are referenced but not loaded yet",
        ]

        summary_task = task or "unspecified task"
        summary = f"Compact scaffold context for: {summary_task}"

        # TODO(v22): compute confidence from source freshness and tool quality.
        confidence = DEFAULT_CONFIDENCE
        if workspace_state.get("workspace"):
            confidence += 0.1
        confidence = min(confidence, 0.95)

        return ContextSnapshot(
            summary=summary,
            facts=tuple(facts),
            workspace_state=dict(workspace_state),
            recent_errors=tuple(dict(item) for item in recent_errors),
            docs=tuple(dict(item) for item in docs),
            blind_spots=tuple(blind_spots),
            confidence=confidence,
        )

    @staticmethod
    def _get_envelope_value(task_envelope: Any, name: str, default: Any = None) -> Any:
        """Read a value from a TaskEnvelope-like object or mapping."""
        if isinstance(task_envelope, Mapping):
            return task_envelope.get(name, default)
        return getattr(task_envelope, name, default)
