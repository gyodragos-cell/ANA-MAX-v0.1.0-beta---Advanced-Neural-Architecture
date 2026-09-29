import subprocess
import json
import re
from tools.base import Tool, ToolResult, ToolStatus

class HardwareScannerTool(Tool):
    name = "hardware_scanner"
    description = "Hardware security scanner (White Hat) - scan IoT, routers, detect vulns, check firmware."
    
    def get_definition(self):
        from tools.base import ToolDefinition, ToolParameter
        return ToolDefinition(
            name=self.name,
            description=self.description,
            parameters=[
                ToolParameter(
                    name="operation",
                    description="Operation: scan_network, check_firmware, detect_default_creds",
                    type="string",
                    required=True,
                    choices=["scan_network", "check_firmware", "detect_default_creds"]
                ),
                ToolParameter(
                    name="target_ip",
                    description="Target IP/range (ONLY with permission!)",
                    type="string",
                    required=True
                ),
                ToolParameter(
                    name="device_type",
                    description="Device: router, camera, smart_home, iot",
                    type="string",
                    required=False
                )
            ],
            category="security"
        )
    
    def execute(self, **kwargs):
        operation = kwargs.get("operation")
        target_ip = kwargs.get("target_ip")
        device_type = kwargs.get("device_type", "router")
        
        if operation == "scan_network":
            return self._scan_network(target_ip, device_type)
        elif operation == "check_firmware":
            return self._check_firmware(target_ip)
        elif operation == "detect_default_creds":
            return self._detect_default_creds(target_ip, device_type)
        else:
            return ToolResult(status=ToolStatus.ERROR, error=f"Unknown operation: {operation}")
    
    def _scan_network(self, target_ip, device_type):
        """Scan network for IoT devices (nmap) - LEGAL SCOPE ONLY"""
        try:
            cmd = [
                "nmap", "-sV", "-p", "80,443,22,23,8080",
                "-oX", "security_research/proofs/hardware_scan.xml",
                target_ip
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                # Parse for open ports
                open_ports = re.findall(r'portid="(\d+)" state="open"', result.stdout)
                
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data=f"Found {len(open_ports)} open ports: {', '.join(open_ports)}",
                    message=f"Hardware scan complete - {len(open_ports)} ports open"
                )
            else:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error=result.stderr
                )
        except FileNotFoundError:
            return ToolResult(
                status=ToolStatus.ERROR,
                error="Nmap not installed. Install: apt install nmap (Linux) or download from nmap.org"
            )
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    def _check_firmware(self, target_ip):
        """Check firmware version (legal with permission)"""
        try:
            # Use curl to grab firmware version from web interface
            cmd = ["curl", "-s", f"http://{target_ip}/status", "-I"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                version_match = re.search(r'Server: (.+)', result.stdout)
                version = version_match.group(1) if version_match else "Unknown"
                
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data=f"Firmware: {version}",
                    message=f"Firmware version detected: {version}"
                )
            else:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error="Could not reach device web interface"
                )
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    def _detect_default_creds(self, target_ip, device_type):
        """Check for default credentials (legal with permission)"""
        try:
            # Common default creds
            default_creds = [
                ("admin", "admin"),
                ("admin", "password"),
                ("root", "root"),
                ("user", "user"),
                ("admin", ""),
                ("pi", "raspberry")
            ]
            
            results = []
            for username, password in default_creds:
                # Test with curl (simplified)
                cmd = ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
                       "-u", f"{username}:{password}",
                       f"http://{target_ip}/login"]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                
                if result.stdout.strip() == "200":
                    results.append(f"Potential default creds: {username}:{password}")
            
            if results:
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data="\n".join(results),
                    message=f"Found {len(results)} potential default credentials!"
                )
            else:
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data="No default credentials found in quick scan",
                    message="No obvious default creds detected"
                )
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
