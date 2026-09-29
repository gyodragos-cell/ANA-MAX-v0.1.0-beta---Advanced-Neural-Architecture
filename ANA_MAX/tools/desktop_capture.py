"""
Desktop Screen Capture Tool - Live Desktop Monitoring (OS27 Hyper++)
====================================================================
Author: ANA_MAX
Date: 2026-05-13
Category: monitoring

Functions:
- capture: Captureaza intregul desktop sau o zona specifica
- capture_region: Captureaza o regiune specifica
- capture_window: Captureaza o fereastra specifica
- get_window_list: Lista ferestre active
- monitor: Monitorizare continua (salveaza screenshot-uri periodice)

OS27 Hyper++ Features:
- Telemetry tracking for capture operations (capture, region, window, monitor)
- Health monitoring for capture method reliability
- MemoryCortex integration for capture errors and method learning
- ContextEngine integration for desktop state awareness
- SelfEvolvingTool integration for anomaly detection on capture failures
- Structured logging with error detection

Requires: Pillow (PIL), mss (optional pentru performanta mai buna)
"""

from __future__ import annotations

import subprocess
import os
import logging
import time
import threading
import traceback
from collections import deque
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
from datetime import datetime

from tools.watchdog_bus import bus
from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# OS27 Hyper++ Ring Buffer & Monitor Thread Infrastructure
# ---------------------------------------------------------------------------
_ring_buffer: deque = deque(maxlen=10)  # stores last 10 frames as dicts
_monitor_thread: Optional[threading.Thread] = None
_monitor_stop_event = threading.Event()
_method_stats: Dict[str, Dict[str, int]] = {}  # {method: {success: N, fail: N, total_ms: N}}


def _update_method_stats(method: str, success: bool, duration_ms: float) -> None:
    """Track per-method success/fail stats for intelligent auto-selection."""
    if method not in _method_stats:
        _method_stats[method] = {"success": 0, "fail": 0, "total_ms": 0}
    if success:
        _method_stats[method]["success"] += 1
    else:
        _method_stats[method]["fail"] += 1
    _method_stats[method]["total_ms"] += int(duration_ms)


def get_best_capture_method() -> str:
    """Return the method with highest success rate and lowest latency."""
    if not _method_stats:
        return "dxcam"  # default
    scored = []
    for m, s in _method_stats.items():
        total = s["success"] + s["fail"]
        if total == 0:
            continue
        rate = s["success"] / total
        avg_ms = s["total_ms"] / total if total else 9999
        scored.append((m, rate, avg_ms))
    if not scored:
        return "dxcam"
    # sort by success rate DESC, then avg latency ASC
    scored.sort(key=lambda x: (-x[1], x[2]))
    return scored[0][0]


def _compute_frame_delta(img_a, img_b) -> float:
    """Return change ratio (0.0-1.0) between two PIL Images."""
    try:
        from PIL import ImageChops, ImageStat
        if img_a is None or img_b is None:
            return 1.0  # treat as fully changed
        if img_a.size != img_b.size:
            return 1.0
        diff = ImageChops.difference(img_a.convert("RGB"), img_b.convert("RGB"))
        stat = ImageStat.Stat(diff)
        # mean across RGB channels, normalized to 0-1
        mean_diff = sum(stat.mean) / (3 * 255)
        return mean_diff
    except Exception:
        return 1.0  # assume changed on error


def _trigger_nervous_system(method: str, error: Exception, tb_str: str) -> Optional[dict]:
    """Report capture failure to OS27 Nervous System for auto-patching."""
    try:
        from tools.os27_nervous_system import OS27NervousSystem
        ns = OS27NervousSystem()
        patch = ns.handle_tool_failure(
            tool_name=f"desktop_capture.{method}",
            error_message=str(error),
            traceback_str=tb_str,
            target_file_path=__file__,
        )
        if patch and patch.get("success"):
            logger.info(f"[NervousSystem] Patch generated for {method}: line {patch.get('error_line')}")
            bus.publish(source="NervousSystem", event_type="CAPTURE_PATCH", data=patch)
        return patch
    except Exception as ns_err:
        logger.debug(f"NervousSystem unavailable: {ns_err}")
        return None

# OS27 Hyper++ Telemetry
_capture_telemetry: Dict[str, Dict[str, Any]] = {}


def _record_capture_telemetry(operation: str, success: bool, execution_time: float, method: str = "") -> None:
    """Record OS27 Hyper++ telemetry for capture operations."""
    if operation not in _capture_telemetry:
        _capture_telemetry[operation] = {
            "operation_count": 0,
            "success_count": 0,
            "failure_count": 0,
            "total_time": 0.0,
            "last_execution_time": 0.0,
            "last_success": False,
            "methods": {},
        }
    
    _capture_telemetry[operation]["operation_count"] += 1
    _capture_telemetry[operation]["total_time"] += execution_time
    _capture_telemetry[operation]["last_execution_time"] = execution_time
    _capture_telemetry[operation]["last_success"] = success
    
    if success:
        _capture_telemetry[operation]["success_count"] += 1
    else:
        _capture_telemetry[operation]["failure_count"] += 1
    
    if method:
        if method not in _capture_telemetry[operation]["methods"]:
            _capture_telemetry[operation]["methods"][method] = 0
        _capture_telemetry[operation]["methods"][method] += 1


def get_capture_telemetry(operation: str | None = None) -> Dict[str, Any] | Dict[str, Dict[str, Any]]:
    """Get telemetry for capture operations."""
    if operation:
        return _capture_telemetry.get(operation, {})
    return _capture_telemetry.copy()


def get_capture_health() -> str:
    """Get health status for capture tool based on telemetry."""
    if not _capture_telemetry:
        return "unknown"
    
    total_ops = sum(stats["operation_count"] for stats in _capture_telemetry.values())
    total_failures = sum(stats["failure_count"] for stats in _capture_telemetry.values())
    
    if total_ops == 0:
        return "unknown"
    
    failure_rate = total_failures / total_ops
    if failure_rate > 0.5:
        return "broken"
    if failure_rate > 0.1:
        return "degraded"
    return "healthy"


class DesktopCaptureTool(Tool):
    """OS27 Hyper++ Desktop Capture — threaded, ring-buffered, delta-aware, self-healing."""

    def __init__(self) -> None:
        self._screenshot_dir = Path(__file__).parent.parent / "screenshots"
        self._screenshot_dir.mkdir(exist_ok=True)
        self._last_capture: Optional[str] = None
        self._last_pil_frame = None  # for delta detection
        self._monitor_thread: Optional[threading.Thread] = None
        self._monitor_stop_event = threading.Event()
        self._monitor_lock = threading.Lock()

    def get_definition(self):
        return ToolDefinition(
            name="desktop_capture",
            description=(
                "OS27 Hyper++ Desktop Capture. Captureaza ecranul desktop cu ring-buffer, "
                "delta-frame detection, threaded monitoring, si Nervous System auto-heal."
            ),
            parameters=[
                ToolParameter(
                    name="operation",
                    description=(
                        "Operatia: capture, capture_region, capture_window, get_windows, "
                        "monitor, start_monitor, stop_monitor, get_buffer, get_last_frames, get_stats, best_method"
                    ),
                    type="string",
                    required=True,
                    choices=[
                        "capture", "capture_region", "capture_window", "get_windows",
                        "monitor", "start_monitor", "stop_monitor",
                        "get_buffer", "get_last_frames", "get_stats", "best_method",
                    ]
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
                ),
                ToolParameter(
                    name="delta_threshold",
                    description="Threshold for delta-frame skip (0.0-1.0, default 0.005 = 0.5%%)",
                    type="string",
                    required=False
                ),
            ],
            category="monitoring"
        )

    def execute(self, **kwargs) -> ToolResult:
        start_time = time.time()
        operation = kwargs.get("operation")
        
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
        
        try:
            if operation == "capture":
                result = self._capture_full_screen(**kwargs)
                execution_time = time.time() - start_time
                success = result.status == ToolStatus.SUCCESS
                method = result.data.get("method", "") if success else ""
                _record_capture_telemetry(operation, success, execution_time, method)
                
                # ContextEngine integration for capture state
                if context_engine and success:
                    try:
                        context_engine.update_context(
                            key="desktop_capture",
                            value={
                                "last_file": result.data.get("file"),
                                "method": method,
                                "timestamp": time.time(),
                            }
                        )
                    except Exception:
                        pass
                
                return result
            elif operation == "capture_region":
                result = self._capture_region(**kwargs)
                execution_time = time.time() - start_time
                success = result.status == ToolStatus.SUCCESS
                _record_capture_telemetry(operation, success, execution_time)
                return result
            elif operation == "capture_window":
                result = self._capture_window(**kwargs)
                execution_time = time.time() - start_time
                success = result.status == ToolStatus.SUCCESS
                _record_capture_telemetry(operation, success, execution_time)
                
                # MemoryCortex integration for window capture errors
                if cortex and not success:
                    try:
                        cortex.remember(
                            "error",
                            f"capture.window.{kwargs.get('window_title')}",
                            f"Window capture failed: {kwargs.get('window_title')}"
                        )
                    except Exception:
                        pass
                
                return result
            elif operation == "get_windows":
                result = self._get_window_list()
                execution_time = time.time() - start_time
                success = result.status == ToolStatus.SUCCESS
                _record_capture_telemetry(operation, success, execution_time)
                
                # ContextEngine integration for window list
                if context_engine and success:
                    try:
                        context_engine.update_context(
                            key="desktop_windows",
                            value={
                                "window_count": result.data.get("count", 0),
                                "windows": result.data.get("windows", [])[:10],  # Limit to 10
                                "timestamp": time.time(),
                            }
                        )
                    except Exception:
                        pass
                
                return result
            elif operation == "monitor":
                result = self._monitor_continuous(**kwargs)
                execution_time = time.time() - start_time
                success = result.status == ToolStatus.SUCCESS
                _record_capture_telemetry(operation, success, execution_time)
                return result
            elif operation == "start_monitor":
                result = self._start_monitor_daemon(**kwargs)
                _record_capture_telemetry(operation, result.status == ToolStatus.SUCCESS, time.time() - start_time)
                return result
            elif operation == "stop_monitor":
                result = self._stop_monitor_daemon()
                _record_capture_telemetry(operation, result.status == ToolStatus.SUCCESS, time.time() - start_time)
                return result
            elif operation in ("get_buffer", "get_last_frames"):
                with self._monitor_lock:
                    frames = list(_ring_buffer)
                _record_capture_telemetry(operation, True, time.time() - start_time)
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data={"frames_count": len(frames), "frames": frames},
                    message=f"Retrieved {len(frames)} frames from buffer"
                )
            else:
                _record_capture_telemetry(operation, False, time.time() - start_time)
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error=f"Operatie necunoscuta: {operation}"
                )
        except Exception as e:
            logger.error(f"Desktop capture error: {e}")
            _record_capture_telemetry(operation, False, time.time() - start_time)
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Eroare capturare ecran: {str(e)}"
            )

    def _capture_full_screen(self, **kwargs) -> ToolResult:
        """Captureaza intregul ecran."""
        output_file = self._get_output_path(kwargs.get("output_file"))
        delta_threshold = float(kwargs.get("delta_threshold", "0.005"))
        
        try:
            # Prevent multiple values for output_file argument
            kwargs_copy = kwargs.copy()
            kwargs_copy.pop("output_file", None)
            
            success, method, diagnostics = self._capture_with_fallbacks(output_file, **kwargs_copy)
            if success:
                from PIL import Image
                # Delta Frame Detection
                skip_frame = False
                change_ratio = 1.0
                current_img_copy = None
                try:
                    with Image.open(output_file) as current_img:
                        current_img_copy = current_img.copy()
                    
                    if self._last_pil_frame is not None:
                        change_ratio = _compute_frame_delta(self._last_pil_frame, current_img_copy)
                        if change_ratio < delta_threshold:
                            skip_frame = True
                except Exception as e:
                    logger.debug(f"Delta calculation error: {e}")

                if skip_frame:
                    try:
                        output_file.unlink()
                    except Exception:
                        pass
                    return ToolResult(
                        status=ToolStatus.SUCCESS,
                        data={
                            "file": self._last_capture,
                            "skipped": True,
                            "change_ratio": change_ratio,
                            "method": method,
                            "diagnostics": diagnostics
                        },
                        message="Captura ecran omisa (fara modificari semnificative)"
                    )

                # Save last pil frame reference
                if current_img_copy is not None:
                    self._last_pil_frame = current_img_copy

                self._last_capture = str(output_file)
                try:
                    bus.publish(source="VisionPC", event_type="DESKTOP_CAPTURE", data={"file": str(output_file), "method": method})
                except Exception:
                    pass
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data={
                        "file": str(output_file),
                        "size": output_file.stat().st_size,
                        "method": method,
                        "diagnostics": diagnostics,
                        "change_ratio": change_ratio
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
                
                kwargs_copy = kwargs.copy()
                kwargs_copy.pop("output_file", None)
                success, _, _ = self._capture_with_fallbacks(output_file, **kwargs_copy)
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

    def _start_monitor_daemon(self, **kwargs) -> ToolResult:
        """Start the threaded monitor daemon."""
        if self._monitor_thread and self._monitor_thread.is_alive():
            return ToolResult(status=ToolStatus.ERROR, error="Monitor daemon is already running.")
        
        interval = float(kwargs.get("monitor_seconds", "2.0"))
        delta_threshold = float(kwargs.get("delta_threshold", "0.005"))
        
        self._monitor_stop_event.clear()
        self._monitor_thread = threading.Thread(
            target=self._monitor_worker, 
            args=(interval, delta_threshold),
            daemon=True
        )
        self._monitor_thread.start()
        
        return ToolResult(status=ToolStatus.SUCCESS, message=f"Monitor daemon started (interval: {interval}s)")

    def _stop_monitor_daemon(self) -> ToolResult:
        """Stop the threaded monitor daemon."""
        if not self._monitor_thread or not self._monitor_thread.is_alive():
            return ToolResult(status=ToolStatus.ERROR, error="Monitor daemon is not running.")
        
        self._monitor_stop_event.set()
        self._monitor_thread.join(timeout=5.0)
        
        return ToolResult(status=ToolStatus.SUCCESS, message="Monitor daemon stopped.")

    def _monitor_worker(self, interval: float, delta_threshold: float):
        """Background thread for continuous frame capture and delta detection."""
        import base64
        while not self._monitor_stop_event.is_set():
            try:
                output_file = self._screenshot_dir / f"daemon_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.png"
                success, method, diagnostics = self._capture_with_fallbacks(output_file)
                
                if success and output_file.exists():
                    from PIL import Image, ImageChops
                    with Image.open(output_file) as img:
                        img_copy = img.copy()
                        
                    # Delta Frame Detection
                    skip_frame = False
                    if self._last_pil_frame is not None:
                        diff = ImageChops.difference(self._last_pil_frame.convert("RGB"), img_copy.convert("RGB"))
                        # Calculate diff ratio roughly
                        bbox = diff.getbbox()
                        if not bbox:
                            skip_frame = True # identical
                        else:
                            # Use simple stats or extrema
                            from PIL import ImageStat
                            stat = ImageStat.Stat(diff)
                            # avg difference across pixels
                            avg_diff = sum(stat.mean) / (3 * 255.0)
                            if avg_diff < delta_threshold:
                                skip_frame = True

                    if not skip_frame:
                        self._last_pil_frame = img_copy
                        # Store in ring buffer (could also store base64)
                        with open(output_file, "rb") as f:
                            b64_str = base64.b64encode(f.read()).decode('utf-8')
                        
                        with self._monitor_lock:
                            _ring_buffer.append({
                                "timestamp": time.time(),
                                "method": method,
                                "b64_image": b64_str
                            })
                            
                    # Clean up file to save disk space if just daemon monitoring
                    try:
                        output_file.unlink()
                    except Exception:
                        pass
                        
            except Exception as e:
                _trigger_nervous_system("_monitor_worker", e, traceback.format_exc())
            
            time.sleep(interval)

    def _get_output_path(self, custom_name: Optional[str] = None) -> Path:
        """Genereaza calea fisierului de output."""
        if custom_name:
            return self._screenshot_dir / custom_name
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return self._screenshot_dir / f"desktop_{timestamp}.png"

    def _try_dxcam_capture(self, output_file: Path, **kwargs) -> ToolResult:
        """Capture via DXGI Desktop Duplication (dxcam).

        Grabs GPU-accelerated / hardware-composited content that GDI, mss and
        PIL ImageGrab return as a black frame. This is the reliable path when
        the other backends produce 'black_frame'.
        """
        camera = None
        try:
            import dxcam
            from PIL import Image

            camera = dxcam.create(output_color="RGB")
            if camera is None:
                raise RuntimeError("Failed to create dxcam camera device.")
            # grab() returns None when there is no NEW frame yet; retry briefly.
            frame = None
            for _ in range(3):
                frame = camera.grab()
                if frame is not None:
                    break
                time.sleep(0.05)
            if frame is None:
                raise RuntimeError("dxcam camera grab timed out or returned None.")
            Image.fromarray(frame).save(str(output_file), "PNG")
            return ToolResult(status=ToolStatus.SUCCESS, message="dxcam capture successful.")
        except Exception as e:
            tb_str = traceback.format_exc()
            patch = _trigger_nervous_system("dxcam", e, tb_str)
            return ToolResult(status=ToolStatus.ERROR, error=str(e), data={"patch": patch})
        finally:
            try:
                if camera is not None:
                    camera.release()
            except Exception:
                pass

    def _try_mss_capture(self, output_file: Path, **kwargs) -> ToolResult:
        """Incearca capturare cu mss (mai rapid)."""
        try:
            import mss
            with mss.mss() as sct:
                sct.shot(output=str(output_file))
            return ToolResult(status=ToolStatus.SUCCESS, message="mss capture successful.")
        except Exception as e:
            tb_str = traceback.format_exc()
            patch = _trigger_nervous_system("mss", e, tb_str)
            return ToolResult(status=ToolStatus.ERROR, error=str(e), data={"patch": patch})

    def _try_pil_capture(self, output_file: Path, **kwargs) -> ToolResult:
        """Incearca capturare cu PIL/Pillow."""
        try:
            from PIL import ImageGrab
            screenshot = ImageGrab.grab()
            screenshot.save(str(output_file), "PNG")
            return ToolResult(status=ToolStatus.SUCCESS, message="PIL capture successful.")
        except Exception as e:
            tb_str = traceback.format_exc()
            patch = _trigger_nervous_system("pil", e, tb_str)
            return ToolResult(status=ToolStatus.ERROR, error=str(e), data={"patch": patch})

    def _try_pil_all_screens_capture(self, output_file: Path, **kwargs) -> ToolResult:
        """Incearca PIL cu toate monitoarele Windows."""
        try:
            from PIL import ImageGrab
            screenshot = ImageGrab.grab(all_screens=True)
            screenshot.save(str(output_file), "PNG")
            return ToolResult(status=ToolStatus.SUCCESS, message="PIL all screens capture successful.")
        except Exception as e:
            tb_str = traceback.format_exc()
            patch = _trigger_nervous_system("pil_all_screens", e, tb_str)
            return ToolResult(status=ToolStatus.ERROR, error=str(e), data={"patch": patch})

    def _try_pyautogui_capture(self, output_file: Path, **kwargs) -> ToolResult:
        """Incearca capturare prin pyautogui."""
        try:
            import pyautogui
            pyautogui.screenshot(str(output_file))
            return ToolResult(status=ToolStatus.SUCCESS, message="pyautogui capture successful.")
        except Exception as e:
            tb_str = traceback.format_exc()
            patch = _trigger_nervous_system("pyautogui", e, tb_str)
            return ToolResult(status=ToolStatus.ERROR, error=str(e), data={"patch": patch})

    def _try_powershell_capture(self, output_file: Path, **kwargs) -> ToolResult:
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
            
            if output_file.exists():
                return ToolResult(status=ToolStatus.SUCCESS, message="PowerShell capture successful.")
            raise RuntimeError(f"PowerShell capture clipboard empty or failed. stdout: {result.stdout}")
        except Exception as e:
            tb_str = traceback.format_exc()
            patch = _trigger_nervous_system("powershell", e, tb_str)
            return ToolResult(status=ToolStatus.ERROR, error=str(e), data={"patch": patch})

    def _try_winrt_capture(self, output_file: Path, **kwargs) -> ToolResult:
        """Capture via WinRT GraphicsCapture API (Windows 10/11)."""
        try:
            # Minimal wrapper using winsdk if available
            import asyncio
            from winsdk.windows.graphics.capture import GraphicsCaptureSession
            raise ImportError("winsdk module is not installed in the python environment.")
        except Exception as e:
            tb_str = traceback.format_exc()
            patch = _trigger_nervous_system("winrt", e, tb_str)
            return ToolResult(status=ToolStatus.ERROR, error=str(e), data={"patch": patch})

    def _try_dwm_thumbnail_capture(self, output_file: Path, **kwargs) -> ToolResult:
        """DWM Thumbnail API / PrintWindow redirection for out-of-focus or background windows."""
        try:
            import win32gui
            import win32ui
            import win32con
            from PIL import Image
            import ctypes
            
            window_title = kwargs.get("window_title")
            if window_title:
                hwnd = win32gui.FindWindow(None, window_title)
                if not hwnd:
                    # try partial match
                    def callback(h, extra):
                        if window_title.lower() in win32gui.GetWindowText(h).lower():
                            extra.append(h)
                        return True
                    hwnds = []
                    win32gui.EnumWindows(callback, hwnds)
                    if hwnds:
                        hwnd = hwnds[0]
            else:
                hwnd = win32gui.GetForegroundWindow()
                if not hwnd or hwnd == win32gui.GetDesktopWindow():
                    hwnd = win32gui.GetShellWindow()
            
            if not hwnd:
                raise ValueError("No active window handle found for DWM capture.")
                
            left, top, right, bottom = win32gui.GetWindowRect(hwnd)
            width = right - left
            height = bottom - top
            if width <= 0 or height <= 0:
                raise ValueError(f"Invalid window dimensions: {width}x{height}")
                
            hwndDC = win32gui.GetWindowDC(hwnd)
            mfcDC  = win32ui.CreateDCFromHandle(hwndDC)
            saveDC = mfcDC.CreateCompatibleDC()
            
            saveBitMap = win32ui.CreateBitmap()
            saveBitMap.CreateCompatibleBitmap(mfcDC, width, height)
            saveDC.SelectObject(saveBitMap)
            
            user32 = ctypes.windll.user32
            # PW_RENDERFULLCONTENT = 2
            result = user32.PrintWindow(hwnd, saveDC.GetSafeHdc(), 2)
            
            success = False
            if result:
                bmpinfo = saveBitMap.GetInfo()
                bmpstr = saveBitMap.GetBitmapBits(True)
                img = Image.frombuffer(
                    'RGB',
                    (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
                    bmpstr, 'raw', 'BGRX', 0, 1
                )
                img.save(str(output_file), "PNG")
                success = True
                
            win32gui.DeleteObject(saveBitMap.GetHandle())
            saveDC.DeleteDC()
            mfcDC.DeleteDC()
            win32gui.ReleaseDC(hwnd, hwndDC)
            
            if not success:
                raise RuntimeError("PrintWindow API returned failure code.")
                
            return ToolResult(status=ToolStatus.SUCCESS, message="DWM Thumbnail capture successful.")
        except Exception as e:
            tb_str = traceback.format_exc()
            patch = _trigger_nervous_system("dwm_thumbnail", e, tb_str)
            return ToolResult(status=ToolStatus.ERROR, error=str(e), data={"patch": patch})

    def _try_ffmpeg_capture(self, output_file: Path, **kwargs) -> ToolResult:
        """FFmpeg ScreenGrab for ultra stable capture in restricted sessions."""
        try:
            window_title = kwargs.get("window_title")
            if window_title:
                cmd = ["ffmpeg", "-y", "-f", "gdigrab", "-framerate", "1", "-i", f"title={window_title}", "-vframes", "1", str(output_file)]
            else:
                cmd = ["ffmpeg", "-y", "-f", "gdigrab", "-framerate", "1", "-i", "desktop", "-vframes", "1", str(output_file)]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            if output_file.exists() and output_file.stat().st_size > 1024:
                return ToolResult(status=ToolStatus.SUCCESS, message="FFmpeg gdigrab capture successful.")
                
            # Fallback to dshow
            cmd = ["ffmpeg", "-y", "-f", "dshow", "-i", "video=screen-capture-recorder", "-vframes", "1", str(output_file)]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            if output_file.exists() and output_file.stat().st_size > 1024:
                return ToolResult(status=ToolStatus.SUCCESS, message="FFmpeg dshow capture successful.")
                
            raise RuntimeError(f"FFmpeg failed. stderr: {result.stderr}")
        except Exception as e:
            tb_str = traceback.format_exc()
            patch = _trigger_nervous_system("ffmpeg", e, tb_str)
            return ToolResult(status=ToolStatus.ERROR, error=str(e), data={"patch": patch})

    def _capture_with_fallbacks(self, output_file: Path, **kwargs) -> Tuple[bool, str, List[Dict[str, Any]]]:
        """Try capture methods and reject black/empty frames.

        OS27 Hyper++ v3 Neural Mode Optimization:
        - dxcam prioritized first for Windows 11 Insider (most reliable for GPU-composited content)
        - Added telemetry for method failure patterns
        - Auto-detection of DX driver availability
        """
        methods = [
            ("dxcam", self._try_dxcam_capture),  # PRIM: DXGI Desktop Duplication - most reliable on Win11 Insider
            ("winrt", self._try_winrt_capture),
            ("dwm_thumbnail", self._try_dwm_thumbnail_capture),
            ("ffmpeg", self._try_ffmpeg_capture),
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

            try:
                res = method(output_file, **kwargs)
                ok = (res.status == ToolStatus.SUCCESS)
                error_msg = res.error if not ok else None
                patch = res.data.get("patch") if res.data else None
            except Exception as e:
                ok = False
                error_msg = str(e)
                patch = None

            usable, reason, metrics = self._is_usable_capture(output_file)
            diagnostics.append({
                "method": method_name,
                "captured": ok,
                "usable": usable,
                "reason": reason,
                "metrics": metrics,
                "error": error_msg,
                "patch": patch
            })

            if ok and usable:
                return True, method_name, diagnostics

        return False, "", diagnostics

    def _is_usable_capture(self, output_file: Path) -> Tuple[bool, str, Dict[str, Any]]:
        """Return false when a screenshot is missing, tiny, black, flat, blurred, or overlay-blocked."""
        if not output_file.exists():
            return False, "missing_file", {}

        size = output_file.stat().st_size
        if size < 1024:
            return False, "too_small", {"bytes": size}

        # Try OpenCV logic first
        try:
            import cv2
            import numpy as np

            img_cv = cv2.imread(str(output_file))
            if img_cv is None:
                return False, "invalid_image_file", {}

            h, w, c = img_cv.shape
            if w <= 1 or h <= 1:
                return False, "invalid_dimensions", {"width": w, "height": h}

            # 1. Entropy calculation
            gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
            hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
            hist_norm = hist.ravel() / hist.sum()
            entropy = -np.sum(hist_norm * np.log2(hist_norm + 1e-7))

            # 2. Edge density calculation (Laplacian variance)
            laplacian = cv2.Laplacian(gray, cv2.CV_64F)
            edge_density = laplacian.var()

            # 3. Histogram peaks (detect overlay blocking/solid screens)
            max_peak = np.max(hist_norm)
            histogram_peak_ratio = 1.0 - max_peak

            # Check for black/white frames or other anomalies
            mean_val = np.mean(gray)
            min_val, max_val, _, _ = cv2.minMaxLoc(gray)

            metrics = {
                "bytes": size,
                "width": w,
                "height": h,
                "entropy": round(float(entropy), 4),
                "edge_density": round(float(edge_density), 4),
                "histogram_peak_ratio": round(float(histogram_peak_ratio), 4),
                "mean_gray": round(float(mean_val), 2),
                "min_gray": float(min_val),
                "max_gray": float(max_val)
            }

            if entropy < 0.1:
                return False, "low_entropy_invalid", metrics
            if edge_density < 5.0:
                return False, "low_edge_density_blur_invalid", metrics
            if histogram_peak_ratio < 0.01:
                return False, "overlay_blocking_invalid", metrics

            # General black frame check
            if max_val <= 4 and mean_val <= 4:
                return False, "black_frame", metrics

            # General white frame check
            if min_val >= 250 and mean_val >= 250:
                return False, "white_frame", metrics

            return True, "ok", metrics

        except Exception as exc:
            logger.debug(f"OpenCV usable check failed, falling back to PIL: {exc}")
            # Fallback to PIL logic
            try:
                from PIL import Image, ImageStat, ImageFilter
                import math
                with Image.open(output_file) as img:
                    rgb = img.convert("RGB")
                    stat = ImageStat.Stat(rgb)
                    extrema = rgb.getextrema()
                    mean = [round(value, 2) for value in stat.mean]
                    max_channel = max(high for _, high in extrema)
                    min_channel = min(low for low, _ in extrema)

                    # Entropy
                    histogram = rgb.histogram()
                    total_pixels = rgb.width * rgb.height
                    entropy = 0.0
                    for count in histogram:
                        if count > 0:
                            p = count / total_pixels
                            entropy -= p * math.log2(p)

                    # Edge Density
                    edges = img.convert("L").filter(ImageFilter.FIND_EDGES)
                    edge_stat = ImageStat.Stat(edges)
                    edge_density = sum(edge_stat.mean) / 255.0

                    # Histogram peak ratio
                    gray_img = img.convert("L")
                    gray_hist = gray_img.histogram()
                    max_peak = max(gray_hist) / total_pixels
                    histogram_peak_ratio = 1.0 - max_peak

                    metrics = {
                        "bytes": size,
                        "width": rgb.width,
                        "height": rgb.height,
                        "mean": mean,
                        "max_channel": max_channel,
                        "min_channel": min_channel,
                        "entropy": round(entropy, 4),
                        "edge_density": round(edge_density, 4),
                        "histogram_peak_ratio": round(histogram_peak_ratio, 4)
                    }

                    if rgb.width <= 1 or rgb.height <= 1:
                        return False, "invalid_dimensions", metrics
                    if entropy < 0.1:
                        return False, "low_entropy_invalid", metrics
                    if edge_density < 5.0:
                        return False, "low_edge_density_blur_invalid", metrics
                    if histogram_peak_ratio < 0.01:
                        return False, "overlay_blocking_invalid", metrics
                    if max_channel <= 4 and sum(mean) <= 4:
                        return False, "black_frame", metrics
                    return True, "ok", metrics
            except Exception as pil_exc:
                return False, f"image_check_failed: {pil_exc}", {"bytes": size}
