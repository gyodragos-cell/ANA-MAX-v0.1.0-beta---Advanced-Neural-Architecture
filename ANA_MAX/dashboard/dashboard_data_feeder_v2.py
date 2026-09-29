"""
Dashboard Data Feeder V3 - Thread-safe telemetry publisher with graceful shutdown and extended metrics.
Collects system metrics and publishes to watchdog_bus every few seconds.
"""

import threading
import time
import logging
import psutil
import os
from pathlib import Path
from queue import Queue, Empty
import warnings
warnings.filterwarnings("ignore", category=SyntaxWarning, module="pywinauto.*")

logger = logging.getLogger(__name__)

class DashboardFeederV3:
    """Collects system metrics and publishes to watchdog_bus for dashboard SSE."""

    def __init__(self, interval=3, procmon_audit_interval=30):
        self.interval = interval
        self.procmon_audit_interval = procmon_audit_interval
        self._stop_event = threading.Event()
        self._queue = Queue()
        self.thread = None
        self.publisher_thread = None
        self._procmon_audit_counter = 0

    def start(self):
        """Start the feeder daemon."""
        if self.thread and self.thread.is_alive():
            return

        self._stop_event.clear()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.publisher_thread = threading.Thread(target=self._publisher, daemon=True)
        self.thread.start()
        self.publisher_thread.start()
        logger.info(f"[FEEDER-V3] Started (interval={self.interval}s)")

    def stop(self):
        """Stop the feeder gracefully."""
        self._stop_event.set()
        if self.thread:
            self.thread.join(timeout=2)
        if self.publisher_thread:
            self.publisher_thread.join(timeout=2)
        logger.info("[FEEDER-V3] Stopped")

    def _collect_system_metrics(self):
        """Collect CPU, memory, disk, and temperature metrics."""
        try:
            temps = None
            if hasattr(psutil, "sensors_temperatures"):
                try:
                    temps = psutil.sensors_temperatures()
                except Exception:
                    pass
            cpu_temp = temps.get("coretemp", [{}])[0].get("current", None) if temps else None
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory_percent = psutil.virtual_memory().percent
            return {
                # Flat format (legacy)
                "cpu": cpu_percent,
                "memory": memory_percent,
                # Nested format (dashboard-compatible)
                "cpu_percent": cpu_percent,
                "memory_percent": memory_percent,
                "cpu_nested": {"percent": cpu_percent},
                "memory_nested": {"percent": memory_percent},
                # Additional metrics
                "disk": psutil.disk_usage('/').percent,
                "uptime": round(time.time() - psutil.boot_time(), 1),
                "cpu_temp": cpu_temp,
            }
        except Exception as e:
            logger.debug(f"[FEEDER-V3] System metrics error: {e}")
            return {}

    def _collect_processes(self):
        """Collect active process list."""
        try:
            procs = []
            for p in psutil.process_iter(['pid', 'name', 'status']):
                procs.append({'pid': p.pid, 'name': p.name(), 'status': p.status()})
            return procs[:10]
        except Exception as e:
            logger.debug(f"[FEEDER-V3] Process list error: {e}")
            return []

    def _collect_procmon_audit_status(self):
        """Collect Procmon Audit Status from blackbox_index.txt."""
        try:
            blackbox_index = Path("C:/blackbox_index.txt")
            if not blackbox_index.exists():
                # Fallback
                ana_max_root = Path(__file__).resolve().parent.parent
                blackbox_index = ana_max_root / "logs" / "blackbox_index.txt"
                
            if not blackbox_index.exists():
                return {"status": "Unknown", "emoji": "⚫", "last_event": "File not found"}
            
            # Read last 5 lines to find latest status
            lines = blackbox_index.read_text(encoding='utf-8', errors='replace').splitlines()
            recent_lines = lines[-5:] if lines else []
            
            # Find latest audit status
            latest_status = "Unknown"
            latest_event = "No events"
            
            for line in reversed(recent_lines):
                if "PROCMON_AUDIT_END" in line:
                    if "[OK]" in line:
                        latest_status = "OK"
                        latest_event = line.strip()
                        break
                    elif "[FAIL]" in line:
                        latest_status = "FAIL"
                        latest_event = line.strip()
                        break
            
            # Determine emoji
            emoji_map = {"OK": "🟢", "FAIL": "🔴", "Unknown": "⚫"}
            emoji = emoji_map.get(latest_status, "⚫")
            
            return {
                "status": latest_status,
                "emoji": emoji,
                "last_event": latest_event
            }
        except Exception as e:
            logger.debug(f"[FEEDER-V3] Procmon audit status error: {e}")
            return {"status": "Unknown", "emoji": "⚫", "last_event": f"Error: {str(e)}"}

    def _collect_memory_cortex_status(self):
        """Collect Memory Cortex total events count."""
        try:
            ana_max_root = Path(__file__).resolve().parent.parent
            events_file = ana_max_root / "memory" / "episodic" / "events.jsonl"
            if not events_file.exists():
                return None
            
            with events_file.open("rb") as f:
                count = sum(1 for _ in f)
            return {"total_count": count}
        except Exception as e:
            logger.debug(f"[FEEDER-V3] Memory cortex count error: {e}")
            return None

    def _run(self):
        """Main loop: collect metrics and enqueue for publishing."""
        while not self._stop_event.is_set():
            metrics = self._collect_system_metrics()
            processes = self._collect_processes()
            
            # Collect procmon audit status only every 30 seconds
            procmon_status = None
            memory_status = None
            self._procmon_audit_counter += 1
            if self._procmon_audit_counter >= (self.procmon_audit_interval // self.interval):
                procmon_status = self._collect_procmon_audit_status()
                memory_status = self._collect_memory_cortex_status()
                self._procmon_audit_counter = 0
            
            if metrics or processes or procmon_status or memory_status:
                self._queue.put({"metrics": metrics, "processes": processes, "procmon_audit": procmon_status, "memory_status": memory_status})
            time.sleep(self.interval)

    def _publisher(self):
        """Publish telemetry from queue to watchdog_bus."""
        publish_count = 0
        while not self._stop_event.is_set():
            try:
                from tools.watchdog_bus import bus
                item = self._queue.get(timeout=self.interval)
                metrics, processes = item["metrics"], item["processes"]
                procmon_audit = item.get("procmon_audit")
                memory_status = item.get("memory_status")

                if metrics:
                    bus.publish("dashboard_feeder", "telemetry.system", metrics)
                if processes:
                    bus.publish("dashboard_feeder", "telemetry.processes", processes)
                if procmon_audit:
                    bus.publish("dashboard_feeder", "telemetry.procmon_audit", procmon_audit)
                if memory_status:
                    bus.publish("memory_cortex", "memory_sync", memory_status)

                if publish_count == 0:
                    logger.info("[FEEDER-V3] [OK] First publish succeeded!")
                publish_count += 1

            except Empty:
                continue
            except Exception as e:
                logger.warning(f"[FEEDER-V3] Publish error: {e}")
                time.sleep(self.interval)


# Global feeder instance
_feeder_instance = None

def start_feeder():
    """Start the global dashboard feeder."""
    global _feeder_instance
    if _feeder_instance is None:
        _feeder_instance = DashboardFeederV3(interval=3)
    _feeder_instance.start()

def stop_feeder():
    """Stop the global dashboard feeder."""
    global _feeder_instance
    if _feeder_instance:
        _feeder_instance.stop()
