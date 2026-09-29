"""
ANA MAX - Black Box Recorder
Centralized logging system for complete observability of agent, OS, tools, and errors.

Collects and publishes events to watchdog_bus for dashboard integration.
Detects errors and notifies agent for self-awareness.
"""
from __future__ import annotations

import logging
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from tools.watchdog_bus import bus
from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus

logger = logging.getLogger(__name__)

ANA_ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ANA_ROOT / "logs"
BLACK_BOX_LOG = LOG_DIR / "black_box.log"

# Ensure log directory exists
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Configure black box logger
_black_box_logger = logging.getLogger("black_box")
_black_box_logger.setLevel(logging.INFO)
if not any(isinstance(h, logging.FileHandler) and getattr(h, "baseFilename", None) == str(BLACK_BOX_LOG) for h in _black_box_logger.handlers):
    _fh = logging.FileHandler(BLACK_BOX_LOG, encoding="utf-8")
    _fh.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    _black_box_logger.addHandler(_fh)


class BlackBoxRecorder:
    """
    Centralized Black Box Recorder for complete system observability.
    
    Categories:
    - TOOL: Tool execution (start, end, error)
    - AGENT: AI agent reasoning, decisions, errors
    - OS: System events, processes, errors
    - VOICE: Voice pipeline events (STT, API, TTS)
    - DASHBOARD: Dashboard metrics and events
    - FRIDA: Frida telemetry events
    - ERROR: All errors with context
    """
    
    def __init__(self):
        self._lock = threading.Lock()
        self._error_count = 0
        self._last_errors: List[Dict[str, Any]] = []
        self._max_errors = 50
        
    def log(self, category: str, event: str, data: Optional[Dict[str, Any]] = None, level: str = "INFO"):
        """
        Log an event to black box and publish to watchdog_bus.
        
        Args:
            category: TOOL, AGENT, OS, VOICE, DASHBOARD, FRIDA, ERROR
            event: Description of the event
            data: Additional event data
            level: INFO, WARNING, ERROR, CRITICAL
        """
        timestamp = datetime.now().isoformat()
        event_data = {
            "timestamp": timestamp,
            "category": category,
            "event": event,
            "level": level,
            "data": data or {}
        }
        
        # Log to black box file
        log_level = getattr(logging, level.upper(), logging.INFO)
        _black_box_logger.log(log_level, f"[{category}] {event} - {data}")
        
        # Publish to watchdog_bus
        try:
            bus.publish(event_data)
        except Exception as e:
            logger.error("Failed to publish to watchdog_bus: %s", e)
        
        # Track errors
        if level in ("ERROR", "CRITICAL"):
            self._track_error(event_data)
    
    def _track_error(self, error_data: Dict[str, Any]):
        """Track errors for agent self-awareness."""
        with self._lock:
            self._error_count += 1
            self._last_errors.append(error_data)
            if len(self._last_errors) > self._max_errors:
                self._last_errors.pop(0)
            
            # Publish error alert to dashboard
            try:
                bus.publish({
                    "type": "ERROR_ALERT",
                    "timestamp": error_data["timestamp"],
                    "category": error_data["category"],
                    "event": error_data["event"],
                    "total_errors": self._error_count
                })
            except Exception as e:
                logger.error("Failed to publish error alert: %s", e)
    
    def get_recent_errors(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent errors for agent self-awareness."""
        with self._lock:
            return self._last_errors[-limit:]
    
    def get_error_count(self) -> int:
        """Get total error count."""
        with self._lock:
            return self._error_count
    
    def get_status(self) -> Dict[str, Any]:
        """Get black box recorder status."""
        return {
            "error_count": self.get_error_count(),
            "recent_errors": self.get_recent_errors(5),
            "log_file": str(BLACK_BOX_LOG),
            "log_size": BLACK_BOX_LOG.stat().st_size if BLACK_BOX_LOG.exists() else 0
        }


# Global instance
recorder = BlackBoxRecorder()


def log_tool_start(tool_name: str, args: Dict[str, Any]):
    """Log tool execution start."""
    recorder.log("TOOL", f"Tool started: {tool_name}", {"tool": tool_name, "args": args})


def log_tool_end(tool_name: str, status: str, duration_ms: float, result: Any = None):
    """Log tool execution end."""
    recorder.log("TOOL", f"Tool ended: {tool_name}", {
        "tool": tool_name,
        "status": status,
        "duration_ms": duration_ms,
        "result": str(result)[:200] if result else None
    })


def log_tool_error(tool_name: str, error: str, args: Dict[str, Any] = None):
    """Log tool execution error."""
    recorder.log("ERROR", f"Tool error: {tool_name}", {
        "tool": tool_name,
        "error": error,
        "args": args
    }, level="ERROR")


def log_agent_thought(thought: str):
    """Log agent reasoning."""
    recorder.log("AGENT", "Agent thought", {"thought": thought[:500]})


def log_agent_action(action: str, args: Dict[str, Any]):
    """Log agent action."""
    recorder.log("AGENT", f"Agent action: {action}", {"action": action, "args": args})


def log_agent_error(error: str, context: Dict[str, Any] = None):
    """Log agent error."""
    recorder.log("ERROR", "Agent error", {"error": error, "context": context}, level="ERROR")


def log_os_event(event: str, data: Dict[str, Any] = None):
    """Log OS event."""
    recorder.log("OS", event, data)


def log_os_error(error: str, context: Dict[str, Any] = None):
    """Log OS error."""
    recorder.log("ERROR", f"OS error: {error}", {"error": error, "context": context}, level="ERROR")


def log_voice_event(event: str, data: Dict[str, Any] = None):
    """Log voice pipeline event."""
    recorder.log("VOICE", event, data)


def log_voice_error(error: str, context: Dict[str, Any] = None):
    """Log voice pipeline error."""
    recorder.log("ERROR", f"Voice error: {error}", {"error": error, "context": context}, level="ERROR")


def log_frida_event(event: str, data: Dict[str, Any] = None):
    """Log Frida telemetry event."""
    recorder.log("FRIDA", event, data)


def log_dashboard_event(event: str, data: Dict[str, Any] = None):
    """Log dashboard event."""
    recorder.log("DASHBOARD", event, data)


class BlackBoxRecorderTool(Tool):
    """Tool for querying black box recorder status and recent errors."""
    
    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="black_box_recorder",
            description="Query black box recorder for system observability, error tracking, and agent self-awareness.",
            parameters=[
                ToolParameter(name="operation", type="str", required=True, 
                             description="Operation: status, errors, error_count"),
                ToolParameter(name="limit", type="int", required=False, 
                             description="Limit for errors query (default: 10)")
            ]
        )
    
    def execute(self, **kwargs) -> ToolResult:
        operation = kwargs.get("operation")
        limit = kwargs.get("limit", 10)
        
        try:
            if operation == "status":
                status = recorder.get_status()
                return ToolResult(status=ToolStatus.SUCCESS, data=status)
            
            elif operation == "errors":
                errors = recorder.get_recent_errors(limit)
                return ToolResult(status=ToolStatus.SUCCESS, data={"errors": errors, "count": len(errors)})
            
            elif operation == "error_count":
                count = recorder.get_error_count()
                return ToolResult(status=ToolStatus.SUCCESS, data={"error_count": count})
            
            else:
                return ToolResult(status=ToolStatus.ERROR, error=f"Unknown operation: {operation}")
        
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
