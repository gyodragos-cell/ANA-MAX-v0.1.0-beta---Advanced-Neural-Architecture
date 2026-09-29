from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any, Callable, Deque, Mapping

from ana.core.error_model.errors import ValidationError


@dataclass(frozen=True)
class Event:
    sequence: int
    topic: str
    payload: Mapping[str, Any]
    trace_id: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "sequence": self.sequence,
            "topic": self.topic,
            "payload": dict(self.payload),
            "trace_id": self.trace_id,
        }


Subscriber = Callable[[Event], None]


class EventBus:
    def __init__(self, *, replay_limit: int = 100) -> None:
        if replay_limit < 1:
            raise ValidationError("replay_limit must be positive", source="event_bus")
        self._sequence = 0
        self._replay_limit = replay_limit
        self._events: Deque[Event] = deque(maxlen=replay_limit)
        self._subscribers: dict[str, list[Subscriber]] = defaultdict(list)

    def subscribe(self, topic: str, subscriber: Subscriber) -> None:
        self._validate_topic(topic)
        self._subscribers[topic].append(subscriber)

    def publish(
        self,
        topic: str,
        payload: Mapping[str, Any] | None = None,
        *,
        trace_id: str,
    ) -> Event:
        self._validate_topic(topic)
        self._sequence += 1
        event = Event(
            sequence=self._sequence,
            topic=topic,
            payload=dict(payload or {}),
            trace_id=trace_id,
        )
        self._events.append(event)
        for subscriber in tuple(self._subscribers.get(topic, ())):
            subscriber(event)
        for subscriber in tuple(self._subscribers.get("*", ())):
            subscriber(event)
        return event

    def replay(self, topic: str | None = None) -> list[Event]:
        if topic is not None:
            self._validate_topic(topic)
        return [
            event
            for event in self._events
            if topic is None or event.topic == topic
        ]

    def queue(self) -> list[Event]:
        return list(self._events)

    def _validate_topic(self, topic: str) -> None:
        if not topic or not topic.strip():
            raise ValidationError("topic must be a non-empty string", source="event_bus")


class EventLog:
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    def record(self, event: Event) -> None:
        self.events.append(event.to_dict())
