import threading
import time
import logging
import os
from datetime import datetime
from typing import Dict, Any
from pathlib import Path

from tools.watchdog_bus import bus
from core.event_stream import get_event_stream

logger = logging.getLogger(__name__)

class OmniSenseWatcher:
    """
    OS-27 Proactive Background Agent (Omni-Sense Vision).
    - Subscribes to telemetry events (RAM/CPU).
    - Runs a background vision thread to capture screen, perform OCR, index memory and detect anomalies.
    """
    def __init__(self):
        self._lock = threading.Lock()
        self._last_alert_time = 0
        self._alert_cooldown = 300 
        
        self.RAM_CRITICAL_PERCENT = 90.0
        self.CPU_CRITICAL_PERCENT = 95.0
        
        self._running_vision = False
        self._vision_thread = None
        self._vision_interval = 10.0  # seconds
        self._last_image_hash = None
        
        self._screenshot_path = Path("ANA_MAX/sandbox/omni_vision_current.png")

    def start(self):
        logger.info("[OMNI-SENSE] Starting proactive background watcher...")
        bus.subscribe(self._handle_event)
        
        self._running_vision = True
        self._vision_thread = threading.Thread(target=self._vision_loop, daemon=True)
        self._vision_thread.start()
        
        logger.info("[OMNI-SENSE] Omni-Sense active (Telemetry + Vision).")

    def stop(self):
        bus.unsubscribe(self._handle_event)
        self._running_vision = False
        if self._vision_thread:
            self._vision_thread.join(timeout=2.0)
        logger.info("[OMNI-SENSE] Stopped proactive background watcher.")

    def _handle_event(self, event: Dict[str, Any]):
        try:
            event_type = event.get("type", "")
            if event_type == "telemetry.system":
                self._analyze_system_telemetry(event.get("data", {}))
        except Exception as e:
            logger.error(f"[OMNI-SENSE] Error handling event: {e}")

    def _analyze_system_telemetry(self, data: Dict[str, Any]):
        ram = data.get("memory_percent", 0.0)
        cpu = data.get("cpu_percent", 0.0)
        
        alert_msg = None
        if ram >= self.RAM_CRITICAL_PERCENT:
            alert_msg = f"RAM-ul a atins nivelul critic de {ram}%. Sistemul tau este sub presiune extrema."
        elif cpu >= self.CPU_CRITICAL_PERCENT:
            alert_msg = f"CPU-ul ruleaza la {cpu}%. Sistemul este incarcat masiv."
            
        if alert_msg:
            with self._lock:
                now = time.time()
                if now - self._last_alert_time > self._alert_cooldown:
                    self._last_alert_time = now
                    self._push_alert_to_chat(alert_msg)

    def _compute_image_hash(self, path: Path):
        """Simple perceptual hash using cv2 to detect if screen changed significantly."""
        try:
            import cv2
            img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
            if img is None: return None
            resized = cv2.resize(img, (9, 8))
            diff = resized[:, 1:] > resized[:, :-1]
            return sum([2 ** i for (i, v) in enumerate(diff.flatten()) if v])
        except:
            return None

    def _vision_loop(self):
        """Background loop that captures screen, compares delta, runs OCR and indexes memory."""
        # Lazy load tools to avoid circular imports / startup delay
        desktop_tool = None
        ocr_tool = None
        cortex = None
        
        try:
            from tools.desktop_capture import DesktopCaptureTool
            from tools.ocr_tool import OcrTool
            from tools.memory_cortex import MemoryCortex
            desktop_tool = DesktopCaptureTool()
            ocr_tool = OcrTool()
            cortex = MemoryCortex()
        except Exception as e:
            logger.error(f"[OMNI-SENSE] Failed to load vision tools: {e}")
            return

        while self._running_vision:
            try:
                # 1. Capture Screen
                self._screenshot_path.parent.mkdir(parents=True, exist_ok=True)
                res = desktop_tool.execute(action="screenshot", output_file=str(self._screenshot_path))
                
                if res.is_success and self._screenshot_path.exists():
                    # 2. Delta Check
                    current_hash = self._compute_image_hash(self._screenshot_path)
                    
                    if current_hash and self._last_image_hash:
                        # Compare hashes (hamming distance)
                        dist = bin(current_hash ^ self._last_image_hash).count('1')
                        if dist < 5:  # Screen hasn't changed much
                            time.sleep(self._vision_interval)
                            continue
                            
                    self._last_image_hash = current_hash
                    
                    # 3. Run VLM Engine
                    try:
                        from core.vision.vlm_engine import VLMDaemon
                        if not hasattr(self, '_vlm_daemon'):
                            self._vlm_daemon = VLMDaemon()
                            
                        vlm_res = self._vlm_daemon.analyze_image(str(self._screenshot_path))
                        
                        if vlm_res:
                            # 4. Save to Memory Cortex
                            try:
                                details = vlm_res.get("details", "")
                                intent = vlm_res.get("intent", "")
                                if details:
                                    cortex.remember("episodic", "omni_sense_vision", f"Screen intent: {intent}. Details: {details}")
                            except:
                                pass
                                
                            # 5. Proactive Intervention if error detected
                            if vlm_res.get("error_visible", False):
                                self._analyze_vision_heuristics(vlm_res.get("details", "Eroare detectata vizual."))
                    except Exception as ve:
                        logger.error(f"[OMNI-SENSE] VLM Error: {ve}")
                            
            except Exception as e:
                logger.debug(f"[OMNI-SENSE] Vision loop error: {e}")
                
            time.sleep(self._vision_interval)

    def _analyze_vision_heuristics(self, text: str):
        """Analyze extracted text for triggers."""
        triggers = ["Exception", "Traceback (most recent call last)", "Error:", "Failed to compile", "SyntaxError:"]
        
        for trigger in triggers:
            if trigger.lower() in text.lower():
                with self._lock:
                    now = time.time()
                    if now - self._last_alert_time > self._alert_cooldown:
                        self._last_alert_time = now
                        self._push_alert_to_chat(
                            f"Am detectat o eroare pe ecranul tau ('{trigger}'). Vrei sa activez Qwen pentru a o investiga si rezolva automat?"
                        )
                break

    def _push_alert_to_chat(self, msg: str):
        """Pushes the message to the user chat via SSE."""
        formatted_alert = (
            f"**[OMNI-SENSE PROACTIVE VISION]**\\n"
            f"> {msg}\\n\\n"
            f"*(Sunt agentul tau de fundal OS-27. Observ ecranul si sunt gata sa intervin!)*"
        )
        logger.warning(f"[OMNI-SENSE] Triggering chat alert: {msg}")
        
        try:
            stream = get_event_stream()
            stream.emit(
                event_type="conversation",
                source="omni-sense",
                data={
                    "role": "assistant",
                    "content": formatted_alert,
                    "timestamp": datetime.now().isoformat()
                }
            )
        except Exception as e:
            logger.error(f"[OMNI-SENSE] Failed to push alert: {e}")

# Global instance
_omnisense_instance = None

def start_omnisense():
    global _omnisense_instance
    if _omnisense_instance is None:
        _omnisense_instance = OmniSenseWatcher()
    if not getattr(_omnisense_instance, '_running_vision', False):
        _omnisense_instance.start()

def stop_omnisense():
    global _omnisense_instance
    if _omnisense_instance is not None:
        _omnisense_instance.stop()
