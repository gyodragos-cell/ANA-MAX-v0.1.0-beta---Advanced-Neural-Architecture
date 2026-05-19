#!/usr/bin/env python3
"""
ANA MAX - Vision-Based GUI Fallback (Inspirat din UI-TARS)
===========================================================
Când UI Automation nu găsește elemente, fallback la Vision AI.

Features:
- Screenshot + Vision LLM analysis
- Click by coordinates
- Text recognition and element detection
- Works with any application (even non-standard UIs)
- Hybrid approach: UIA first, Vision fallback

Author: ANA MAX Team (2026-05-19)
Inspired by: UI-TARS Desktop Vision-Based GUI Control
"""

import os
import base64
import logging
import requests
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

# Add project root to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

logger = logging.getLogger(__name__)


@dataclass
class VisionElement:
    """Represents a detected UI element via vision."""
    label: str
    confidence: float
    bounding_box: Tuple[int, int, int, int]  # (x, y, width, height)
    center: Tuple[int, int]  # (x, y)
    element_type: str = "unknown"  # button, input, text, icon, etc.


class VisionGUIFallback:
    """
    Vision-based GUI control fallback.
    
    When UI Automation fails, use Vision AI to:
    1. Take screenshot
    2. Analyze with Vision LLM
    3. Get element coordinates
    4. Click/type at coordinates
    
    Supported Vision Providers:
    - OpenAI GPT-4V
    - Anthropic Claude Vision
    - Google Gemini Vision
    - Local VLM (optional)
    """
    
    def __init__(self, provider: str = "openai", api_key: str = None, model: str = None):
        self.provider = provider.lower()
        self.api_key = api_key or os.environ.get(f"{self.provider.upper()}_API_KEY")
        
        # Default models
        if model:
            self.model = model
        elif self.provider == "openai":
            self.model = "gpt-4-vision-preview"
        elif self.provider == "anthropic":
            self.model = "claude-3-5-sonnet-20241022"
        elif self.provider == "google":
            self.model = "gemini-1.5-pro"
        else:
            raise ValueError(f"Unsupported provider: {provider}")
        
        logger.info(f"Vision GUI Fallback initialized (provider={provider}, model={model})")
    
    def take_screenshot(self, region: Tuple[int, int, int, int] = None) -> bytes:
        """Take a screenshot and return as bytes."""
        try:
            from tools.desktop_capture import DesktopCaptureTool
            capture_tool = DesktopCaptureTool()
            
            if region:
                result = capture_tool.execute(
                    action="capture_region",
                    x=region[0], y=region[1],
                    width=region[2], height=region[3]
                )
            else:
                result = capture_tool.execute(action="capture")
            
            if result.is_success:
                screenshot_path = result.data.get("screenshot_path")
                if screenshot_path:
                    with open(screenshot_path, 'rb') as f:
                        return f.read()
            
            logger.error(f"Screenshot failed: {result.error}")
            return None
            
        except Exception as e:
            logger.error(f"Screenshot error: {e}")
            return None
    
    def encode_image_to_base64(self, image_bytes: bytes) -> str:
        """Encode image bytes to base64 string."""
        return base64.b64encode(image_bytes).decode('utf-8')
    
    def analyze_with_vision(self, screenshot: bytes, query: str) -> Dict[str, Any]:
        """
        Analyze screenshot with Vision LLM.
        
        Args:
            screenshot: Screenshot bytes
            query: What to look for (e.g., "Find the login button")
        
        Returns:
            Dict with elements, coordinates, and confidence
        """
        base64_image = self.encode_image_to_base64(screenshot)
        
        if self.provider == "openai":
            return self._call_openai_vision(base64_image, query)
        elif self.provider == "anthropic":
            return self._call_anthropic_vision(base64_image, query)
        elif self.provider == "google":
            return self._call_google_vision(base64_image, query)
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")
    
    def _call_openai_vision(self, base64_image: str, query: str) -> Dict[str, Any]:
        """Call OpenAI GPT-4V for vision analysis."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a GUI element detector. Analyze the screenshot and find UI elements. "
                        "Return JSON with: elements array containing {label, confidence, bounding_box (x,y,w,h), element_type}. "
                        "Element types: button, input, text, icon, image, link, menu, checkbox, dropdown."
                    )
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": f"Find: {query}"},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 2000
        }
        
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            content = data['choices'][0]['message']['content']
            # Parse JSON response
            import json
            try:
                return json.loads(content)
            except:
                return {"error": "Failed to parse response", "raw": content}
        else:
            return {"error": f"API error: {response.status_code}", "details": response.text}
    
    def _call_anthropic_vision(self, base64_image: str, query: str) -> Dict[str, Any]:
        """Call Anthropic Claude Vision for analysis."""
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "max_tokens": 2000,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": base64_image
                            }
                        },
                        {
                            "type": "text",
                            "text": f"Analyze this GUI screenshot and find: {query}. Return JSON with elements array."
                        }
                    ]
                }
            ]
        }
        
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            content = data['content'][0]['text']
            import json
            try:
                return json.loads(content)
            except:
                return {"error": "Failed to parse response", "raw": content}
        else:
            return {"error": f"API error: {response.status_code}", "details": response.text}
    
    def _call_google_vision(self, base64_image: str, query: str) -> Dict[str, Any]:
        """Call Google Gemini Vision for analysis."""
        import json
        
        headers = {
            "Content-Type": "application/json"
        }
        
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": f"Analyze this GUI screenshot and find: {query}. Return JSON with elements array."
                        },
                        {
                            "inline_data": {
                                "mime_type": "image/png",
                                "data": base64_image
                            }
                        }
                    ]
                }
            ],
            "generationConfig": {
                "maxOutputTokens": 2000
            }
        }
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            content = data['candidates'][0]['content']['parts'][0]['text']
            try:
                return json.loads(content)
            except:
                return {"error": "Failed to parse response", "raw": content}
        else:
            return {"error": f"API error: {response.status_code}", "details": response.text}
    
    def click_element(self, element: VisionElement) -> bool:
        """Click on element by coordinates."""
        try:
            import pyautogui
            
            x, y = element.center
            logger.info(f"Clicking element '{element.label}' at ({x}, {y})")
            
            pyautogui.click(x, y)
            return True
            
        except Exception as e:
            logger.error(f"Click error: {e}")
            return False
    
    def type_at_element(self, element: VisionElement, text: str) -> bool:
        """Click on element and type text."""
        try:
            import pyautogui
            
            x, y = element.center
            logger.info(f"Typing at element '{element.label}' at ({x}, {y})")
            
            pyautogui.click(x, y)
            pyautogui.typewrite(text, interval=0.05)
            return True
            
        except Exception as e:
            logger.error(f"Type error: {e}")
            return False
    
    def find_element(self, query: str, region: Tuple[int, int, int, int] = None) -> Optional[VisionElement]:
        """
        Find a single element in the GUI.
        
        Args:
            query: What to find (e.g., "Login button")
            region: Optional region to search (x, y, width, height)
        
        Returns:
            VisionElement or None
        """
        # Take screenshot
        screenshot = self.take_screenshot(region)
        if not screenshot:
            return None
        
        # Analyze with vision
        result = self.analyze_with_vision(screenshot, query)
        
        if "error" in result:
            logger.error(f"Vision analysis failed: {result['error']}")
            return None
        
        # Parse elements
        elements = result.get("elements", [])
        if not elements:
            logger.warning(f"No elements found for query: {query}")
            return None
        
        # Return best match
        best_element = max(elements, key=lambda e: e.get("confidence", 0))
        
        return VisionElement(
            label=best_element.get("label", "unknown"),
            confidence=best_element.get("confidence", 0.0),
            bounding_box=tuple(best_element.get("bounding_box", [0, 0, 0, 0])),
            center=tuple(best_element.get("bounding_box", [0, 0, 0, 0])[:2]),
            element_type=best_element.get("element_type", "unknown")
        )
    
    def find_all_elements(self, query: str, region: Tuple[int, int, int, int] = None) -> List[VisionElement]:
        """
        Find all matching elements in the GUI.
        
        Args:
            query: What to find
            region: Optional region
        
        Returns:
            List of VisionElement
        """
        screenshot = self.take_screenshot(region)
        if not screenshot:
            return []
        
        result = self.analyze_with_vision(screenshot, query)
        
        if "error" in result:
            return []
        
        elements = result.get("elements", [])
        
        return [
            VisionElement(
                label=e.get("label", "unknown"),
                confidence=e.get("confidence", 0.0),
                bounding_box=tuple(e.get("bounding_box", [0, 0, 0, 0])),
                center=(
                    e.get("bounding_box", [0, 0])[0] + e.get("bounding_box", [0, 0, 0, 0])[2] // 2,
                    e.get("bounding_box", [0, 0, 0, 0])[1] + e.get("bounding_box", [0, 0, 0, 0])[3] // 2
                ),
                element_type=e.get("element_type", "unknown")
            )
            for e in elements
        ]


# Singleton instance
_vision_instance = None


def get_vision_fallback(provider: str = "openai", api_key: str = None) -> VisionGUIFallback:
    """Get or create VisionGUIFallback singleton."""
    global _vision_instance
    
    if _vision_instance is None:
        _vision_instance = VisionGUIFallback(provider=provider, api_key=api_key)
    
    return _vision_instance


if __name__ == "__main__":
    # Test vision fallback
    vision = get_vision_fallback(provider="openai")
    
    # Find element
    element = vision.find_element("Login button")
    
    if element:
        print(f"Found: {element.label}")
        print(f"Confidence: {element.confidence}")
        print(f"Center: {element.center}")
        print(f"Type: {element.element_type}")
        
        # Click it
        vision.click_element(element)
    else:
        print("Element not found")
