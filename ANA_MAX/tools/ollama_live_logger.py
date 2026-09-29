import os
import threading
import time
import logging
from pathlib import Path
from typing import List, Optional
from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus
from tools.watchdog_bus import bus

logger = logging.getLogger(__name__)

_TAIL_BOOT_LINES = 20
_ANA_ROOT = Path(__file__).resolve().parents[1]


# A server log is considered stale (dead) if it has not been written to for
# this many seconds. Ollama launched via `ollama serve` logs to stdout, not to
# server.log, so the on-disk file can be days old while the server is live.
_STALE_LOG_SECONDS = 120


def _candidate_log_paths() -> List[Path]:
    """Candidate paths for the real Ollama SERVER log.

    Only actual Ollama server logs are tailed here. `ollama_reasoning.log` is
    intentionally excluded: the Ollama backend already publishes ANA<->Qwen
    inference to the bus via `_publish_llm_log`, so tailing that file too would
    duplicate every token on the dashboard. We include rotated `server-*.log`
    files so the freshest one can be selected.
    """
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    candidates: List[Path] = []
    if local_app_data:
        ollama_dir = Path(local_app_data) / "Ollama"
        try:
            candidates.extend(sorted(ollama_dir.glob("server*.log")))
        except Exception:
            candidates.append(ollama_dir / "server.log")
    candidates.append(_ANA_ROOT / "ollama.log")
    return candidates


def resolve_ollama_log_path() -> Optional[Path]:
    """Return the most recently modified existing Ollama server log."""
    existing = [p for p in _candidate_log_paths() if p.exists()]
    if not existing:
        return None
    return max(existing, key=lambda p: p.stat().st_mtime)


def _is_log_stale(log_path: Path) -> bool:
    """True if the log file has not been touched recently (likely a dead file)."""
    try:
        return (time.time() - log_path.stat().st_mtime) > _STALE_LOG_SECONDS
    except Exception:
        return False


def _read_tail_lines(log_path: Path, max_lines: int = _TAIL_BOOT_LINES) -> List[str]:
    if not log_path.exists():
        return []
    try:
        with log_path.open("r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        return [line.strip() for line in lines[-max_lines:] if line.strip()]
    except Exception as e:
        logger.debug("Ollama tail bootstrap error: %s", e)
        return []


class _LogTailer(threading.Thread):
    def __init__(self, log_path: Path, stop_event: threading.Event, bootstrap_lines: Optional[List[str]] = None):
        super().__init__(daemon=True)
        self.log_path = log_path
        self.stop_event = stop_event
        self._position = 0
        self._bootstrap_lines = bootstrap_lines or []

        if self.log_path.exists():
            with self.log_path.open("r", encoding="utf-8", errors="ignore") as f:
                f.seek(0, os.SEEK_END)
                self._position = f.tell()

    def _publish_line(self, line: str) -> None:
        if line.strip():
            # Add OS27 debug prefix for easier filtering
            if "tool" in line.lower() or "error" in line.lower() or "timeout" in line.lower():
                line = f"[OS27-DEBUG] {line.strip()}"
            # Also print to console for immediate visibility
            print(f"[OLLAMA-LOG] {line.strip()}")
            bus.publish(source="OllamaLive", event_type="LLM_LOG", data=line.strip())

    def run(self):
        for line in self._bootstrap_lines:
            self._publish_line(line)

        while not self.stop_event.is_set():
            if not self.log_path.exists():
                time.sleep(1)
                continue

            try:
                with self.log_path.open("r", encoding="utf-8", errors="ignore") as f:
                    f.seek(self._position)
                    new_lines = f.read()
                    if new_lines:
                        for line in new_lines.splitlines():
                            self._publish_line(line)
                        self._position = f.tell()
            except Exception as e:
                logger.debug("Ollama tail error: %s", e)
            time.sleep(0.5)


class OllamaLiveLoggerTool(Tool):
    """
    Tails the Ollama server log and streams it to the Watchdog Event Bus.
    Provides transparent visibility into local LLM operations.
    """

    def __init__(self):
        self._thread = None
        self._stop_event = None
        self.log_path: Optional[Path] = None

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="ollama_live_logger",
            description="Start/Stop live tailing of the Ollama server log.",
            parameters=[
                ToolParameter(
                    name="action",
                    description="start or stop the live logger",
                    type="string",
                    required=True,
                    choices=["start", "stop"],
                )
            ],
            category="system_intelligence",
        )

    def execute(self, action: str, **kwargs) -> ToolResult:
        if action == "start":
            if self._thread and self._thread.is_alive():
                return ToolResult(status=ToolStatus.SUCCESS, message="Ollama live logger is already running.")

            self.log_path = resolve_ollama_log_path()
            if not self.log_path:
                candidates = ", ".join(str(p) for p in _candidate_log_paths())
                bus.publish(
                    "OllamaLive",
                    "LLM_LOG",
                    f"Ollama logger degraded: no log file found (checked: {candidates})",
                )
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error=f"Ollama log not found. Checked: {candidates}",
                )

            bootstrap_lines = _read_tail_lines(self.log_path)
            if _is_log_stale(self.log_path):
                # server.log exists but is not being written to. This is normal
                # when Ollama runs via `ollama serve` (logs go to stdout). Live
                # ANA<->Qwen inference is still streamed here by the backend via
                # _publish_llm_log, so tell the dashboard the truth instead of
                # claiming an active file connection.
                bus.publish(
                    "OllamaLive",
                    "LLM_LOG",
                    "Ollama server log is idle (server likely started via 'ollama serve'). "
                    "Live inference will appear here when ANA reasons via Qwen.",
                )
            else:
                bus.publish(
                    "OllamaLive",
                    "LLM_LOG",
                    f"Ollama logger connected: {self.log_path}",
                )

            self._stop_event = threading.Event()
            self._thread = _LogTailer(self.log_path, self._stop_event, bootstrap_lines=bootstrap_lines)
            self._thread.start()
            return ToolResult(
                status=ToolStatus.SUCCESS,
                message=f"Ollama live logger started on {self.log_path}",
            )

        elif action == "stop":
            if self._stop_event:
                self._stop_event.set()
                return ToolResult(status=ToolStatus.SUCCESS, message="Ollama live logger stopped.")
            return ToolResult(status=ToolStatus.ERROR, error="Logger not running.")

        return ToolResult(status=ToolStatus.ERROR, error=f"Invalid action: {action}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["start", "stop"])
    args = parser.parse_args()

    bus.subscribe(lambda e: print(f"[OLLAMA] {e['data']}"))
    bus.start()

    tool = OllamaLiveLoggerTool()
    tool.execute(args.action)

    if args.action == "start":
        print("Listening for 10 seconds...")
        time.sleep(10)
        tool.execute("stop")
        bus.stop()
