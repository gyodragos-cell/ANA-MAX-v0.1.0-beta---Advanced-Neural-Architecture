import threading
import time
import os
from pathlib import Path
import logging
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
        action = kwargs.get("action")
        if action == "start":
            if self._thread and self._thread.is_alive():
                return ToolResult(status=ToolStatus.SUCCESS, message="Watchdog already running.")
            self._stop_event = threading.Event()
            try:
                self._thread = _LogHandler(self.log_path, self._stop_event)
                self._thread.start()
                return ToolResult(status=ToolStatus.SUCCESS, message="Watchdog started.")
            except Exception as e:
                return ToolResult(status=ToolStatus.ERROR, error=str(e))
        elif action == "stop":
            if self._stop_event:
                self._stop_event.set()
                return ToolResult(status=ToolStatus.SUCCESS, message="Watchdog stopping.")
            else:
                return ToolResult(status=ToolStatus.ERROR, error="Watchdog not running.")
        else:
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
