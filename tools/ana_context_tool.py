"""
ANA MAX - Context and identity tool for MCP clients.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from tools.base import Tool, ToolDefinition, ToolResult, ToolStatus, registry


class AnaContextTool(Tool):
    """Expose ANA identity, strengths, and integration context to MCP clients."""

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="ana_identity",
            description=(
                "Explica cine este ANA, cum lucreaza cu OpenCode, cate tool-uri are active "
                "si care sunt punctele ei forte. Foloseste acest tool cand utilizatorul intreaba "
                "despre identitatea ANA, capabilitati, arhitectura sau istoric."
            ),
            parameters=[],
            category="meta",
        )

    def execute(self, **kwargs: Any) -> ToolResult:
        del kwargs

        project_root = Path(__file__).resolve().parents[1]
        tools = sorted(name for name in registry.list_tools() if name != "ana_identity")
        payload = {
            "name": "A.N.A. MAX",
            "role": "runtime MCP local pentru OpenCode",
            "architecture": (
                "OpenCode este clientul si interfata de conversatie. "
                "ANA furnizeaza tool-uri, memorie, cautare, debug, browser automation, "
                "audit si capabilitati de lucru pe proiect."
            ),
            "mode": "tools-only",
            "tool_count": len(tools),
            "tool_names": tools,
            "strengths": self._strengths(),
            "proof_points": self._proof_points(project_root),
        }
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data=payload,
            message=f"ANA identity ready ({len(tools)} active tools).",
        )

    def _strengths(self) -> List[str]:
        return [
            "smart_search si codebase_understanding pentru context rapid pe codebase",
            "file_operations cu diff_preview si surgical_edit pentru modificari sigure",
            "browser_control cu debug_feedback pentru frontend si web debugging",
            "ana_memory, conversation_learning si session_log_miner pentru memorie persistenta",
            "debugger, qa_testing si security_audit pentru verificare si triere rapida",
            "autonomous_engine pentru workflow Plan -> Execute -> Verify in runtime-ul ANA",
        ]

    def _proof_points(self, project_root: Path) -> Dict[str, str]:
        return {
            "capabilities_doc": str(project_root / "docs" / "ANA_CAPABILITIES.md"),
            "opencode_integration_doc": str(project_root / "integrations" / "opencode" / "README.md"),
            "worklog": str(project_root / "docs" / "WORKLOG_2026-03-26.md"),
            "archive_strengths": str(project_root.parent / "md" / "archive" / "COMPETITIVE_ADVANTAGE.md"),
        }
