"""Shared helpers for ANA MAX OS-3 modules."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

RAW_START = "::OS3_RAW_OUTPUT_START::"
RAW_END = "::OS3_RAW_OUTPUT_END::"


def print_raw_json(result: Any) -> None:
    """Print JSON wrapped so external shells do not parse it as tool calls."""
    print(RAW_START)
    print(json.dumps(result, indent=2, default=str, ensure_ascii=False))
    print(RAW_END)


def ensure_dir(path: Path) -> Path:
    """Create a directory if needed and return it."""
    path.mkdir(parents=True, exist_ok=True)
    return path
