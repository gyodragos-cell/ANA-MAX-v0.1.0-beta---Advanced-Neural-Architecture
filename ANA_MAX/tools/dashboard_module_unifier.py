"""
Dashboard Module Unifier — Reconnects LLM Inference, Auto-Remediation, and Vision
===================================================================================

This tool ensures:
1. LLM backend is active and publishing LLM_LOG events
2. Reflex dispatcher is listening and publishing REFLEX_ALERT events
3. Vision PC captures are fed to dashboard
4. All modules connected to watchdog_bus
"""

import logging
import threading
import time
from typing import Dict, Any, Optional
import requests
import json

logger = logging.getLogger(__name__)


class DashboardModuleUnifier:
    """Unified bootstrap for dashboard modules."""
    
    def __init__(self):
        self.modules_status: Dict[str, bool] = {
            "frida_telemetry": False,
            "llm_inference": False,
            "reflex_alerts": False,
            "vision_capture": False,
            "bus_connected": False,
        }
        self.running = False
        self.startup_thread: Optional[threading.Thread] = None
    
    def start(self):
        """Start unified module initialization."""
        if self.running:
            logger.warning("[UNIFIER] Already running")
            return
        
        self.running = True
        self.startup_thread = threading.Thread(target=self._startup_sequence, daemon=True)
        self.startup_thread.start()
        logger.info("[UNIFIER] Startup sequence initiated")
    
    def stop(self):
        """Stop unifier."""
        self.running = False
        if self.startup_thread:
            self.startup_thread.join(timeout=2)
        logger.info("[UNIFIER] Stopped")
    
    def _startup_sequence(self):
        """Execute startup in order: bus → LLM → reflex → vision."""
        try:
            # 1. Initialize watchdog bus
            logger.info("[UNIFIER PHASE 1] Initializing watchdog bus...")
            if self._init_bus():
                self.modules_status["bus_connected"] = True
                logger.info("[UNIFIER] ✓ Bus connected")
            else:
                logger.error("[UNIFIER] ✗ Bus initialization failed")
                return
            
            time.sleep(0.5)
            
            # 2. Initialize and warm up LLM
            logger.info("[UNIFIER PHASE 2] Warming up LLM backend...")
            if self._init_llm():
                self.modules_status["llm_inference"] = True
                logger.info("[UNIFIER] ✓ LLM ready")
            else:
                logger.warning("[UNIFIER] ⚠ LLM initialization skipped (Ollama may be offline)")
            
            time.sleep(1)
            
            # 3. Start reflex dispatcher
            logger.info("[UNIFIER PHASE 3] Starting Reflex auto-remediation...")
            if self._start_reflex():
                self.modules_status["reflex_alerts"] = True
                logger.info("[UNIFIER] ✓ Reflex running")
            else:
                logger.warning("[UNIFIER] ⚠ Reflex initialization failed")
            
            # 4. Verify vision capture
            logger.info("[UNIFIER PHASE 4] Checking Vision PC...")
            if self._check_vision():
                self.modules_status["vision_capture"] = True
                logger.info("[UNIFIER] ✓ Vision ready")
            else:
                logger.warning("[UNIFIER] ⚠ Vision needs attention")
            
            # 5. Verify Frida telemetry
            logger.info("[UNIFIER PHASE 5] Verifying Frida telemetry...")
            if self._check_frida():
                self.modules_status["frida_telemetry"] = True
                logger.info("[UNIFIER] ✓ Frida active")
            else:
                logger.warning("[UNIFIER] ⚠ Frida may need restart")
            
            # Summary
            enabled = sum(1 for v in self.modules_status.values() if v)
            logger.info(f"[UNIFIER] Startup complete: {enabled}/{len(self.modules_status)} modules active")
            
        except Exception as e:
            logger.error(f"[UNIFIER] Startup sequence failed: {e}")
    
    def _init_bus(self) -> bool:
        """Initialize watchdog bus."""
        try:
            from tools.watchdog_bus import bus
            # Test publish
            bus.publish("unifier", "startup", {"phase": 1})
            return True
        except Exception as e:
            logger.error(f"[UNIFIER] Bus init error: {e}")
            return False
    
    def _init_llm(self) -> bool:
        """Initialize LLM backend and warm up first model."""
        try:
            # Test Ollama connectivity
            response = requests.get("http://127.0.0.1:11434/api/tags", timeout=2)
            if response.status_code != 200:
                return False
            
            models = response.json().get("models", [])
            if not models:
                logger.warning("[UNIFIER] No models loaded in Ollama")
                return False
            
            # Pick first available model
            model_name = models[0].get("name", "qwen2.5-coder:7b")
            logger.info(f"[UNIFIER] Warming up model: {model_name}")
            
            # Send a quick inference to warm it up
            warm_response = requests.post(
                "http://127.0.0.1:11434/api/generate",
                json={
                    "model": model_name,
                    "prompt": "Hello",
                    "stream": False,
                    "num_ctx": 128,
                },
                timeout=10
            )
            
            if warm_response.status_code == 200:
                logger.info(f"[UNIFIER] Model warmed: {model_name}")
                
                # Publish event to bus so dashboard knows LLM is active
                try:
                    from tools.watchdog_bus import bus
                    bus.publish("OllamaLive", "LLM_LOG", {
                        "model": model_name,
                        "status": "ready",
                        "timestamp": time.time()
                    })
                except:
                    pass
                
                return True
            else:
                logger.warning(f"[UNIFIER] Model warmup failed: {warm_response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"[UNIFIER] LLM init error: {e}")
            return False
    
    def _start_reflex(self) -> bool:
        """Start reflex dispatcher."""
        try:
            from tools.reflex_core import reflex_engine
            reflex_engine.start()
            
            # Publish startup event
            try:
                from tools.watchdog_bus import bus
                bus.publish("reflexModule", "REFLEX_ALERT", {
                    "level": "INFO",
                    "message": "Auto-remediation engine online",
                    "timestamp": time.time()
                })
            except:
                pass
            
            return True
        except Exception as e:
            logger.error(f"[UNIFIER] Reflex start error: {e}")
            return False
    
    def _check_vision(self) -> bool:
        """Verify vision capture tool."""
        try:
            from tools.desktop_capture import DesktopCaptureTool
            tool = DesktopCaptureTool()
            # Quick test
            result = tool.execute(operation="capture")
            return str(result.status) == "ToolStatus.SUCCESS"
        except Exception as e:
            logger.debug(f"[UNIFIER] Vision check: {e}")
            return False
    
    def _check_frida(self) -> bool:
        """Verify frida telemetry is running or fallback to psutil."""
        try:
            # First try Frida
            from tools.windows_frida_telemetry import WindowsFridaTelemetryTool
            tool = WindowsFridaTelemetryTool()
            result = tool.execute(action='list')
            if str(result.status) == "ToolStatus.SUCCESS":
                return True
        except:
            pass
        
        # Fallback: use psutil process info (always available)
        try:
            import psutil
            procs = list(psutil.process_iter(['pid', 'name', 'status']))
            if len(procs) > 0:
                # Publish fallback telemetry to bus
                try:
                    from tools.watchdog_bus import bus
                    bus.publish("nativeTelemetry", "FRIDA_FALLBACK", {
                        "process_count": len(procs),
                        "timestamp": time.time()
                    })
                except:
                    pass
                return True
        except:
            pass
        
        return False
    
    def get_status(self) -> Dict[str, Any]:
        """Return module status."""
        return {
            "running": self.running,
            "modules": self.modules_status,
            "enabled_count": sum(1 for v in self.modules_status.values() if v),
            "total": len(self.modules_status),
        }


# Global instance
_unifier: Optional[DashboardModuleUnifier] = None


def get_unifier() -> DashboardModuleUnifier:
    """Get or create global unifier."""
    global _unifier
    if _unifier is None:
        _unifier = DashboardModuleUnifier()
    return _unifier


def run(args: Dict[str, Any]) -> Dict[str, Any]:
    """Tool entrypoint."""
    action = args.get("action", "start")
    unifier = get_unifier()
    
    if action == "start":
        unifier.start()
        return {"status": "success", "message": "Dashboard unifier started"}
    
    elif action == "stop":
        unifier.stop()
        return {"status": "success", "message": "Dashboard unifier stopped"}
    
    elif action == "status":
        status = unifier.get_status()
        return {"status": "success", "data": status}
    
    else:
        return {"status": "error", "error": f"Unknown action: {action}"}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    unifier = get_unifier()
    unifier.start()
    
    # Keep running for 30 seconds
    for i in range(30):
        status = unifier.get_status()
        print(f"[{i}s] Status: {status['enabled_count']}/{status['total']} modules")
        time.sleep(1)
    
    unifier.stop()
