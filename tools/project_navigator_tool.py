"""Project navigation tool: list, search, and open source files compactly."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Iterable

from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus


SKIP_DIRS = {".git", "venv", "__pycache__", "logs", "memory", "screenshots", "data", "browser_snapshots", "voice_temp"}
TEXT_EXTS = {".py", ".md", ".txt", ".json", ".yaml", ".yml", ".html", ".css", ".js", ".ts", ".bat", ".ps1", ".toml"}


class ProjectNavigatorTool(Tool):
    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="project_navigator",
            description="List, search, and open project files with compact, private-safe output.",
            parameters=[
                ToolParameter("operation", "list, find, grep, open, tree", "string", True, choices=["list", "find", "grep", "open", "tree"]),
                ToolParameter("path", "Root path or file path", "string", False, "."),
                ToolParameter("pattern", "Name pattern or regex", "string", False, ""),
                ToolParameter("query", "Text or regex to search for", "string", False, ""),
                ToolParameter("limit", "Maximum results", "integer", False, 80),
                ToolParameter("max_chars", "Maximum file content characters for open", "integer", False, 12000),
            ],
            category="files",
        )

    def execute(self, operation: str, **kwargs: Any) -> ToolResult:
        root = Path(str(kwargs.get("path") or ".")).expanduser().resolve()
        limit = int(kwargs.get("limit") or 80)
        max_chars = int(kwargs.get("max_chars") or 12000)

        try:
            if operation == "list":
                return self._list(root, limit)
            if operation == "tree":
                return self._tree(root, limit)
            if operation == "find":
                return self._find(root, str(kwargs.get("pattern") or "*"), limit)
            if operation == "grep":
                return self._grep(root, str(kwargs.get("query") or ""), limit)
            if operation == "open":
                return self._open(root, max_chars)
        except Exception as exc:
            return ToolResult(status=ToolStatus.ERROR, error=str(exc))
        return ToolResult(status=ToolStatus.ERROR, error=f"Unknown operation: {operation}")

    def _list(self, path: Path, limit: int) -> ToolResult:
        if not path.exists() or not path.is_dir():
            return ToolResult(status=ToolStatus.ERROR, error=f"Directory not found: {path}")
        items = []
        for child in sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))[:limit]:
            if self._skip(child):
                continue
            items.append({"name": child.name, "type": "dir" if child.is_dir() else "file", "size": child.stat().st_size if child.is_file() else None})
        return ToolResult(status=ToolStatus.SUCCESS, data={"path": str(path), "items": items, "count": len(items)}, message=f"{len(items)} items")

    def _tree(self, path: Path, limit: int) -> ToolResult:
        if not path.exists() or not path.is_dir():
            return ToolResult(status=ToolStatus.ERROR, error=f"Directory not found: {path}")
        entries = []
        for item in self._walk(path):
            rel = item.relative_to(path)
            entries.append(str(rel) + ("/" if item.is_dir() else ""))
            if len(entries) >= limit:
                break
        return ToolResult(status=ToolStatus.SUCCESS, data={"root": str(path), "entries": entries, "truncated": len(entries) >= limit}, message=f"{len(entries)} entries")

    def _find(self, path: Path, pattern: str, limit: int) -> ToolResult:
        regex = re.compile(pattern.replace("*", ".*"), re.IGNORECASE)
        matches = []
        base = path if path.is_dir() else path.parent
        for item in self._walk(base):
            if regex.search(item.name):
                matches.append(str(item))
                if len(matches) >= limit:
                    break
        return ToolResult(status=ToolStatus.SUCCESS, data={"matches": matches, "count": len(matches)}, message=f"{len(matches)} matches")

    def _grep(self, path: Path, query: str, limit: int) -> ToolResult:
        if not query:
            return ToolResult(status=ToolStatus.ERROR, error="query is required")
        regex = re.compile(query, re.IGNORECASE)
        base = path if path.is_dir() else path.parent
        matches = []
        for item in self._walk(base):
            if not item.is_file() or item.suffix.lower() not in TEXT_EXTS:
                continue
            try:
                for lineno, line in enumerate(item.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
                    if regex.search(line):
                        matches.append({"path": str(item), "line": lineno, "text": line.strip()[:240]})
                        if len(matches) >= limit:
                            return ToolResult(status=ToolStatus.SUCCESS, data={"matches": matches, "count": len(matches), "truncated": True}, message=f"{len(matches)} matches")
            except Exception:
                continue
        return ToolResult(status=ToolStatus.SUCCESS, data={"matches": matches, "count": len(matches), "truncated": False}, message=f"{len(matches)} matches")

    def _open(self, path: Path, max_chars: int) -> ToolResult:
        if self._skip(path) or path.suffix.lower() not in TEXT_EXTS:
            return ToolResult(status=ToolStatus.BLOCKED, error=f"Refusing to open protected or non-text file: {path.name}")
        if not path.exists() or not path.is_file():
            return ToolResult(status=ToolStatus.ERROR, error=f"File not found: {path}")
        text = path.read_text(encoding="utf-8", errors="ignore")
        truncated = len(text) > max_chars
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={"path": str(path), "content": text[:max_chars], "chars": len(text), "truncated": truncated},
            message=f"Opened {path.name}",
        )

    def _walk(self, root: Path) -> Iterable[Path]:
        for current, dirs, files in os.walk(root):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
            current_path = Path(current)
            for dirname in sorted(dirs):
                yield current_path / dirname
            for filename in sorted(files):
                path = current_path / filename
                if not self._skip(path):
                    yield path

    def _skip(self, path: Path) -> bool:
        parts = {part.lower() for part in path.parts}
        return bool(parts.intersection(SKIP_DIRS)) or path.name.lower() in {".env", ".license"} or path.suffix.lower() in {".db", ".log"}
