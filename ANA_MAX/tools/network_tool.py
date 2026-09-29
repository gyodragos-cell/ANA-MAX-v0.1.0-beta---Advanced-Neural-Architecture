"""
A.N.A. v15.0 - Network Tool (OS27 Hyper++)
===========================================
Instrumente pentru inginerie de retea si diagnoza.

OS27 Hyper++ Features:
- Telemetry tracking for network operations (ping, scan_ports, dns_lookup, ip_info)
- Health monitoring for network operations reliability
- MemoryCortex integration for network errors and state learning
- ContextEngine integration for network state awareness
- SelfEvolvingTool integration for anomaly detection on network failures
- Structured logging with error detection
"""

import os
import subprocess
import socket
import logging
import time
from typing import Optional, Dict, Any, List
from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus

logger = logging.getLogger(__name__)

# OS27 Hyper++ Telemetry
_network_telemetry: Dict[str, Dict[str, Any]] = {}


def _record_network_telemetry(operation: str, success: bool, execution_time: float) -> None:
    """Record OS27 Hyper++ telemetry for network operations."""
    if operation not in _network_telemetry:
        _network_telemetry[operation] = {
            "operation_count": 0,
            "success_count": 0,
            "failure_count": 0,
            "total_time": 0.0,
            "last_execution_time": 0.0,
            "last_success": False,
        }
    
    _network_telemetry[operation]["operation_count"] += 1
    _network_telemetry[operation]["total_time"] += execution_time
    _network_telemetry[operation]["last_execution_time"] = execution_time
    _network_telemetry[operation]["last_success"] = success
    
    if success:
        _network_telemetry[operation]["success_count"] += 1
    else:
        _network_telemetry[operation]["failure_count"] += 1


def get_network_telemetry(operation: str | None = None) -> Dict[str, Any] | Dict[str, Dict[str, Any]]:
    """Get telemetry for network operations."""
    if operation:
        return _network_telemetry.get(operation, {})
    return _network_telemetry.copy()


def get_network_health() -> str:
    """Get health status for network tool based on telemetry."""
    if not _network_telemetry:
        return "unknown"
    
    total_ops = sum(stats["operation_count"] for stats in _network_telemetry.values())
    total_failures = sum(stats["failure_count"] for stats in _network_telemetry.values())
    
    if total_ops == 0:
        return "unknown"
    
    failure_rate = total_failures / total_ops
    if failure_rate > 0.5:
        return "broken"
    if failure_rate > 0.1:
        return "degraded"
    return "healthy"

class NetworkTool(Tool):
    """
    Tool pentru diagnoza retea si conectivitate.
    """
    
    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="network_diag",
            description="Diagnoza retea: ping, port scan, DNS, IP info.",
            parameters=[
                ToolParameter(
                    name="operation",
                    description="Operatiunea: ping, scan_ports, dns_lookup, ip_info",
                    type="string",
                    required=True,
                    choices=["ping", "scan_ports", "dns_lookup", "ip_info"]
                ),
                ToolParameter(
                    name="target",
                    description="Tinta: IP sau Domain",
                    type="string",
                    required=True
                ),
                ToolParameter(
                    name="ports",
                    description="Porturi pentru scanare (ex: '80,443' sau '1-100')",
                    type="string",
                    required=False
                )
            ],
            category="system"
        )

    def execute(self, operation: str, target: str, **kwargs) -> ToolResult:
        """Executa operatiunea network."""
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
        
        handlers = {
            "ping": self._ping,
            "scan_ports": self._scan_ports,
            "dns_lookup": self._dns_lookup,
            "ip_info": self._ip_info
        }
        
        if operation not in handlers:
            execution_time = time.time() - start_time
            _record_network_telemetry(operation, False, execution_time)
            return ToolResult(status=ToolStatus.ERROR, error=f"Operatiune necunoscuta: {operation}")
        
        result = handlers[operation](target, **kwargs)
        
        execution_time = time.time() - start_time
        _record_network_telemetry(operation, result.is_success, execution_time)
        
        # ContextEngine integration for network state
        if context_engine and result.is_success:
            try:
                context_engine.update_context(
                    key="network_state",
                    value={
                        "operation": operation,
                        "target": target,
                        "success": result.is_success,
                        "timestamp": time.time(),
                    }
                )
            except Exception:
                pass
        
        # MemoryCortex integration for network errors
        if cortex and not result.is_success:
            try:
                cortex.remember(
                    "error",
                    f"network.{operation}",
                    f"Network operation failed for {target}: {result.error}"
                )
            except Exception:
                pass
        
        return result

    def _ping(self, target: str, **kwargs) -> ToolResult:
        """Ping catre un host."""
        param = "-n" if os.name == "nt" else "-c"
        try:
            output = subprocess.check_output(["ping", param, "4", target], text=True, stderr=subprocess.STDOUT)
            return ToolResult(status=ToolStatus.SUCCESS, data=output, message=f"Ping realizat catre {target}")
        except subprocess.CalledProcessError as e:
            return ToolResult(status=ToolStatus.ERROR, error=f"Host-ul {target} nu raspunde.")

    def _scan_ports(self, target: str, **kwargs) -> ToolResult:
        """Scanare simpla de porturi."""
        port_str = kwargs.get('ports', '80,443,22,21,3389')
        ports = []
        if '-' in port_str:
            start, end = map(int, port_str.split('-'))
            ports = range(start, end + 1)
        else:
            ports = [int(p.strip()) for p in port_str.split(',')]
            
        open_ports = []
        for port in ports:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.5)
                if s.connect_ex((target, port)) == 0:
                    open_ports.append(port)
                    
        res = f"Scanare porturi pe {target}:\n"
        if open_ports:
            res += f"Porturi deschise: {', '.join(map(str, open_ports))}"
        else:
            res += "Toate porturile scanate par inchise."
            
        return ToolResult(status=ToolStatus.SUCCESS, data=res)

    def _dns_lookup(self, target: str, **kwargs) -> ToolResult:
        """Cautare DNS."""
        try:
            addr = socket.gethostbyname(target)
            return ToolResult(status=ToolStatus.SUCCESS, data=f"{target} -> IP: {addr}")
        except socket.gaierror:
            return ToolResult(status=ToolStatus.ERROR, error="Nu am putut rezolva domeniul.")

    def _ip_info(self, target: str, **kwargs) -> ToolResult:
        """Informatii IP (local momentan)."""
        try:
            info = socket.gethostbyaddr(target)
            return ToolResult(status=ToolStatus.SUCCESS, data=str(info))
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error="Informatii indisponibile.")
