"""
ANA MAX - win32_telepathy_tool.py
===================================
Universal GUI Telepathy (Win32 + UIAutomation)

Controleaza GUI-ul aplicatiilor fara a misca cursorul de mouse.
Faza 1: Incearca UIAutomation (pentru aplicatii moderne, Electron, Browsere).
Faza 2: Fallback pe mesagerie nativa Win32 (SendMessage) pentru aplicatii clasice.
Invizibil si ultra-rapid.
"""
from __future__ import annotations

import ctypes
import logging
import time
from typing import Any

from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus

logger = logging.getLogger("ANA.UniversalTelepathy")

WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_CHAR = 0x0102

user32 = ctypes.windll.user32


def _find_window_by_title(title_substring: str) -> int:
    hwnds = []
    def callback(hwnd, extra):
        if user32.IsWindowVisible(hwnd):
            length = user32.GetWindowTextLengthW(hwnd)
            buff = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buff, length + 1)
            if title_substring.lower() in buff.value.lower():
                hwnds.append(hwnd)
        return True

    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)
    user32.EnumWindows(WNDENUMPROC(callback), 0)
    return hwnds[0] if hwnds else 0


def _send_text_to_hwnd(hwnd: int, text: str):
    child_hwnd = user32.GetWindow(hwnd, 5) # GW_CHILD
    target = child_hwnd if child_hwnd else hwnd
    for char in text:
        user32.PostMessageW(target, WM_CHAR, ord(char), 0)
        time.sleep(0.01)


def _try_uiautomation(title: str, text: str) -> bool:
    """Incearca sa foloseasca Microsoft UI Automation (suport Electron/Web)."""
    try:
        # Daca exista libraria uiautomation (comtypes-based)
        import uiautomation as auto
        window = auto.WindowControl(searchDepth=1, Name=title)
        if window.Exists(0, 0):
            edit = window.EditControl()
            if edit.Exists(0, 0):
                edit.SendKeys(text)
                return True
    except ImportError:
        logger.debug("Libraria 'uiautomation' nu este instalata. Fallback la Win32.")
    except Exception as e:
        logger.debug(f"UIAutomation a esuat: {e}")
    return False


class Win32TelepathyTool(Tool):
    """Controleaza ferestre invizibil (UIAutomation + Win32)."""

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="gui_telepathy",
            description="Trimite input direct in aplicatii (Electron, Web, Native) folosind injectare UIAutomation si Win32, fara mouse fizic.",
            parameters=[
                ToolParameter(
                    name="window_title",
                    description="Sub-string din titlul ferestrei (ex: 'Discord', 'Notepad').",
                    type="string",
                    required=True,
                ),
                ToolParameter(
                    name="text_payload",
                    description="Textul de injectat.",
                    type="string",
                    required=True,
                ),
            ],
            category="system",
        )

    def execute(self, **kwargs: Any) -> ToolResult:
        title = kwargs.get("window_title", "")
        payload = kwargs.get("text_payload", "")

        try:
            # 1. Incearca UIAutomation (Electron / Modern Apps)
            if _try_uiautomation(title, payload):
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data={"target": title, "method": "uiautomation"},
                    message="Payload injectat telepatic cu succes via UIAutomation."
                )
            
            # 2. Fallback la Win32 HWND (Classic Apps)
            hwnd = _find_window_by_title(title)
            if not hwnd:
                return ToolResult(status=ToolStatus.ERROR, error=f"Nu s-a gasit fereastra: {title}")
                
            _send_text_to_hwnd(hwnd, payload)
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"target_hwnd": hwnd, "method": "win32_postmessage"},
                message="Payload injectat telepatic cu succes via Win32 API."
            )
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=f"Eroare de injectare GUI: {e}")
