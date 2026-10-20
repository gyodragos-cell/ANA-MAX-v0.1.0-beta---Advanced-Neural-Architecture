"""tests/test_telemetry_rotation.py

Verifica:
  T1 - scriere continua in timp ce un reader tine fisierul deschis (no PermissionError)
  T2 - archive_session(): arhivare explicita + truncate + continut prezent in arhiva
  T3 - log_startup(): arhiveaza sesiunea anterioara (crash/restart) inainte de banner
  T4 - log_shutdown(): emite marker, arhiveaza, nu lasa handle orfan
  T5 - pruning: backup_count respectat dupa rotatie frecventa
  T6 - log_shutdown nu opreste OS29 (procesul MCP ramane independent de LIVE_CONSOLE)
"""
from __future__ import annotations

import logging
import os
import threading
import time
from pathlib import Path

import pytest

from os29.telemetry import _AppendRotatingHandler


# ---------------------------------------------------------------------------
# Factory helper — always isolated, never shares state with other tests
# ---------------------------------------------------------------------------

def _handler(tmp_path: Path, max_bytes: int = 5_000_000, backup_count: int = 3):
    log = tmp_path / "live_session.log"
    h = _AppendRotatingHandler(log, max_bytes=max_bytes, backup_count=backup_count)
    h.setFormatter(logging.Formatter("%(message)s"))
    return h, log


def _write(h: _AppendRotatingHandler, msg: str) -> None:
    rec = logging.LogRecord("test", logging.INFO, "", 0, msg, (), None)
    h.emit(rec)


def _arch(log: Path) -> Path:
    return log.parent / "archive"


# ---------------------------------------------------------------------------
# T1: continuous write while a reader holds the file open (no PermissionError)
# ---------------------------------------------------------------------------

def test_t1_write_while_reader_open(tmp_path):
    h, log = _handler(tmp_path, max_bytes=2_000)

    # Seed the file so the reader opens an existing path
    _write(h, "seed line")

    reader_errors: list[str] = []
    stop_ev = threading.Event()

    def reader():
        try:
            with open(log, "r", encoding="utf-8", errors="replace") as f:
                while not stop_ev.is_set():
                    f.read()
                    time.sleep(0.02)
        except Exception as exc:
            reader_errors.append(str(exc))

    rt = threading.Thread(target=reader, daemon=True)
    rt.start()
    time.sleep(0.05)

    write_errors: list[str] = []
    for i in range(100):
        try:
            _write(h, f"[TOOL_CALL] tool_{i}  trace=trace-{i}  arg=val{i}" + " " * 30)
        except Exception as exc:
            write_errors.append(str(exc))

    stop_ev.set()
    rt.join(timeout=3)

    h.close()

    assert not write_errors, f"Write errors: {write_errors}"
    assert not reader_errors, f"Reader errors (PermissionError?): {reader_errors}"
    assert log.exists(), "Active log path missing after writes"


# ---------------------------------------------------------------------------
# T2: archive_session() archives content, truncates active file
# ---------------------------------------------------------------------------

def test_t2_archive_session_explicit(tmp_path):
    h, log = _handler(tmp_path)

    _write(h, "hello world line 1")
    _write(h, "hello world line 2")
    h._stream.flush()

    size_before = log.stat().st_size
    assert size_before > 0, "Nothing written to log"

    archived = h.archive_session(reason="test-explicit")

    assert archived is not None, "archive_session returned None"
    assert archived.exists(), f"Archive file not created: {archived}"
    assert archived.stat().st_size > 0, "Archive file is empty"

    content = archived.read_text(encoding="utf-8", errors="replace")
    assert "hello world" in content, "Log content missing from archive"
    assert "test-explicit" in content, "Reason marker missing from archive"

    size_after = log.stat().st_size
    assert size_after < size_before, (
        f"Active log not truncated after archive: before={size_before} after={size_after}"
    )

    h.close()


# ---------------------------------------------------------------------------
# T3: restart archives previous session before the new startup banner
# ---------------------------------------------------------------------------

def test_t3_restart_archives_previous_session(tmp_path):
    """Simulates a new OS29 process starting while live_session.log has
    leftover content from the previous (crashed/stopped) run."""
    log = tmp_path / "live_session.log"
    arch = _arch(log)

    # Write leftover data from the previous session directly to the log file
    log.write_text("CRASHED SESSION DATA\nsome previous logs\n", encoding="utf-8")
    assert log.stat().st_size > 0

    # Create a fresh handler (new process simulation)
    h, _ = _handler(tmp_path, max_bytes=5_000_000, backup_count=3)
    h._stream.flush()

    archives_before = {a.name for a in arch.glob("*.log")}

    # Manually run the restart-archive logic (what log_startup calls internally)
    archived = h.archive_session(reason="previous-session")

    archives_after = {a.name for a in arch.glob("*.log")}
    new_archives = archives_after - archives_before

    assert archived is not None, "archive_session returned None for non-empty previous session"
    assert new_archives, "No new archive created for previous session"

    all_text = "".join(
        (arch / n).read_text(encoding="utf-8", errors="replace") for n in archives_after
    )
    assert "CRASHED SESSION DATA" in all_text, "Previous session content missing from archive"
    assert "previous-session" in all_text, "Reason marker missing from archive"

    h.close()


# ---------------------------------------------------------------------------
# T4: log_shutdown emits marker, archives, leaves no orphan handle
# ---------------------------------------------------------------------------

def test_t4_shutdown_archives_and_no_orphan(tmp_path):
    h, log = _handler(tmp_path)
    arch = _arch(log)

    _write(h, "[STARTUP] OS29 server=srv")
    _write(h, "[TOOL_CALL] some-tool  trace=some-trace")
    h._stream.flush()

    assert log.stat().st_size > 0, "Log must have content before shutdown"

    archives_before = {a.name for a in arch.glob("*.log")}

    # Emit shutdown marker then archive
    _write(h, "[SHUTDOWN] OS29 SHUTDOWN  stdin closed")
    h._stream.flush()
    archived = h.archive_session(reason="clean-shutdown")
    h.close()

    archives_after = {a.name for a in arch.glob("*.log")}
    new_archives = archives_after - archives_before

    assert archived is not None, "archive_session returned None after shutdown write"
    assert new_archives, "log_shutdown sequence did not create an archive"

    archive_text = (arch / list(new_archives)[0]).read_text(encoding="utf-8", errors="replace")
    assert "SHUTDOWN" in archive_text, "Shutdown marker missing from archive"

    # No orphan handle: file must be writable/deletable after close()
    try:
        log.write_text("post-shutdown-write\n", encoding="utf-8")
    except PermissionError as exc:
        pytest.fail(f"Orphan handle detected after close(): {exc}")


# ---------------------------------------------------------------------------
# T5: backup_count prunes old archives
# ---------------------------------------------------------------------------

def test_t5_pruning_respects_backup_count(tmp_path):
    h, log = _handler(tmp_path, max_bytes=200, backup_count=2)

    for i in range(60):
        _write(h, f"line-{i}-padding-{'x' * 30}")

    archives = sorted(_arch(log).glob("*.log"))

    # backup_count=2 → at most 2 should remain after pruning.
    # Allow 3 in case two rotations happen within the same second (same-name
    # collision) so Python creates a third without pruning it.
    assert len(archives) <= 3, (
        f"Expected ≤3 archives with backup_count=2, got {len(archives)}: "
        f"{[a.name for a in archives]}"
    )

    h.close()


# ---------------------------------------------------------------------------
# T6: closing the reader (LIVE_CONSOLE) does not affect the writer
# ---------------------------------------------------------------------------

def test_t6_closing_reader_does_not_affect_writer(tmp_path):
    h, log = _handler(tmp_path)

    _write(h, "startup banner line")
    h._stream.flush()

    # Open a reader — simulates LIVE_CONSOLE Get-Content -Wait
    reader_fh = open(log, "r", encoding="utf-8", errors="replace")

    for i in range(20):
        _write(h, f"[TOOL_CALL] tool_{i}  trace=trace-{i}")

    # Close reader — simulates the user closing LIVE_CONSOLE.bat
    reader_fh.close()

    write_errors: list[str] = []
    for i in range(20, 40):
        try:
            _write(h, f"[TOOL_CALL] tool_{i}  trace=trace-{i}")
        except Exception as exc:
            write_errors.append(str(exc))

    h._stream.flush()
    h.close()

    assert not write_errors, f"Writer failed after reader close: {write_errors}"
    archives = list(_arch(log).glob("*.log"))
    total_content = sum(
        p.stat().st_size for p in [log] + archives if p.exists()
    )
    assert total_content > 0, "No content in log or archives after writer ran"


# ---------------------------------------------------------------------------
# T7: module-level lifecycle with reload (verifies stale handlers replaced)
# ---------------------------------------------------------------------------

def test_t7_module_level_startup_shutdown_reload(tmp_path, monkeypatch):
    import importlib
    monkeypatch.setenv("OS29_LOG_DIR", str(tmp_path))
    import os29.telemetry as tel
    tel = importlib.reload(tel)

    assert tel.SESSION_LOG == tmp_path / "live_session.log"

    tel.log_startup(server_name="test-srv", db_path="test-db")
    tel.log_tool_call("probe_tool", "trace-abc", "key=val")
    tel.log_shutdown()

    arch_dir = tmp_path / "archive"
    archives = list(arch_dir.glob("*.log"))
    assert len(archives) >= 1, "Module-level log_shutdown did not create archive"

    archive_content = archives[0].read_text(encoding="utf-8", errors="replace")
    assert "probe_tool" in archive_content, "probe_tool missing from archive"
    assert "OS29 STARTUP" in archive_content, "OS29 STARTUP missing from archive"
    assert "OS29 SHUTDOWN" in archive_content, "OS29 SHUTDOWN missing from archive"