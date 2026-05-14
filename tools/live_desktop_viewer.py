"""
Live Desktop Viewer Tool - Browser-based Desktop Streaming
Author: ANA_MAX
Date: 2026-05-13
Category: monitoring

Functions:
- start_server: Porneste server web cu live desktop streaming
- stop_server: Opreste serverul
- status: Verifica statusul serverului

Opens a web browser where you can see the desktop in real-time (like VNC but simpler)
"""

from __future__ import annotations

import subprocess
import os
import logging
import threading
import time
import json
import base64
from typing import Optional, Dict, Any
from pathlib import Path
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler
from socketserver import ThreadingMixIn

from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus

logger = logging.getLogger(__name__)


class DesktopStreamHandler(SimpleHTTPRequestHandler):
    """HTTP Handler pentru live desktop streaming."""
    
    # Clasa va fi configurata dinamic cu referinta la tool
    desktop_tool = None
    
    def do_GET(self):
        if self.path == '/':
            self.serve_html()
        elif self.path == '/stream':
            self.serve_stream()
        elif self.path == '/api/status':
            self.serve_status()
        else:
            self.send_error(404)
    
    def serve_html(self):
        """Serveste pagina HTML cu viewer-ul live."""
        html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ANA_MAX - Live Desktop Viewer</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #1a1a2e;
            color: #eee;
            overflow: hidden;
        }
        
        .header {
            background: #16213e;
            padding: 15px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 2px solid #0f3460;
        }
        
        .header h1 {
            font-size: 1.5em;
            color: #e94560;
        }
        
        .status {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .status-dot {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: #00ff00;
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        .controls {
            display: flex;
            gap: 10px;
        }
        
        .btn {
            background: #0f3460;
            color: #eee;
            border: none;
            padding: 8px 16px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 0.9em;
            transition: all 0.3s;
        }
        
        .btn:hover {
            background: #e94560;
        }
        
        .viewer-container {
            position: relative;
            width: 100vw;
            height: calc(100vh - 70px);
            display: flex;
            justify-content: center;
            align-items: center;
            background: #0a0a14;
        }
        
        #desktop-frame {
            max-width: 100%;
            max-height: 100%;
            border: 2px solid #0f3460;
            border-radius: 5px;
            box-shadow: 0 0 20px rgba(233, 69, 96, 0.3);
        }
        
        .info-bar {
            position: absolute;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            background: rgba(22, 33, 62, 0.9);
            padding: 10px 20px;
            border-radius: 25px;
            display: flex;
            gap: 20px;
            font-size: 0.85em;
        }
        
        .info-item {
            display: flex;
            align-items: center;
            gap: 5px;
        }
        
        .loading {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 15px;
        }
        
        .spinner {
            width: 50px;
            height: 50px;
            border: 4px solid #0f3460;
            border-top: 4px solid #e94560;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🖥️ ANA_MAX Live Desktop Viewer</h1>
        <div class="status">
            <div class="status-dot"></div>
            <span id="status-text">Connecting...</span>
        </div>
        <div class="controls">
            <button class="btn" onclick="toggleFullscreen()"> Fullscreen</button>
            <button class="btn" onclick="refreshStream()">🔄 Refresh</button>
            <button class="btn" onclick="downloadScreenshot()">💾 Screenshot</button>
        </div>
    </div>
    
    <div class="viewer-container">
        <div id="loading" class="loading">
            <div class="spinner"></div>
            <p>Connecting to desktop stream...</p>
        </div>
        <img id="desktop-frame" style="display:none;" alt="Desktop Stream">
    </div>
    
    <div class="info-bar">
        <div class="info-item">
            <span>🖥️</span>
            <span id="resolution">Loading...</span>
        </div>
        <div class="info-item">
            <span></span>
            <span id="fps">FPS: --</span>
        </div>
        <div class="info-item">
            <span>🕐</span>
            <span id="uptime">Uptime: 0s</span>
        </div>
    </div>
    
    <script>
        let frameCount = 0;
        let lastFpsTime = Date.now();
        let startTime = Date.now();
        let streamActive = false;
        
        function updateStream() {
            const img = document.getElementById('desktop-frame');
            const loading = document.getElementById('loading');
            const statusText = document.getElementById('status-text');
            
            fetch('/stream?t=' + Date.now())
                .then(response => response.json())
                .then(data => {
                    if (data.success && data.image) {
                        img.src = 'data:image/png;base64,' + data.image;
                        img.style.display = 'block';
                        loading.style.display = 'none';
                        
                        if (!streamActive) {
                            streamActive = true;
                            statusText.textContent = 'Live';
                        }
                        
                        // Update stats
                        frameCount++;
                        const now = Date.now();
                        if (now - lastFpsTime >= 1000) {
                            document.getElementById('fps').textContent = 'FPS: ' + frameCount;
                            frameCount = 0;
                            lastFpsTime = now;
                        }
                        
                        const uptime = Math.floor((now - startTime) / 1000);
                        document.getElementById('uptime').textContent = 'Uptime: ' + uptime + 's';
                        
                        // Update resolution when image loads
                        img.onload = function() {
                            document.getElementById('resolution').textContent = 
                                this.naturalWidth + 'x' + this.naturalHeight;
                        };
                    } else {
                        statusText.textContent = 'Error: ' + (data.error || 'Unknown');
                    }
                })
                .catch(err => {
                    statusText.textContent = 'Connection lost';
                    console.error('Stream error:', err);
                })
                .finally(() => {
                    setTimeout(updateStream, 100); // Update every 100ms (10 FPS)
                });
        }
        
        function toggleFullscreen() {
            if (!document.fullscreenElement) {
                document.documentElement.requestFullscreen();
            } else {
                document.exitFullscreen();
            }
        }
        
        function refreshStream() {
            streamActive = false;
            document.getElementById('desktop-frame').style.display = 'none';
            document.getElementById('loading').style.display = 'flex';
            document.getElementById('status-text').textContent = 'Reconnecting...';
        }
        
        function downloadScreenshot() {
            const img = document.getElementById('desktop-frame');
            if (img.src) {
                const link = document.createElement('a');
                link.href = img.src;
                link.download = 'desktop_' + Date.now() + '.png';
                link.click();
            }
        }
        
        // Start stream
        updateStream();
    </script>
</body>
</html>
        """
        
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))
    
    def serve_stream(self):
        """Serveste captura de ecran ca JSON."""
        try:
            from PIL import ImageGrab
            import io
            
            # Capture screenshot
            screenshot = ImageGrab.grab()
            
            # Resize pentru performanta (max 1920x1080)
            max_width = 1920
            max_height = 1080
            if screenshot.width > max_width or screenshot.height > max_height:
                screenshot.thumbnail((max_width, max_height))  # PIL auto-uses best resampling
            
            # Convert to base64
            buffered = io.BytesIO()
            screenshot.save(buffered, format="PNG", optimize=True, quality=85)
            img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
            
            response = {
                'success': True,
                'image': img_base64,
                'timestamp': datetime.now().isoformat()
            }
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode('utf-8'))
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                'success': False,
                'error': str(e)
            }).encode('utf-8'))
    
    def serve_status(self):
        """Serveste statusul serverului."""
        status = {
            'running': True,
            'uptime': (datetime.now() - self.desktop_tool.start_time).total_seconds() if self.desktop_tool.start_time else 0,
            'frames_served': self.desktop_tool.frames_served if self.desktop_tool else 0
        }
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(status).encode('utf-8'))
    
    def log_message(self, format, *args):
        """Suprascriem logging-ul default."""
        pass


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Server HTTP thread-safe."""
    allow_reuse_address = True
    daemon_threads = True


class LiveDesktopViewerTool(Tool):
    """Tool pentru live desktop streaming in browser."""

    def __init__(self) -> None:
        self.server: Optional[ThreadedHTTPServer] = None
        self.server_thread: Optional[threading.Thread] = None
        self.port: int = 8765
        self.running: bool = False
        self.start_time: Optional[datetime] = None
        self.frames_served: int = 0

    def get_definition(self):
        return ToolDefinition(
            name="live_desktop_viewer",
            description="Porneste un server web cu live desktop streaming. Accesibil in browser pentru a vedea desktop-ul in timp real (ca un VNC simplificat).",
            parameters=[
                ToolParameter(
                    name="operation",
                    description="Operatia: start (porneste server), stop (opreste server), status (verifica status)",
                    type="string",
                    required=True,
                    choices=["start", "stop", "status"]
                ),
                ToolParameter(
                    name="port",
                    description="Portul serverului (default: 8765)",
                    type="string",
                    required=False
                ),
                ToolParameter(
                    name="auto_open",
                    description="Deschide automat browserul (true/false, default: true)",
                    type="string",
                    required=False
                )
            ],
            category="monitoring"
        )

    def execute(self, **kwargs) -> ToolResult:
        operation = kwargs.get("operation")
        
        try:
            if operation == "start":
                return self._start_server(**kwargs)
            elif operation == "stop":
                return self._stop_server()
            elif operation == "status":
                return self._get_status()
            else:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error=f"Operatie necunoscuta: {operation}"
                )
        except Exception as e:
            logger.error(f"Live desktop viewer error: {e}")
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Eroare: {str(e)}"
            )

    def _start_server(self, **kwargs) -> ToolResult:
        """Porneste serverul web cu live streaming."""
        if self.running:
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"url": f"http://127.0.0.1:{self.port}"},
                message=f"Serverul ruleaza deja pe http://127.0.0.1:{self.port}"
            )
        
        # Configurare port
        if kwargs.get("port"):
            self.port = int(kwargs["port"])
        
        auto_open = kwargs.get("auto_open", "true").lower() == "true"
        
        try:
            # Configure handler cu referinta la tool
            DesktopStreamHandler.desktop_tool = self
            
            # Porneste server
            self.server = ThreadedHTTPServer(('127.0.0.1', self.port), DesktopStreamHandler)
            self.start_time = datetime.now()
            self.running = True
            self.frames_served = 0
            
            # Thread pentru server
            self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.server_thread.start()
            
            url = f"http://127.0.0.1:{self.port}"
            
            # Deschide browser automat
            if auto_open:
                import webbrowser
                time.sleep(0.5)
                webbrowser.open(url)
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={
                    "url": url,
                    "port": self.port,
                    "auto_opened": auto_open
                },
                message=f"✅ Live Desktop Viewer pornit!\n\n"
                       f"🌐 URL: {url}\n"
                       f"📊 Port: {self.port}\n"
                       f"🔄 Auto-refresh: 10 FPS\n"
                       f"💡 Deschide URL-ul in browser pentru a vedea desktop-ul live\n"
                       f"💡 Foloseste 'live_desktop_viewer operation=stop' pentru a opri"
            )
            
        except Exception as e:
            self.running = False
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Nu s-a putut porni serverul: {str(e)}"
            )

    def _stop_server(self) -> ToolResult:
        """Opreste serverul."""
        if not self.running:
            return ToolResult(
                status=ToolStatus.SUCCESS,
                message="Serverul nu ruleaza"
            )
        
        try:
            self.running = False
            if self.server:
                self.server.shutdown()
                self.server.server_close()
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                message="✅ Live Desktop Viewer oprit"
            )
            
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Eroare la oprire: {str(e)}"
            )

    def _get_status(self) -> ToolResult:
        """Obtine statusul serverului."""
        if not self.running:
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"running": False},
                message="Serverul nu ruleaza"
            )
        
        uptime = 0
        if self.start_time:
            uptime = (datetime.now() - self.start_time).total_seconds()
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={
                "running": True,
                "url": f"http://127.0.0.1:{self.port}",
                "port": self.port,
                "uptime_seconds": uptime,
                "frames_served": self.frames_served
            },
            message=f"✅ Server activ\n"
                   f" URL: http://127.0.0.1:{self.port}\n"
                   f"⏱️ Uptime: {uptime:.1f}s\n"
                   f"📊 Frames served: {self.frames_served}"
        )
