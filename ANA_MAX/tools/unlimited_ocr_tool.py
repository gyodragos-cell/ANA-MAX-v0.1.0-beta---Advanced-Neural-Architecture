"""
ANA MAX - Unlimited OCR Tool (OS27 Hyper++)
===========================================
Tool care foloseste Unlimited-OCR pentru recunoastere text din imagine
"Umplem tevile cu apa" - testam sistemul si gasim problemele

OS27 Hyper++ Features:
- Telemetry tracking for OCR operations (process, convert, health, start)
- Health monitoring for OCR reliability
- MemoryCortex integration for OCR errors and state learning
- ContextEngine integration for OCR state awareness
- SelfEvolvingTool integration for anomaly detection on OCR failures
- Structured logging with error detection
"""

import os
import json
import logging
import time
from pathlib import Path
from typing import Optional, Dict, Any

from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus

logger = logging.getLogger(__name__)

# OS27 Hyper++ Telemetry
_ocr_telemetry: Dict[str, Dict[str, Any]] = {}


def _record_ocr_telemetry(operation: str, success: bool, execution_time: float) -> None:
    """Record OS27 Hyper++ telemetry for OCR operations."""
    if operation not in _ocr_telemetry:
        _ocr_telemetry[operation] = {
            "operation_count": 0,
            "success_count": 0,
            "failure_count": 0,
            "total_time": 0.0,
            "last_execution_time": 0.0,
            "last_success": False,
        }
    
    _ocr_telemetry[operation]["operation_count"] += 1
    _ocr_telemetry[operation]["total_time"] += execution_time
    _ocr_telemetry[operation]["last_execution_time"] = execution_time
    _ocr_telemetry[operation]["last_success"] = success
    
    if success:
        _ocr_telemetry[operation]["success_count"] += 1
    else:
        _ocr_telemetry[operation]["failure_count"] += 1


def get_ocr_telemetry(operation: str | None = None) -> Dict[str, Any] | Dict[str, Dict[str, Any]]:
    """Get telemetry for OCR operations."""
    if operation:
        return _ocr_telemetry.get(operation, {})
    return _ocr_telemetry.copy()


def get_ocr_health() -> str:
    """Get health status for OCR tool based on telemetry."""
    if not _ocr_telemetry:
        return "unknown"
    
    total_ops = sum(stats["operation_count"] for stats in _ocr_telemetry.values())
    total_failures = sum(stats["failure_count"] for stats in _ocr_telemetry.values())
    
    if total_ops == 0:
        return "unknown"
    
    failure_rate = total_failures / total_ops
    if failure_rate > 0.5:
        return "broken"
    if failure_rate > 0.1:
        return "degraded"
    return "healthy"


class UnlimitedOCRTool(Tool):
    """
    Tool pentru OCR folosind Unlimited-OCR local server.
    Functioneaza ca un "tevi cu apa" - trimite imagine, primeste text.
    """

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="unlimited_ocr",
            description="Extract text from ANY file using Unlimited-OCR local server. Supports images (PNG, JPG, JPEG, WEBP, BMP), PDF, and converts other formats to image first. Perfect for document parsing, screenshots, and file-to-text conversion.",
            parameters=[
                ToolParameter(
                    name="file_path",
                    description="Path to ANY file for OCR processing (images, PDF, or other files that will be converted)",
                    type="string",
                    required=True
                ),
                ToolParameter(
                    name="output_file",
                    description="Optional path to save extracted text",
                    type="string",
                    required=False
                ),
                ToolParameter(
                    name="server_url",
                    description="Unlimited-OCR server URL (default: http://127.0.0.1:10000)",
                    type="string",
                    required=False
                )
            ],
            category="vision"
        )

    def execute(self, **kwargs) -> ToolResult:
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
        
        file_path = kwargs.get("file_path")
        output_file = kwargs.get("output_file")
        server_url = kwargs.get("server_url", "http://127.0.0.1:10000")

        if not file_path:
            execution_time = time.time() - start_time
            _record_ocr_telemetry("execute", False, execution_time)
            return ToolResult(
                status=ToolStatus.ERROR,
                error="file_path is required"
            )

        # Verificam daca fisierul exista
        if not os.path.exists(file_path):
            execution_time = time.time() - start_time
            _record_ocr_telemetry("execute", False, execution_time)
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"File not found: {file_path}"
            )

        try:
            # Determinam tipul fisierului
            file_ext = Path(file_path).suffix.lower()
            
            # Formate imagine direct suportate
            image_extensions = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tiff"}
            
            # Formate PDF
            pdf_extensions = {".pdf"}
            
            # Formate text/cod - converteste in imagine
            text_extensions = {".py", ".json", ".md", ".tt", ".yaml", ".yml", ".txt", ".js", ".ts", ".html", ".css", ".xml", ".cfg", ".ini", ".log"}
            
            # Daca e imagine sau PDF, procesam direct
            if file_ext in image_extensions or file_ext in pdf_extensions:
                result = self._process_with_ocr(file_path, output_file, server_url)
            
            # Daca e fisier text/cod, converteste in imagine apoi OCR
            elif file_ext in text_extensions:
                result = self._convert_and_ocr(file_path, output_file, server_url)
            
            # Alte formate - incercam conversie
            else:
                result = self._convert_and_ocr(file_path, output_file, server_url)

            execution_time = time.time() - start_time
            _record_ocr_telemetry("execute", result.is_success, execution_time)
            
            # ContextEngine integration for OCR state
            if context_engine and result.is_success:
                try:
                    context_engine.update_context(
                        key="ocr_state",
                        value={
                            "file_path": file_path,
                            "success": result.is_success,
                            "tokens": result.data.get("tokens", 0) if result.data else 0,
                            "timestamp": time.time(),
                        }
                    )
                except Exception:
                    pass
            
            # MemoryCortex integration for OCR errors
            if cortex and not result.is_success:
                try:
                    cortex.remember(
                        "error",
                        "ocr.execute",
                        f"OCR failed for {file_path}: {result.error}"
                    )
                except Exception:
                    pass
            
            return result

        except Exception as e:
            logger.exception("Unlimited-OCR processing failed")
            execution_time = time.time() - start_time
            _record_ocr_telemetry("execute", False, execution_time)
            
            # MemoryCortex integration for OCR errors
            if cortex:
                try:
                    cortex.remember(
                        "error",
                        "ocr.execute",
                        f"OCR exception for {file_path}: {str(e)}"
                    )
                except Exception:
                    pass
            
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"OCR processing failed: {e}"
            )
    
    def _process_with_ocr(self, file_path: str, output_file: str, server_url: str) -> ToolResult:
        """Proceseaza direct imagine/PDF cu OCR."""
        # Importam modulul Unlimited-OCR
        unlimited_ocr_path = Path(r"C:\Users\billy\Desktop\Unlimited-OCR-main")
        infer_py = unlimited_ocr_path / "infer.py"

        if not infer_py.exists():
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Unlimited-OCR not found at: {unlimited_ocr_path}"
            )

        # Adaugam la sys.path pentru a putea importa
        import sys
        if str(unlimited_ocr_path) not in sys.path:
            sys.path.insert(0, str(unlimited_ocr_path))

        # Folosim infer.py functions
        from infer import (
            encode_image,
            build_content,
            server_ready,
            infer_one,
            collect_stream_silent
        )

        # Verificam daca serverul e pornit
        if not server_ready(server_url):
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Unlimited-OCR server not ready at {server_url}. Start the server first."
            )

        # Procesam fisierul
        logger.info(f"Processing file with Unlimited-OCR: {file_path}")

        # Simulam un job pentru infer_one
        class Args:
            def __init__(self):
                self.image_mode = "default"

        args = Args()

        # Apelam infer_one
        result = infer_one(file_path, output_file, args, idx=0)

        if result["tokens"] == 0:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"OCR processing failed for {file_path}"
            )

        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={
                "text": result["text"],
                "tokens": result["tokens"],
                "decode_time": result["decode_time"],
                "file_path": file_path,
                "output_file": output_file
            },
            message=f"OCR completed: {result['tokens']} tokens extracted in {result['decode_time']:.1f}s"
        )
    
    def _convert_and_ocr(self, file_path: str, output_file: str, server_url: str) -> ToolResult:
        """Converteste fisier text/cod in imagine apoi OCR."""
        try:
            from PIL import Image, ImageDraw, ImageFont
            import tempfile
            
            # Citim continutul fisierului
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Calculam numarul de linii
            lines = content.split('\n')
            num_lines = len(lines)
            
            # Dimensiuni dinamice bazate pe numarul de linii
            img_width = 1200
            line_height = 20
            padding = 20
            img_height = max(800, num_lines * line_height + padding * 2)
            
            # Limitam imaginea la 10000px inaltime pentru a evita probleme de memorie
            max_height = 10000
            if img_height > max_height:
                img_height = max_height
                logger.warning(f"File too large ({num_lines} lines), truncating to {max_height // line_height} lines")
                lines = lines[:max_height // line_height]
            
            # Cream imagine din text
            img = Image.new('RGB', (img_width, img_height), color='white')
            draw = ImageDraw.Draw(img)
            
            # Incercam sa folosim un font
            try:
                font = ImageFont.truetype("arial.ttf", 14)
            except:
                font = ImageFont.load_default()
            
            # Desenam text pe imagine
            y_position = padding
            for line in lines:
                if y_position > img_height - padding:
                    break
                draw.text((10, y_position), line, fill='black', font=font)
                y_position += line_height
            
            # Salvam imagine temporara
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                temp_image_path = tmp.name
                img.save(temp_image_path)
            
            # Procesam cu OCR
            result = self._process_with_ocr(temp_image_path, output_file, server_url)
            
            # Stergem imagine temporara
            os.unlink(temp_image_path)
            
            return result
            
        except Exception as e:
            logger.exception("File to image conversion failed")
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Failed to convert file to image: {e}"
            )


class UnlimitedOCRHealthTool(Tool):
    """
    Tool pentru a verifica daca Unlimited-OCR server functioneaza.
    "Vedem daca teava are apa" - verificam server health.
    """

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="unlimited_ocr_health",
            description="Check if Unlimited-OCR server is running and healthy. 'Vedem daca teava are apa'.",
            parameters=[
                ToolParameter(
                    name="server_url",
                    description="Unlimited-OCR server URL (default: http://127.0.0.1:10000)",
                    type="string",
                    required=False
                )
            ],
            category="vision"
        )

    def execute(self, **kwargs) -> ToolResult:
        server_url = kwargs.get("server_url", "http://127.0.0.1:10000")

        try:
            import requests

            resp = requests.get(f"{server_url}/health", timeout=5)

            if resp.status_code == 200:
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data={
                        "server_url": server_url,
                        "status": "healthy",
                        "response": resp.json() if resp.headers.get("content-type", "").startswith("application/json") else resp.text
                    },
                    message=f"Unlimited-OCR server is healthy at {server_url}"
                )
            else:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error=f"Server returned status {resp.status_code}"
                )

        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Server health check failed: {e}"
            )


class UnlimitedOCRStartTool(Tool):
    """
    Tool pentru a porni Unlimited-OCR server.
    "Deschidem robinetul" - pornim serverul.
    """

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="unlimited_ocr_start",
            description="Start Unlimited-OCR server locally. 'Deschidem robinetul'.",
            parameters=[
                ToolParameter(
                    name="model_dir",
                    description="Path to Unlimited-OCR model directory",
                    type="string",
                    required=True
                ),
                ToolParameter(
                    name="gpu",
                    description="GPU ID to use (default: 0)",
                    type="string",
                    required=False
                ),
                ToolParameter(
                    name="server_log",
                    description="Path to server log file",
                    type="string",
                    required=False
                )
            ],
            category="vision"
        )

    def execute(self, **kwargs) -> ToolResult:
        model_dir = kwargs.get("model_dir")
        gpu = kwargs.get("gpu", "0")
        server_log = kwargs.get("server_log", "unlimited_ocr_server.log")

        if not model_dir:
            return ToolResult(
                status=ToolStatus.ERROR,
                error="model_dir is required"
            )

        try:
            # Adaugam la sys.path
            unlimited_ocr_path = Path(r"C:\Users\billy\Desktop\Unlimited-OCR-main")
            import sys
            if str(unlimited_ocr_path) not in sys.path:
                sys.path.insert(0, str(unlimited_ocr_path))

            from infer import start_server, SERVER_URL

            class Args:
                def __init__(self):
                    self.model_dir = model_dir
                    self.gpu = gpu
                    self.server_log = server_log

            args = Args()

            process = start_server(args)

            if process is None:
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data={
                        "server_url": SERVER_URL,
                        "status": "reused_existing"
                    },
                    message=f"Reused existing Unlimited-OCR server at {SERVER_URL}"
                )

            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={
                    "server_url": SERVER_URL,
                    "pid": process.pid,
                    "status": "started"
                },
                message=f"Unlimited-OCR server started at {SERVER_URL} (PID: {process.pid})"
            )

        except Exception as e:
            logger.exception("Failed to start Unlimited-OCR server")
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Failed to start server: {e}"
            )
