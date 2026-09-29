import queue
import threading
import time
import logging
from typing import List, Dict, Any, Callable
from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus

# optional colour output
try:
    from colorama import init, Fore, Style
    init(autoreset=True)
    RED = Fore.RED
    GREEN = Fore.GREEN
    CYAN = Fore.CYAN
    RESET = Style.RESET_ALL
except Exception:
    RED = GREEN = CYAN = RESET = ''

logger = logging.getLogger(__name__)

class EventBus:
    """Singleton Event Bus for Event-Driven Architecture."""
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(EventBus, cls).__new__(cls)
                cls._instance._init()
            return cls._instance

    def _init(self):
        self._subscribers: List[Callable[[Dict[str, Any]], None]] = []
        self._queue = queue.Queue(maxsize=5000)
        self._stop_event = threading.Event()
        self._worker_thread = None

    def start(self):
        if self._worker_thread and self._worker_thread.is_alive():
            return
        self._stop_event.clear()
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker_thread.start()

    def stop(self):
        self._stop_event.set()
        if self._worker_thread:
            self._worker_thread.join(timeout=2.0)

    def publish(self, source: str, event_type: str, data: Any):
        try:
            self._queue.put_nowait({
                "source": source,
                "type": event_type,
                "data": data,
                "timestamp": time.strftime('%H:%M:%S')
            })
        except queue.Full:
            pass # Drop event if bus is overwhelmed

    def subscribe(self, callback: Callable[[Dict[str, Any]], None]):
        if callback not in self._subscribers:
            self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[Dict[str, Any]], None]):
        if callback in self._subscribers:
            self._subscribers.remove(callback)

    def _worker_loop(self):
        while not self._stop_event.is_set():
            try:
                event = self._queue.get(timeout=0.5)
                for sub in self._subscribers:
                    try:
                        sub(event)
                    except Exception as e:
                        logger.error(f"EventBus subscriber error: {e}")
            except queue.Empty:
                continue

# Expose a global instance
bus = EventBus()

def _console_logger_subscriber(event: Dict[str, Any]):
    """Default subscriber to print events to terminal with OS27 debug highlighting."""
    ts = event.get('timestamp')
    src = event.get('source')
    typ = event.get('type')
    data = event.get('data')
    
    # OS27 debug highlighting for critical events
    if '[OS27-DEBUG]' in str(data) or 'tool_failure' in str(typ) or 'blockage' in str(typ):
        print(f"{RED}[OS27-ALERT {ts}] {src} | {typ} | {data}{RESET}")
    elif 'tool_success' in str(typ):
        print(f"{GREEN}[OS27-OK {ts}] {src} | {typ} | {data}{RESET}")
    else:
        # Silenced console spam:
        # print(f"{CYAN}[EVENT-BUS {ts}] {src} | {typ} | {data}{RESET}")
        logger.debug(f"[EVENT-BUS {ts}] {src} | {typ} | {data}")

class WatchdogBusTool(Tool):
    """
    Tool to manage the Event-Driven Watchdog Bus.
    """
    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="watchdog_bus",
            description="Manage the central event-driven watchdog bus (start/stop/status).",
            parameters=[
                ToolParameter(
                    name="action",
                    description="start or stop the watchdog bus",
                    type="string",
                    required=True,
                    choices=["start", "stop", "status"]
                )
            ],
            category="system_intelligence"
        )

    def execute(self, action: str, **kwargs) -> ToolResult:
        if action == "start":
            bus.subscribe(_console_logger_subscriber)
            bus.start()
            return ToolResult(status=ToolStatus.SUCCESS, message="Watchdog Event Bus started.")
        elif action == "stop":
            bus.stop()
            return ToolResult(status=ToolStatus.SUCCESS, message="Watchdog Event Bus stopped.")
        elif action == "status":
            is_running = bus._worker_thread is not None and bus._worker_thread.is_alive()
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"running": is_running, "subscribers": len(bus._subscribers)},
                message=f"Bus running: {is_running}, Subscribers: {len(bus._subscribers)}"
            )
        else:
            return ToolResult(status=ToolStatus.ERROR, error=f"Invalid action: {action}")
