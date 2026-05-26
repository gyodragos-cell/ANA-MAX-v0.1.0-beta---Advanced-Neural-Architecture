"""ANA MAX v22 observability layer scaffolding.

This module records compact runtime events and tool metrics for the v22
orchestrator. It is intentionally in-memory for now: the shape is stable enough
for router scoring and dashboard integrations, while long-term storage remains a
future concern.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping


DEFAULT_NOISY_FAILURE_RATE = 0.35
DEFAULT_NOISY_OUTPUT_BYTES = 16_384


def _utc_now() -> str:
    """Return an ISO-8601 UTC timestamp for observability records."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class ToolStats:
    """Aggregated placeholder metrics for one tool."""

    tool_name: str
    calls: int = 0
    successes: int = 0
    failures: int = 0
    total_latency_ms: float = 0.0
    total_output_bytes: int = 0
    estimated_tokens_saved: int = 0
    latency_samples: list[float] = field(default_factory=list)
    recent_success: bool | None = None
    last_seen_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe stats snapshot."""
        avg_latency = self.total_latency_ms / self.calls if self.calls else 0.0
        avg_output = self.total_output_bytes / self.calls if self.calls else 0.0
        failure_rate = self.failures / self.calls if self.calls else 0.0
        latency_percentiles = self._latency_percentiles()
        return {
            "tool_name": self.tool_name,
            "calls": self.calls,
            "successes": self.successes,
            "failures": self.failures,
            "failure_rate": failure_rate,
            "avg_latency_ms": avg_latency,
            "latency_percentiles": latency_percentiles,
            "avg_output_bytes": avg_output,
            "total_output_bytes": self.total_output_bytes,
            "estimated_tokens_saved": self.estimated_tokens_saved,
            "noisy_tool_score": self.noisy_tool_score(),
            "recent_success": self.recent_success,
            "last_seen_at": self.last_seen_at,
            "is_noisy": self.is_noisy(),
        }

    def is_noisy(self) -> bool:
        """Return whether this tool currently looks noisy or unreliable."""
        if not self.calls:
            return False
        failure_rate = self.failures / self.calls
        avg_output = self.total_output_bytes / self.calls
        return failure_rate >= DEFAULT_NOISY_FAILURE_RATE or avg_output >= DEFAULT_NOISY_OUTPUT_BYTES

    def noisy_tool_score(self) -> float:
        """Return a small placeholder score for noisy-tool routing feedback."""
        if not self.calls:
            return 0.0
        failure_rate = self.failures / self.calls
        avg_output = self.total_output_bytes / self.calls
        output_pressure = min(1.0, avg_output / DEFAULT_NOISY_OUTPUT_BYTES)
        return min(1.0, round((failure_rate + output_pressure) / 2, 4))

    def _latency_percentiles(self) -> dict[str, float | None]:
        """Return placeholder latency percentiles from in-memory samples."""
        if not self.latency_samples:
            return {"p50": None, "p95": None}
        samples = sorted(self.latency_samples)
        return {
            "p50": self._percentile(samples, 0.50),
            "p95": self._percentile(samples, 0.95),
        }

    @staticmethod
    def _percentile(samples: list[float], percentile: float) -> float:
        """Return a nearest-rank percentile for a non-empty sample list."""
        index = min(len(samples) - 1, max(0, round((len(samples) - 1) * percentile)))
        return samples[index]


@dataclass(frozen=True)
class ObservabilityEvent:
    """Compact event record for debugging and learning."""

    event_type: str
    payload: Mapping[str, Any] = field(default_factory=dict)
    correlation_id: str | None = None
    created_at: str = field(default_factory=_utc_now)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe event payload."""
        return {
            "event_type": self.event_type,
            "payload": dict(self.payload),
            "correlation_id": self.correlation_id,
            "created_at": self.created_at,
        }


class Observability:
    """Record compact v22 runtime events and tool metrics."""

    def __init__(self, sinks: list[Any] | None = None) -> None:
        """Initialize in-memory event and metric stores."""
        self.sinks = list(sinks or [])
        self.events: list[ObservabilityEvent] = []
        self.tool_stats: dict[str, ToolStats] = {}
        self.created_at = _utc_now()
        self.default_correlation_id = "v22-placeholder"
        # TODO(v22): export metrics to dashboard and health endpoints.
        # TODO(v22): add long-term storage for compact historical metrics.

    def record_event(self, event_type: str, payload: Mapping[str, Any] | None = None) -> ObservabilityEvent:
        """Record a compact event and forward it to configured sinks."""
        if not isinstance(event_type, str) or not event_type.strip():
            raise ValueError("event_type must be a non-empty string")
        if payload is not None and not isinstance(payload, Mapping):
            raise ValueError("payload must be a mapping")

        data = dict(payload or {})
        correlation_id = str(data.get("correlation_id") or self.default_correlation_id)
        event = ObservabilityEvent(event_type=event_type.strip(), payload=data, correlation_id=correlation_id)
        self.events.append(event)
        for sink in self.sinks:
            self._emit_to_sink(sink, event)
        return event

    def record_tool_metrics(self, tool_name: str, latency_ms: float, output_bytes: int, success: bool) -> ToolStats:
        """Update aggregate metrics for a tool call."""
        normalized = self._normalize_tool_name(tool_name)
        stats = self.tool_stats.setdefault(normalized, ToolStats(tool_name=normalized))
        stats.calls += 1
        stats.successes += 1 if success else 0
        stats.failures += 0 if success else 1
        safe_latency = max(0.0, float(latency_ms))
        stats.total_latency_ms += safe_latency
        stats.latency_samples.append(safe_latency)
        stats.total_output_bytes += max(0, int(output_bytes))
        stats.estimated_tokens_saved += self._estimate_tokens_saved(output_bytes)
        stats.recent_success = bool(success)
        stats.last_seen_at = _utc_now()

        self.record_event(
            "tool_metrics",
            {
                "tool_name": normalized,
                "latency_ms": latency_ms,
                "output_bytes": output_bytes,
                "success": bool(success),
                "correlation_id": self.default_correlation_id,
            },
        )
        # TODO(v22): feed noisy-tool signals back into ToolRouter scoring.
        # TODO(v22): adapt scoring weights from latency and failure trends.
        return stats

    def get_health_snapshot(self) -> dict[str, Any]:
        """Return a compact health snapshot for dashboards and tests."""
        total_calls = sum(stats.calls for stats in self.tool_stats.values())
        total_failures = sum(stats.failures for stats in self.tool_stats.values())
        noisy_tools = [name for name, stats in self.tool_stats.items() if stats.is_noisy()]
        failure_rate = total_failures / total_calls if total_calls else 0.0
        return {
            "created_at": self.created_at,
            "snapshot_at": _utc_now(),
            "event_count": len(self.events),
            "tool_count": len(self.tool_stats),
            "total_tool_calls": total_calls,
            "total_failures": total_failures,
            "failure_rate": failure_rate,
            "noisy_tools": noisy_tools,
            "correlation_id": self.default_correlation_id,
            "latency_percentiles": {
                name: stats.to_dict()["latency_percentiles"] for name, stats in self.tool_stats.items()
            },
            "noisy_tool_score": {
                name: stats.noisy_tool_score() for name, stats in self.tool_stats.items()
            },
            "status": "degraded" if noisy_tools or failure_rate >= DEFAULT_NOISY_FAILURE_RATE else "ok",
        }

    def get_tool_stats(self, tool_name: str) -> dict[str, Any]:
        """Return aggregate stats for one tool, or an empty stats object."""
        normalized = self._normalize_tool_name(tool_name)
        stats = self.tool_stats.get(normalized)
        if stats is None:
            return ToolStats(tool_name=normalized).to_dict()
        return stats.to_dict()

    def _estimate_tokens_saved(self, output_bytes: int) -> int:
        """Estimate token savings from tool-assisted compact output."""
        # Placeholder: assume compact tool output saves about one token per
        # eight raw bytes avoided compared with reasoning-only context dumping.
        # TODO(v22): compare reasoning-only budget against actual compact context.
        return max(0, int(output_bytes) // 8)

    @staticmethod
    def _emit_to_sink(sink: Any, event: ObservabilityEvent) -> None:
        """Forward an event to a sink if it exposes a compatible method."""
        if hasattr(sink, "record_event"):
            sink.record_event(event.to_dict())
        elif callable(sink):
            sink(event.to_dict())

    @staticmethod
    def _normalize_tool_name(tool_name: str) -> str:
        """Normalize a tool name for metric keys."""
        if not isinstance(tool_name, str) or not tool_name.strip():
            raise ValueError("tool_name must be a non-empty string")
        return tool_name.strip().lower()
