from __future__ import annotations

from typing import Any, Mapping

from ana.core.event_bus.bus import EventBus
from ana.core.logging.formatters import format_log_entry


class StructuredLogger:
    def __init__(self, event_bus: EventBus, *, level: str = "info") -> None:
        self.event_bus = event_bus
        self.level = level.lower()

    def info(self, message: str, payload: Mapping[str, Any] | None = None, *, trace_id: str) -> None:
        self.log("info", message, payload or {}, trace_id=trace_id)

    def warn(self, message: str, payload: Mapping[str, Any] | None = None, *, trace_id: str) -> None:
        self.log("warn", message, payload or {}, trace_id=trace_id)

    def error(self, message: str, payload: Mapping[str, Any] | None = None, *, trace_id: str) -> None:
        self.log("error", message, payload or {}, trace_id=trace_id)

    def log(self, level: str, message: str, payload: Mapping[str, Any], *, trace_id: str) -> None:
        entry = {
            "level": level,
            "message": message,
            "payload": dict(payload),
            "trace_id": trace_id,
        }
        self.event_bus.publish("log.entry", entry, trace_id=trace_id)
        formatted = format_log_entry(entry)
        # Keep structured logs available through EventBus; console output is optional.
        print(formatted)
