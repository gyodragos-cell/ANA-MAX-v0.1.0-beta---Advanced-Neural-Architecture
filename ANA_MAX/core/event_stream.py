#!/usr/bin/env python3
"""
ANA MAX - Event Stream Architecture
===================================
Local observability stream for ANA MAX tools and runtime events.

The module stays deterministic, ASCII-safe, and dependency-light so it can be
used from tool hooks without destabilizing the main runtime.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Deque, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

DEFAULT_DB_NAME = "events.db"
EVENT_CACHE_SIZE = 1000
REPLAYABLE_EVENT_TYPES = {
    "tool_call",
    "remote_action",
    "vision_analysis",
}


class EventType(str, Enum):
    """Event categories stored in the local observability stream."""

    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    VISION_ANALYSIS = "vision_analysis"
    REMOTE_ACTION = "remote_action"
    SWARM_TASK = "swarm_task"
    MEMORY_OPERATION = "memory_operation"
    ERROR = "error"
    USER_INPUT = "user_input"
    SYSTEM_STATE = "system_state"
    SCREENSHOT = "screenshot"
    CONVERSATION = "conversation"


@dataclass
class BusEvent:
    """Compatibility event object for topic-based publish/subscribe flows."""

    sequence: int
    topic: str
    payload: Dict[str, Any]
    trace_id: str = ""
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sequence": self.sequence,
            "topic": self.topic,
            "payload": self.payload,
            "trace_id": self.trace_id,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


class EventLog:
    """Small recorder used by legacy event-bus style tests."""

    def __init__(self) -> None:
        self.events: List[Dict[str, Any]] = []

    def record(self, event: Any) -> None:
        if isinstance(event, BusEvent):
            self.events.append(event.to_dict())
        elif isinstance(event, dict):
            self.events.append(dict(event))
        else:
            self.events.append({"value": event})


class EventBus:
    """
    Minimal topic-based compatibility bus.

    This is intentionally separate from EventStream so that we can preserve
    event-stream persistence while still satisfying simple publish/subscribe
    expectations from older tests and tools.
    """

    def __init__(self, replay_limit: int = 1000) -> None:
        self.replay_limit = max(1, int(replay_limit))
        self._sequence = 0
        self._events: Deque[BusEvent] = deque(maxlen=self.replay_limit)
        self._subscribers: List[Tuple[str, Callable[[BusEvent], None]]] = []

    def subscribe(self, topic: str, callback: Callable[[BusEvent], None]) -> None:
        self._subscribers.append((topic, callback))

    def unsubscribe(self, topic: str, callback: Callable[[BusEvent], None]) -> None:
        self._subscribers = [
            item for item in self._subscribers if item != (topic, callback)
        ]

    def publish(
        self,
        topic: str,
        payload: Dict[str, Any],
        trace_id: str | None = None,
        **metadata: Any,
    ) -> BusEvent:
        self._sequence += 1
        event = BusEvent(
            sequence=self._sequence,
            topic=topic,
            payload=dict(payload),
            trace_id=trace_id or "",
            metadata=dict(metadata),
        )
        self._events.append(event)

        for pattern, callback in list(self._subscribers):
            if _topic_matches(pattern, topic):
                try:
                    callback(event)
                except Exception as exc:
                    logger.debug("EventBus subscriber error: %s", exc)

        return event

    def replay(self, topic: str | None = None) -> List[BusEvent]:
        if topic is None:
            return list(self._events)
        return [event for event in self._events if _topic_matches(topic, event.topic)]


def _topic_matches(pattern: str, topic: str) -> bool:
    if pattern == "*" or topic == "*":
        return True
    if pattern.endswith("*"):
        return topic.startswith(pattern[:-1])
    return pattern == topic


def _default_db_path() -> Path:
    override = (
        os.environ.get("ANA_EVENT_STREAM_DB")
        or os.environ.get("ANA_EVENT_DB_PATH")
        or ""
    ).strip()
    if override:
        return Path(override).expanduser()
    return Path(__file__).resolve().parents[1] / "data" / DEFAULT_DB_NAME


def _normalize_event_type(event_type: EventType | str | Enum) -> EventType:
    if isinstance(event_type, EventType):
        return event_type
    if isinstance(event_type, Enum):
        return EventType(str(event_type.value).strip())
    value = str(event_type).strip()
    if value.startswith("EventType."):
        value = value.split(".", 1)[1].lower()
    return EventType(value)


def _safe_json_loads(value: Any) -> Any:
    if value is None:
        return {}
    if isinstance(value, (dict, list, int, float, bool)):
        return value
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return {}
        try:
            parsed = json.loads(text)
        except Exception:
            return {"raw": text}
        return parsed
    return value


class EventStream:
    """
    SQLite-backed event stream for ANA MAX debugging and observability.
    """

    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = Path(db_path) if db_path is not None else _default_db_path()
        self._db_path = self.db_path.expanduser()
        self._conn: sqlite3.Connection | None = None
        self._lock = threading.Lock()
        self._subscribers: List[Callable[[Dict[str, Any]], None]] = []
        self._cache: Deque[Dict[str, Any]] = deque(maxlen=EVENT_CACHE_SIZE)
        self._init_db()

    def _init_db(self) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS events (
                id TEXT PRIMARY KEY,
                timestamp REAL NOT NULL,
                event_type TEXT NOT NULL,
                source TEXT,
                data TEXT DEFAULT '{}',
                metadata TEXT DEFAULT '{}',
                screenshot_path TEXT,
                duration REAL,
                success INTEGER DEFAULT 1
            );

            CREATE INDEX IF NOT EXISTS idx_event_type ON events(event_type);
            CREATE INDEX IF NOT EXISTS idx_timestamp ON events(timestamp);
            CREATE INDEX IF NOT EXISTS idx_source ON events(source);
            CREATE INDEX IF NOT EXISTS idx_success ON events(success);
            """
        )
        self._conn.commit()

    def subscribe(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        if callback not in self._subscribers:
            self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        if callback in self._subscribers:
            self._subscribers.remove(callback)

    def emit(
        self,
        event_type: EventType | str,
        source: str,
        data: Dict[str, Any],
        metadata: Dict[str, Any] | None = None,
        screenshot_path: str | None = None,
        duration: float | None = None,
        success: bool = True,
    ) -> str:
        event_type_obj = _normalize_event_type(event_type)
        event_id = str(uuid.uuid4())[:12]
        timestamp = time.time()
        event = {
            "id": event_id,
            "timestamp": timestamp,
            "event_type": event_type_obj.value,
            "source": source,
            "data": dict(data),
            "metadata": dict(metadata or {}),
            "screenshot_path": screenshot_path,
            "duration": duration,
            "success": bool(success),
        }

        if self._conn is None:
            raise RuntimeError("Event stream database is not initialized")

        with self._lock:
            self._conn.execute(
                """
                INSERT INTO events
                    (id, timestamp, event_type, source, data, metadata,
                     screenshot_path, duration, success)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id,
                    timestamp,
                    event_type_obj.value,
                    source,
                    json.dumps(data, ensure_ascii=True),
                    json.dumps(metadata or {}, ensure_ascii=True),
                    screenshot_path,
                    duration,
                    1 if success else 0,
                ),
            )
            self._conn.commit()

        self._cache.append(event)

        for callback in list(self._subscribers):
            try:
                callback(dict(event))
            except Exception as exc:
                logger.debug("Event subscriber error: %s", exc)

        return event_id

    def query_events(
        self,
        event_type: EventType | str | None = None,
        source: str | None = None,
        start_time: float | None = None,
        end_time: float | None = None,
        limit: int = 100,
        success: bool | None = None,
    ) -> List[Dict[str, Any]]:
        if self._conn is None:
            raise RuntimeError("Event stream database is not initialized")

        query = "SELECT * FROM events WHERE 1=1"
        params: List[Any] = []

        if event_type is not None:
            query += " AND event_type = ?"
            params.append(_normalize_event_type(event_type).value)
        if source is not None:
            query += " AND source = ?"
            params.append(source)
        if start_time is not None:
            query += " AND timestamp >= ?"
            params.append(float(start_time))
        if end_time is not None:
            query += " AND timestamp <= ?"
            params.append(float(end_time))
        if success is not None:
            query += " AND success = ?"
            params.append(1 if success else 0)

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(max(1, int(limit)))

        with self._lock:
            rows = self._conn.execute(query, params).fetchall()

        events: List[Dict[str, Any]] = []
        for row in rows:
            event = dict(row)
            event["data"] = _safe_json_loads(event.get("data"))
            event["metadata"] = _safe_json_loads(event.get("metadata"))
            event["success"] = bool(event.get("success"))
            events.append(event)
        return events

    def get_timeline(
        self,
        start_time: float | None = None,
        end_time: float | None = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        if start_time is None:
            start_time = time.time() - 3600
        if end_time is None:
            end_time = time.time()

        events = self.query_events(
            start_time=start_time,
            end_time=end_time,
            limit=limit,
        )
        events.reverse()

        timeline: List[Dict[str, Any]] = []
        for event in events:
            timeline.append(
                {
                    "id": event["id"],
                    "time": datetime.fromtimestamp(event["timestamp"]).strftime(
                        "%H:%M:%S"
                    ),
                    "type": event["event_type"],
                    "source": event.get("source"),
                    "success": event.get("success", True),
                    "duration": event.get("duration"),
                    "summary": self._summarize_event(event),
                }
            )
        return timeline

    def _summarize_event(self, event: Dict[str, Any]) -> str:
        event_type = event.get("event_type", "")
        data = event.get("data") or {}
        if not isinstance(data, dict):
            data = {"value": data}

        if event_type == EventType.TOOL_CALL.value:
            return f"Called tool: {data.get('tool_name') or data.get('tool') or 'unknown'}"
        if event_type == EventType.TOOL_RESULT.value:
            return f"Tool result: {data.get('tool_name') or data.get('tool') or 'unknown'}"
        if event_type == EventType.VISION_ANALYSIS.value:
            return f"Vision analysis: {data.get('query', 'unknown')}"
        if event_type == EventType.REMOTE_ACTION.value:
            return f"Remote action: {data.get('action', 'unknown')}"
        if event_type == EventType.ERROR.value:
            return f"Error: {data.get('message') or data.get('error') or 'unknown error'}"
        if event_type == EventType.USER_INPUT.value:
            return f"User input: {str(data.get('text', ''))[:50]}"
        if event_type == EventType.SYSTEM_STATE.value:
            return f"System state: {str(data)[:60]}"
        if event_type == EventType.SCREENSHOT.value:
            return "Screenshot captured"
        if event_type == EventType.CONVERSATION.value:
            return f"Conversation: {str(data)[:60]}"
        return str(data)[:100]

    def get_statistics(self, hours: int = 24) -> Dict[str, Any]:
        start_time = time.time() - (max(1, int(hours)) * 3600)
        events = self.query_events(start_time=start_time, limit=10000)

        stats: Dict[str, Any] = {
            "total_events": len(events),
            "by_type": {},
            "by_source": {},
            "success_rate": 0,
            "avg_duration": 0,
            "time_range": int(hours),
        }

        successful = 0
        total_duration = 0.0
        duration_count = 0
        for event in events:
            event_type = event.get("event_type", "unknown")
            source = event.get("source") or "unknown"
            stats["by_type"][event_type] = stats["by_type"].get(event_type, 0) + 1
            stats["by_source"][source] = stats["by_source"].get(source, 0) + 1
            if event.get("success"):
                successful += 1
            if event.get("duration") is not None:
                total_duration += float(event["duration"])
                duration_count += 1

        if events:
            stats["success_rate"] = successful / len(events)
        if duration_count:
            stats["avg_duration"] = total_duration / duration_count
        return stats

    def replay_actions(
        self,
        session_id: str | None = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        events = self.query_events(limit=max(1, int(limit)) * 5)
        actions: List[Dict[str, Any]] = []
        for event in events:
            if event.get("event_type") not in REPLAYABLE_EVENT_TYPES:
                continue
            if session_id is not None:
                metadata = event.get("metadata") or {}
                data = event.get("data") or {}
                if not isinstance(metadata, dict):
                    metadata = {}
                if not isinstance(data, dict):
                    data = {}
                if session_id not in {
                    str(metadata.get("session_id", "")),
                    str(data.get("session_id", "")),
                }:
                    continue
            actions.append(event)
            if len(actions) >= max(1, int(limit)):
                break
        return actions

    def cleanup_old_events(self, max_age_hours: int = 168) -> int:
        if self._conn is None:
            raise RuntimeError("Event stream database is not initialized")

        cutoff_time = time.time() - (max(1, int(max_age_hours)) * 3600)
        with self._lock:
            cursor = self._conn.execute(
                "DELETE FROM events WHERE timestamp < ?",
                (cutoff_time,),
            )
            deleted = int(cursor.rowcount or 0)
            self._conn.commit()

        if deleted:
            self._cache = deque(
                [event for event in self._cache if event.get("timestamp", 0) >= cutoff_time],
                maxlen=EVENT_CACHE_SIZE,
            )
            logger.info("Cleaned up %s old events", deleted)
        return deleted

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None


_event_stream_instance: EventStream | None = None
_event_stream_lock = threading.Lock()


def get_event_stream() -> EventStream:
    """Return the singleton event stream used by tool observability hooks."""

    global _event_stream_instance
    if _event_stream_instance is None:
        with _event_stream_lock:
            if _event_stream_instance is None:
                _event_stream_instance = EventStream()
    return _event_stream_instance


__all__ = [
    "BusEvent",
    "EventBus",
    "EventLog",
    "EventStream",
    "EventType",
    "get_event_stream",
]


if __name__ == "__main__":
    stream = get_event_stream()
    stream.emit(
        EventType.TOOL_CALL,
        "test_tool",
        {"tool_name": "file_operations", "action": "read"},
        duration=0.5,
    )
    stream.emit(
        EventType.VISION_ANALYSIS,
        "vision_fallback",
        {"query": "Find login button"},
        duration=2.3,
    )
    events = stream.query_events(limit=10)
    print(f"Total events: {len(events)}")
    print("\nTimeline:")
    for event in stream.get_timeline(limit=5):
        print(f"  {event['time']} - {event['summary']}")
    stats = stream.get_statistics(hours=1)
    print("\nStatistics:")
    print(f"  Total: {stats['total_events']}")
    print(f"  Success rate: {stats['success_rate']:.2%}")
    stream.close()
