from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from typing import Any

from .models import TraceEvent, new_id
from .store import Store


def terminal_exec(
    command: str,
    cwd: str | None = None,
    timeout_seconds: int = 60,
    store: Store | None = None,
    trace_id: str | None = None,
) -> dict[str, Any]:
    """Execute a shell command and optionally record a TraceEvent.

    Args:
        trace_id: If provided, the TraceEvent shares this trace_id with the
                  calling MCP tool call instead of creating an isolated trace.
    """
    import time as _time
    cmd_str = str(command).strip()
    if not cmd_str:
        return {"exit_code": 1, "stdout": "", "stderr": "empty command"}
    work_dir = Path(cwd).resolve() if cwd else Path.cwd()
    try:
        env_vars = os.environ.copy()
        if "SystemRoot" not in env_vars:
            env_vars["SystemRoot"] = r"C:\Windows"
        if "ComSpec" not in env_vars:
            env_vars["ComSpec"] = r"C:\Windows\system32\cmd.exe"
        _t0 = _time.perf_counter()
        proc = subprocess.run(
            cmd_str,
            env=env_vars,
            cwd=str(work_dir),
            shell=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=int(timeout_seconds),
        )
        duration_ms = (_time.perf_counter() - _t0) * 1000
        res = {
            "exit_code":   proc.returncode,
            "stdout":      proc.stdout or "",
            "stderr":      proc.stderr or "",
            "cwd":         str(work_dir),
            "duration_ms": round(duration_ms, 1),
        }
        if store:
            effective_trace_id = trace_id or f"term-{new_id()}"
            store.record_event(TraceEvent(
                trace_id=effective_trace_id,
                source="os29.terminal",
                component="terminal_exec",
                kind="exec.command",
                action=cmd_str[:128],
                outcome="success" if proc.returncode == 0 else "failure",
                duration_ms=duration_ms,
                attributes={"exit_code": proc.returncode, "stdout_len": len(res["stdout"])},
            ))
        return res
    except subprocess.TimeoutExpired:
        if store:
            effective_trace_id = trace_id or f"term-{new_id()}"
            store.record_event(TraceEvent(
                trace_id=effective_trace_id,
                source="os29.terminal",
                component="terminal_exec",
                kind="exec.command",
                action=cmd_str[:128],
                outcome="failure",
                attributes={"exit_code": -1, "reason": "timeout", "timeout_seconds": timeout_seconds},
            ))
        return {"exit_code": -1, "stdout": "", "stderr": f"command timed out after {timeout_seconds}s"}
    except Exception as exc:
        if store:
            effective_trace_id = trace_id or f"term-{new_id()}"
            store.record_event(TraceEvent(
                trace_id=effective_trace_id,
                source="os29.terminal",
                component="terminal_exec",
                kind="exec.command",
                action=cmd_str[:128],
                outcome="error",
                attributes={"exit_code": -1, "exc_type": type(exc).__name__},
            ))
        return {"exit_code": -1, "stdout": "", "stderr": str(exc)}


def file_read(path: str, start_line: int | None = None, end_line: int | None = None) -> dict[str, Any]:
    target = Path(path).resolve()
    if not target.is_file():
        raise FileNotFoundError(f"file not found: {path}")
    text = target.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    total_lines = len(lines)
    s = max(1, int(start_line)) if start_line else 1
    e = min(total_lines, int(end_line)) if end_line else total_lines
    selected = lines[s - 1 : e]
    return {
        "path": str(target),
        "total_lines": total_lines,
        "start_line": s,
        "end_line": e,
        "content": "\n".join(selected),
    }


def file_write(path: str, content: str, overwrite: bool = True) -> dict[str, Any]:
    target = Path(path).resolve()
    if target.is_file() and not overwrite:
        raise FileExistsError(f"file already exists and overwrite is false: {path}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(str(content), encoding="utf-8")
    return {
        "path": str(target),
        "bytes_written": len(str(content).encode("utf-8")),
        "success": True,
    }


def code_search(pattern: str, search_path: str | None = None, max_results: int = 50, case_sensitive: bool = False) -> dict[str, Any]:
    root = Path(search_path).resolve() if search_path else Path.cwd()
    if not root.is_dir():
        raise NotADirectoryError(f"search path is not a directory: {search_path}")
    flags = 0 if case_sensitive else re.IGNORECASE
    regex = re.compile(pattern, flags)
    matches = []
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if any(part in {".git", ".pytest_cache", "__pycache__", "venv", "node_modules"} for part in p.parts):
            continue
        try:
            for idx, line in enumerate(p.read_text(encoding="utf-8", errors="ignore").splitlines(), start=1):
                if regex.search(line):
                    matches.append({
                        "file": str(p),
                        "line": idx,
                        "text": line[:250].strip(),
                    })
                    if len(matches) >= int(max_results):
                        break
        except Exception:
            continue
        if len(matches) >= int(max_results):
            break
    return {
        "pattern": pattern,
        "search_path": str(root),
        "match_count": len(matches),
        "matches": matches,
    }