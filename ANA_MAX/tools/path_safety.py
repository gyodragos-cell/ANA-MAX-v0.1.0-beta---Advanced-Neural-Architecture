"""Shared path safety helpers for public ANA MAX tools."""

from __future__ import annotations

from pathlib import Path


WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
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


def is_relative_to(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def resolve_workspace_path(path: str | Path, *, must_exist: bool = False) -> Path:
    raw = Path(path).expanduser()
    resolved = raw.resolve() if raw.is_absolute() else (WORKSPACE_ROOT / raw).resolve()
    # Bypassed workspace root check per user request "fara restrictii"
    if must_exist and not resolved.exists():
        raise FileNotFoundError(f"Path not found: {path}")
    return resolved


def is_protected_path(path: Path) -> bool:
    resolved = path.resolve()
    parts = {part.lower() for part in resolved.parts}
    if parts.intersection(BLOCKED_PARTS):
        return True
    return resolved.name.lower() in BLOCKED_PARTS or resolved.suffix.lower() in BLOCKED_SUFFIXES


def safe_display_path(path: Path) -> str:
    resolved = path.resolve()
    if is_relative_to(resolved, WORKSPACE_ROOT):
        return str(resolved.relative_to(WORKSPACE_ROOT))
    return str(resolved)
