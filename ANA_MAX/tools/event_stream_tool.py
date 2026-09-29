#!/usr/bin/env python3
"""
ANA MAX - Event Stream Tool
=============================
Tool wrapper for Event Stream Architecture.

Author: ANA MAX Team (2026-05-19)
"""

import sys
import json
import time
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus
from core.event_stream import get_event_stream, EventType


def _as_int(value, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


class EventStreamTool(Tool):
    """Event Stream Tool for debugging and observability."""
    
    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="event_stream",
            description=(
                "Query and analyze event stream for debugging. "
                "View timeline, statistics, and replay actions. "
                "Actions: query, timeline, stats, replay, cleanup, emit"
            ),
            parameters=[
                ToolParameter(
                    name="action",
                    description="Action to perform",
                    type="string",
                    required=True,
                    choices=["query", "timeline", "stats", "replay", "cleanup", "emit"]
                ),
                ToolParameter(
                    name="event_type",
                    description="Filter by event type",
                    type="string",
                    required=False,
                    choices=["tool_call", "vision_analysis", "remote_action", "error", "user_input", "screenshot", "swarm_task", "memory_operation"]
                ),
                ToolParameter(
                    name="source",
                    description="Filter by source",
                    type="string",
                    required=False
                ),
                ToolParameter(
                    name="hours",
                    description="Time range in hours",
                    type="integer",
                    required=False,
                    default=24
                ),
                ToolParameter(
                    name="limit",
                    description="Max results",
                    type="integer",
                    required=False,
                    default=50
                ),
                ToolParameter(
                    name="event_data",
                    description="Event data as JSON (for emit action)",
                    type="string",
                    required=False
                )
            ],
            category="debugging"
        )
    
    def execute(self, action: str, **kwargs) -> ToolResult:
        try:
            stream = get_event_stream()
            
            if action == "query":
                return self._query(stream, **kwargs)
            elif action == "timeline":
                return self._timeline(stream, **kwargs)
            elif action == "stats":
                return self._stats(stream, **kwargs)
            elif action == "replay":
                return self._replay(stream, **kwargs)
            elif action == "cleanup":
                return self._cleanup(stream, **kwargs)
            elif action == "emit":
                return self._emit(stream, **kwargs)
            else:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error=f"Unknown action: {action}"
                )
        
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Event stream error: {e}"
            )
    
    def _query(self, stream, event_type: str = None, source: str = None,
               hours: int = 24, limit: int = 50, **kwargs) -> ToolResult:
        """Query events."""
        hours = _as_int(hours, 24)
        limit = _as_int(limit, 50)
        end_time = time.time()
        start_time = end_time - (hours * 3600)
        
        event_type_enum = None
        if event_type:
            try:
                event_type_enum = EventType(event_type)
            except ValueError:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error=f"Invalid event type: {event_type}"
                )
        
        events = stream.query_events(
            event_type=event_type_enum,
            source=source,
            start_time=start_time,
            end_time=end_time,
            limit=limit
        )
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={"events": events, "count": len(events)},
            message=f"Found {len(events)} events"
        )
    
    def _timeline(self, stream, hours: int = 1, limit: int = 50, **kwargs) -> ToolResult:
        """Get event timeline."""
        hours = _as_int(hours, 1)
        limit = _as_int(limit, 50)
        end_time = time.time()
        start_time = end_time - (hours * 3600)
        
        timeline = stream.get_timeline(
            start_time=start_time,
            end_time=end_time,
            limit=limit
        )
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={"timeline": timeline, "count": len(timeline)},
            message=f"Timeline with {len(timeline)} events"
        )
    
    def _stats(self, stream, hours: int = 24, **kwargs) -> ToolResult:
        """Get event statistics."""
        hours = _as_int(hours, 24)
        stats = stream.get_statistics(hours=hours)
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data=stats,
            message=f"Stats for last {hours} hours"
        )
    
    def _replay(self, stream, limit: int = 50, **kwargs) -> ToolResult:
        """Get replayable actions."""
        limit = _as_int(limit, 50)
        actions = stream.replay_actions(limit=limit)
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={"actions": actions, "count": len(actions)},
            message=f"{len(actions)} replayable actions"
        )
    
    def _cleanup(self, stream, hours: int = 168, **kwargs) -> ToolResult:
        """Clean up old events."""
        hours = _as_int(hours, 168)
        deleted = stream.cleanup_old_events(max_age_hours=hours)
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={"deleted": deleted, "max_age_hours": hours},
            message=f"Deleted {deleted} old events"
        )
    
    def _emit(self, stream, event_type: str = None, event_data: str = None, **kwargs) -> ToolResult:
        """Emit a test event."""
        if not event_type or not event_data:
            return ToolResult(
                status=ToolStatus.ERROR,
                error="event_type and event_data are required"
            )
        
        try:
            event_type_enum = EventType(event_type)
        except ValueError:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Invalid event type: {event_type}"
            )
        
        try:
            data = json.loads(event_data)
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                error="event_data must be valid JSON"
            )
        
        event_id = stream.emit(
            event_type=event_type_enum,
            source="event_stream_tool",
            data=data
        )
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={"event_id": event_id},
            message=f"Emitted event: {event_id}"
        )


if __name__ == "__main__":
    tool = EventStreamTool()
    
    # Get stats
    result = tool.execute("stats", hours=1)
    print(f"Stats: {result.message}")
    if result.data:
        print(f"Total events: {result.data.get('total_events', 0)}")
    
    # Get timeline
    result = tool.execute("timeline", hours=1, limit=5)
    print(f"\nTimeline: {result.message}")
