"""os29.telemetry -- Unified three-tier logging for OS29 Lab

LIVE   : stderr + live_session.log (always active, color-coded, ms precision)
HISTORY: SQLite via store.record_event(TraceEvent) -- caller responsibility
TRACE  : same TraceEvent with shared trace_id for correlated investigations

Rotation strategy (Windows-safe)
---------------------------------
Standard RotatingFileHandler and TimedRotatingFileHandler both call
os.rename(active_log -> backup) which fails with PermissionError [WinError 32]
when any other process holds the file open — including LIVE_CONSOLE.bat's
``Get-Content -Wait`` (or any reader opened without FILE_SHARE_DELETE).

_AppendRotatingHandler never renames the active file.  Instead it rotates by:
  1. Seeking to 0, reading all content.
  2. Writing that content to a dated archive file.
  3. Seeking to 0 and truncating the active file to 0 bytes.

The active file path (live_session.log) never changes.  The PowerShell tail
process keeps its handle and continues receiving new data after the truncation;
Windows file position is advanced past the truncation point but a ``-Wait``
reader detects the shrink and resets to 0 automatically.

Closing LIVE_CONSOLE.bat does NOT stop OS29.  It is a tail viewer only.

Restart behaviour
-----------------
log_startup() archives any existing session log before writing the first
startup banner, so history is never lost across restarts.
"""

from __future__ import annotations

import logging
import logging.handlers
import os
import re
import shutil
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# ANSI colours — stripped automatically when stderr is not a TTY
# ---------------------------------------------------------------------------
_TTY = hasattr(sys.stderr, "isatty") and sys.stderr.isatty()

_C: dict[str, str] = {
    "reset":   "\033[0m"  if _TTY else "",
    "grey":    "\033[90m" if _TTY else "",
    "green":   "\033[92m" if _TTY else "",
    "yellow":  "\033[93m" if _TTY else "",
    "red":     "\033[91m" if _TTY else "",
    "cyan":    "\033[96m" if _TTY else "",
    "bold":    "\033[1m"  if _TTY else "",
}

_OUTCOME_COLOR: dict[str, str] = {
    "success":  _C["green"],
    "failure":  _C["red"],
    "error":    _C["red"],
    "blocked":  _C["yellow"],
    "unknown":  _C["grey"],
    "observed": _C["cyan"],
}

# Patterns used to sanitise exception messages before they reach the log file.
_SECRET_FRAGMENT = re.compile(
    r"(?i)(password|passwd|token|secret|apikey|api[_-]key|credential|bearer|authorization)",
)


# ---------------------------------------------------------------------------
# Paths and size limits
# ---------------------------------------------------------------------------
_ROOT    = Path(__file__).resolve().parents[1]
_LOG_DIR = Path(os.environ.get("OS29_LOG_DIR", str(_ROOT / "logs")))
_LOG_DIR.mkdir(parents=True, exist_ok=True)

SESSION_LOG   = _LOG_DIR / "live_session.log"
ARCHIVE_DIR   = _LOG_DIR / "archive"

# Maximum active-file size before a copy-truncate rotation is triggered.
_MAX_BYTES    = int(os.environ.get("OS29_LOG_MAX_BYTES",    str(5 * 1024 * 1024)))
# Number of dated archive files to keep.
_BACKUP_COUNT = int(os.environ.get("OS29_LOG_BACKUP_COUNT", "7"))


# ---------------------------------------------------------------------------
# _AppendRotatingHandler — Windows-safe copy-truncate log rotation
# ---------------------------------------------------------------------------

class _AppendRotatingHandler(logging.StreamHandler):
    """Rotating file logger that never renames the active log file.

    The active log (SESSION_LOG) is always the same path.  When it exceeds
    ``max_bytes``, the handler:

      1. Acquires the rotation lock.
      2. Reads the current file content.
      3. Writes it to ``archive/<stem>.<YYYYMMDD_HHMMSS>.log``.
      4. Truncates the active file to 0 bytes (seek+truncate, not rename).
      5. Prunes old archive files beyond ``backup_count``.

    ``Get-Content -Wait`` keeps its open handle across the truncation.
    PowerShell resets its read position to 0 when it detects a file shrink,
    so new log entries are still shown in the live console.
    """

    def __init__(
        self,
        path: Path,
        max_bytes: int = 5 * 1024 * 1024,
        backup_count: int = 7,
        encoding: str = "utf-8",
    ) -> None:
        self._path         = path
        self._max_bytes    = max_bytes
        self._backup_count = backup_count
        self._encoding     = encoding
        self._lock         = threading.Lock()
        self._archive_dir  = path.parent / "archive"
        self._archive_dir.mkdir(parents=True, exist_ok=True)
        # Open in append mode.  'a' on Windows creates the file if missing and
        # does NOT hold an exclusive lock — other processes can read freely.
        self._stream = self._open()
        super().__init__(stream=self._stream)

    # -- stream management ---------------------------------------------------

    def _open(self):                                    # noqa: ANN001
        return open(self._path, "a", encoding=self._encoding, errors="replace")

    def _current_size(self) -> int:
        try:
            return self._path.stat().st_size
        except OSError:
            return 0

    # -- rotation ------------------------------------------------------------

    def _archive_name(self) -> Path:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return self._archive_dir / f"{self._path.stem}.{stamp}.log"

    def _prune_archives(self) -> None:
        """Remove oldest archives beyond backup_count."""
        archives = sorted(self._archive_dir.glob(f"{self._path.stem}.*.log"))
        for old in archives[: max(0, len(archives) - self._backup_count)]:
            try:
                old.unlink(missing_ok=True)
            except OSError:
                pass

    def _rotate(self) -> None:
        """Copy active log → archive, then truncate active log to 0 bytes.

        This is called only from emit() while ``self._lock`` is held.
        The active file handle remains open throughout — no rename, no close.
        """
        try:
            # 1. Flush pending writes.
            self._stream.flush()

            # 2. Read current content.
            try:
                content = self._path.read_bytes()
            except OSError:
                content = b""

            # 3. Write to archive (best-effort; do not lose current events
            #    if the archive write fails).
            if content:
                archive = self._archive_name()
                try:
                    archive.write_bytes(content)
                    self._prune_archives()
                except OSError:
                    pass  # archive disk full / permission — keep going

            # 4. Truncate the active file without closing it.
            #    On Windows, truncating an open file works because we hold
            #    the write handle and there is no rename involved.
            try:
                self._stream.seek(0)
                self._stream.truncate(0)
                self._stream.flush()
            except OSError:
                # If truncation fails, reopen (fallback).
                try:
                    self._stream.close()
                except Exception:
                    pass
                self._stream = self._open()
                self.stream  = self._stream

        except Exception:
            # Rotation errors must never propagate to callers.
            pass

    # -- logging.StreamHandler overrides ------------------------------------

    def emit(self, record: logging.LogRecord) -> None:  # type: ignore[override]
        with self._lock:
            if self._current_size() >= self._max_bytes:
                self._rotate()
            try:
                msg = self.format(record)
                self._stream.write(msg + self.terminator)
                self._stream.flush()
            except Exception:
                self.handleError(record)

    def close(self) -> None:
        with self._lock:
            try:
                self._stream.flush()
                self._stream.close()
            except Exception:
                pass
        super().close()

    # -- explicit session archive (used by log_shutdown / log_startup) -------

    def archive_session(self, reason: str = "shutdown") -> Path | None:
        """Flush, archive current content, truncate.  Returns archive path."""
        with self._lock:
            try:
                self._stream.flush()
                content = self._path.read_bytes()
                if len(content) == 0:
                    return None
                archive = self._archive_name()
                # Append a reason marker.
                try:
                    marker = f"\n# --- archived: reason={reason} at {datetime.now().isoformat()} ---\n"
                    archive.write_bytes(content + marker.encode(self._encoding, "replace"))
                    self._prune_archives()
                except OSError:
                    return None
                # Truncate active log.
                self._stream.seek(0)
                self._stream.truncate(0)
                self._stream.flush()
                return archive
            except Exception:
                return None


# ---------------------------------------------------------------------------
# Module-level logger setup
# ---------------------------------------------------------------------------

_handler = _AppendRotatingHandler(
    SESSION_LOG,
    max_bytes=_MAX_BYTES,
    backup_count=_BACKUP_COUNT,
)
_handler.setFormatter(logging.Formatter("%(message)s"))

_log = logging.getLogger("os29.telemetry")
_log.setLevel(logging.DEBUG)
_log.propagate = False
# Clean up any stale handlers from previous imports/reloads before attaching active handler
for _h in list(_log.handlers):
    try:
        _h.close()
    except Exception:
        pass
    _log.removeHandler(_h)
_log.addHandler(_handler)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _ts() -> str:
    """Wall-clock timestamp, millisecond precision.  Uses datetime.now()."""
    now = datetime.now()
    return now.strftime("%H:%M:%S.") + f"{now.microsecond // 1000:03d}"


def _sanitize_exc(exc: Exception) -> str:
    """Return a safe string representation of exc, redacting likely secrets."""
    msg = f"{type(exc).__name__}: {exc}"
    if _SECRET_FRAGMENT.search(msg):
        msg = re.sub(
            r"(?i)(password|passwd|token|secret|apikey|api[_-]key|credential|bearer|authorization)"
            r"([=:\s]+)\S+",
            r"\1\2[REDACTED]",
            msg,
        )
    return msg


def _emit(line: str) -> None:
    """Write one log line to stderr AND the file handler."""
    try:
        print(line, file=sys.stderr, flush=True)
    except Exception:
        pass  # detached console — keep writing to file
    try:
        clean = re.sub(r"\033\[[0-9;]*m", "", line)
        _log.info(clean)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def log_tool_call(tool_name: str, trace_id: str, args_summary: str = "") -> float:
    """Emit TOOL_CALL line.  Returns ``perf_counter()`` start for timing."""
    c    = _C
    tid  = f"  {c['grey']}trace={trace_id}{c['reset']}" if trace_id else ""
    tail = f"  {c['grey']}{args_summary}{c['reset']}" if args_summary else ""
    _emit(
        f"{c['grey']}[{_ts()}]{c['reset']} "
        f"{c['bold']}{c['cyan']}TOOL_CALL{c['reset']}    "
        f"{c['bold']}{tool_name}{c['reset']}{tid}{tail}"
    )
    return time.perf_counter()


def log_tool_result(
    tool_name:  str,
    trace_id:   str,
    start_time: float,
    outcome:    str,
    extra:      dict[str, Any] | None = None,
) -> float:
    """Emit TOOL_RESULT line with duration.  Returns ``duration_ms``."""
    duration_ms   = (time.perf_counter() - start_time) * 1000
    c             = _C
    outcome_color = _OUTCOME_COLOR.get(outcome, c["grey"])
    extra_str     = (
        "  " + "  ".join(f"{k}={v}" for k, v in (extra or {}).items())
        if extra else ""
    )
    tid = f"  {c['grey']}trace={trace_id}{c['reset']}" if trace_id else ""
    _emit(
        f"{c['grey']}[{_ts()}]{c['reset']} "
        f"{outcome_color}TOOL_RESULT{c['reset']}  "
        f"{tool_name}  {outcome_color}{outcome}{c['reset']}  "
        f"{c['grey']}duration={duration_ms:.1f}ms{c['reset']}"
        f"{tid}"
        f"{c['grey']}{extra_str}{c['reset']}"
    )
    return duration_ms


def log_auth(tool_name: str, profile: str, allowed: bool) -> None:
    c      = _C
    color  = c["green"] if allowed else c["red"]
    status = "ALLOW" if allowed else "DENY"
    _emit(
        f"{c['grey']}[{_ts()}]{c['reset']} "
        f"{color}AUTH         {status}{c['reset']}  "
        f"tool={tool_name}  profile={profile}"
    )


def log_error(tool_name: str, exc: Exception, trace_id: str = "") -> None:
    c    = _C
    tid  = f"  {c['grey']}trace={trace_id}{c['reset']}" if trace_id else ""
    safe = _sanitize_exc(exc)
    _emit(
        f"{c['grey']}[{_ts()}]{c['reset']} "
        f"{c['red']}ERROR{c['reset']}        "
        f"{tool_name}  {c['red']}{safe}{c['reset']}{tid}"
    )


def log_startup(server_name: str, db_path: str) -> None:
    """Emit startup banner.

    If ``live_session.log`` already contains data from a previous process
    (e.g. after a crash or restart), it is archived first so history is
    preserved and the new session starts from a clean file.
    """
    # Archive any leftover log from a previous run.
    prev_size = SESSION_LOG.stat().st_size if SESSION_LOG.exists() else 0
    if prev_size > 0:
        archived = _handler.archive_session(reason="previous-session")
        if archived:
            _emit(
                f"{_C['grey']}[{_ts()}] previous session archived -> "
                f"{archived.name}{_C['reset']}"
            )

    c   = _C
    sep = c["cyan"] + "-" * 60 + c["reset"]
    _emit(sep)
    _emit(
        f"{c['grey']}[{_ts()}]{c['reset']} "
        f"{c['bold']}{c['green']}OS29 STARTUP{c['reset']}  "
        f"server={server_name}  db={db_path}"
    )
    _emit(f"{c['grey']}  log -> {SESSION_LOG}{c['reset']}")
    _emit(sep)


def log_shutdown() -> None:
    """Emit shutdown marker and archive the current session log."""
    c = _C
    _emit(
        f"{c['grey']}[{_ts()}]{c['reset']} "
        f"{c['yellow']}OS29 SHUTDOWN{c['reset']}  stdin closed"
    )
    archived = _handler.archive_session(reason="clean-shutdown")
    if archived:
        _emit(
            f"{c['grey']}[{_ts()}] session archived -> "
            f"{archived.name}{c['reset']}"
        )
    _handler.close()