"""
Compact file patch tool for exact read -> patch -> write edits (OS27 Hyper++)
============================================================================

OS27 Hyper++ Features:
- Telemetry tracking for patch operations (preview, apply)
- Health monitoring for patch reliability
- MemoryCortex integration for patch errors and state learning
- ContextEngine integration for file patch state awareness
- SelfEvolvingTool integration for anomaly detection on patch failures
- Structured logging with error detection
"""

from __future__ import annotations

import difflib
import hashlib
import time
from typing import Any, Dict

from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus
from tools.path_safety import is_protected_path, resolve_workspace_path, safe_display_path

# OS27 Hyper++ Telemetry
_patch_telemetry: Dict[str, Dict[str, Any]] = {}


def _record_patch_telemetry(operation: str, success: bool, execution_time: float) -> None:
    """Record OS27 Hyper++ telemetry for patch operations."""
    if operation not in _patch_telemetry:
        _patch_telemetry[operation] = {
            "operation_count": 0,
            "success_count": 0,
            "failure_count": 0,
            "total_time": 0.0,
            "last_execution_time": 0.0,
            "last_success": False,
        }
    
    _patch_telemetry[operation]["operation_count"] += 1
    _patch_telemetry[operation]["total_time"] += execution_time
    _patch_telemetry[operation]["last_execution_time"] = execution_time
    _patch_telemetry[operation]["last_success"] = success
    
    if success:
        _patch_telemetry[operation]["success_count"] += 1
    else:
        _patch_telemetry[operation]["failure_count"] += 1


def get_patch_telemetry(operation: str | None = None) -> Dict[str, Any] | Dict[str, Dict[str, Any]]:
    """Get telemetry for patch operations."""
    if operation:
        return _patch_telemetry.get(operation, {})
    return _patch_telemetry.copy()


def get_patch_health() -> str:
    """Get health status for patch tool based on telemetry."""
    if not _patch_telemetry:
        return "unknown"
    
    total_ops = sum(stats["operation_count"] for stats in _patch_telemetry.values())
    total_failures = sum(stats["failure_count"] for stats in _patch_telemetry.values())
    
    if total_ops == 0:
        return "unknown"
    
    failure_rate = total_failures / total_ops
    if failure_rate > 0.5:
        return "broken"
    if failure_rate > 0.1:
        return "degraded"
    return "healthy"


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
        start_time = time.time()
        
        # AI Core hooks (lazy import for safety)
        cortex = None
        context_engine = None
        evolver = None
        try:
            from tools.memory_cortex import MemoryCortex
            cortex = MemoryCortex()
        except Exception:
            pass
        try:
            from tools.context_engine import ContextEngine
            context_engine = ContextEngine()
        except Exception:
            pass
        try:
            from tools.self_evolving_tool import SelfEvolvingTool
            evolver = SelfEvolvingTool()
        except Exception:
            pass
        
        raw_path = str(kwargs.get("path") or "")
        old_text = str(kwargs.get("old_text") or "")
        new_text = str(kwargs.get("new_text") or "")
        replace_all = self._to_bool(kwargs.get("replace_all"), False)
        preview_only = self._to_bool(kwargs.get("preview_only"), True)
        max_diff_chars = int(kwargs.get("max_diff_chars") or 12000)

        if not raw_path:
            execution_time = time.time() - start_time
            _record_patch_telemetry("execute", False, execution_time)
            return ToolResult(status=ToolStatus.ERROR, error="path is required")
        if not old_text:
            execution_time = time.time() - start_time
            _record_patch_telemetry("execute", False, execution_time)
            return ToolResult(status=ToolStatus.ERROR, error="old_text is required")

        try:
            resolved = resolve_workspace_path(raw_path)
        except (OSError, ValueError) as exc:
            execution_time = time.time() - start_time
            _record_patch_telemetry("execute", False, execution_time)
            return ToolResult(status=ToolStatus.BLOCKED, error=str(exc))
        display_path = safe_display_path(resolved)
        if is_protected_path(resolved):
            execution_time = time.time() - start_time
            _record_patch_telemetry("execute", False, execution_time)
            return ToolResult(status=ToolStatus.BLOCKED, error=f"Refusing to patch protected path: {display_path}")
        if not resolved.exists() or not resolved.is_file():
            execution_time = time.time() - start_time
            _record_patch_telemetry("execute", False, execution_time)
            return ToolResult(status=ToolStatus.ERROR, error=f"File not found: {display_path}")

        try:
            original = resolved.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            execution_time = time.time() - start_time
            _record_patch_telemetry("execute", False, execution_time)
            return ToolResult(status=ToolStatus.ERROR, error="Only UTF-8 text files are supported")

        matches = original.count(old_text)
        if matches == 0:
            execution_time = time.time() - start_time
            _record_patch_telemetry("execute", False, execution_time)
            return ToolResult(status=ToolStatus.ERROR, error="old_text was not found exactly")
        if matches > 1 and not replace_all:
            execution_time = time.time() - start_time
            _record_patch_telemetry("execute", False, execution_time)
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

        operation_type = "preview" if preview_only else "apply"
        
        if preview_only:
            execution_time = time.time() - start_time
            _record_patch_telemetry(operation_type, True, execution_time)
            return ToolResult(status=ToolStatus.SUCCESS, data=data, message="Patch preview generated")

        if str(resolved).lower().endswith(".py"):
            import ast
            try:
                ast.parse(updated)
            except SyntaxError as syn_err:
                hint_line = f" pe linia cod: '{syn_err.text.strip()}'" if syn_err.text else ""
                err_msg = f"VALIDARE SINTAXA ESUATA (AST Guard): Patch-ul nu a fost aplicat deoarece rezulta o eroare de sintaxa la linia {syn_err.lineno}: {syn_err.msg}{hint_line}. Corecteaza patch-ul!"
                return ToolResult(status=ToolStatus.ERROR, error=err_msg)

        resolved.write_text(updated, encoding="utf-8")
        execution_time = time.time() - start_time
        _record_patch_telemetry(operation_type, True, execution_time)
        
        # ContextEngine integration for file patch state
        if context_engine:
            try:
                context_engine.update_context(
                    key="file_patch",
                    value={
                        "path": display_path,
                        "operation": operation_type,
                        "changed": data["changed"],
                        "timestamp": time.time(),
                    }
                )
            except Exception:
                pass
        
        # MemoryCortex integration for patch history
        if cortex and data["changed"]:
            try:
                cortex.remember(
                    "patch",
                    f"file_patch.{display_path}",
                    f"Applied patch to {display_path}: {matches} match(es)"
                )
            except Exception:
                pass
        
        return ToolResult(status=ToolStatus.SUCCESS, data=data, message="Patch applied")

    def _to_bool(self, value: Any, default: bool) -> bool:
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in {"1", "true", "yes", "on"}
