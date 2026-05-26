"""ANA MAX v22 execution layer scaffolding.

The execution layer is the boundary between routed tool decisions and actual
tool calls. This scaffold keeps the interface stable, normalizes raw tool
results, applies small output limits, and leaves policy, streaming, fallback,
and observability integrations for later v22 phases.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping


DEFAULT_OUTPUT_LIMITS = {
    "max_text_bytes": 4096,
    "summary_bytes": 512,
}

DEFAULT_REDACTION_RULES = (
    "api_key",
    "token",
    "secret",
    "password",
)


def _utc_now() -> str:
    """Return an ISO-8601 UTC timestamp for audit-friendly records."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass(frozen=True)
class ExecutionResult:
    """Normalized result returned by the execution layer."""

    tool: str
    success: bool
    data: Any = None
    summary: str = ""
    error: str | None = None
    output_bytes: int = 0
    truncated: bool = False
    started_at: str = ""
    ended_at: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe execution result."""
        return {
            "tool": self.tool,
            "success": self.success,
            "data": self.data,
            "summary": self.summary,
            "error": self.error,
            "output_bytes": self.output_bytes,
            "truncated": self.truncated,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "metadata": dict(self.metadata),
        }


class ExecutionLayer:
    """Execute routed tools and normalize their outputs for v22."""

    def __init__(self, tool_registry: Any = None, output_limits: Mapping[str, int] | None = None) -> None:
        """Initialize execution dependencies and output policies."""
        self.tool_registry = tool_registry
        self.output_limits = dict(DEFAULT_OUTPUT_LIMITS)
        if output_limits:
            self.output_limits.update(output_limits)
        self.redaction_rules = tuple(DEFAULT_REDACTION_RULES)
        self.audit_events: list[dict[str, Any]] = []
        # TODO(v22): connect audit trail hooks to observability/event stream.
        # TODO(v22): add policy failure handling before tool invocation.

    def execute(self, tool_name: str, arguments: Mapping[str, Any] | None = None) -> ExecutionResult:
        """Execute a tool through the injected registry and normalize output."""
        started_at = _utc_now()
        arguments = dict(arguments or {})
        self._record_audit_event("start", tool_name, arguments)

        try:
            if self.tool_registry is None:
                raw_result = {
                    "success": False,
                    "error": "no tool registry configured",
                    "data": None,
                }
            else:
                raw_result = self.tool_registry.execute(tool_name, **arguments)
            normalized = self._normalize_result(raw_result)
            limited = self._apply_output_limits(normalized)
            result = ExecutionResult(
                tool=tool_name,
                success=limited["success"],
                data=limited.get("data"),
                summary=limited.get("summary", ""),
                error=limited.get("error"),
                output_bytes=limited.get("output_bytes", 0),
                truncated=limited.get("truncated", False),
                started_at=started_at,
                ended_at=_utc_now(),
                metadata={"executor": "v22_scaffold"},
            )
            self._record_audit_event("end", tool_name, {"success": result.success})
            # TODO(v22): emit latency, output size, and success to observability.
            return result
        except Exception as error:  # pragma: no cover - defensive boundary
            handled = self._handle_error(error)
            result = ExecutionResult(
                tool=tool_name,
                success=False,
                summary=handled["summary"],
                error=handled["error"],
                started_at=started_at,
                ended_at=_utc_now(),
                metadata={"executor": "v22_scaffold", "handled_error": True},
            )
            self._record_audit_event("error", tool_name, {"error": result.error})
            return result

    def _normalize_result(self, raw_result: Any) -> dict[str, Any]:
        """Convert registry-specific output into a stable compact mapping."""
        if isinstance(raw_result, ExecutionResult):
            return raw_result.to_dict()
        if isinstance(raw_result, Mapping):
            data = raw_result.get("data")
            error = raw_result.get("error")
            success = bool(raw_result.get("success", error is None))
            summary = str(raw_result.get("summary") or raw_result.get("message") or "")
            return {
                "success": success,
                "data": data,
                "summary": self._redact(summary),
                "error": self._redact(str(error)) if error else None,
                "truncated": False,
            }
        status = getattr(raw_result, "status", None)
        error = getattr(raw_result, "error", None)
        data = getattr(raw_result, "data", raw_result)
        success = str(status).lower().endswith("success") if status is not None else error is None
        return {
            "success": success,
            "data": data,
            "summary": self._redact(str(getattr(raw_result, "message", ""))),
            "error": self._redact(str(error)) if error else None,
            "truncated": False,
        }

    def _apply_output_limits(self, result: Mapping[str, Any]) -> dict[str, Any]:
        """Apply byte limits and summarization placeholders to a result."""
        limited = dict(result)
        text = self._stringify_output(limited.get("data"))
        output_bytes = len(text.encode("utf-8", errors="replace"))
        limited["output_bytes"] = output_bytes
        limited.setdefault("truncated", False)

        max_bytes = int(self.output_limits.get("max_text_bytes", 4096))
        if output_bytes > max_bytes:
            limited = self._summarize_large_output(limited)
        return limited

    def _summarize_large_output(self, result: Mapping[str, Any]) -> dict[str, Any]:
        """Replace large output with a compact placeholder summary."""
        summarized = dict(result)
        text = self._stringify_output(summarized.get("data"))
        budget = int(self.output_limits.get("summary_bytes", 512))
        clipped = text[: max(0, budget - 18)].rstrip()
        summarized["data"] = None
        summarized["summary"] = self._redact(f"{clipped}... [summarized]")
        summarized["truncated"] = True
        # TODO(v22): use AIEngine.summarize for structured large-output summaries.
        # TODO(v22): support streaming output handling for long-running tools.
        return summarized

    def _handle_error(self, error: Exception) -> dict[str, str]:
        """Convert unexpected execution errors into compact safe errors."""
        message = self._redact(str(error) or error.__class__.__name__)
        # TODO(v22): add fallback tool execution for recoverable failures.
        return {
            "summary": "execution failed before a normalized tool result was returned",
            "error": message,
        }

    def _record_audit_event(self, event: str, tool_name: str, payload: Mapping[str, Any]) -> None:
        """Record a compact in-memory audit event placeholder."""
        self.audit_events.append(
            {
                "event": event,
                "tool": tool_name,
                "payload_keys": sorted(str(key) for key in payload.keys()),
                "created_at": _utc_now(),
            }
        )

    def _redact(self, text: str) -> str:
        """Apply simple placeholder redaction rules to text."""
        redacted = text
        for marker in self.redaction_rules:
            redacted = redacted.replace(marker, "[redacted]")
        return redacted

    @staticmethod
    def _stringify_output(value: Any) -> str:
        """Convert output values into text for byte counting and summaries."""
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        return str(value)