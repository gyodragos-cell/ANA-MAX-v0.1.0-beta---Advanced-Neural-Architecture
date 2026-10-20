from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import math
from typing import Any
from uuid import uuid4


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def new_id() -> str:
    return str(uuid4())


@dataclass(slots=True)
class TraceEvent:
    trace_id: str
    source: str
    component: str
    kind: str
    action: str
    outcome: str = "observed"
    event_id: str = field(default_factory=new_id)
    timestamp: str = field(default_factory=utc_now)
    parent_event_id: str | None = None
    mission_id: str | None = None
    target: str | None = None
    duration_ms: float | None = None
    attributes: dict[str, Any] = field(default_factory=dict)
    schema_version: str = "os29.trace.v1"

    def validate(self) -> None:
        for name in ("trace_id", "source", "component", "kind", "action", "event_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string")
            if len(value) > 256:
                raise ValueError(f"{name} exceeds 256 characters")
        if self.outcome not in {"observed", "success", "failure", "error", "blocked", "unknown"}:
            raise ValueError("outcome must be one of observed/success/failure/error/blocked/unknown")
        if self.duration_ms is not None:
            if isinstance(self.duration_ms, bool) or not isinstance(self.duration_ms, (int, float)):
                raise ValueError("duration_ms must be a finite non-negative number")
            if not math.isfinite(float(self.duration_ms)) or self.duration_ms < 0:
                raise ValueError("duration_ms must be a finite non-negative number")
        for name in ("parent_event_id", "mission_id", "target"):
            value = getattr(self, name)
            if value is not None and not isinstance(value, str):
                raise ValueError(f"{name} must be a string or null")
            if isinstance(value, str) and len(value) > 4096:
                raise ValueError(f"{name} exceeds 4096 characters")
        if not isinstance(self.timestamp, str):
            raise ValueError("timestamp must be ISO-8601 text")
        try:
            datetime.fromisoformat(self.timestamp.replace("Z", "+00:00"))
        except (ValueError, AttributeError) as exc:
            raise ValueError("timestamp must be ISO-8601") from exc
        if not isinstance(self.attributes, dict):
            raise ValueError("attributes must be a JSON object")
        if self.schema_version != "os29.trace.v1":
            raise ValueError(f"unsupported trace schema: {self.schema_version}")

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "TraceEvent":
        if not isinstance(value, dict):
            raise ValueError("event must be a JSON object")
        allowed = {
            "trace_id", "source", "component", "kind", "action", "outcome",
            "event_id", "timestamp", "parent_event_id", "mission_id", "target",
            "duration_ms", "attributes", "schema_version",
        }
        extra = set(value) - allowed
        if extra:
            raise ValueError(f"unknown event fields: {', '.join(sorted(extra))}")
        event = cls(**value)
        event.validate()
        return event