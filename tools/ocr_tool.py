"""
ANA MAX - OCR Tool (Optical Character Recognition)
tools/ocr_tool.py

OCR pe ecran, regiune, fisier sau clipboard
Suporta PaddleOCR (recomandat) sau Tesseract (fallback)
"""

import logging
from typing import Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)

# OCR engine (lazy loading)
_ocr_engine = None
_ocr_backend = None  # "paddle" or "tesseract"


def run(args: Dict[str, Any]) -> Dict[str, Any]:
    """OCR tool entry point."""
    action = args.get("action")
    
    if action == "check":
        return _check_engine()
    elif action == "screen":
        return _ocr_screen(args)
    elif action == "file":
        return _ocr_file(args)
    elif action == "clipboard":
        return _ocr_clipboard(args)
    elif action == "region":
        return _ocr_region(args)
    else:
        return {"status": "error", "error": f"Unknown action: {action}"}


def _check_engine() -> Dict[str, Any]:
    """Check OCR engine availability."""
    try:
        engine, backend = _get_engine()
        return {
            "status": "success",
            "available": True,
            "backend": backend,
            "message": f"OCR engine loaded: {backend}"
        }
    except Exception as e:
        return {
            "status": "error",
            "available": False,
            "error": str(e),
            "message": "OCR engine not available. Install: pip install paddleocr paddlepaddle pillow"
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
        _ocr_engine = PaddleOCR(
            use_angle_cls=False,  # Faster for straight text
            lang='en',
            quiet=True  # Suppress verbose logging
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
    """Perform OCR on PIL Image."""
    try:
        engine, backend = _get_engine()
        
        if backend == "paddle":
            # PaddleOCR returns list of [box, (text, confidence)]
            result = engine.ocr(img, cls=False)
            
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
            
            return {
                "status": "success",
                "backend": "paddle",
                "text": full_text,
                "lines": texts,
                "line_count": len(texts),
                "average_confidence": round(avg_confidence, 3)
            }
        
        elif backend == "tesseract":
            # Tesseract returns plain text
            full_text = engine.image_to_string(img)
            
            return {
                "status": "success",
                "backend": "tesseract",
                "text": full_text,
                "lines": full_text.split("\n"),
                "line_count": len(full_text.split("\n"))
            }
        
        else:
            return {"status": "error", "error": f"Unknown backend: {backend}"}
    
    except Exception as e:
        return {"status": "error", "error": str(e)}
