#!/usr/bin/env python3
"""Mitmproxy Live Analyzer - Whitehat Testing Tool for ANA"""

import asyncio
import json
from mitmproxy import http, ctx
from mitmproxy.tools import cmdline
from datetime import datetime
import os

class MitmLiveAnalyzer:
    """Live MITM analyzer pentru whitehat testing - integrare cu ANA"""
    
    def __init__(self, output_dir="ANA_MAX/security_research/mitm_captures"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.captured_requests = []
        self.vulnerability_patterns = {
            "xss": ["<script>", "javascript:", "onerror=", "onload="],
            "sqli": ["'", "OR", "UNION", "SELECT", "DROP", "--"],
            "path_traversal": ["../", "..\\", "%2e%2e"],
            "ssrf": ["http://", "https://", "file://"],
            "info_disclosure": ["password", "api_key", "secret", "token"]
        }
    
    def request(self, flow: http.HTTPFlow):
        """Captureaza si analizeaza request-uri in timp real"""
        try:
            request_data = {
                "timestamp": datetime.now().isoformat(),
                "method": flow.request.method,
                "url": flow.request.pretty_url,
                "host": flow.request.pretty_host,
                "path": flow.request.path,
                "headers": dict(flow.request.headers),
                "content_length": len(flow.request.content) if flow.request.content else 0
            }
            
            # Vulnerability scanning
            vulnerabilities = self._scan_for_vulnerabilities(flow)
            if vulnerabilities:
                request_data["vulnerabilities"] = vulnerabilities
                ctx.log.warn(f"[VULN DETECTED] {vulnerabilities} in {flow.request.pretty_url}")
            
            self.captured_requests.append(request_data)
            
            # Log pentru ANA agent
            ctx.log.info(f"[ANA MITM] {flow.request.method} {flow.request.pretty_url}")
            
        except Exception as e:
            ctx.log.error(f"[ANA MITM] Error processing request: {str(e)}")
    
    def response(self, flow: http.HTTPFlow):
        """Analizeaza response-uri pentru informatii sensibile"""
        try:
            if flow.response:
                response_data = {
                    "status_code": flow.response.status_code,
                    "content_type": flow.response.headers.get("content-type", ""),
                    "size": len(flow.response.content) if flow.response.content else 0
                }
                
                # Check for sensitive data in response
                if flow.response.text:
                    sensitive_info = self._check_sensitive_data(flow.response.text)
                    if sensitive_info:
                        ctx.log.warn(f"[SENSITIVE DATA] {sensitive_info} in response from {flow.request.pretty_url}")
                
                ctx.log.info(f"[ANA MITM] Response {flow.response.status_code} for {flow.request.pretty_url}")
                
        except Exception as e:
            ctx.log.error(f"[ANA MITM] Error processing response: {str(e)}")
    
    def _scan_for_vulnerabilities(self, flow: http.HTTPFlow):
        """Scaneaza request pentru vulnerabilitati cunoscute"""
        found_vulns = []
        
        if not flow.request.text:
            return found_vulns
        
        request_text = flow.request.text.lower()
        
        for vuln_type, patterns in self.vulnerability_patterns.items():
            for pattern in patterns:
                if pattern.lower() in request_text:
                    found_vulns.append(f"{vuln_type}:{pattern}")
        
        return found_vulns
    
    def _check_sensitive_data(self, text):
        """Verifica date sensibile in response"""
        sensitive_keywords = ["password", "api_key", "secret", "token", "credit_card", "ssn"]
        found = []
        
        text_lower = text.lower()
        for keyword in sensitive_keywords:
            if keyword in text_lower:
                found.append(keyword)
        
        return found if found else None
    
    def export_capture(self, filename="mitm_capture.json"):
        """Exporta capture-ul pentru analiza ulterioara"""
        export_path = os.path.join(self.output_dir, filename)
        
        with open(export_path, 'w', encoding='utf-8') as f:
            json.dump({
                "capture_time": datetime.now().isoformat(),
                "total_requests": len(self.captured_requests),
                "requests": self.captured_requests
            }, f, indent=2)
        
        ctx.log.info(f"[ANA MITM] Exported {len(self.captured_requests)} requests to {export_path}")
        return export_path


# Addons pentru mitmproxy
class ANAMitmAddon:
    def __init__(self):
        self.analyzer = MitmLiveAnalyzer()
    
    def request(self, flow: http.HTTPFlow):
        self.analyzer.request(flow)
    
    def response(self, flow: http.HTTPFlow):
        self.analyzer.response(flow)


# Functie pentru pornire programatica
def start_mitm_proxy(port=8080, mode="reverse", upstream="http://127.0.0.1:8765"):
    """
    Porneste mitmproxy in modul reverse pentru a intercepta traficul ANA
    
    Args:
        port: Portul pe care asculta mitmproxy (default: 8080)
        mode: Modul de operare (reverse, regular, socks5)
        upstream: Serverul upstream pentru interceptare (default: ANA MCP)
    """
    from mitmproxy.tools.main import mitmdump
    
    opts = cmdline.mkopts_parser().parse_args([
        f"--listen-port", str(port),
        f"--mode", mode,
        f"--upstream", upstream,
        "--set", "console_eventlog_verbosity=info"
    ])
    
    ctx.options.update(opts)
    return opts


if __name__ == "__main__":
    # Demo pentru pornire
    print("ANA MITM Live Analyzer - Whitehat Testing Tool")
    print("Usage: mitmdump -s mitmproxy_live_analyzer.py --listen-port 8080")
    print("For reverse proxy: mitmdump -s mitmproxy_live_analyzer.py --mode reverse --upstream http://127.0.0.1:8765")
