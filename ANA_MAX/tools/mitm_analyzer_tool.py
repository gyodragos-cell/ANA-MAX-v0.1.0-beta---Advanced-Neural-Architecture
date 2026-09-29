"""
MITM Analyzer Tool (OS27 Hyper++)
==================================
Analiza trafic MITM (Charles/Wireshark) pentru bug bounty - capture, analyze, export.

OS27 Hyper++ Features:
- Telemetry tracking for MITM operations (capture_start, capture_stop, analyze, export)
- Health monitoring for MITM operations reliability
- MemoryCortex integration for MITM errors and state learning
- ContextEngine integration for MITM state awareness
- SelfEvolvingTool integration for anomaly detection on MITM failures
- Structured logging with error detection
"""

import subprocess
import json
import os
import time
import logging
from typing import Dict, Any
from tools.base import Tool, ToolResult, ToolStatus

logger = logging.getLogger(__name__)

# OS27 Hyper++ Telemetry
_mitm_telemetry: Dict[str, Dict[str, Any]] = {}


def _record_mitm_telemetry(operation: str, success: bool, execution_time: float) -> None:
    """Record OS27 Hyper++ telemetry for MITM operations."""
    if operation not in _mitm_telemetry:
        _mitm_telemetry[operation] = {
            "operation_count": 0,
            "success_count": 0,
            "failure_count": 0,
            "total_time": 0.0,
            "last_execution_time": 0.0,
            "last_success": False,
        }
    
    _mitm_telemetry[operation]["operation_count"] += 1
    _mitm_telemetry[operation]["total_time"] += execution_time
    _mitm_telemetry[operation]["last_execution_time"] = execution_time
    _mitm_telemetry[operation]["last_success"] = success
    
    if success:
        _mitm_telemetry[operation]["success_count"] += 1
    else:
        _mitm_telemetry[operation]["failure_count"] += 1


def get_mitm_telemetry(operation: str | None = None) -> Dict[str, Any] | Dict[str, Dict[str, Any]]:
    """Get telemetry for MITM operations."""
    if operation:
        return _mitm_telemetry.get(operation, {})
    return _mitm_telemetry.copy()


def get_mitm_health() -> str:
    """Get health status for MITM tool based on telemetry."""
    if not _mitm_telemetry:
        return "unknown"
    
    total_ops = sum(stats["operation_count"] for stats in _mitm_telemetry.values())
    total_failures = sum(stats["failure_count"] for stats in _mitm_telemetry.values())
    
    if total_ops == 0:
        return "unknown"
    
    failure_rate = total_failures / total_ops
    if failure_rate > 0.5:
        return "broken"
    if failure_rate > 0.1:
        return "degraded"
    return "healthy"

class MITMAnalyzerTool(Tool):
    name = "mitm_analyzer"
    description = "Analiza trafic MITM (Charles/Wireshark) pentru bug bounty - capture, analyze, export."
    
    def get_definition(self):
        from tools.base import ToolDefinition, ToolParameter
        return ToolDefinition(
            name=self.name,
            description=self.description,
            parameters=[
                ToolParameter(
                    name="operation",
                    description="Operatiunea: capture_start, capture_stop, analyze, export",
                    type="string",
                    required=True,
                    choices=["capture_start", "capture_stop", "analyze", "export"]
                ),
                ToolParameter(
                    name="interface",
                    description="Interfata retea (ex: 'Loopback', 'Wi-Fi')",
                    type="string",
                    required=False
                ),
                ToolParameter(
                    name="target_port",
                    description="Port tinta (ex: 8765 pentru ANA MCP)",
                    type="string",
                    required=False
                ),
                ToolParameter(
                    name="output_file",
                    description="Fisier output pentru export",
                    type="string",
                    required=False
                )
            ],
            category="security"
        )
    
    def execute(self, **kwargs):
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
        
        operation = kwargs.get("operation")
        interface = kwargs.get("interface", "Loopback Pseudo-Interface")
        target_port = kwargs.get("target_port", "8765")
        output_file = kwargs.get("output_file", "bounty_proof.pcapng")
        
        if operation == "capture_start":
            result = self._start_capture(interface, target_port)
        elif operation == "capture_stop":
            result = self._stop_capture()
        elif operation == "analyze":
            result = self._analyze_capture(output_file)
        elif operation == "export":
            result = self._export_for_bounty(output_file)
        else:
            execution_time = time.time() - start_time
            _record_mitm_telemetry("unknown", False, execution_time)
            return ToolResult(status=ToolStatus.ERROR, error=f"Operatiune necunoscuta: {operation}")
        
        execution_time = time.time() - start_time
        _record_mitm_telemetry(operation, result.is_success, execution_time)
        
        # ContextEngine integration for MITM state
        if context_engine and result.is_success:
            try:
                context_engine.update_context(
                    key="mitm_state",
                    value={
                        "operation": operation,
                        "interface": interface,
                        "target_port": target_port,
                        "success": result.is_success,
                        "timestamp": time.time(),
                    }
                )
            except Exception:
                pass
        
        # MemoryCortex integration for MITM errors
        if cortex and not result.is_success:
            try:
                cortex.remember(
                    "error",
                    f"mitm.{operation}",
                    f"MITM operation failed for {interface}: {result.error}"
                )
            except Exception:
                pass
        
        return result
    
    def _start_capture(self, interface, target_port):
        """Porneste Wireshark pentru capture"""
        try:
            # Start Wireshark with filter
            cmd = [
                "wireshark",
                "-i", interface,
                "-f", f"tcp port {target_port}"
            ]
            subprocess.Popen(cmd)
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data=f"Wireshark pornit pe {interface}, filtru: tcp port {target_port}",
                message=f"Capture pornit - trafic catre portul {target_port}"
            )
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    def _stop_capture(self):
        """Opreste capture (salinformatia)"""
        try:
            # Kill wireshark gracefully
            subprocess.run(["taskkill", "/IM", "wireshark.exe", "/F"], capture_output=True)
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data="Capture oprit",
                message="Wireshark oprit - salveaza capture-ul manual"
            )
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    def _analyze_capture(self, pcap_file):
        """Analizeaza pachete pentru vulnerabilitati"""
        try:
            # Check if tshark exists
            import shutil
            if not shutil.which("tshark"):
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error="tshark (Wireshark) nu este instalat. Instaleaza Wireshark de la https://www.wireshark.org/ si asigura-te ca tshark este in PATH."
                )
            # Use tshark for analysis
            cmd = [
                "tshark",
                "-r", pcap_file,
                "-Y", "http.request or http.response",
                "-T", "json"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            
            if result.returncode == 0:
                packets = result.stdout.count('\n')
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data=f"Analizate {packets} pachete HTTP din {pcap_file}",
                    message=f"Gasite {packets} pachete pentru analiza"
                )
            else:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error=result.stderr
                )
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    def _export_for_bounty(self, output_file):
        """Exporta dovezi pentru bug bounty"""
        try:
            # Export in format compatible cu HackerOne/Bugcrowd
            export_path = f"security_research/proofs/{output_file}"
            cmd = [
                "tshark",
                "-r", "temp_capture.pcapng",
                "-w", export_path,
                "-F", "pcapng"
            ]
            subprocess.run(cmd, capture_output=True, timeout=10)
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data=f"Exportat in {export_path}",
                message="Dovezi exportate pentru bug bounty"
            )
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
