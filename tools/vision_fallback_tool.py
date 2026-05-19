#!/usr/bin/env python3
"""
ANA MAX - Vision Fallback Tool
================================
Tool wrapper for Vision-Based GUI Fallback.

Author: ANA MAX Team (2026-05-19)
"""

import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus
from core.vision_fallback import get_vision_fallback


class VisionFallbackTool(Tool):
    """Vision-Based GUI Fallback Tool."""
    
    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="vision_fallback",
            description=(
                "Vision-based GUI control when UI Automation fails. "
                "Uses AI vision to find and interact with screen elements. "
                "Actions: find_element, click_element, type_text, analyze_screen"
            ),
            parameters=[
                ToolParameter(
                    name="action",
                    description="Action to perform",
                    type="string",
                    required=True,
                    choices=["find_element", "click_element", "type_text", "analyze_screen"]
                ),
                ToolParameter(
                    name="query",
                    description="What to find on screen (e.g., 'Login button')",
                    type="string",
                    required=False
                ),
                ToolParameter(
                    name="text",
                    description="Text to type (for type_text action)",
                    type="string",
                    required=False
                ),
                ToolParameter(
                    name="provider",
                    description="Vision provider: openai, anthropic, google",
                    type="string",
                    required=False,
                    choices=["openai", "anthropic", "google"],
                    default="openai"
                ),
                ToolParameter(
                    name="api_key",
                    description="API key for vision provider",
                    type="string",
                    required=False
                )
            ],
            category="vision"
        )
    
    def execute(self, action: str, **kwargs) -> ToolResult:
        try:
            provider = kwargs.get("provider", "openai")
            api_key = kwargs.get("api_key")
            
            vision = get_vision_fallback(provider=provider, api_key=api_key)
            
            if action == "find_element":
                return self._find_element(vision, **kwargs)
            elif action == "click_element":
                return self._click_element(vision, **kwargs)
            elif action == "type_text":
                return self._type_text(vision, **kwargs)
            elif action == "analyze_screen":
                return self._analyze_screen(vision, **kwargs)
            else:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error=f"Unknown action: {action}"
                )
        
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Vision fallback error: {e}"
            )
    
    def _find_element(self, vision, query: str = None, **kwargs) -> ToolResult:
        """Find element on screen."""
        if not query:
            return ToolResult(
                status=ToolStatus.ERROR,
                error="Query is required for find_element"
            )
        
        element = vision.find_element(query)
        
        if element:
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={
                    "label": element.label,
                    "confidence": element.confidence,
                    "center": element.center,
                    "element_type": element.element_type,
                    "bounding_box": element.bounding_box
                },
                message=f"Found '{element.label}' at {element.center}"
            )
        else:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Element not found: {query}"
            )
    
    def _click_element(self, vision, query: str = None, **kwargs) -> ToolResult:
        """Find and click element."""
        if not query:
            return ToolResult(
                status=ToolStatus.ERROR,
                error="Query is required for click_element"
            )
        
        element = vision.find_element(query)
        
        if element:
            success = vision.click_element(element)
            
            if success:
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data={"clicked": element.label, "position": element.center},
                    message=f"Clicked '{element.label}' at {element.center}"
                )
            else:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error="Failed to click element"
                )
        else:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Element not found: {query}"
            )
    
    def _type_text(self, vision, query: str = None, text: str = None, **kwargs) -> ToolResult:
        """Find element and type text."""
        if not query or not text:
            return ToolResult(
                status=ToolStatus.ERROR,
                error="Query and text are required for type_text"
            )
        
        element = vision.find_element(query)
        
        if element:
            success = vision.type_at_element(element, text)
            
            if success:
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data={"typed": text, "at": element.label},
                    message=f"Typed '{text}' at '{element.label}'"
                )
            else:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error="Failed to type text"
                )
        else:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Element not found: {query}"
            )
    
    def _analyze_screen(self, vision, query: str = None, **kwargs) -> ToolResult:
        """Analyze entire screen and list all elements."""
        query = query or "All UI elements"
        
        elements = vision.find_all_elements(query)
        
        if elements:
            elements_data = [
                {
                    "label": e.label,
                    "confidence": e.confidence,
                    "center": e.center,
                    "element_type": e.element_type
                }
                for e in elements
            ]
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"elements": elements_data, "count": len(elements)},
                message=f"Found {len(elements)} elements on screen"
            )
        else:
            return ToolResult(
                status=ToolStatus.ERROR,
                error="No elements found"
            )


if __name__ == "__main__":
    tool = VisionFallbackTool()
    
    # Test analyze
    result = tool.execute("analyze_screen", query="Buttons and inputs")
    print(f"Analyze: {result.message}")
    if result.data:
        print(f"Elements: {result.data.get('count', 0)}")
