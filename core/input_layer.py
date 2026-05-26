"""ANA MAX v22 input layer scaffolding.

This module normalizes incoming user or client requests into a compact task
envelope for the v22 orchestrator. It intentionally stays small: validation is
strict enough to protect downstream modules, while policy-heavy behavior remains
in the future router and execution layers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping


DEFAULT_SOURCE = "codex"
DEFAULT_MODE = "observe_only"
SUPPORTED_MODES = {
    "observe_only",
    "plan_only",
    "execute_with_confirmation",
    "execute_auto_safe",
}
__all__ = ["InputLayer", "InputValidationError", "TaskEnvelope"]


class InputValidationError(ValueError):
    """Raised when an incoming request cannot become a task envelope."""


@dataclass(frozen=True)
class TaskEnvelope:
    """Normalized request passed from the input layer to context building."""

    task: str
    source: str = DEFAULT_SOURCE
    workspace: str = ""
    mode: str = DEFAULT_MODE
    constraints: tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe representation for MCP, logs, and tests."""
        return {
            "task": self.task,
            "source": self.source,
            "workspace": self.workspace,
            "mode": self.mode,
            "constraints": list(self.constraints),
            "metadata": dict(self.metadata),
        }


class InputLayer:
    """Normalize external requests into compact ANA MAX v22 task envelopes."""

    def __init__(self, default_workspace: str | Path | None = None) -> None:
        """Initialize the layer with a default workspace for task envelopes."""
        self.default_workspace = str(default_workspace or Path.cwd())

    def normalize(self, request: str | Mapping[str, Any]) -> TaskEnvelope:
        """Normalize a raw string or mapping into a validated task envelope."""
        if isinstance(request, str):
            payload: Mapping[str, Any] = {"task": request}
        elif isinstance(request, Mapping):
            payload = request
        else:
            raise InputValidationError("request must be a string or mapping")

        task = self._require_text(payload.get("task"), "task")
        source = self._optional_text(payload.get("source"), DEFAULT_SOURCE)
        workspace = self._optional_text(payload.get("workspace"), self.default_workspace)
        mode = self._optional_text(payload.get("mode"), DEFAULT_MODE)
        constraints = self._normalize_constraints(payload.get("constraints", ()))
        metadata = payload.get("metadata", {})

        if mode not in SUPPORTED_MODES:
            raise InputValidationError(f"unsupported mode: {mode}")
        if not isinstance(metadata, Mapping):
            raise InputValidationError("metadata must be a mapping")

        # TODO(v22): attach caller identity and permission tier from MCP auth.
        # TODO(v22): add workspace allowlist checks before execution phases.
        return TaskEnvelope(
            task=task,
            source=source,
            workspace=workspace,
            mode=mode,
            constraints=constraints,
            metadata=dict(metadata),
        )

    @staticmethod
    def _require_text(value: Any, field_name: str) -> str:
        """Return stripped required text or raise a validation error."""
        if not isinstance(value, str) or not value.strip():
            raise InputValidationError(f"{field_name} must be a non-empty string")
        return value.strip()

    @staticmethod
    def _optional_text(value: Any, default: str) -> str:
        """Return stripped optional text or the provided default."""
        if value is None:
            return default
        if not isinstance(value, str) or not value.strip():
            raise InputValidationError("optional text fields must be strings")
        return value.strip()

    @staticmethod
    def _normalize_constraints(value: Any) -> tuple[str, ...]:
        """Normalize constraint input into a tuple of non-empty strings."""
        if value is None:
            return ()
        if isinstance(value, str):
            return (value.strip(),) if value.strip() else ()
        if not isinstance(value, (list, tuple, set)):
            raise InputValidationError("constraints must be a string or sequence")

        constraints: list[str] = []
        for item in value:
            if not isinstance(item, str) or not item.strip():
                raise InputValidationError("constraints must contain only strings")
            constraints.append(item.strip())
        return tuple(constraints)
