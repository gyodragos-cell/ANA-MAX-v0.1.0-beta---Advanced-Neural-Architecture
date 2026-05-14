"""
A.N.A. v15.0 - Network Tool
===========================
Instrumente pentru inginerie de rețea și diagnoză.
"""

import os
import subprocess
import socket
import logging
from typing import Optional, Dict, Any, List
from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus

logger = logging.getLogger(__name__)

class NetworkTool(Tool):
    """
    Tool pentru diagnoză rețea și conectivitate.
    """
    
    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="network_diag",
            description="Diagnoză rețea: ping, port scan, DNS, IP info.",
            parameters=[
                ToolParameter(
                    name="operation",
                    description="Operațiunea: ping, scan_ports, dns_lookup, ip_info",
                    type="string",
                    required=True,
                    choices=["ping", "scan_ports", "dns_lookup", "ip_info"]
                ),
                ToolParameter(
                    name="target",
                    description="Ținta: IP sau Domain",
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
        """Execută operațiunea network."""
        handlers = {
            "ping": self._ping,
            "scan_ports": self._scan_ports,
            "dns_lookup": self._dns_lookup,
            "ip_info": self._ip_info
        }
        
        if operation not in handlers:
            return ToolResult(status=ToolStatus.ERROR, error=f"Operațiune necunoscută: {operation}")
            
        return handlers[operation](target, **kwargs)

    def _ping(self, target: str, **kwargs) -> ToolResult:
        """Ping către un host."""
        param = "-n" if os.name == "nt" else "-c"
        try:
            output = subprocess.check_output(["ping", param, "4", target], text=True, stderr=subprocess.STDOUT)
            return ToolResult(status=ToolStatus.SUCCESS, data=output, message=f"Ping realizat către {target}")
        except subprocess.CalledProcessError as e:
            return ToolResult(status=ToolStatus.ERROR, error=f"Host-ul {target} nu răspunde.")

    def _scan_ports(self, target: str, **kwargs) -> ToolResult:
        """Scanare simplă de porturi."""
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
            res += "Toate porturile scanate par închise."
            
        return ToolResult(status=ToolStatus.SUCCESS, data=res)

    def _dns_lookup(self, target: str, **kwargs) -> ToolResult:
        """Căutare DNS."""
        try:
            addr = socket.gethostbyname(target)
            return ToolResult(status=ToolStatus.SUCCESS, data=f"{target} -> IP: {addr}")
        except socket.gaierror:
            return ToolResult(status=ToolStatus.ERROR, error="Nu am putut rezolva domeniul.")

    def _ip_info(self, target: str, **kwargs) -> ToolResult:
        """Informații IP (local momentan)."""
        try:
            info = socket.gethostbyaddr(target)
            return ToolResult(status=ToolStatus.SUCCESS, data=str(info))
        except:
            return ToolResult(status=ToolStatus.ERROR, error="Informații indisponibile.")
