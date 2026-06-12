"""Minimal ANA code map runtime used by context-pack tools.

Read-only source scanner. Writes compact indexes only under ANA_MAX/memory.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


INDEX_JSON = "code_map.json"
TEXT_EXTENSIONS = {".py", ".md", ".txt", ".json", ".yaml", ".yml", ".ps1", ".bat", ".html", ".css", ".js", ".ts"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _iter_files(root: Path, limit: int = 1200):
    ignored = {"venv", "__pycache__", ".git", "node_modules", "voice_temp", "screenshots"}
    for path in root.rglob("*"):
        if any(part in ignored for part in path.parts):
            continue
        if path.is_file() and path.suffix.lower() in TEXT_EXTENSIONS:
            yield path
            limit -= 1
            if limit <= 0:
                return


def _summarize(root: Path, path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    symbols = re.findall(r"^\s*(?:def|class)\s+([A-Za-z_][A-Za-z0-9_]*)", text, flags=re.MULTILINE)
    imports = re.findall(r"^\s*(?:from\s+[\w.]+\s+import|import)\s+(.+)", text, flags=re.MULTILINE)
    rel = str(path.relative_to(root)) if path.is_relative_to(root) else str(path)
    return {
        "file": rel,
        "suffix": path.suffix.lower(),
        "bytes": path.stat().st_size,
        "symbols": symbols[:30],
        "imports": imports[:20],
        "preview": " ".join(text.split())[:500],
    }


def refresh(root: str | Path, out_dir: str | Path, force: bool = False) -> dict[str, Any]:
    root = Path(root).resolve()
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    summaries = [_summarize(root, path) for path in _iter_files(root)]
    payload = {
        "schema": "ana.code_map.v1",
        "root": str(root),
        "updated_at": _now(),
        "summaries": summaries,
    }
    (out_dir / INDEX_JSON).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return stats(out_dir)


def _load(out_dir: str | Path) -> dict[str, Any]:
    path = Path(out_dir) / INDEX_JSON
    if not path.exists():
        return {"schema": "ana.code_map.v1", "updated_at": None, "summaries": []}
    return json.loads(path.read_text(encoding="utf-8"))


def stats(out_dir: str | Path) -> dict[str, Any]:
    payload = _load(out_dir)
    return {
        "schema": payload.get("schema", "ana.code_map.v1"),
        "updated_at": payload.get("updated_at"),
        "summaries": len(payload.get("summaries") or []),
    }


def query(out_dir: str | Path, query_text: str, limit: int = 5) -> dict[str, Any]:
    payload = _load(out_dir)
    terms = [term.lower() for term in re.findall(r"[A-Za-z0-9_.-]{3,}", query_text or "")]
    results = []
    for item in payload.get("summaries") or []:
        haystack = " ".join(
            [
                item.get("file", ""),
                " ".join(item.get("symbols") or []),
                " ".join(item.get("imports") or []),
                item.get("preview", ""),
            ]
        ).lower()
        score = sum(1 for term in terms if term in haystack)
        if score or not terms:
            result = dict(item)
            result["score"] = score
            results.append(result)
    results.sort(key=lambda item: (-int(item.get("score") or 0), item.get("file", "")))
    return {
        "schema": "ana.code_map.query.v1",
        "updated_at": payload.get("updated_at"),
        "query": query_text,
        "results": results[: max(1, int(limit or 5))],
    }
