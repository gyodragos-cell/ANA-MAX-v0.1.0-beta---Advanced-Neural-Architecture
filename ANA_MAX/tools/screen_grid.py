"""
OS-27 Computer Use Grid Tool (Faza 3)
======================================
tools/screen_grid.py

Combina OCR-ul existent (ocr_tool.py) cu coordonate (x,y) pentru fiecare cuvant/linie.
LLM-ul (Qwen) primeste un tabel simplu cu text -> click position.
Fara Vision models, fara VRAM overhead. 100% CPU.
"""

import sys
import os
import logging
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus

logger = logging.getLogger(__name__)


def _get_screen_grid_with_coords() -> dict:
    """
    Face screenshot + OCR cu coordonate bounding box complete.
    Returneaza o lista de elemente: {text, x_center, y_center, width, height}.
    """
    try:
        import mss
        import numpy as np
        import contextlib
        import io as _io

        with mss.mss() as sct:
            monitor = sct.monitors[1]  # Primary monitor
            screenshot = sct.grab(monitor)

        from PIL import Image
        img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
        img_array = np.array(img)
        screen_w = monitor["width"]
        screen_h = monitor["height"]


        # Try PaddleOCR (has bounding boxes)
        try:
            from paddleocr import PaddleOCR
            with contextlib.redirect_stdout(_io.StringIO()), contextlib.redirect_stderr(_io.StringIO()):
                ocr = PaddleOCR(use_angle_cls=False, lang='en', enable_mkldnn=False)
                result = ocr.ocr(img_array)

            grid_items = []
            if result and result[0]:
                try:
                    # Check if PaddleOCRv5/PaddleX dictionary format
                    if isinstance(result[0], dict) and "rec_texts" in result[0]:
                        res_dict = result[0]
                        texts = res_dict.get("rec_texts", [])
                        scores = res_dict.get("rec_scores", [])
                        polys = res_dict.get("dt_polys", [])
                        
                        for i in range(len(texts)):
                            text = texts[i]
                            confidence = scores[i]
                            box = polys[i]
                            
                            if confidence < 0.5 or not text.strip():
                                continue
                            
                            xs = [p[0] for p in box]
                            ys = [p[1] for p in box]
                            x_center = int(sum(xs) / 4)
                            y_center = int(sum(ys) / 4)
                            w = int(max(xs) - min(xs))
                            h = int(max(ys) - min(ys))
                            
                            grid_items.append({
                                "text": text.strip(),
                                "x": x_center,
                                "y": y_center,
                                "w": w,
                                "h": h,
                                "confidence": round(float(confidence), 2)
                            })
                    else:
                        # Legacy PaddleOCR format
                        for line in result[0]:
                            box = line[0]   # [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
                            text = line[1][0]
                            confidence = line[1][1]

                            if confidence < 0.5 or not text.strip():
                                continue

                            xs = [p[0] for p in box]
                            ys = [p[1] for p in box]
                            x_center = int(sum(xs) / 4)
                            y_center = int(sum(ys) / 4)
                            w = int(max(xs) - min(xs))
                            h = int(max(ys) - min(ys))

                            grid_items.append({
                                "text": text.strip(),
                                "x": x_center,
                                "y": y_center,
                                "w": w,
                                "h": h,
                                "confidence": round(float(confidence), 2)
                            })
                except Exception as ex:
                    return {"status": "error", "error": f"Parse error: {ex}. Raw result keys: {list(result[0].keys()) if isinstance(result[0], dict) else 'Not Dict'}"}

            return {
                "status": "success",
                "backend": "paddle",
                "screen_w": screen_w,
                "screen_h": screen_h,
                "element_count": len(grid_items),
                "grid": grid_items
            }

        except ImportError:
            # Tesseract fallback - no bounding boxes, just text
            import pytesseract
            data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
            grid_items = []
            for i, text in enumerate(data["text"]):
                text = text.strip()
                if not text or int(data["conf"][i]) < 30:
                    continue
                x = data["left"][i] + data["width"][i] // 2
                y = data["top"][i] + data["height"][i] // 2
                grid_items.append({
                    "text": text,
                    "x": x,
                    "y": y,
                    "w": data["width"][i],
                    "h": data["height"][i],
                    "confidence": round(int(data["conf"][i]) / 100, 2)
                })
            return {
                "status": "success",
                "backend": "tesseract",
                "screen_w": screen_w,
                "screen_h": screen_h,
                "element_count": len(grid_items),
                "grid": grid_items
            }

    except Exception as e:
        logger.error(f"[SCREEN-GRID] Error: {e}")
        return {"status": "error", "error": str(e)}


def _search_grid(grid_items, query):
    """Find the grid element best matching the query."""
    query_lower = query.lower()
    best_match = None
    for item in grid_items:
        if query_lower in item["text"].lower():
            # Prefer shorter (more exact) match
            if best_match is None or len(item["text"]) < len(best_match["text"]):
                best_match = item
    return best_match


def _format_grid_for_llm(grid_data: dict, top_n=50) -> str:
    """Format grid to a compact table the LLM can read without exploding context."""
    if grid_data.get("status") != "success":
        return f"Error getting grid: {grid_data.get('error')}"

    grid = grid_data["grid"][:top_n]
    screen_w = grid_data["screen_w"]
    screen_h = grid_data["screen_h"]
    backend = grid_data["backend"]

    lines = [
        f"[SCREEN GRID | {backend} | Resolution: {screen_w}x{screen_h} | Showing {len(grid)}/{grid_data['element_count']} elements]",
        f"{'#':<4} {'TEXT':<35} {'X':>6} {'Y':>6}",
        "-" * 55
    ]
    for i, item in enumerate(grid):
        text = item["text"][:33]
        lines.append(f"{i:<4} {text:<35} {item['x']:>6} {item['y']:>6}")

    lines.append("")
    lines.append("To click an element, use: mouse_click(x=<X>, y=<Y>)")
    lines.append("To search for text: rag_search_grid(query='button text')")
    return "\n".join(lines)


class ScreenGridTool(Tool):
    """OS-27 Computer Use — screenshot + OCR -> clickable grid for LLM."""

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="screen_grid",
            description=(
                "Take a screenshot and build a clickable grid using OCR (Zero-VRAM). "
                "Returns a table with: text label + (x, y) center coordinates. "
                "Use this when you need to see what's on screen and interact with UI elements. "
                "Optionally filter with 'search' to find specific text on screen."
            ),
            parameters=[
                ToolParameter(
                    name="search",
                    description="Optional: text to search in the OCR grid. If provided, returns only the matching element with its coordinates.",
                    type="string",
                    required=False
                )
            ],
            category="desktop"
        )

    def execute(self, params: dict = None, **kwargs) -> ToolResult:
        if params is None:
            params = kwargs

        search_query = params.get("search", "").strip()
        start = time.time()

        logger.info("[SCREEN-GRID] Starting screenshot + OCR grid build...")
        grid_data = _get_screen_grid_with_coords()
        elapsed = round(time.time() - start, 2)

        if grid_data.get("status") != "success":
            return ToolResult(
                status=ToolStatus.ERROR,
                error=grid_data.get("error", "Unknown error"),
                message=f"Screen grid failed after {elapsed}s"
            )

        logger.info(f"[SCREEN-GRID] Got {grid_data['element_count']} elements in {elapsed}s")

        # If search is provided, find the element
        if search_query:
            match = _search_grid(grid_data["grid"], search_query)
            if match:
                result_text = (
                    f"Found '{match['text']}' at coordinates X={match['x']}, Y={match['y']} "
                    f"(size: {match['w']}x{match['h']}, confidence: {match['confidence']})\n"
                    f"To click it: mouse_click(x={match['x']}, y={match['y']})"
                )
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data=result_text,
                    message=f"Grid search complete in {elapsed}s"
                )
            else:
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data=f"No element matching '{search_query}' found on screen. Try a different text fragment.",
                    message=f"Grid search: no match"
                )

        # Return full grid (condensed for LLM)
        formatted = _format_grid_for_llm(grid_data)
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data=formatted,
            message=f"Screen grid built in {elapsed}s — {grid_data['element_count']} elements found"
        )
