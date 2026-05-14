"""
ANA MAX - Advanced Desktop Control Tool
=======================================
Control total asupra desktop-ului: Mouse, Tastatura, OCR (Optical Character Recognition).
Permite AI-ului sa opereze PC-ul exact ca un om.
"""

import os
import time
import logging
import subprocess
from typing import Optional, Dict, Any, List
from pathlib import Path

try:
    import pyautogui
    import pygetwindow as gw
    import pytesseract
    from PIL import Image
    import cv2
    import numpy as np
    
    # Fortam calea catre Tesseract (nu necesita restart PC sau setari de mediu)
    tesseract_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    if os.path.exists(tesseract_path):
        pytesseract.pytesseract.tesseract_cmd = tesseract_path
        
    HAS_DESKTOP_LIBS = True
except ImportError:
    HAS_DESKTOP_LIBS = False

from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus

logger = logging.getLogger(__name__)

class DesktopControlTool(Tool):
    def __init__(self):
        self.screenshot_dir = Path("screenshots")
        self.screenshot_dir.mkdir(exist_ok=True)
        pyautogui.FAILSAFE = False # Permitem controlul total

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="desktop_control",
            description="Control avansat desktop: click pe text, tastare, screenshot, OCR.",
            parameters=[
                ToolParameter(
                    name="operation",
                    description="Operatia: view, read_text, click_text, click_at, type, hotkey, move_window, click_image",
                    type="string",
                    required=True,
                    choices=["view", "read_text", "click_text", "click_at", "type", "hotkey", "move_window", "click_image"]
                ),
                ToolParameter(
                    name="target",
                    description="Textul cautat, coordonatele (x,y) sau textul de tastat",
                    type="string",
                    required=False
                ),
                ToolParameter(
                    name="window_title",
                    description="Titlul ferestrei pentru operatiuni specifice",
                    type="string",
                    required=False
                )
            ],
            category="desktop_automation"
        )

    def execute(self, operation: str, target: Optional[str] = None, window_title: Optional[str] = None, **kwargs) -> ToolResult:
        if not HAS_DESKTOP_LIBS:
            return ToolResult(status=ToolStatus.ERROR, error="Lipsesc librariile necesare (pyautogui, pygetwindow, pytesseract, Pillow).")

        try:
            if operation == "view":
                return self._view_screen()
            if operation == "read_text":
                return self._read_text()
            if operation == "click_at":
                return self._click_at(target)
            if operation == "type":
                return self._type_text(target)
            if operation == "hotkey":
                return self._send_hotkey(target)
            if operation == "click_text":
                return self._click_text(target, window_title)
            if operation == "click_image":
                return self._click_image(target, window_title)
            
            return ToolResult(status=ToolStatus.ERROR, error=f"Operatie necunoscuta: {operation}")
        except Exception as e:
            logger.error(f"Desktop control error: {e}")
            return ToolResult(status=ToolStatus.ERROR, error=str(e))

    def _view_screen(self) -> ToolResult:
        path = self.screenshot_dir / f"view_{int(time.time())}.png"
        pyautogui.screenshot(str(path))
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={"file": str(path)},
            message="Ecran capturat cu succes."
        )

    def _read_text(self) -> ToolResult:
        path = self.screenshot_dir / "temp_ocr.png"
        pyautogui.screenshot(str(path))
        text = pytesseract.image_to_string(Image.open(path))
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={"text": text},
            message="Textul a fost citit de pe ecran."
        )

    def _click_at(self, target: str) -> ToolResult:
        if not target: return ToolResult(status=ToolStatus.ERROR, error="Coordonate lipsa")
        x, y = map(int, target.replace(" ", "").split(","))
        pyautogui.click(x, y)
        return ToolResult(status=ToolStatus.SUCCESS, message=f"Click la ({x}, {y})")

    def _type_text(self, target: str) -> ToolResult:
        if not target: return ToolResult(status=ToolStatus.ERROR, error="Text lipsa")
        pyautogui.write(target, interval=0.05)
        return ToolResult(status=ToolStatus.SUCCESS, message=f"Text tastat: {target}")

    def _send_hotkey(self, target: str) -> ToolResult:
        if not target: return ToolResult(status=ToolStatus.ERROR, error="Taste lipsa (ex: ctrl,c)")
        keys = target.replace(" ", "").split(",")
        pyautogui.hotkey(*keys)
        return ToolResult(status=ToolStatus.SUCCESS, message=f"Hotkey trimis: {target}")

    def _click_text(self, target: str, window_title: Optional[str] = None) -> ToolResult:
        if not target: return ToolResult(status=ToolStatus.ERROR, error="Textul tinta lipseste")
        
        offset_x, offset_y = 0, 0
        region = None
        
        # Focus si izolare pe o anumita fereastra
        if window_title:
            windows = gw.getWindowsWithTitle(window_title)
            if not windows:
                return ToolResult(status=ToolStatus.ERROR, error=f"Fereastra '{window_title}' nu a fost gasita.")
            win = windows[0]
            try:
                win.activate()
                time.sleep(0.5)
            except:
                pass
            
            # Definim regiunea fix pe coordonatele ferestrei
            region = (win.left, win.top, win.width, win.height)
            offset_x, offset_y = win.left, win.top

        path = self.screenshot_dir / "click_search.png"
        
        if region:
            pyautogui.screenshot(str(path), region=region)
        else:
            pyautogui.screenshot(str(path))
        
        # OCR cu date de pozitionare
        data = pytesseract.image_to_data(Image.open(path), output_type=pytesseract.Output.DICT)
        
        # Cauta textul in rezultate
        for i, word in enumerate(data['text']):
            if target.lower() in word.lower() and word.strip():
                # Calculam X si Y locale + offset-ul ferestrei
                x = data['left'][i] + (data['width'][i] // 2) + offset_x
                y = data['top'][i] + (data['height'][i] // 2) + offset_y
                pyautogui.click(x, y)
                return ToolResult(status=ToolStatus.SUCCESS, message=f"Am gasit '{target}' in '{window_title or 'ecran complet'}' si am dat click la absolut ({x}, {y})")
        
        return ToolResult(status=ToolStatus.ERROR, error=f"Textul '{target}' nu a fost gasit.")

    def _click_image(self, target: str, window_title: Optional[str] = None) -> ToolResult:
        if not target or not os.path.exists(target):
            return ToolResult(status=ToolStatus.ERROR, error=f"Imaginea sablon '{target}' nu exista.")
        
        offset_x, offset_y = 0, 0
        region = None
        
        if window_title:
            windows = gw.getWindowsWithTitle(window_title)
            if not windows:
                return ToolResult(status=ToolStatus.ERROR, error=f"Fereastra '{window_title}' nu a fost gasita.")
            win = windows[0]
            try:
                win.activate()
                time.sleep(0.5)
            except:
                pass
            region = (win.left, win.top, win.width, win.height)
            offset_x, offset_y = win.left, win.top

        path = self.screenshot_dir / "click_image_search.png"
        if region:
            pyautogui.screenshot(str(path), region=region)
        else:
            pyautogui.screenshot(str(path))
            
        # Template Matching cu OpenCV
        img_rgb = cv2.imread(str(path))
        template = cv2.imread(target)
        
        if img_rgb is None or template is None:
            return ToolResult(status=ToolStatus.ERROR, error="Eroare la incarcarea imaginilor pentru OpenCV.")
            
        res = cv2.matchTemplate(img_rgb, template, cv2.TM_CCOEFF_NORMED)
        threshold = 0.8
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
        
        if max_val >= threshold:
            h, w = template.shape[:2]
            # Calculam centrul imaginii gasite
            center_x = max_loc[0] + w // 2 + offset_x
            center_y = max_loc[1] + h // 2 + offset_y
            pyautogui.click(center_x, center_y)
            return ToolResult(status=ToolStatus.SUCCESS, message=f"Imagine gasita (potrivire {max_val:.2f}) in '{window_title or 'ecran complet'}' -> click la ({center_x}, {center_y})")
            
        return ToolResult(status=ToolStatus.ERROR, error=f"Imaginea nu a fost gasita (scor maxim: {max_val:.2f} < {threshold}).")
