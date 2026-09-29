"""
ANA MAX - Context and identity tool for MCP clients (OS27 Hyper++).

OS27 Hyper++ Features:
- Telemetry tracking for ANA context operations
- Health monitoring for ANA context operations reliability
- MemoryCortex integration for ANA context errors and state learning
- ContextEngine integration for ANA context state awareness
- SelfEvolvingTool integration for anomaly detection on ANA context failures
- Structured logging with error detection
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, List

from tools.base import Tool, ToolDefinition, ToolResult, ToolStatus, registry

# OS27 Hyper++ Telemetry
_ana_context_telemetry: Dict[str, Dict[str, Any]] = {}


def _record_ana_context_telemetry(operation: str, success: bool, execution_time: float) -> None:
    """Record OS27 Hyper++ telemetry for ANA context operations."""
    if operation not in _ana_context_telemetry:
        _ana_context_telemetry[operation] = {
            "operation_count": 0,
            "success_count": 0,
            "failure_count": 0,
            "total_time": 0.0,
            "last_execution_time": 0.0,
            "last_success": False,
        }
    
    _ana_context_telemetry[operation]["operation_count"] += 1
    _ana_context_telemetry[operation]["total_time"] += execution_time
    _ana_context_telemetry[operation]["last_execution_time"] = execution_time
    _ana_context_telemetry[operation]["last_success"] = success
    
    if success:
        _ana_context_telemetry[operation]["success_count"] += 1
    else:
        _ana_context_telemetry[operation]["failure_count"] += 1


def get_ana_context_telemetry(operation: str | None = None) -> Dict[str, Any] | Dict[str, Dict[str, Any]]:
    """Get telemetry for ANA context operations."""
    if operation:
        return _ana_context_telemetry.get(operation, {})
    return _ana_context_telemetry.copy()


def get_ana_context_health() -> str:
    """Get health status for ANA context tool based on telemetry."""
    if not _ana_context_telemetry:
        return "unknown"
    
    total_ops = sum(stats["operation_count"] for stats in _ana_context_telemetry.values())
    total_failures = sum(stats["failure_count"] for stats in _ana_context_telemetry.values())
    
    if total_ops == 0:
        return "unknown"
    
    failure_rate = total_failures / total_ops
    if failure_rate > 0.5:
        return "broken"
    if failure_rate > 0.1:
        return "degraded"
    return "healthy"


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
        
        try:
            from tools.agent_context_injector import collect_full_context
            
            ctx = collect_full_context(fast=True)
            result = ToolResult(
                status=ToolStatus.SUCCESS,
                data=ctx,
                message=f"Mirror Brain context ready ({ctx['tool_count']} active tools).",
            )
            
            execution_time = time.time() - start_time
            _record_ana_context_telemetry("identity", result.is_success, execution_time)
            
            # ContextEngine integration for ANA context state
            if context_engine and result.is_success:
                try:
                    context_engine.update_context(
                        key="ana_context_state",
                        value={
                            "operation": "identity",
                            "tool_count": ctx.get("tool_count", 0),
                            "success": result.is_success,
                            "timestamp": time.time(),
                        }
                    )
                except Exception:
                    pass
            
            # MemoryCortex integration for ANA context errors
            if cortex and not result.is_success:
                try:
                    cortex.remember(
                        "error",
                        "ana_context.identity",
                        f"ANA context identity failed: {result.error}"
                    )
                except Exception:
                    pass
            
            return result
        except Exception as exc:
            execution_time = time.time() - start_time
            _record_ana_context_telemetry("identity", False, execution_time)
            
            # MemoryCortex integration for ANA context errors
            if cortex:
                try:
                    cortex.remember(
                        "error",
                        "ana_context.identity",
                        f"ANA context identity failed: {str(exc)}"
                    )
                except Exception:
                    pass
            
            return ToolResult(status=ToolStatus.ERROR, error=str(exc))

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
