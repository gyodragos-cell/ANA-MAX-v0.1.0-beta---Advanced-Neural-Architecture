"""
Desktop Screen Capture Tool - Live Desktop Monitoring
Author: ANA_MAX
Date: 2026-05-13
Category: monitoring

Functions:
- capture: Captureaza intregul desktop sau o zona specifica
- capture_region: Captureaza o regiune specifica
- capture_window: Captureaza o fereastra specifica
- get_window_list: Lista ferestre active
- monitor: Monitorizare continua (salveaza screenshot-uri periodice)

Requires: Pillow (PIL), mss (optional pentru performanta mai buna)
"""

from __future__ import annotations

import subprocess
import os
import logging
import time
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
from datetime import datetime

from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus

logger = logging.getLogger(__name__)


class DesktopCaptureTool(Tool):
    """Tool pentru capturarea ecranului desktop - monitoring live."""

    def __init__(self) -> None:
        self._screenshot_dir = Path(__file__).parent.parent / "screenshots"
        self._screenshot_dir.mkdir(exist_ok=True)
        self._last_capture: Optional[str] = None

    def get_definition(self):
        return ToolDefinition(
            name="desktop_capture",
            description="Captureaza ecranul desktop pentru monitoring live. Poate captura intregul ecran, o regiune specifica sau o fereastra anume.",
            parameters=[
                ToolParameter(
                    name="operation",
                    description="Operatia: capture (intreg ecran), capture_region (zona), capture_window (fereastra), get_windows (lista ferestre), monitor (monitorizare continua)",
                    type="string",
                    required=True,
                    choices=["capture", "capture_region", "capture_window", "get_windows", "monitor"]
                ),
                ToolParameter(
                    name="output_file",
                    description="Nume fisier output (default: auto-generat cu timestamp)",
                    type="string",
                    required=False
                ),
                ToolParameter(
                    name="region",
                    description="Regiune pentru capture_region: 'x,y,width,height' (ex: '0,0,1920,1080')",
                    type="string",
                    required=False
                ),
                ToolParameter(
                    name="window_title",
                    description="Titlu fereastra pentru capture_window (ex: 'Chrome', 'Visual Studio Code')",
                    type="string",
                    required=False
                ),
                ToolParameter(
                    name="monitor_seconds",
                    description="Interval monitorizare in secunde (default: 5)",
                    type="string",
                    required=False
                ),
                ToolParameter(
                    name="monitor_count",
                    description="Numar captur pentru monitorizare (default: 10)",
                    type="string",
                    required=False
                )
            ],
            category="monitoring"
        )

    def execute(self, **kwargs) -> ToolResult:
        operation = kwargs.get("operation")
        
        try:
            if operation == "capture":
                return self._capture_full_screen(**kwargs)
            elif operation == "capture_region":
                return self._capture_region(**kwargs)
            elif operation == "capture_window":
                return self._capture_window(**kwargs)
            elif operation == "get_windows":
                return self._get_window_list()
            elif operation == "monitor":
                return self._monitor_continuous(**kwargs)
            else:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error=f"Operatie necunoscuta: {operation}"
                )
        except Exception as e:
            logger.error(f"Desktop capture error: {e}")
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Eroare capturare ecran: {str(e)}"
            )

    def _capture_full_screen(self, **kwargs) -> ToolResult:
        """Captureaza intregul ecran."""
        output_file = self._get_output_path(kwargs.get("output_file"))
        
        try:
            success, method, diagnostics = self._capture_with_fallbacks(output_file)
            if success:
                self._last_capture = str(output_file)
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data={
                        "file": str(output_file),
                        "size": output_file.stat().st_size,
                        "method": method,
                        "diagnostics": diagnostics,
                    },
                    message=f"Captura ecran salvata: {output_file.name}"
                )
            
            return ToolResult(
                status=ToolStatus.ERROR,
                error="Screen capture failed or returned a black frame",
                data={
                    "file": str(output_file) if output_file.exists() else None,
                    "diagnostics": diagnostics,
                    "hint": (
                        "Windows may be blocking screen capture in this session. "
                        "Use foreground_ui_snapshot/windows_uia_bridge as structural fallback."
                    ),
                },
            )
            
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Eroare capturare ecran: {str(e)}"
            )

    def _capture_region(self, **kwargs) -> ToolResult:
        """Captureaza o regiune specifica."""
        region_str = kwargs.get("region")
        if not region_str:
            return ToolResult(
                status=ToolStatus.ERROR,
                error="Parametrul 'region' este necesar. Format: 'x,y,width,height'"
            )
        
        try:
            x, y, width, height = map(int, region_str.split(","))
        except ValueError:
            return ToolResult(
                status=ToolStatus.ERROR,
                error="Format regiune invalid. Foloseste: 'x,y,width,height'"
            )
        
        output_file = self._get_output_path(kwargs.get("output_file"))
        
        try:
            from PIL import ImageGrab
            screenshot = ImageGrab.grab(bbox=(x, y, x + width, y + height))
            screenshot.save(str(output_file), "PNG")
            
            self._last_capture = output_file
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"file": str(output_file), "region": f"{x},{y},{width},{height}"},
                message=f"Captura regiune salvata: {output_file.name}"
            )
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Eroare capturare regiune: {str(e)}"
            )

    def _capture_window(self, **kwargs) -> ToolResult:
        """Captureaza o fereastra specifica."""
        window_title = kwargs.get("window_title")
        if not window_title:
            return ToolResult(
                status=ToolStatus.ERROR,
                error="Parametrul 'window_title' este necesar"
            )
        
        output_file = self._get_output_path(kwargs.get("output_file"))
        
        try:
            # Foloseste PowerShell pentru a gasi fereastra si a o captura
            ps_script = f"""
            Add-Type -AssemblyName System.Windows.Forms
            Add-Type -AssemblyName System.Drawing
            
            $windows = Get-Process | Where-Object {{ $_.MainWindowTitle -like '*{window_title}*' }} | Select-Object -First 1
            
            if ($windows) {{
                [System.Windows.Forms.SendKeys]::SendWait('%{{PRTSC}}')
                Start-Sleep -Milliseconds 500
                
                $bitmap = [System.Windows.Forms.Clipboard]::GetImage()
                if ($bitmap) {{
                    $bitmap.Save('{output_file}', [System.Drawing.Imaging.ImageFormat]::Png)
                    Write-Output "SUCCESS"
                }} else {{
                    Write-Output "NO_IMAGE"
                }}
            }} else {{
                Write-Output "NOT_FOUND"
            }}
            """
            
            result = subprocess.run(
                ["powershell", "-Command", ps_script],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if "SUCCESS" in result.stdout:
                self._last_capture = output_file
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data={"file": str(output_file), "window": window_title},
                    message=f"Captura fereastra '{window_title}' salvata: {output_file.name}"
                )
            elif "NOT_FOUND" in result.stdout:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error=f"Fereastra '{window_title}' nu a fost gasita"
                )
            else:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error=f"Eroare la capturare fereastra: {result.stderr}"
                )
                
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Eroare capturare fereastra: {str(e)}"
            )

    def _get_window_list(self) -> ToolResult:
        """Obtine lista ferestrelor active."""
        try:
            ps_script = """
            Get-Process | Where-Object { $_.MainWindowTitle -ne '' } | 
            Select-Object Id, ProcessName, MainWindowTitle | 
            ConvertTo-Json
            """
            
            result = subprocess.run(
                ["powershell", "-Command", ps_script],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            import json
            windows = json.loads(result.stdout) if result.stdout.strip() else []
            
            window_list = []
            for w in windows:
                window_list.append({
                    "pid": w.get("Id"),
                    "process": w.get("ProcessName"),
                    "title": w.get("MainWindowTitle")[:100]
                })
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"windows": window_list, "count": len(window_list)},
                message=f"Gasite {len(window_list)} ferestre active"
            )
            
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Eroare obtinere lista ferestre: {str(e)}"
            )

    def _monitor_continuous(self, **kwargs) -> ToolResult:
        """Monitorizare continua - multiple captur."""
        interval = int(kwargs.get("monitor_seconds", "5"))
        count = int(kwargs.get("monitor_count", "10"))
        
        captured_files = []
        
        try:
            for i in range(count):
                output_file = self._screenshot_dir / f"monitor_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{i+1:03d}.png"
                
                success, _, _ = self._capture_with_fallbacks(output_file)
                if success:
                    captured_files.append(str(output_file))
                    logger.info(f"Monitor capture {i+1}/{count}: {output_file.name}")
                
                if i < count - 1:
                    time.sleep(interval)
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"files": captured_files, "count": len(captured_files)},
                message=f"Monitorizare completa: {len(captured_files)} captur salvate"
            )
            
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Eroare monitorizare: {str(e)}",
                data={"files": captured_files}
            )

    def _get_output_path(self, custom_name: Optional[str] = None) -> Path:
        """Genereaza calea fisierului de output."""
        if custom_name:
            return self._screenshot_dir / custom_name
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return self._screenshot_dir / f"desktop_{timestamp}.png"

    def _try_mss_capture(self, output_file: Path) -> bool:
        """Incearca capturare cu mss (mai rapid)."""
        try:
            import mss
            with mss.mss() as sct:
                sct.shot(output=str(output_file))
            return True
        except ImportError:
            return False
        except Exception:
            return False

    def _try_pil_capture(self, output_file: Path) -> bool:
        """Incearca capturare cu PIL/Pillow."""
        try:
            from PIL import ImageGrab
            screenshot = ImageGrab.grab()
            screenshot.save(str(output_file), "PNG")
            return True
        except ImportError:
            return False
        except Exception:
            return False

    def _try_pil_all_screens_capture(self, output_file: Path) -> bool:
        """Incearca PIL cu toate monitoarele Windows."""
        try:
            from PIL import ImageGrab
            screenshot = ImageGrab.grab(all_screens=True)
            screenshot.save(str(output_file), "PNG")
            return True
        except ImportError:
            return False
        except Exception:
            return False

    def _try_pyautogui_capture(self, output_file: Path) -> bool:
        """Incearca capturare prin pyautogui."""
        try:
            import pyautogui
            pyautogui.screenshot(str(output_file))
            return True
        except ImportError:
            return False
        except Exception:
            return False

    def _try_powershell_capture(self, output_file: Path) -> bool:
        """Incearca capturare cu PowerShell."""
        try:
            ps_script = f"""
            Add-Type -AssemblyName System.Windows.Forms
            Add-Type -AssemblyName System.Drawing
            
            [System.Windows.Forms.SendKeys]::SendWait('%{{PRTSC}}')
            Start-Sleep -Milliseconds 500
            
            $bitmap = [System.Windows.Forms.Clipboard]::GetImage()
            if ($bitmap) {{
                $bitmap.Save('{output_file}', [System.Drawing.Imaging.ImageFormat]::Png)
            }}
            """
            
            result = subprocess.run(
                ["powershell", "-Command", ps_script],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            return output_file.exists()
            
        except Exception:
            return False

    def _capture_with_fallbacks(self, output_file: Path) -> Tuple[bool, str, List[Dict[str, Any]]]:
        """Try capture methods and reject black/empty frames."""
        methods = [
            ("mss", self._try_mss_capture),
            ("pil", self._try_pil_capture),
            ("pil_all_screens", self._try_pil_all_screens_capture),
            ("pyautogui", self._try_pyautogui_capture),
            ("powershell", self._try_powershell_capture),
        ]
        diagnostics: List[Dict[str, Any]] = []

        for method_name, method in methods:
            if output_file.exists():
                try:
                    output_file.unlink()
                except Exception:
                    pass

            ok = method(output_file)
            usable, reason, metrics = self._is_usable_capture(output_file)
            diagnostics.append({
                "method": method_name,
                "captured": ok,
                "usable": usable,
                "reason": reason,
                "metrics": metrics,
            })

            if ok and usable:
                return True, method_name, diagnostics

        return False, "", diagnostics

    def _is_usable_capture(self, output_file: Path) -> Tuple[bool, str, Dict[str, Any]]:
        """Return false when a screenshot is missing, tiny, or fully black."""
        if not output_file.exists():
            return False, "missing_file", {}

        size = output_file.stat().st_size
        if size < 1024:
            return False, "too_small", {"bytes": size}

        try:
            from PIL import Image, ImageStat
            with Image.open(output_file) as img:
                rgb = img.convert("RGB")
                stat = ImageStat.Stat(rgb)
                extrema = rgb.getextrema()
                mean = [round(value, 2) for value in stat.mean]
                max_channel = max(high for _, high in extrema)
                min_channel = min(low for low, _ in extrema)
                metrics = {
                    "bytes": size,
                    "width": rgb.width,
                    "height": rgb.height,
                    "mean": mean,
                    "max_channel": max_channel,
                    "min_channel": min_channel,
                }

                if rgb.width <= 1 or rgb.height <= 1:
                    return False, "invalid_dimensions", metrics
                if max_channel <= 8 and sum(mean) <= 8:
                    return False, "black_frame", metrics
                return True, "ok", metrics
        except Exception as exc:
            return False, f"image_check_failed: {exc}", {"bytes": size}
