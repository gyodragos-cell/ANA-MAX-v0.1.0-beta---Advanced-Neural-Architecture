"""Find a visual element by template matching."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional, Tuple

from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus


class VisionFindElementTool(Tool):
    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="vision_find_element",
            description="Find a template image on screen or inside an image using OpenCV template matching.",
            parameters=[
                ToolParameter("template_path", "Template image path", "string", True),
                ToolParameter("image_path", "Optional source image path; if omitted captures screen", "string", False),
                ToolParameter("threshold", "Minimum confidence 0.0-1.0", "number", False, 0.8),
                ToolParameter("region", "Optional screen region x,y,width,height", "string", False),
            ],
            category="desktop",
        )

    def execute(self, template_path: str, **kwargs: Any) -> ToolResult:
        try:
            import cv2
            import numpy as np
            from PIL import ImageGrab
        except Exception as exc:
            return ToolResult(status=ToolStatus.ERROR, error=f"OpenCV/Pillow unavailable: {exc}")

        template = Path(template_path).expanduser().resolve()
        if not template.exists():
            return ToolResult(status=ToolStatus.ERROR, error=f"Template not found: {template}")

        threshold = float(kwargs.get("threshold") or 0.8)
        if not 0 <= threshold <= 1:
            return ToolResult(status=ToolStatus.ERROR, error="threshold must be between 0 and 1")

        source_path = kwargs.get("image_path")
        region = self._parse_region(kwargs.get("region"))
        try:
            if source_path:
                source_img = cv2.imread(str(Path(str(source_path)).expanduser().resolve()))
            else:
                bbox = None
                offset_x = offset_y = 0
                if region:
                    x, y, w, h = region
                    bbox = (x, y, x + w, y + h)
                    offset_x, offset_y = x, y
                else:
                    offset_x = offset_y = 0
                pil_img = ImageGrab.grab(bbox=bbox)
                source_img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

            template_img = cv2.imread(str(template))
            if source_img is None or template_img is None:
                return ToolResult(status=ToolStatus.ERROR, error="Could not load source or template image")

            result = cv2.matchTemplate(source_img, template_img, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(result)
            h, w = template_img.shape[:2]
            offset_x = region[0] if region and not source_path else 0
            offset_y = region[1] if region and not source_path else 0
            center = {"x": int(max_loc[0] + w // 2 + offset_x), "y": int(max_loc[1] + h // 2 + offset_y)}
            data = {
                "found": bool(max_val >= threshold),
                "confidence": round(float(max_val), 4),
                "threshold": threshold,
                "center": center,
                "box": {"x": int(max_loc[0] + offset_x), "y": int(max_loc[1] + offset_y), "width": int(w), "height": int(h)},
            }
            return ToolResult(status=ToolStatus.SUCCESS, data=data, message="Template search complete")
        except Exception as exc:
            return ToolResult(status=ToolStatus.ERROR, error=f"Template search failed: {exc}")

    def _parse_region(self, value: Any) -> Optional[Tuple[int, int, int, int]]:
        if not value:
            return None
        parts = [int(p.strip()) for p in str(value).split(",")]
        if len(parts) != 4:
            raise ValueError("region must be x,y,width,height")
        if parts[2] <= 0 or parts[3] <= 0:
            raise ValueError("region width/height must be positive")
        return parts[0], parts[1], parts[2], parts[3]
