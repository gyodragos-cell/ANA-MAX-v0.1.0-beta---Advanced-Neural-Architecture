"""Compact file patch tool for exact read -> patch -> write edits."""

from __future__ import annotations

import difflib
import hashlib
from pathlib import Path
from typing import Any

from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus


BLOCKED_PARTS = {".env", ".license", "logs", "memory", "screenshots", "data", "voice_temp"}


class FilePatchTool(Tool):
    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="file_patch",
            description="Apply an exact text patch to a file with diff preview and safety checks.",
            parameters=[
                ToolParameter("path", "File path to patch", "string", True),
                ToolParameter("old_text", "Exact text block to replace", "string", True),
                ToolParameter("new_text", "Replacement text block", "string", True),
                ToolParameter("replace_all", "Replace all exact matches", "boolean", False, False),
                ToolParameter("preview_only", "Return diff without writing", "boolean", False, True),
                ToolParameter("max_diff_chars", "Maximum diff characters returned", "integer", False, 12000),
            ],
            category="files",
        )

    def execute(self, **kwargs: Any) -> ToolResult:
        path = Path(str(kwargs.get("path") or "")).expanduser()
        old_text = str(kwargs.get("old_text") or "")
        new_text = str(kwargs.get("new_text") or "")
        replace_all = self._to_bool(kwargs.get("replace_all"), False)
        preview_only = self._to_bool(kwargs.get("preview_only"), True)
        max_diff_chars = int(kwargs.get("max_diff_chars") or 12000)

        if not path:
            return ToolResult(status=ToolStatus.ERROR, error="path is required")
        if not old_text:
            return ToolResult(status=ToolStatus.ERROR, error="old_text is required")

        resolved = path.resolve()
        if self._blocked_path(resolved):
            return ToolResult(status=ToolStatus.BLOCKED, error=f"Refusing to patch protected path: {resolved.name}")
        if not resolved.exists() or not resolved.is_file():
            return ToolResult(status=ToolStatus.ERROR, error=f"File not found: {resolved}")

        try:
            original = resolved.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return ToolResult(status=ToolStatus.ERROR, error="Only UTF-8 text files are supported")

        matches = original.count(old_text)
        if matches == 0:
            return ToolResult(status=ToolStatus.ERROR, error="old_text was not found exactly")
        if matches > 1 and not replace_all:
            return ToolResult(status=ToolStatus.ERROR, error=f"old_text matched {matches} times; set replace_all=True or narrow it")

        updated = original.replace(old_text, new_text, matches if replace_all else 1)
        diff = "".join(
            difflib.unified_diff(
                original.splitlines(True),
                updated.splitlines(True),
                fromfile=str(resolved),
                tofile=str(resolved),
            )
        )
        truncated = len(diff) > max_diff_chars
        diff_preview = diff[:max_diff_chars] + ("\n... diff truncated ..." if truncated else "")

        data = {
            "path": str(resolved),
            "changed": original != updated,
            "matches": matches,
            "preview_only": preview_only,
            "diff": diff_preview,
            "diff_truncated": truncated,
            "before_sha256": hashlib.sha256(original.encode("utf-8")).hexdigest(),
            "after_sha256": hashlib.sha256(updated.encode("utf-8")).hexdigest(),
        }

        if preview_only:
            return ToolResult(status=ToolStatus.SUCCESS, data=data, message="Patch preview generated")

        resolved.write_text(updated, encoding="utf-8")
        return ToolResult(status=ToolStatus.SUCCESS, data=data, message="Patch applied")

    def _blocked_path(self, path: Path) -> bool:
        parts = {part.lower() for part in path.parts}
        if parts.intersection(BLOCKED_PARTS):
            return True
        return path.name.lower() in BLOCKED_PARTS or path.suffix.lower() in {".db", ".sqlite", ".sqlite3", ".log"}

    def _to_bool(self, value: Any, default: bool) -> bool:
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in {"1", "true", "yes", "on"}
