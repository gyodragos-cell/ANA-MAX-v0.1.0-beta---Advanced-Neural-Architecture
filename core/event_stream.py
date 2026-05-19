#!/usr/bin/env python3
"""
ANA MAX - Event Stream Architecture (Inspirat din UI-TARS)
===========================================================
Protocol-driven event stream for debugging and context engineering.

Features:
- Structured event logging
- Real-time event streaming
- Visual debugging support
- Event timeline
- Action replay
- Performance metrics

Author: ANA MAX Team (2026-05-19)
Inspired by: UI-TARS Desktop Event Stream
"""

import os
import json
import time
import uuid
import sqlite3
import logging
import threading
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from collections import deque
from enum import Enum

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Types of events in the stream."""
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


class EventStream:
    """
    Event stream for ANA MAX debugging and observability.
    
    Features:
    - Store events in SQLite
    - Real-time event streaming via callbacks
    - Event filtering and querying
    - Timeline visualization data
    - Performance tracking
    - Action replay support
    """
    
    def __init__(self, db_path: str = "data/events_stream.db"):
        self.db_path = Path(db_path)
        self._conn = None
        self._lock = threading.Lock()
        
        # Real-time subscribers
        self._subscribers: List[Callable] = []
        
        # Event cache (last 1000 events)
        self._cache = deque(maxlen=1000)
        
        # Initialize database
        self._init_db()
        
        logger.info(f"Event Stream initialized")
    
    def _init_db(self):
        """Initialize SQLite database for event storage."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        
        # Create events table
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS events (
                id TEXT PRIMARY KEY,
                timestamp REAL NOT NULL,
                event_type TEXT NOT NULL,
                source TEXT,
                data TEXT DEFAULT '{}',
                metadata TEXT DEFAULT '{}',
                screenshot_path TEXT,
                duration REAL,
                success BOOLEAN DEFAULT 1
            );
            
            CREATE INDEX IF NOT EXISTS idx_event_type ON events(event_type);
            CREATE INDEX IF NOT EXISTS idx_timestamp ON events(timestamp);
            CREATE INDEX IF NOT EXISTS idx_source ON events(source);
            CREATE INDEX IF NOT EXISTS idx_success ON events(success);
        """)
        
        self._conn.commit()
        logger.info("Event stream database initialized")
    
    def subscribe(self, callback: Callable):
        """
        Subscribe to real-time events.
        
        Args:
            callback: Function to call on each event (receives event dict)
        """
        self._subscribers.append(callback)
        logger.debug(f"Event subscriber added (total: {len(self._subscribers)})")
    
    def unsubscribe(self, callback: Callable):
        """Unsubscribe from events."""
        if callback in self._subscribers:
            self._subscribers.remove(callback)
    
    def emit(self, event_type: EventType, source: str, data: Dict,
             metadata: Dict = None, screenshot_path: str = None,
             duration: float = None, success: bool = True) -> str:
        """
        Emit an event to the stream.
        
        Args:
            event_type: Type of event
            source: Source component (tool name, module, etc.)
            data: Event payload
            metadata: Optional metadata
            screenshot_path: Optional screenshot path
            duration: Optional duration in seconds
            success: Whether the action succeeded
        
        Returns:
            Event ID
        """
        event_id = str(uuid.uuid4())[:12]
        timestamp = time.time()
        
        event = {
            "id": event_id,
            "timestamp": timestamp,
            "event_type": event_type.value,
            "source": source,
            "data": data,
            "metadata": metadata or {},
            "screenshot_path": screenshot_path,
            "duration": duration,
            "success": success
        }
        
        # Store in database
        with self._lock:
            self._conn.execute(
                "INSERT INTO events (id, timestamp, event_type, source, data, metadata, screenshot_path, duration, success) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    event_id,
                    timestamp,
                    event_type.value,
                    source,
                    json.dumps(data),
                    json.dumps(metadata or {}),
                    screenshot_path,
                    duration,
                    success
                )
            )
            self._conn.commit()
        
        # Add to cache
        self._cache.append(event)
        
        # Notify subscribers
        for callback in self._subscribers:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Event subscriber error: {e}")
        
        return event_id
    
    def query_events(self, event_type: EventType = None, source: str = None,
                    start_time: float = None, end_time: float = None,
                    limit: int = 100, success: bool = None) -> List[Dict]:
        """
        Query events with filters.
        
        Args:
            event_type: Filter by event type
            source: Filter by source
            start_time: Start timestamp
            end_time: End timestamp
            limit: Max results
            success: Filter by success status
        
        Returns:
            List of events
        """
        query = "SELECT * FROM events WHERE 1=1"
        params = []
        
        if event_type:
            query += " AND event_type = ?"
            params.append(event_type.value)
        
        if source:
            query += " AND source = ?"
            params.append(source)
        
        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time)
        
        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time)
        
        if success is not None:
            query += " AND success = ?"
            params.append(success)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        with self._lock:
            cursor = self._conn.execute(query, params)
            events = []
            for row in cursor.fetchall():
                event = dict(row)
                # Parse JSON fields
                event['data'] = json.loads(event['data'])
                event['metadata'] = json.loads(event['metadata'])
                events.append(event)
        
        return events
    
    def get_timeline(self, start_time: float = None, end_time: float = None,
                    limit: int = 50) -> List[Dict]:
        """
        Get event timeline for visualization.
        
        Returns events in chronological order with formatted timestamps.
        """
        if not start_time:
            start_time = time.time() - 3600  # Last hour
        
        if not end_time:
            end_time = time.time()
        
        events = self.query_events(
            start_time=start_time,
            end_time=end_time,
            limit=limit
        )
        
        # Reverse for chronological order
        events.reverse()
        
        # Format for timeline
        timeline = []
        for event in events:
            timeline.append({
                "id": event['id'],
                "time": datetime.fromtimestamp(event['timestamp']).strftime("%H:%M:%S"),
                "type": event['event_type'],
                "source": event['source'],
                "success": event['success'],
                "duration": event.get('duration'),
                "summary": self._summarize_event(event)
            })
        
        return timeline
    
    def _summarize_event(self, event: Dict) -> str:
        """Create a human-readable summary of an event."""
        event_type = event['event_type']
        data = event['data']
        
        if event_type == EventType.TOOL_CALL.value:
            return f"Called tool: {data.get('tool_name', 'unknown')}"
        elif event_type == EventType.VISION_ANALYSIS.value:
            return f"Vision analysis: {data.get('query', 'unknown')}"
        elif event_type == EventType.REMOTE_ACTION.value:
            return f"Remote action: {data.get('action', 'unknown')}"
        elif event_type == EventType.ERROR.value:
            return f"Error: {data.get('message', 'unknown error')}"
        elif event_type == EventType.USER_INPUT.value:
            return f"User input: {str(data.get('text', ''))[:50]}"
        else:
            return str(data)[:100]
    
    def get_statistics(self, hours: int = 24) -> Dict:
        """Get event statistics for the last N hours."""
        start_time = time.time() - (hours * 3600)
        
        events = self.query_events(start_time=start_time, limit=10000)
        
        stats = {
            "total_events": len(events),
            "by_type": {},
            "by_source": {},
            "success_rate": 0,
            "avg_duration": 0,
            "time_range": hours
        }
        
        successful = 0
        total_duration = 0
        
        for event in events:
            # Count by type
            event_type = event['event_type']
            stats['by_type'][event_type] = stats['by_type'].get(event_type, 0) + 1
            
            # Count by source
            source = event['source']
            stats['by_source'][source] = stats['by_source'].get(source, 0) + 1
            
            # Success rate
            if event['success']:
                successful += 1
            
            # Average duration
            if event.get('duration'):
                total_duration += event['duration']
        
        if events:
            stats['success_rate'] = successful / len(events)
            stats['avg_duration'] = total_duration / len(events) if total_duration > 0 else 0
        
        return stats
    
    def replay_actions(self, session_id: str = None, limit: int = 50) -> List[Dict]:
        """
        Get replayable actions from event stream.
        
        Returns actions that can be replayed (tool calls, remote actions, etc.)
        """
        replayable_types = [
            EventType.TOOL_CALL.value,
            EventType.REMOTE_ACTION.value,
            EventType.VISION_ANALYSIS.value
        ]
        
        query = """
            SELECT * FROM events 
            WHERE event_type IN (?, ?, ?)
            ORDER BY timestamp DESC
            LIMIT ?
        """
        
        with self._lock:
            cursor = self._conn.execute(query, (
                replayable_types[0],
                replayable_types[1],
                replayable_types[2],
                limit
            ))
            
            actions = []
            for row in cursor.fetchall():
                event = dict(row)
                event['data'] = json.loads(event['data'])
                event['metadata'] = json.loads(event['metadata'])
                actions.append(event)
        
        return actions
    
    def cleanup_old_events(self, max_age_hours: int = 168):  # 7 days
        """Remove events older than max_age_hours."""
        cutoff_time = time.time() - (max_age_hours * 3600)
        
        with self._lock:
            cursor = self._conn.execute(
                "DELETE FROM events WHERE timestamp < ?",
                (cutoff_time,)
            )
            deleted = cursor.rowcount
            self._conn.commit()
        
        if deleted > 0:
            logger.info(f"Cleaned up {deleted} old events")
        
        return deleted
    
    def close(self):
        """Close database connection."""
        if self._conn:
            self._conn.close()
            logger.info("Event stream closed")


# Singleton instance
_event_stream_instance = None
_event_stream_lock = threading.Lock()


def get_event_stream() -> EventStream:
    """Get or create EventStream singleton."""
    global _event_stream_instance
    
    if _event_stream_instance is None:
        with _event_stream_lock:
            if _event_stream_instance is None:
                _event_stream_instance = EventStream()
    
    return _event_stream_instance


if __name__ == "__main__":
    # Test event stream
    stream = get_event_stream()
    
    # Emit some test events
    stream.emit(
        EventType.TOOL_CALL,
        "test_tool",
        {"tool_name": "file_operations", "action": "read"},
        duration=0.5
    )
    
    stream.emit(
        EventType.VISION_ANALYSIS,
        "vision_fallback",
        {"query": "Find login button"},
        duration=2.3
    )
    
    # Query events
    events = stream.query_events(limit=10)
    print(f"Total events: {len(events)}")
    
    # Get timeline
    timeline = stream.get_timeline(limit=5)
    print(f"\nTimeline:")
    for event in timeline:
        print(f"  {event['time']} - {event['summary']}")
    
    # Statistics
    stats = stream.get_statistics(hours=1)
    print(f"\nStatistics:")
    print(f"  Total: {stats['total_events']}")
    print(f"  Success rate: {stats['success_rate']:.2%}")
    
    stream.close()
