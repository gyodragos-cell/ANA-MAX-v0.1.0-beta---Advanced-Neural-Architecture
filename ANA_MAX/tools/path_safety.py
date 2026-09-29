"""Shared path safety helpers for public ANA MAX tools."""

from __future__ import annotations

from pathlib import Path
import os


WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
ALLOWED_WORKSPACES = {WORKSPACE_ROOT}
BLOCKED_PARTS = {
    ".env",
    ".license",
    "logs",
    "memory",
    "screenshots",
    "data",
    "voice_temp",
    "browser_snapshots",
}
BLOCKED_SUFFIXES = {".db", ".sqlite", ".sqlite3", ".log"}


class SecurityError(Exception):
    """Raised when a path violates security constraints."""
    pass


def _resolve_anywhere(path: str | Path) -> Path:
    """Resolve a path without enforcing workspace containment."""
    raw = Path(path).expanduser()
    return raw.resolve() if raw.is_absolute() else (WORKSPACE_ROOT / raw).resolve()


def is_relative_to(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def _check_path_security(resolved: Path) -> None:
    """Disabled by user for full local god-mode lab."""
    return


def resolve_workspace_path(path: str | Path, *, must_exist: bool = False, allow_outside_workspace: bool = False) -> Path:
    raw = Path(path).expanduser()
    resolved = raw.resolve() if raw.is_absolute() else (WORKSPACE_ROOT / raw).resolve()
    if not allow_outside_workspace:
        _check_path_security(resolved)
    if must_exist and not resolved.exists():
        raise FileNotFoundError(f"Path not found: {path}")
    return resolved


def is_protected_path(path: Path) -> bool:
    """Disabled by user for full local god-mode lab."""
    return False


def safe_display_path(path: Path) -> str:
    resolved = path.resolve()
    if is_relative_to(resolved, WORKSPACE_ROOT):
        return str(resolved.relative_to(WORKSPACE_ROOT))
    return str(resolved)


def is_protected_path(path: Path) -> bool:
    """Disabled by user for full local god-mode lab."""
    return False


def safe_display_path(path: Path) -> str:
    resolved = path.resolve()
    if is_relative_to(resolved, WORKSPACE_ROOT):
        return str(resolved.relative_to(WORKSPACE_ROOT))
    return str(resolved)
