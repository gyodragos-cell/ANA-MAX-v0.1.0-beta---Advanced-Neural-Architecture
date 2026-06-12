# PATCH_START v19_phase1
"""Read-only ANA MAX runtime inspection helpers.

This module is intentionally not auto-registered in Phase 1. It exposes a
manual ``run(args)`` entry point and does not modify files, processes, or
runtime state.
"""

from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path
from typing import Any


DEFAULT_PORTS = (8765, 8790)
HASH_TARGETS = (
    "main.py",
    "tools/tool_adapters.py",
    "tools/context_engine.py",
    "tools/verdent_tools.py",
    "ana-max-bridge/bridge_server.py",
)
SKIP_DIRS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    "venv",
    ".venv",
    "node_modules",
    "logs",
    "memory",
    "data",
    "screenshots",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _file_hashes(base: Path) -> dict[str, str | None]:
    hashes: dict[str, str | None] = {}
    for rel in HASH_TARGETS:
        path = base / rel
        hashes[rel] = _sha256(path) if path.is_file() else None
    return hashes


def _psutil_module() -> Any | None:
    try:
        import psutil  # type: ignore

        return psutil
    except Exception:
        return None


def _port_snapshot(ports: tuple[int, ...] = DEFAULT_PORTS) -> dict[str, Any]:
    psutil = _psutil_module()
    snapshot: dict[str, Any] = {str(port): {"listening": False, "pid": None} for port in ports}
    if psutil is None:
        return snapshot

    try:
        for conn in psutil.net_connections(kind="tcp"):
            local = getattr(conn, "laddr", None)
            port = getattr(local, "port", None)
            if port in ports and getattr(conn, "status", "") == "LISTEN":
                snapshot[str(port)] = {"listening": True, "pid": conn.pid}
    except Exception:
        pass
    return snapshot


def _bridge_pid(ports: dict[str, Any]) -> int | None:
    item = ports.get("8790", {})
    pid = item.get("pid") if isinstance(item, dict) else None
    return int(pid) if isinstance(pid, int) else None


def _iter_files(base: Path, max_files: int) -> dict[str, str]:
    result: dict[str, str] = {}
    count = 0
    for root, dirs, files in os.walk(base):
        dirs[:] = [name for name in dirs if name not in SKIP_DIRS]
        root_path = Path(root)
        for name in files:
            path = root_path / name
            rel = path.relative_to(base).as_posix()
            try:
                result[rel] = _sha256(path)
            except Exception:
                continue
            count += 1
            if count >= max_files:
                return result
    return result


def _snapshot() -> dict[str, Any]:
    cwd = Path.cwd()
    ports = _port_snapshot()
    return {
        "success": True,
        "runtime": {
            "cwd": str(cwd),
            "bridge_pid": _bridge_pid(ports),
            "ports": ports,
            "loaded_modules": sorted(sys.modules.keys())[:300],
            "file_hashes": _file_hashes(cwd),
        },
    }


def _compare_envs(args: dict[str, Any]) -> dict[str, Any]:
    dev_path = Path(str(args.get("dev_path", ""))).expanduser()
    release_path = Path(str(args.get("release_path", ""))).expanduser()
    max_files = int(args.get("max_files", 5000))

    if not dev_path.is_dir():
        return {"success": False, "error": f"dev_path is not a directory: {dev_path}"}
    if not release_path.is_dir():
        return {"success": False, "error": f"release_path is not a directory: {release_path}"}

    dev_files = _iter_files(dev_path, max_files)
    release_files = _iter_files(release_path, max_files)
    dev_keys = set(dev_files)
    release_keys = set(release_files)
    common = dev_keys & release_keys

    return {
        "success": True,
        "diff": {
            "modified": sorted(key for key in common if dev_files[key] != release_files[key]),
            "missing": sorted(dev_keys - release_keys),
            "extra": sorted(release_keys - dev_keys),
        },
        "limits": {"max_files": max_files},
    }


def run(args: dict[str, Any] | None = None) -> dict[str, Any]:
    args = args or {}
    action = str(args.get("action", "snapshot"))
    if action == "snapshot":
        return _snapshot()
    if action == "compare_envs":
        return _compare_envs(args)
    return {"success": False, "error": f"unknown action: {action}"}


# PATCH_END v19_phase1
