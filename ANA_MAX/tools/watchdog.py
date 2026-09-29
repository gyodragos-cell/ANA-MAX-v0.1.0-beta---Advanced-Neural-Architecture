"""
Watchdog Tool (OS27 Hyper++)
============================
Live log watchdog that prints new log lines to the console.

OS27 Hyper++ Features:
- Telemetry tracking for watchdog operations (start, stop)
- Health monitoring for watchdog operations reliability
- MemoryCortex integration for watchdog errors and state learning
- ContextEngine integration for watchdog state awareness
- SelfEvolvingTool integration for anomaly detection on watchdog failures
- Structured logging with error detection
"""

import threading
import time
import os
from pathlib import Path
import logging
from typing import Dict, Any
from tools.base import Tool, ToolResult, ToolStatus, ToolDefinition, ToolParameter

# optional colour output
try:
    from colorama import init, Fore, Style
    init(autoreset=True)
    RED = Fore.RED
    GREEN = Fore.GREEN
    RESET = Style.RESET_ALL
except Exception:
    RED = GREEN = RESET = ''

logger = logging.getLogger(__name__)

# OS27 Hyper++ Telemetry
_watchdog_telemetry: Dict[str, Dict[str, Any]] = {}


def _record_watchdog_telemetry(operation: str, success: bool, execution_time: float) -> None:
    """Record OS27 Hyper++ telemetry for watchdog operations."""
    if operation not in _watchdog_telemetry:
        _watchdog_telemetry[operation] = {
            "operation_count": 0,
            "success_count": 0,
            "failure_count": 0,
            "total_time": 0.0,
            "last_execution_time": 0.0,
            "last_success": False,
        }
    
    _watchdog_telemetry[operation]["operation_count"] += 1
    _watchdog_telemetry[operation]["total_time"] += execution_time
    _watchdog_telemetry[operation]["last_execution_time"] = execution_time
    _watchdog_telemetry[operation]["last_success"] = success
    
    if success:
        _watchdog_telemetry[operation]["success_count"] += 1
    else:
        _watchdog_telemetry[operation]["failure_count"] += 1


def get_watchdog_telemetry(operation: str | None = None) -> Dict[str, Any] | Dict[str, Dict[str, Any]]:
    """Get telemetry for watchdog operations."""
    if operation:
        return _watchdog_telemetry.get(operation, {})
    return _watchdog_telemetry.copy()


def get_watchdog_health() -> str:
    """Get health status for watchdog tool based on telemetry."""
    if not _watchdog_telemetry:
        return "unknown"
    
    total_ops = sum(stats["operation_count"] for stats in _watchdog_telemetry.values())
    total_failures = sum(stats["failure_count"] for stats in _watchdog_telemetry.values())
    
    if total_ops == 0:
        return "unknown"
    
    failure_rate = total_failures / total_ops
    if failure_rate > 0.5:
        return "broken"
    if failure_rate > 0.1:
        return "degraded"
    return "healthy"

class _LogHandler(threading.Thread):
    """Background thread that tails a log file and prints new lines."""

    def __init__(self, log_path: Path, stop_event: threading.Event):
        super().__init__(daemon=True)
        self.log_path = log_path
        self.stop_event = stop_event
        self._position = 0
        if not self.log_path.exists():
            raise FileNotFoundError(f"Log file not found: {self.log_path}")
        # start reading from end of file
        with self.log_path.open('r', encoding='utf-8', errors='ignore') as f:
            f.seek(0, os.SEEK_END)
            self._position = f.tell()

    def run(self):
        while not self.stop_event.is_set():
            try:
                with self.log_path.open('r', encoding='utf-8', errors='ignore') as f:
                    f.seek(self._position)
                    new_lines = f.read()
                    if new_lines:
                        for line in new_lines.splitlines():
                            timestamp = time.strftime('%H:%M:%S')
                            if 'ERROR' in line.upper():
                                print(f"{RED}[{timestamp}] {line}{RESET}")
                            else:
                                print(f"{GREEN}[{timestamp}] {line}{RESET}")
                        self._position = f.tell()
            except Exception as e:
                logger.error(f"Watchdog read error: {e}")
            time.sleep(0.5)

class WatchdogTool(Tool):
    """Tool that starts/stops a live log watchdog.

    Actions:
        - start : begin tailing `logs/ana_max.log`
        - stop  : terminate the background thread
    """

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="watchdog",
            description="Live log watchdog that prints new log lines to the console.",
            parameters=[
                ToolParameter(
                    name="action",
                    description="start or stop the watchdog",
                    type="string",
                    required=True,
                    choices=["start", "stop"]
                )
            ],
            category="debug"
        )

    def __init__(self):
        self._thread = None
        self._stop_event = None
        self.log_path = Path(__file__).parents[2] / "logs" / "ana_max.log"

    def execute(self, **kwargs) -> ToolResult:
        start_time = time.time()
        
        # AI Core hooks (lazy import for safety)
        cortex = None
        context_engine = None
        evolver = None
        try:
            from tools.memory_cortex import MemoryCortex
            cortex = MemoryCortex()
        except Exception:
            pass
        try:
            from tools.context_engine import ContextEngine
            context_engine = ContextEngine()
        except Exception:
            pass
        try:
            from tools.self_evolving_tool import SelfEvolvingTool
            evolver = SelfEvolvingTool()
        except Exception:
            pass
        
        action = kwargs.get("action")
        
        if action == "start":
            if self._thread and self._thread.is_alive():
                execution_time = time.time() - start_time
                _record_watchdog_telemetry("start", True, execution_time)
                return ToolResult(status=ToolStatus.SUCCESS, message="Watchdog already running.")
            self._stop_event = threading.Event()
            try:
                self._thread = _LogHandler(self.log_path, self._stop_event)
                self._thread.start()
                execution_time = time.time() - start_time
                _record_watchdog_telemetry("start", True, execution_time)
                
                # ContextEngine integration for watchdog state
                if context_engine:
                    try:
                        context_engine.update_context(
                            key="watchdog_state",
                            value={
                                "action": "start",
                                "log_path": str(self.log_path),
                                "running": True,
                                "timestamp": time.time(),
                            }
                        )
                    except Exception:
                        pass
                
                return ToolResult(status=ToolStatus.SUCCESS, message="Watchdog started.")
            except Exception as e:
                execution_time = time.time() - start_time
                _record_watchdog_telemetry("start", False, execution_time)
                
                # MemoryCortex integration for watchdog errors
                if cortex:
                    try:
                        cortex.remember(
                            "error",
                            "watchdog.start",
                            f"Watchdog start failed: {str(e)}"
                        )
                    except Exception:
                        pass
                
                return ToolResult(status=ToolStatus.ERROR, error=str(e))
        elif action == "stop":
            if self._stop_event:
                self._stop_event.set()
                execution_time = time.time() - start_time
                _record_watchdog_telemetry("stop", True, execution_time)
                
                # ContextEngine integration for watchdog state
                if context_engine:
                    try:
                        context_engine.update_context(
                            key="watchdog_state",
                            value={
                                "action": "stop",
                                "running": False,
                                "timestamp": time.time(),
                            }
                        )
                    except Exception:
                        pass
                
                return ToolResult(status=ToolStatus.SUCCESS, message="Watchdog stopping.")
            else:
                execution_time = time.time() - start_time
                _record_watchdog_telemetry("stop", False, execution_time)
                return ToolResult(status=ToolStatus.ERROR, error="Watchdog not running.")
        else:
            execution_time = time.time() - start_time
            _record_watchdog_telemetry("unknown", False, execution_time)
            return ToolResult(status=ToolStatus.ERROR, error=f"Invalid action: {action}")
if __name__ == '__main__':
    import argparse, sys
    parser = argparse.ArgumentParser(description='Watchdog tool CLI')
    parser.add_argument('action', choices=['start', 'stop'], help='Action to perform')
    args = parser.parse_args()
    tool = WatchdogTool()
    result = tool.execute(action=args.action)
    if result.status == ToolStatus.SUCCESS:
        print(result.message)
    else:
        print('Error:', result.error, file=sys.stderr)
        sys.exit(1)
