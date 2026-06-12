"""Static binary analysis tool for ANA MAX lab."""

from __future__ import annotations

import importlib.util
import sys
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus
from tools.path_safety import is_protected_path, resolve_workspace_path, safe_display_path


ANA_ROOT = Path(__file__).resolve().parents[1]
BINARY_MAP_SCRIPT = ANA_ROOT / "dev_artifacts" / "scripts" / "ana_binary_map.py"


def _load_binary_map_module():
    spec = importlib.util.spec_from_file_location("ana_binary_map_runtime", BINARY_MAP_SCRIPT)
    if not spec or not spec.loader:
        raise RuntimeError(f"Binary map script not found: {BINARY_MAP_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class BinaryMapTool(Tool):
    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="binary_map",
            description=(
                "Static-only binary analyzer for PE/ELF files. Extracts metadata, "
                "architecture, sections, imports, exports, and printable strings without executing the file."
            ),
            parameters=[
                ToolParameter("path", "Binary path inside ANA workspace", "string", True),
                ToolParameter("max_bytes", "Maximum file size to analyze", "integer", False, 26214400),
                ToolParameter("strings_limit", "Maximum printable strings", "integer", False, 80),
            ],
            category="diagnostics",
        )

    def execute(self, **kwargs: Any) -> ToolResult:
        try:
            path = resolve_workspace_path(str(kwargs.get("path") or ""), must_exist=True)
            if is_protected_path(path):
                return ToolResult(status=ToolStatus.BLOCKED, error=f"Refusing protected path: {safe_display_path(path)}")
            if not path.is_file():
                return ToolResult(status=ToolStatus.ERROR, error=f"Not a file: {safe_display_path(path)}")
            max_bytes = max(1, min(int(kwargs.get("max_bytes") or 26_214_400), 100 * 1024 * 1024))
            strings_limit = max(0, min(int(kwargs.get("strings_limit") or 80), 500))
            module = _load_binary_map_module()
            result = module.parse_binary(path, max_bytes=max_bytes, strings_limit=strings_limit)
            data = asdict(result) if is_dataclass(result) else dict(result)
            data["path"] = safe_display_path(path)
            data["lab_mode"] = True
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data=data,
                message=f"Static binary map: {data.get('format')} {data.get('architecture')}",
            )
        except Exception as exc:
            return ToolResult(status=ToolStatus.ERROR, error=f"binary_map failed: {exc}")
