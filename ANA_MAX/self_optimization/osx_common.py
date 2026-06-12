#!/usr/bin/env python3
"""Shared local-only helpers for OS-5+ additive layers."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

WORKSPACE_ROOT = ROOT
ANA_MAX_ROOT = WORKSPACE_ROOT / "ANA_MAX"
MEMORY_DIR = ANA_MAX_ROOT / "memory"
DOCS_DIR = WORKSPACE_ROOT / "docs"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        return {} if default is None else default
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"error": str(exc), "path": str(path)}
    if isinstance(loaded, dict):
        return loaded
    return {"value": loaded}


def write_json(path: Path, data: Any) -> Path:
    ensure_dir(path.parent)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    return path


def read_text(path: Path, limit: int = 4000) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "path": str(path)}
    text = path.read_text(encoding="utf-8", errors="replace")
    return {
        "exists": True,
        "path": str(path),
        "bytes": path.stat().st_size,
        "line_count": text.count("\n") + 1,
        "tail": text[-limit:],
    }
