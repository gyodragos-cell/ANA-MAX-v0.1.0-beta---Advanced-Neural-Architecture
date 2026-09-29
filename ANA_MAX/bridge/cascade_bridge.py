#!/usr/bin/env python3
"""
ANA MAX Hybrid Bridge for Cascade
==================================
Hybrid integration between ANA MAX and Cascade with:
- Direct Python access for high-priority tools (no MCP overhead)
- MCP fallback for all tools (backup, IDE integration)
- Qoder, local LLM, and Antigravity integration support
- Performance benchmarking and routing optimization

High-Priority Direct Tools:
- Code/File/Dev: code_search, edit, file_operations
- Memory/Session: ana_memory, conversation_learning, vector_memory
- Runtime/Process: system_control, watchdog, debugger_tool
- Agent Core: agent_coach, ana_orchestrator, autonomous_engine

Usage:
    python cascade_bridge.py --health-check
    python cascade_bridge.py --smoke-test
    python cascade_bridge.py --benchmark
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import httpx

# Add paths
ANA_ROOT = Path(__file__).resolve().parent.parent
ANA_OS_V2_ROOT = ANA_ROOT / "ana"
ANA_MAX_ROOT = ANA_ROOT / "ANA_MAX"

sys.path.insert(0, str(ANA_ROOT))
sys.path.insert(0, str(ANA_MAX_ROOT))

# Imports after path setup (intentional for dynamic path resolution)
from ana.config.loader import ConfigLoader  # noqa: E402
from ana.core.orchestrator.orchestrator import ANAMaxOS  # noqa: E402
from ana.tools.registry.registry import ToolRegistry  # noqa: E402
from ana.services.llm.service import RealLLMService  # noqa: E402

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RoutingMode(Enum):
    """Routing mode for tool execution."""
    DIRECT = "direct"  # Direct Python access (high-priority tools)
    MCP = "mcp"  # MCP server fallback
    AUTO = "auto"  # Automatic routing based on tool priority


@dataclass
class ToolPriority:
    """Tool priority configuration."""
    name: str
    priority: str  # "high", "medium", "low"
    category: str
    direct_access: bool = False
    mcp_fallback: bool = True


@dataclass
class ExecutionMetrics:
    """Metrics for tool execution."""
    tool_name: str
    mode: RoutingMode
    latency_ms: float
    success: bool
    timestamp: float
    error: Optional[str] = None


HIGH_PRIORITY_TOOLS = [
    "code_search",
    "edit",
    "file_operations",
    "terminal",  # git/shell ops (no separate git_operations tool)
    "tool_router",
    "ana_memory",
    "conversation_learning",
    "vector_memory",
    "system_control",
    "agent_coach",
    "ana_orchestrator",
    "autonomous_tool",
    "debugger_tool",
    "error_radar",
]

MEDIUM_PRIORITY_TOOLS = [
    "browser_control",
    "ocr_tool",
    "uia_click",
    "uia_type",
    "desktop_control",
    "security_tool",
    "adb_tool",
    "advanced_scanner",
    "web_search",
    "web_scraper",
    "text_to_speech",
]

LOW_PRIORITY_TOOLS = [
    "qa_tool",
    "smoke_test_runner",
    "dashboard",
    "lab",
    "license_manager",
]


class CascadeBridge:
    """Hybrid bridge between ANA MAX and Cascade with direct + MCP routing."""

    def __init__(
        self,
        *,
        llm_provider: str = "ollama",
        llm_model: str | None = None,
        llm_base_url: str | None = None,
        llm_api_key: str | None = None,
        mcp_host: str = "127.0.0.1",
        mcp_port: int = 8766,
        routing_mode: RoutingMode = RoutingMode.AUTO,
        enable_qoder: bool = True,
        enable_antigravity: bool = True,
    ) -> None:
        """Initialize the Cascade hybrid bridge."""
        self.ana_root = ANA_ROOT
        self.ana_os_v2_root = ANA_OS_V2_ROOT
        self.ana_max_root = ANA_MAX_ROOT
        self.routing_mode = routing_mode
        self.mcp_host = mcp_host
        self.mcp_port = mcp_port
        self.enable_qoder = enable_qoder
        self.enable_antigravity = enable_antigravity
        
        # Performance metrics
        self.metrics: List[ExecutionMetrics] = []
        self.tool_priorities: Dict[str, ToolPriority] = {}
        
        # Load OS v2 config
        config_loader = ConfigLoader()
        self.config = config_loader.from_mapping({
            "mode": "dev",
            "services": ["fs", "http", "shell", "llm"],
            "event_bus": {"replay_limit": 100},
            "fallback": {"max_attempts": 3},
            "sandbox": {"max_input_keys": 32, "allow_external_effects": False},
            "logging": {"level": "info"},
            "skills": {
                "self.repair": {"skill": "self-repair", "capability": "self.repair", "version": "1.0.0", "enabled": True},
                "health.check": {"skill": "health-check", "capability": "health.check", "version": "1.0.0", "enabled": True},
                "fs.inspect": {"skill": "fs-inspect", "capability": "fs.inspect", "version": "1.0.0", "enabled": True},
            },
        })

        # Initialize tool registry
        self.registry = ToolRegistry()

        # Initialize LLM service
        self.llm_service = RealLLMService(
            provider=llm_provider,
            base_url=llm_base_url,
            model=llm_model,
            api_key=llm_api_key,
        )

        # Initialize OS v2 runtime
        self.os_v2 = ANAMaxOS(config=self.config, registry=self.registry)

        # Load ANA MAX tools into registry
        self._load_ana_max_tools()
        
        # Initialize tool priorities
        self._initialize_tool_priorities()
        
        # MCP client (lazy initialization)
        self._mcp_client: Optional[httpx.AsyncClient] = None
        
        # Qoder integration (lazy initialization)
        self._qoder_client: Optional[Any] = None
        
        # Antigravity integration (lazy initialization)
        self._antigravity_client: Optional[Any] = None

    def _initialize_tool_priorities(self) -> None:
        """Initialize tool priority mapping."""
        for tool in HIGH_PRIORITY_TOOLS:
            self.tool_priorities[tool] = ToolPriority(
                name=tool,
                priority="high",
                category="core",
                direct_access=True,
                mcp_fallback=True
            )
        
        for tool in MEDIUM_PRIORITY_TOOLS:
            self.tool_priorities[tool] = ToolPriority(
                name=tool,
                priority="medium",
                category="extended",
                direct_access=False,
                mcp_fallback=True
            )
        
        for tool in LOW_PRIORITY_TOOLS:
            self.tool_priorities[tool] = ToolPriority(
                name=tool,
                priority="low",
                category="lab",
                direct_access=False,
                mcp_fallback=True
            )
    
    def _load_ana_max_tools(self) -> None:
        """Load ANA MAX tools into the registry."""
        try:
            sys.path.insert(0, str(self.ana_max_root))
            from mcp_stdio import load_tools
            from tools.base import registry as ana_max_registry

            loaded = load_tools()
            tool_names = ana_max_registry.list_tools()
            logger.info(f"[Cascade Bridge] Registered {loaded} ANA MAX tools")

            from ana.tools.registry.registry import ToolSpec

            for tool_name in tool_names:
                tool = ana_max_registry.get(tool_name)
                if tool:
                    definition = tool.get_definition()
                    self.registry.register(
                        ToolSpec(
                            name=definition.name,
                            capability=f"ana_max.{definition.name}",
                            handler=lambda payload, t=tool: self._wrap_ana_max_tool(t, payload),
                            priority=100,
                        )
                    )
                    # Initialize priority for tools not in predefined lists
                    if tool_name not in self.tool_priorities:
                        self.tool_priorities[tool_name] = ToolPriority(
                            name=tool_name,
                            priority="medium",
                            category="unknown",
                            direct_access=False,
                            mcp_fallback=True
                        )

            logger.info(f"[Cascade Bridge] Loaded {len(tool_names)} ANA MAX tools")
        except Exception as exc:
            logger.warning(f"[Cascade Bridge] Warning: Failed to load ANA MAX tools: {exc}")

    def _wrap_ana_max_tool(self, tool, payload: dict[str, Any]) -> dict[str, Any]:
        """Wrap ANA MAX tool execution."""
        try:
            result = tool.execute(**payload)
            return {
                "success": result.is_success,
                "data": result.data,
                "message": result.message,
                "error": result.error,
            }
        except Exception as exc:
            return {
                "success": False,
                "data": None,
                "message": str(exc),
                "error": str(exc),
            }

    def _get_routing_mode(self, tool_name: str) -> RoutingMode:
        """Determine routing mode for a tool."""
        if self.routing_mode == RoutingMode.DIRECT:
            return RoutingMode.DIRECT
        if self.routing_mode == RoutingMode.MCP:
            return RoutingMode.MCP
        
        # AUTO mode: decide based on tool priority
        priority = self.tool_priorities.get(tool_name)
        if priority and priority.direct_access:
            return RoutingMode.DIRECT
        return RoutingMode.MCP
    
    async def _execute_via_mcp(self, tool_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tool via MCP server fallback."""
        if self._mcp_client is None:
            self._mcp_client = httpx.AsyncClient(timeout=30.0)
        
        try:
            response = await self._mcp_client.post(
                f"http://{self.mcp_host}:{self.mcp_port}/execute",
                json={"name": tool_name, "args": payload},
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            logger.error(f"[Cascade Bridge] MCP execution failed for {tool_name}: {exc}")
            return {
                "success": False,
                "error": f"MCP fallback failed: {exc}",
                "mode": "mcp"
            }
    
    async def execute_tool(
        self,
        tool_name: str,
        payload: Dict[str, Any] | None = None,
        *,
        trace_id: str = "cascade-trace",
        force_mode: Optional[RoutingMode] = None,
    ) -> Dict[str, Any]:
        """Execute a tool with hybrid routing (direct or MCP fallback)."""
        payload = payload or {}
        mode = force_mode or self._get_routing_mode(tool_name)
        start_time = time.time()
        
        logger.info(f"[Cascade Bridge] Executing {tool_name} via {mode.value}")
        
        try:
            if mode == RoutingMode.DIRECT:
                result = await self._execute_direct(tool_name, payload, trace_id)
            else:
                result = await self._execute_via_mcp(tool_name, payload)
            
            latency_ms = (time.time() - start_time) * 1000
            success = result.get("success", result.get("ok", False))
            
            # Record metrics
            self.metrics.append(ExecutionMetrics(
                tool_name=tool_name,
                mode=mode,
                latency_ms=latency_ms,
                success=success,
                timestamp=time.time(),
                error=result.get("error")
            ))
            
            # If direct failed and mode is AUTO, try MCP fallback
            if not success and mode == RoutingMode.DIRECT and self.routing_mode == RoutingMode.AUTO:
                logger.warning(f"[Cascade Bridge] Direct execution failed, trying MCP fallback")
                result = await self._execute_via_mcp(tool_name, payload)
                latency_ms = (time.time() - start_time) * 1000
                self.metrics.append(ExecutionMetrics(
                    tool_name=tool_name,
                    mode=RoutingMode.MCP,
                    latency_ms=latency_ms,
                    success=result.get("success", False),
                    timestamp=time.time(),
                    error=result.get("error")
                ))
            
            return result
            
        except Exception as exc:
            logger.error(f"[Cascade Bridge] Tool execution failed: {exc}")
            return {
                "success": False,
                "error": str(exc),
                "mode": mode.value
            }
    
    async def _execute_direct(self, tool_name: str, payload: Dict[str, Any], trace_id: str) -> Dict[str, Any]:
        """Execute tool via direct Python access (registry first, then OS v2)."""
        from tools.base import registry as ana_max_registry

        # 1. Fast path: ANA MAX tool registry (no orchestrator overhead)
        tool = ana_max_registry.get(tool_name)
        if tool:
            try:
                tool_result = tool.safe_execute(**payload)
                return {
                    "success": tool_result.is_success,
                    "data": tool_result.data,
                    "message": tool_result.message,
                    "error": tool_result.error,
                    "mode": "direct",
                }
            except Exception as exc:
                logger.error(f"[Cascade Bridge] Registry execution failed for {tool_name}: {exc}")

        # 2. OS v2 capability path (ana_max.* prefix or raw name)
        for capability in (f"ana_max.{tool_name}", tool_name):
            try:
                response = self.os_v2.execute(capability, payload, trace_id=trace_id)
                if response.ok:
                    result = response.to_dict()
                    result["success"] = True
                    result["mode"] = "direct"
                    return result
            except Exception:
                continue

        return {
            "success": False,
            "error": f"Tool '{tool_name}' not found in registry or OS v2",
            "mode": "direct",
        }
    
    def execute_capability(
        self,
        capability: str,
        payload: dict[str, Any] | None = None,
        *,
        trace_id: str = "cascade-trace",
    ) -> dict[str, Any]:
        """Execute a capability through ANA OS v2 (synchronous wrapper)."""
        response = self.os_v2.execute(capability, payload or {}, trace_id=trace_id)
        return response.to_dict()

    def complete_llm(
        self,
        prompt: str | None = None,
        messages: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Complete using the LLM service."""
        payload: dict[str, Any] = {}
        if prompt:
            payload["prompt"] = prompt
        if messages:
            payload["messages"] = messages

        try:
            return self.llm_service.complete(payload)
        except Exception as exc:
            return {
                "text": "",
                "error": str(exc),
                "provider": self.llm_service.provider,
            }

    def list_capabilities(self) -> list[str]:
        """List all available capabilities."""
        return self.os_v2.registry.all_capabilities()

    def health_check(self) -> dict[str, Any]:
        """Perform a comprehensive health check."""
        return {
            "os_v2": {
                "capabilities": self.os_v2.registry.capabilities(),
                "fallback_capabilities": self.os_v2.registry.fallback_capabilities(),
            },
            "llm": {
                "provider": self.llm_service.provider,
                "model": self.llm_service.model,
                "base_url": self.llm_service.base_url,
            },
            "bridge": {
                "type": "hybrid",
                "routing_mode": self.routing_mode.value,
                "mcp_enabled": True,
                "mcp_endpoint": f"http://{self.mcp_host}:{self.mcp_port}",
                "total_capabilities": len(self.list_capabilities()),
                "high_priority_tools": len(HIGH_PRIORITY_TOOLS),
                "medium_priority_tools": len(MEDIUM_PRIORITY_TOOLS),
                "low_priority_tools": len(LOW_PRIORITY_TOOLS),
            },
            "integrations": {
                "qoder_enabled": self.enable_qoder,
                "antigravity_enabled": self.enable_antigravity,
            },
            "metrics": {
                "total_executions": len(self.metrics),
                "success_rate": self._calculate_success_rate(),
                "avg_latency_ms": self._calculate_avg_latency(),
            },
        }
    
    def _calculate_success_rate(self) -> float:
        """Calculate overall success rate from metrics."""
        if not self.metrics:
            return 0.0
        successful = sum(1 for m in self.metrics if m.success)
        return (successful / len(self.metrics)) * 100
    
    def _calculate_avg_latency(self) -> float:
        """Calculate average latency from metrics."""
        if not self.metrics:
            return 0.0
        total_latency = sum(m.latency_ms for m in self.metrics)
        return total_latency / len(self.metrics)
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Generate detailed performance report."""
        direct_metrics = [m for m in self.metrics if m.mode == RoutingMode.DIRECT]
        mcp_metrics = [m for m in self.metrics if m.mode == RoutingMode.MCP]
        
        return {
            "summary": {
                "total_executions": len(self.metrics),
                "direct_executions": len(direct_metrics),
                "mcp_executions": len(mcp_metrics),
                "overall_success_rate": self._calculate_success_rate(),
            },
            "direct_performance": {
                "count": len(direct_metrics),
                "success_rate": (sum(1 for m in direct_metrics if m.success) / len(direct_metrics) * 100) if direct_metrics else 0,
                "avg_latency_ms": sum(m.latency_ms for m in direct_metrics) / len(direct_metrics) if direct_metrics else 0,
            },
            "mcp_performance": {
                "count": len(mcp_metrics),
                "success_rate": (sum(1 for m in mcp_metrics if m.success) / len(mcp_metrics) * 100) if mcp_metrics else 0,
                "avg_latency_ms": sum(m.latency_ms for m in mcp_metrics) / len(mcp_metrics) if mcp_metrics else 0,
            },
            "tool_breakdown": self._get_tool_breakdown(),
        }
    
    def _get_tool_breakdown(self) -> Dict[str, Any]:
        """Get performance breakdown by tool."""
        tool_stats: Dict[str, Dict[str, Any]] = {}
        
        for metric in self.metrics:
            if metric.tool_name not in tool_stats:
                tool_stats[metric.tool_name] = {
                    "count": 0,
                    "success_count": 0,
                    "total_latency": 0.0,
                    "modes": set(),
                }
            
            stats = tool_stats[metric.tool_name]
            stats["count"] += 1
            if metric.success:
                stats["success_count"] += 1
            stats["total_latency"] += metric.latency_ms
            stats["modes"].add(metric.mode.value)
        
        # Convert to final format
        return {
            tool_name: {
                "count": stats["count"],
                "success_rate": (stats["success_count"] / stats["count"] * 100) if stats["count"] > 0 else 0,
                "avg_latency_ms": stats["total_latency"] / stats["count"] if stats["count"] > 0 else 0,
                "modes_used": list(stats["modes"]),
                "priority": self.tool_priorities.get(tool_name, ToolPriority(tool_name, "medium", "unknown")).priority,
            }
            for tool_name, stats in tool_stats.items()
        }

    async def close(self) -> None:
        """Clean up resources."""
        self.llm_service.close()
        if self._mcp_client:
            await self._mcp_client.aclose()
    
    async def smoke_test(self) -> Dict[str, Any]:
        """Run comprehensive smoke test on high-priority tools."""
        logger.info("[Cascade Bridge] Starting smoke test...")
        results = {}
        
        # Test a subset of high-priority tools
        test_tools = [
            ("file_operations", {"operation": "list", "path": "."}),
            ("system_control", {"action": "status"}),
            ("agent_coach", {"action": "recommend", "task": "test", "limit": 5}),
        ]
        
        for tool_name, payload in test_tools:
            try:
                result = await self.execute_tool(tool_name, payload)
                results[tool_name] = {
                    "success": result.get("success", False),
                    "mode": result.get("mode", "unknown"),
                    "latency_ms": self.metrics[-1].latency_ms if self.metrics else 0,
                }
                logger.info(f"[Cascade Bridge] {tool_name}: {results[tool_name]}")
            except Exception as exc:
                results[tool_name] = {
                    "success": False,
                    "error": str(exc),
                }
                logger.error(f"[Cascade Bridge] {tool_name} failed: {exc}")
        
        summary = {
            "total_tests": len(test_tools),
            "passed": sum(1 for r in results.values() if r.get("success")),
            "failed": sum(1 for r in results.values() if not r.get("success")),
            "results": results,
        }
        
        logger.info(f"[Cascade Bridge] Smoke test complete: {summary['passed']}/{summary['total_tests']} passed")
        return summary
    
    async def benchmark(self, iterations: int = 5) -> Dict[str, Any]:
        """Benchmark direct vs MCP performance for high-priority tools."""
        logger.info(f"[Cascade Bridge] Starting benchmark with {iterations} iterations...")
        
        # Clear previous metrics
        self.metrics = []
        
        benchmark_tools = [
            ("file_operations", {"operation": "list", "path": "."}),
            ("system_control", {"action": "status"}),
        ]
        
        results = {}
        
        for tool_name, payload in benchmark_tools:
            # Benchmark direct mode
            direct_times = []
            for _ in range(iterations):
                result = await self.execute_tool(tool_name, payload, force_mode=RoutingMode.DIRECT)
                if self.metrics:
                    direct_times.append(self.metrics[-1].latency_ms)
            
            # Benchmark MCP mode
            mcp_times = []
            for _ in range(iterations):
                result = await self.execute_tool(tool_name, payload, force_mode=RoutingMode.MCP)
                if self.metrics:
                    mcp_times.append(self.metrics[-1].latency_ms)
            
            results[tool_name] = {
                "direct": {
                    "avg_latency_ms": sum(direct_times) / len(direct_times) if direct_times else 0,
                    "min_latency_ms": min(direct_times) if direct_times else 0,
                    "max_latency_ms": max(direct_times) if direct_times else 0,
                },
                "mcp": {
                    "avg_latency_ms": sum(mcp_times) / len(mcp_times) if mcp_times else 0,
                    "min_latency_ms": min(mcp_times) if mcp_times else 0,
                    "max_latency_ms": max(mcp_times) if mcp_times else 0,
                },
                "speedup": (sum(mcp_times) / len(mcp_times) / sum(direct_times) / len(direct_times)) if direct_times and mcp_times else 0,
            }
        
        logger.info(f"[Cascade Bridge] Benchmark complete")
        return results


def main() -> int:
    """Main entry point for Cascade hybrid bridge."""
    import argparse
    import asyncio

    parser = argparse.ArgumentParser(description="ANA MAX Hybrid Bridge for Cascade")
    parser.add_argument("--llm-provider", default="ollama", help="LLM provider")
    parser.add_argument("--llm-model", help="LLM model name")
    parser.add_argument("--llm-base-url", help="LLM base URL")
    parser.add_argument("--llm-api-key", help="LLM API key")
    parser.add_argument("--mcp-host", default="127.0.0.1", help="MCP server host")
    parser.add_argument("--mcp-port", type=int, default=8766, help="MCP server port")
    parser.add_argument("--routing-mode", choices=["direct", "mcp", "auto"], default="auto", help="Tool routing mode")
    parser.add_argument("--health-check", action="store_true", help="Run health check")
    parser.add_argument("--list-capabilities", action="store_true", help="List capabilities")
    parser.add_argument("--smoke-test", action="store_true", help="Run smoke test")
    parser.add_argument("--benchmark", action="store_true", help="Run performance benchmark")
    parser.add_argument("--performance-report", action="store_true", help="Show performance report")

    args = parser.parse_args()

    async def run():
        bridge = CascadeBridge(
            llm_provider=args.llm_provider,
            llm_model=args.llm_model,
            llm_base_url=args.llm_base_url,
            llm_api_key=args.llm_api_key,
            mcp_host=args.mcp_host,
            mcp_port=args.mcp_port,
            routing_mode=RoutingMode(args.routing_mode),
        )

        try:
            if args.health_check:
                health = bridge.health_check()
                print(json.dumps(health, indent=2))
                return 0

            if args.list_capabilities:
                capabilities = bridge.list_capabilities()
                print(json.dumps(capabilities, indent=2))
                return 0

            if args.smoke_test:
                results = await bridge.smoke_test()
                print(json.dumps(results, indent=2))
                return 0
            
            if args.benchmark:
                results = await bridge.benchmark(iterations=5)
                print(json.dumps(results, indent=2))
                return 0
            
            if args.performance_report:
                report = bridge.get_performance_report()
                print(json.dumps(report, indent=2))
                return 0

            print("[Cascade Bridge] Hybrid integration ready")
            print(f"[Cascade Bridge] LLM: {bridge.llm_service.provider} @ {bridge.llm_service.base_url}")
            print(f"[Cascade Bridge] MCP: http://{args.mcp_host}:{args.mcp_port}")
            print(f"[Cascade Bridge] Routing: {args.routing_mode}")
            print(f"[Cascade Bridge] Capabilities: {len(bridge.list_capabilities())}")
            print(f"[Cascade Bridge] High-priority tools: {len(HIGH_PRIORITY_TOOLS)}")
            print("[Cascade Bridge] Use --health-check, --smoke-test, or --benchmark for more info")

            return 0
        finally:
            await bridge.close()

    return asyncio.run(run())


if __name__ == "__main__":
    raise SystemExit(main())
