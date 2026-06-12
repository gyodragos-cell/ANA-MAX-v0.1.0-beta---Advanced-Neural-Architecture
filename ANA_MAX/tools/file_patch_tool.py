"""Compact file patch tool for exact read -> patch -> write edits."""

from __future__ import annotations

import difflib
import hashlib
from typing import Any

from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus
from tools.path_safety import is_protected_path, resolve_workspace_path, safe_display_path


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
            dangerous=True,
        )

    def execute(self, **kwargs: Any) -> ToolResult:
        raw_path = str(kwargs.get("path") or "")
        old_text = str(kwargs.get("old_text") or "")
        new_text = str(kwargs.get("new_text") or "")
        replace_all = self._to_bool(kwargs.get("replace_all"), False)
        preview_only = self._to_bool(kwargs.get("preview_only"), True)
        max_diff_chars = int(kwargs.get("max_diff_chars") or 12000)

        if not raw_path:
            return ToolResult(status=ToolStatus.ERROR, error="path is required")
        if not old_text:
            return ToolResult(status=ToolStatus.ERROR, error="old_text is required")

        try:
            resolved = resolve_workspace_path(raw_path)
        except (OSError, ValueError) as exc:
            return ToolResult(status=ToolStatus.BLOCKED, error=str(exc))
        display_path = safe_display_path(resolved)
        if is_protected_path(resolved):
            return ToolResult(status=ToolStatus.BLOCKED, error=f"Refusing to patch protected path: {display_path}")
        if not resolved.exists() or not resolved.is_file():
            return ToolResult(status=ToolStatus.ERROR, error=f"File not found: {display_path}")

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
                fromfile=display_path,
                tofile=display_path,
            )
        )
        truncated = len(diff) > max_diff_chars
        diff_preview = diff[:max_diff_chars] + ("\n... diff truncated ..." if truncated else "")

        data = {
            "path": display_path,
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

    def _to_bool(self, value: Any, default: bool) -> bool:
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in {"1", "true", "yes", "on"}
