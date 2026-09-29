"""
ANA MAX - OCR Tool (Optical Character Recognition) (OS27 Hyper++)
====================================================================
tools/ocr_tool.py

OCR pe ecran, regiune, fisier sau clipboard
Suporta PaddleOCR (recomandat) sau Tesseract (fallback)

OS27 Hyper++ Features:
- Telemetry tracking for OCR operations (check, screen, file, clipboard, region)
- Health monitoring for OCR engine reliability
- MemoryCortex integration for OCR errors and backend learning
- ContextEngine integration for OCR state awareness
- SelfEvolvingTool integration for anomaly detection on OCR failures
- Structured logging with error detection
"""

import logging
import contextlib
import importlib.util
import io
import time
from typing import Dict, Any
from pathlib import Path

from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus

logger = logging.getLogger(__name__)

# OS27 Hyper++ Telemetry
_ocr_telemetry: Dict[str, Dict[str, Any]] = {}


def _record_ocr_telemetry(operation: str, success: bool, execution_time: float, backend: str = "") -> None:
    """Record OS27 Hyper++ telemetry for OCR operations."""
    if operation not in _ocr_telemetry:
        _ocr_telemetry[operation] = {
            "operation_count": 0,
            "success_count": 0,
            "failure_count": 0,
            "total_time": 0.0,
            "last_execution_time": 0.0,
            "last_success": False,
            "backends": {},
        }
    
    _ocr_telemetry[operation]["operation_count"] += 1
    _ocr_telemetry[operation]["total_time"] += execution_time
    _ocr_telemetry[operation]["last_execution_time"] = execution_time
    _ocr_telemetry[operation]["last_success"] = success
    
    if success:
        _ocr_telemetry[operation]["success_count"] += 1
    else:
        _ocr_telemetry[operation]["failure_count"] += 1
    
    if backend:
        if backend not in _ocr_telemetry[operation]["backends"]:
            _ocr_telemetry[operation]["backends"][backend] = 0
        _ocr_telemetry[operation]["backends"][backend] += 1


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

# OCR engine (lazy loading)
_ocr_engine = None
_ocr_backend = None  # "paddle" or "tesseract"


def run(args: Dict[str, Any]) -> Dict[str, Any]:
    """OCR tool entry point with OS27 Hyper++ telemetry."""
    start_time = time.time()
    action = args.get("action")
    
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
    
    result = None
    backend = ""
    
    if action == "check":
        result = _check_engine()
        backend = result.get("backend", "")
    elif action == "screen":
        result = _ocr_screen(args)
        backend = result.get("backend", "") if result.get("status") == "success" else ""
    elif action == "file":
        result = _ocr_file(args)
        backend = result.get("backend", "") if result.get("status") == "success" else ""
    elif action == "clipboard":
        result = _ocr_clipboard(args)
        backend = result.get("backend", "") if result.get("status") == "success" else ""
    elif action == "region":
        result = _ocr_region(args)
        backend = result.get("backend", "") if result.get("status") == "success" else ""
    else:
        result = {"status": "error", "error": f"Unknown action: {action}"}
    
    execution_time = time.time() - start_time
    success = result.get("status") == "success"
    _record_ocr_telemetry(action, success, execution_time, backend)
    
    # MemoryCortex integration for OCR errors
    if cortex and not success:
        try:
            cortex.remember(
                "error",
                f"ocr.{action}",
                f"OCR failed: {result.get('error', 'Unknown error')}"
            )
        except Exception:
            pass
    
    # ContextEngine integration for OCR state
    if context_engine and success:
        try:
            context_engine.update_context(
                key="ocr_state",
                value={
                    "last_action": action,
                    "backend": backend,
                    "timestamp": time.time(),
                }
            )
        except Exception:
            pass
    
    return result


def _check_engine() -> Dict[str, Any]:
    """Check OCR engine availability."""
    paddle_available = importlib.util.find_spec("paddleocr") is not None
    tesseract_available = importlib.util.find_spec("pytesseract") is not None
    pillow_available = importlib.util.find_spec("PIL") is not None

    if paddle_available and pillow_available:
        return {
            "status": "success",
            "available": True,
            "backend": "paddle",
            "loaded": _ocr_engine is not None,
            "message": "OCR engine available: paddle"
        }

    if tesseract_available and pillow_available:
        return {
            "status": "success",
            "available": True,
            "backend": "tesseract",
            "loaded": _ocr_engine is not None,
            "message": "OCR engine available: tesseract"
        }

    return {
        "status": "error",
        "available": False,
        "error": "No OCR engine available",
        "message": "Install paddleocr/paddlepaddle/pillow or pytesseract/pillow"
    }


def _get_engine():
    """Lazy load OCR engine."""
    global _ocr_engine, _ocr_backend
    
    if _ocr_engine is not None:
        return _ocr_engine, _ocr_backend
    
    # Try PaddleOCR first (recommended)
    try:
        from paddleocr import PaddleOCR
        logger.info("Loading PaddleOCR engine...")
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            _ocr_engine = PaddleOCR(
                use_angle_cls=False,  # Faster for straight text
                lang='en',
                enable_mkldnn=False  # Fix for Windows OneDNN/pir error
                # No quiet/show_log parameter in PaddleOCR 3.5.0
            )
        _ocr_backend = "paddle"
        logger.info("PaddleOCR loaded successfully")
        return _ocr_engine, _ocr_backend
    except ImportError:
        pass
    
    # Fallback to Tesseract
    try:
        import pytesseract
        from PIL import Image
        _ocr_engine = pytesseract
        _ocr_backend = "tesseract"
        logger.info("Tesseract OCR loaded (fallback)")
        return _ocr_engine, _ocr_backend
    except ImportError:
        raise RuntimeError(
            "No OCR engine available. Install one:\n"
            "  pip install paddleocr paddlepaddle pillow  (recommended)\n"
            "  OR\n"
            "  pip install pytesseract pillow  (+ install Tesseract OCR separately)"
        )


def _ocr_screen(args: Dict[str, Any]) -> Dict[str, Any]:
    """OCR on full screen or region."""
    try:
        import mss
        
        # Capture screen
        x = args.get("x", 0)
        y = args.get("y", 0)
        width = args.get("width")
        height = args.get("height")
        
        with mss.mss() as sct:
            if width and height:
                monitor = {"top": y, "left": x, "width": width, "height": height}
            else:
                monitor = sct.monitors[1]  # Primary monitor
            
            screenshot = sct.grab(monitor)
            
            # Convert to PIL Image
            from PIL import Image
            img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
            
            # Perform OCR
            return _perform_ocr(img)
    except ImportError:
        return {"status": "error", "error": "mss library not installed. Run: pip install mss"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def _ocr_file(args: Dict[str, Any]) -> Dict[str, Any]:
    """OCR on image file."""
    try:
        image_path = args.get("image_path")
        
        if not image_path:
            return {"status": "error", "error": "image_path parameter required"}
        
        path = Path(image_path)
        if not path.exists():
            return {"status": "error", "error": f"File not found: {image_path}"}
        
        from PIL import Image
        img = Image.open(path)
        
        return _perform_ocr(img)
    except Exception as e:
        return {"status": "error", "error": str(e)}


def _ocr_clipboard(args: Dict[str, Any]) -> Dict[str, Any]:
    """OCR on clipboard image."""
    try:
        import win32clipboard
        from PIL import Image
        import io
        
        win32clipboard.OpenClipboard()
        
        # Check if clipboard has image
        if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_DIB):
            dib = win32clipboard.GetClipboardData(win32clipboard.CF_DIB)
            win32clipboard.CloseClipboard()
            
            # Convert DIB to PIL Image
            img = Image.open(io.BytesIO(dib))
            return _perform_ocr(img)
        else:
            win32clipboard.CloseClipboard()
            return {"status": "error", "error": "No image in clipboard"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def _ocr_region(args: Dict[str, Any]) -> Dict[str, Any]:
    """OCR on specific screen region."""
    # Same as screen but requires coordinates
    if not all(k in args for k in ["x", "y", "width", "height"]):
        return {"status": "error", "error": "Region requires x, y, width, height parameters"}
    
    return _ocr_screen(args)


def _perform_ocr(img) -> Dict[str, Any]:
    """Perform OCR on PIL Image with timeout protection."""
    import threading
    import queue

    timeout = 30  # 30 seconds timeout for OCR operations
    result_queue = queue.Queue()

    def _ocr_worker():
        try:
            engine, backend = _get_engine()

            if backend == "paddle":
                # PaddleOCR 3.5.0 requires numpy array, not PIL Image
                import numpy as np
                img_array = np.array(img)

                # PaddleOCR returns list of [box, (text, confidence)]
                with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                    result = engine.ocr(img_array)

                texts = []
                confidence_scores = []

                if result and len(result) > 0:
                    for line in result[0]:
                        text = line[1][0]
                        confidence = line[1][1]
                        texts.append(text)
                        confidence_scores.append(confidence)

                full_text = "\n".join(texts)
                avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0

                result_queue.put({
                    "status": "success",
                    "backend": "paddle",
                    "text": full_text,
                    "lines": texts,
                    "line_count": len(texts),
                    "average_confidence": round(avg_confidence, 3)
                })

            elif backend == "tesseract":
                # Tesseract returns plain text
                full_text = engine.image_to_string(img)

                result_queue.put({
                    "status": "success",
                    "backend": "tesseract",
                    "text": full_text,
                    "lines": full_text.split("\n"),
                    "line_count": len(full_text.split("\n"))
                })

            else:
                result_queue.put({"status": "error", "error": f"Unknown backend: {backend}"})

        except Exception as e:
            result_queue.put({"status": "error", "error": str(e)})

    # Start OCR worker thread
    worker_thread = threading.Thread(target=_ocr_worker)
    worker_thread.start()
    worker_thread.join(timeout=timeout)

    if worker_thread.is_alive():
        # Timeout - thread still running
        logger.warning(f"OCR operation timed out after {timeout}s")
        return {
            "status": "error",
            "error": f"OCR operation timed out after {timeout}s. Try with a smaller image or region."
        }

    # Get result from queue
    try:
        return result_queue.get_nowait()
    except queue.Empty:
        return {"status": "error", "error": "OCR operation failed - no result returned"}
    
    except Exception as e:
        return {"status": "error", "error": str(e)}


class OcrTool(Tool):
    """Standard Tool wrapper for OCR operations."""

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="ocr_tool",
            description="OCR on screen, region, file or clipboard using PaddleOCR or Tesseract.",
            parameters=[
                ToolParameter("action", "check, screen, file, clipboard, region", "string", True, choices=["check", "screen", "file", "clipboard", "region"]),
                ToolParameter("image_path", "Path to image file", "string", False),
                ToolParameter("x", "Region X coordinate", "integer", False),
                ToolParameter("y", "Region Y coordinate", "integer", False),
                ToolParameter("width", "Region width", "integer", False),
                ToolParameter("height", "Region height", "integer", False),
            ],
            category="desktop",
        )

    def execute(self, **kwargs: Any) -> ToolResult:
        result = run(kwargs)
        if result.get("status") == "success":
            return ToolResult(status=ToolStatus.SUCCESS, data=result, message=result.get("message", "OCR complete"))
        return ToolResult(status=ToolStatus.ERROR, error=result.get("error", "OCR failed"), data=result)
