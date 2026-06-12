"""Capture a precise desktop region for vision/OCR follow-up."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus


class VisionRegionCaptureTool(Tool):
    def __init__(self) -> None:
        self.output_dir = Path(__file__).resolve().parents[1] / "screenshots"

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="vision_region_capture",
            description="Capture a desktop crop by x,y,width,height and return compact image metadata.",
            parameters=[
                ToolParameter("x", "Left coordinate", "integer", True),
                ToolParameter("y", "Top coordinate", "integer", True),
                ToolParameter("width", "Region width", "integer", True),
                ToolParameter("height", "Region height", "integer", True),
                ToolParameter("output_file", "Optional PNG filename", "string", False),
            ],
            category="desktop",
            dangerous=True,
        )

    def execute(self, x: int, y: int, width: int, height: int, **kwargs: Any) -> ToolResult:
        x, y, width, height = int(x), int(y), int(width), int(height)
        if width <= 0 or height <= 0:
            return ToolResult(status=ToolStatus.ERROR, error="width and height must be positive")
        if width > 8000 or height > 8000:
            return ToolResult(status=ToolStatus.ERROR, error="region is too large")

        filename = kwargs.get("output_file") or f"region_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        output = self.output_dir / Path(str(filename)).name
        try:
            from PIL import ImageGrab, ImageStat

            self.output_dir.mkdir(exist_ok=True)
            image = ImageGrab.grab(bbox=(x, y, x + width, y + height))
            image.save(output, "PNG")
            rgb = image.convert("RGB")
            stat = ImageStat.Stat(rgb)
            data = {
                "file": str(output),
                "region": {"x": x, "y": y, "width": width, "height": height},
                "bytes": output.stat().st_size,
                "mean_rgb": [round(v, 2) for v in stat.mean],
            }
            return ToolResult(status=ToolStatus.SUCCESS, data=data, message="Region captured")
        except Exception as exc:
            return ToolResult(status=ToolStatus.ERROR, error=f"Region capture failed: {exc}")
