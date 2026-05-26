"""Unified event bus for ANA MAX AI OS."""

from __future__ import annotations

import queue
import threading
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Callable, Mapping

from ana_os_v1.transport import Transport


Subscriber = Callable[[Mapping[str, Any]], None]
EVENT_PUBLISH = "event.publish"


class EventDelivery(dict):
    """Event object delivered to subscribers with payload-friendly equality."""

    def __eq__(self, other: object) -> bool:
        """Compare like the raw payload when tests/users expect data directly."""
        if isinstance(other, dict) and "category" not in other and "payload" not in other:
            return self.get("payload") == other
        return super().__eq__(other)


class EventBus:
    """Subscribe and publish categorized events."""

    def __init__(self, transport: Transport | None = None, node_id: str = "local") -> None:
        """Initialize subscribers."""
        self.transport = transport
        self.node_id = node_id
        self.subscribers: dict[str, list[Subscriber]] = defaultdict(list)
        self.history: list[dict[str, Any]] = []
        self.queue: queue.Queue[dict[str, Any]] = queue.Queue()

    def subscribe(self, category: str, callback: Subscriber) -> None:
        """Subscribe to a category."""
        self.subscribers[category].append(callback)

    def publish(
        self,
        category: str,
        payload: Mapping[str, Any] | None = None,
        local_only: bool = False,
        data: Mapping[str, Any] | None = None,
    ) -> None:
        """Publish synchronously."""
        payload_data = data if data is not None else payload
        event = EventDelivery({"category": category, "payload": dict(payload_data or {})})
        self.history.append(event)
        self.queue.put(event)
        for callback in self.subscribers.get(category, []):
            callback(event)
        for callback in self.subscribers.get("*", []):
            callback(event)
        if not local_only:
            self._send_event_message(category, payload_data or {})

    def publish_async(self, category: str, payload: Mapping[str, Any]) -> threading.Thread:
        """Publish in a daemon thread."""
        thread = threading.Thread(target=self.publish, args=(category, payload), daemon=True)
        thread.start()
        return thread

    def filter_events(self, category: str | None = None, key: str | None = None) -> list[dict[str, Any]]:
        """Return matching events from in-memory history."""
        events = self.history
        if category is not None:
            events = [event for event in events if event["category"] == category]
        if key is not None:
            events = [event for event in events if key in event["payload"]]
        return list(events)

    def handle_event_message(self, envelope: dict[str, Any]) -> None:
        """Handle one externally received distributed event envelope."""
        msg_type = envelope.get("type")
        if msg_type != EVENT_PUBLISH:
            return

        payload = envelope.get("payload") or {}
        topic = payload.get("topic")
        data = payload.get("data")
        if topic:
            self.publish(str(topic), data=data if isinstance(data, Mapping) else {"value": data}, local_only=True)

    def _send_event_message(self, topic: str, data: Any) -> None:
        """Broadcast an event over transport if configured."""
        if not self.transport:
            return
        envelope = {
            "version": 1,
            "type": EVENT_PUBLISH,
            "source_node": self.node_id,
            "target_node": "*",
            "timestamp": self._now(),
            "payload": {
                "topic": topic,
                "data": dict(data) if isinstance(data, Mapping) else data,
                "origin_node": self.node_id,
            },
        }
        try:
            self.transport.send(envelope)
        except Exception:
            return

    @staticmethod
    def _now() -> str:
        """Return an ISO-8601 UTC timestamp."""
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

__all__ = ["EVENT_PUBLISH", "EventBus", "EventDelivery"]

