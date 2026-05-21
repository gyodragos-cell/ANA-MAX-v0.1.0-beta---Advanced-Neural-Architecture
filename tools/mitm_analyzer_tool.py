import subprocess
import json
import os
from tools.base import Tool, ToolResult, ToolStatus

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
        operation = kwargs.get("operation")
        interface = kwargs.get("interface", "Loopback Pseudo-Interface")
        target_port = kwargs.get("target_port", "8765")
        output_file = kwargs.get("output_file", "bounty_proof.pcapng")
        
        if operation == "capture_start":
            return self._start_capture(interface, target_port)
        elif operation == "capture_stop":
            return self._stop_capture()
        elif operation == "analyze":
            return self._analyze_capture(output_file)
        elif operation == "export":
            return self._export_for_bounty(output_file)
        else:
            return ToolResult(status=ToolStatus.ERROR, error=f"Operatiune necunoscuta: {operation}")
    
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
