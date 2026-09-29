"""
ANA MAX - Procmon Monitor
Continuous diagnostic sensor for OS-level events.

Captures system events via Sysinternals Procmon, exports logs,
cleans data, compresses, and feeds into Black Box Recorder.
"""
from __future__ import annotations

import logging
import subprocess
import threading
import time
import json
import gzip
import shutil
from datetime import datetime
from pathlib import Path
from collections import Counter
from typing import Dict, Any, List, Optional

from tools.black_box_recorder import recorder
from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus

logger = logging.getLogger(__name__)

# Paths
PROCMON_PATH = Path(r"C:\Sysinternals\Procmon.exe")
PROCMON_DIR = Path(r"C:\ANA_MAX\procmon")
PROCMON_DIR.mkdir(parents=True, exist_ok=True)

BACKING_FILE = PROCMON_DIR / "live_capture.pml"
EXPORT_CSV = PROCMON_DIR / "export.csv"
EXPORT_CLEAN_GZ = PROCMON_DIR / "export_clean.gz"
ARCHIVE_DIR = PROCMON_DIR / "archive"
ARCHIVE_DIR.mkdir(exist_ok=True)

# Constants
EXPORT_INTERVAL = 60  # seconds
MAX_PML_SIZE_MB = 500
EXPORT_RETRIES = 3
NOISE_EVENTS = {"RegQueryKey", "ThreadCreate", "ProcessStart", "ProcessExit", "FileClose"}


class ProcmonMonitor:
    """Continuous Procmon monitoring system."""
    
    def __init__(self):
        self._running = False
        self._procmon_process: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()
        self._last_export_time = 0
        self._events_captured = 0
        self._anomalies_detected = 0
        
    def check_procmon_exists(self) -> bool:
        """Check if Procmon.exe exists."""
        if not PROCMON_PATH.exists():
            recorder.log("ERROR", "Procmon.exe not found", {"path": str(PROCMON_PATH)}, level="CRITICAL")
            return False
        return True
    
    def is_procmon_running(self) -> bool:
        """Check if Procmon is already running."""
        try:
            result = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq Procmon.exe"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return "Procmon.exe" in result.stdout
        except Exception as e:
            logger.error(f"Failed to check Procmon status: {e}")
            return False
    
    def start_procmon(self) -> bool:
        """Start Procmon with required flags."""
        if not self.check_procmon_exists():
            return False
        
        if self.is_procmon_running():
            logger.info("Procmon already running, skipping duplicate start")
            return True
        
        try:
            cmd = [
                str(PROCMON_PATH),
                "/AcceptEula",
                "/Quiet",
                f"/BackingFile {BACKING_FILE}",
                "/Minimized",
                "/NoFilter"
            ]
            
            logger.info(f"Starting Procmon: {' '.join(cmd)}")
            self._procmon_process = subprocess.Popen(
                cmd,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            # Wait a moment for Procmon to start
            time.sleep(3)
            
            if self.is_procmon_running():
                recorder.log("OS", "Procmon started successfully", {"backing_file": str(BACKING_FILE)})
                return True
            else:
                recorder.log("ERROR", "Procmon failed to start", {}, level="CRITICAL")
                return False
                
        except Exception as e:
            recorder.log("ERROR", f"Procmon start failed: {e}", {}, level="CRITICAL")
            return False
    
    def export_logs(self) -> bool:
        """Export Procmon logs to CSV."""
        if not BACKING_FILE.exists():
            logger.warning(f"Backing file not found: {BACKING_FILE}")
            return False
        
        for attempt in range(EXPORT_RETRIES):
            try:
                cmd = [
                    str(PROCMON_PATH),
                    "/OpenLog", str(BACKING_FILE),
                    "/SaveAs", str(EXPORT_CSV)
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                
                if EXPORT_CSV.exists() and EXPORT_CSV.stat().st_size > 0:
                    logger.info(f"Export successful (attempt {attempt + 1})")
                    return True
                else:
                    logger.warning(f"Export failed (attempt {attempt + 1}): empty or missing CSV")
                    time.sleep(2)
                    
            except Exception as e:
                logger.error(f"Export error (attempt {attempt + 1}): {e}")
                time.sleep(2)
        
        recorder.log("ERROR", "Procmon export failed after retries", {}, level="CRITICAL")
        return False
    
    def clean_csv(self) -> List[Dict[str, Any]]:
        """Clean and parse CSV, return structured events."""
        if not EXPORT_CSV.exists():
            return []
        
        events = []
        try:
            with open(EXPORT_CSV, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            # Skip header, process data lines
            seen = set()
            for line in lines[1:]:
                if not line.strip():
                    continue
                
                # Simple deduplication
                line_hash = hash(line.strip())
                if line_hash in seen:
                    continue
                seen.add(line_hash)
                
                # Parse CSV line (simplified)
                parts = [p.strip() for p in line.split(',')]
                if len(parts) < 6:
                    continue
                
                event = {
                    "time_of_day": parts[0] if len(parts) > 0 else "",
                    "process_name": parts[1] if len(parts) > 1 else "",
                    "pid": parts[2] if len(parts) > 2 else "",
                    "operation": parts[3] if len(parts) > 3 else "",
                    "path": parts[4] if len(parts) > 4 else "",
                    "result": parts[5] if len(parts) > 5 else ""
                }
                
                # Filter noise events
                if event["operation"] in NOISE_EVENTS:
                    continue
                
                events.append(event)
            
            logger.info(f"Cleaned {len(events)} events from CSV")
            return events
            
        except Exception as e:
            logger.error(f"CSV cleaning error: {e}")
            return []
    
    def compress_export(self, events: List[Dict[str, Any]]) -> bool:
        """Compress cleaned events to gzip."""
        try:
            with gzip.open(EXPORT_CLEAN_GZ, 'wt', encoding='utf-8') as f:
                json.dump(events, f)
            
            logger.info(f"Compressed {len(events)} events to {EXPORT_CLEAN_GZ}")
            return True
        except Exception as e:
            logger.error(f"Compression error: {e}")
            return False
    
    def analyze_events(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze events for anomalies and statistics."""
        if not events:
            return {"events": 0, "top_processes": [], "top_operations": [], "anomalies": []}
        
        # Count processes and operations
        processes = Counter(e["process_name"] for e in events)
        operations = Counter(e["operation"] for e in events)
        
        # Top 20
        top_processes = processes.most_common(20)
        top_operations = operations.most_common(20)
        
        # Detect anomalies
        anomalies = []
        
        # I/O spike (many file operations)
        file_ops = sum(1 for e in events if "File" in e["operation"])
        if file_ops > 1000:
            anomalies.append(f"I/O spike: {file_ops} file operations")
        
        # Registry storm
        reg_ops = sum(1 for e in events if "Reg" in e["operation"])
        if reg_ops > 500:
            anomalies.append(f"Registry storm: {reg_ops} registry operations")
        
        # Thread explosion
        thread_ops = sum(1 for e in events if "Thread" in e["operation"])
        if thread_ops > 200:
            anomalies.append(f"Thread explosion: {thread_ops} thread operations")
        
        return {
            "events": len(events),
            "top_processes": top_processes,
            "top_operations": top_operations,
            "anomalies": anomalies
        }
    
    def feed_black_box(self, analysis: Dict[str, Any]) -> None:
        """Feed analysis into Black Box Recorder."""
        recorder.log("PROC_MONITOR", "Procmon capture cycle", {
            "timestamp": datetime.now().isoformat(),
            "events": analysis["events"],
            "top_processes": [p[0] for p in analysis["top_processes"][:10]],
            "top_operations": [o[0] for o in analysis["top_operations"][:10]],
            "anomalies": analysis["anomalies"],
            "pml_size_mb": BACKING_FILE.stat().st_size / (1024 * 1024) if BACKING_FILE.exists() else 0
        })
        
        self._events_captured = analysis["events"]
        self._anomalies_detected = len(analysis["anomalies"])
    
    def rotate_logs(self) -> bool:
        """Rotate PML logs if exceeding size limit."""
        if not BACKING_FILE.exists():
            return False
        
        size_mb = BACKING_FILE.stat().st_size / (1024 * 1024)
        if size_mb < MAX_PML_SIZE_MB:
            return False
        
        try:
            # Archive old log
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            archive_name = f"live_capture_{timestamp}.pml"
            archive_path = ARCHIVE_DIR / archive_name
            
            shutil.move(str(BACKING_FILE), str(archive_path))
            logger.info(f"Rotated PML log: {archive_path} ({size_mb:.2f} MB)")
            
            # Restart Procmon with fresh backing file
            if self._procmon_process:
                self._procmon_process.terminate()
                time.sleep(2)
            
            return self.start_procmon()
            
        except Exception as e:
            recorder.log("ERROR", f"Log rotation failed: {e}", {}, level="HIGH")
            return False
    
    def get_heartbeat(self) -> Dict[str, Any]:
        """Get JSON heartbeat status."""
        pml_size_mb = BACKING_FILE.stat().st_size / (1024 * 1024) if BACKING_FILE.exists() else 0
        
        status = "OK"
        if self._anomalies_detected > 0:
            status = "WARNING"
        if pml_size_mb > MAX_PML_SIZE_MB:
            status = "CRITICAL"
        
        return {
            "procmon_running": self.is_procmon_running(),
            "last_export": datetime.fromtimestamp(self._last_export_time).isoformat() if self._last_export_time else None,
            "events_captured": self._events_captured,
            "anomalies_detected": self._anomalies_detected,
            "pml_size_mb": round(pml_size_mb, 2),
            "status": status
        }
    
    def run_cycle(self) -> None:
        """Run one monitoring cycle."""
        with self._lock:
            # Check and start Procmon
            if not self.is_procmon_running():
                if not self.start_procmon():
                    logger.error("Failed to start Procmon, skipping cycle")
                    return
            
            # Rotate logs if needed
            self.rotate_logs()
            
            # Export logs
            if not self.export_logs():
                logger.error("Export failed, skipping analysis")
                return
            
            # Clean and analyze
            events = self.clean_csv()
            analysis = self.analyze_events(events)
            
            # Compress
            self.compress_export(events)
            
            # Feed Black Box
            self.feed_black_box(analysis)
            
            self._last_export_time = time.time()
            
            # Print heartbeat
            heartbeat = self.get_heartbeat()
            print(json.dumps(heartbeat, indent=2))
    
    def start(self) -> None:
        """Start continuous monitoring."""
        if not self.check_procmon_exists():
            logger.error("Procmon.exe not found, cannot start monitoring")
            return
        
        self._running = True
        logger.info("Starting Procmon monitor")
        
        while self._running:
            try:
                self.run_cycle()
                time.sleep(EXPORT_INTERVAL)
            except KeyboardInterrupt:
                logger.info("Procmon monitor stopped by user")
                break
            except Exception as e:
                logger.error(f"Monitor cycle error: {e}")
                recorder.log("ERROR", f"Procmon monitor error: {e}", {}, level="HIGH")
                time.sleep(EXPORT_INTERVAL)
    
    def stop(self) -> None:
        """Stop monitoring."""
        self._running = False
        if self._procmon_process:
            self._procmon_process.terminate()
        logger.info("Procmon monitor stopped")


class ProcmonMonitorTool(Tool):
    """Tool for controlling Procmon monitoring system."""
    
    def __init__(self):
        self._monitor: Optional[ProcmonMonitor] = None
        self._monitor_thread: Optional[threading.Thread] = None
    
    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="procmon_monitor",
            description="Control Sysinternals Procmon for continuous OS-level event monitoring. Operations: start, stop, status, heartbeat.",
            parameters=[
                ToolParameter(name="operation", type="str", required=True, 
                             description="Operation: start, stop, status, heartbeat")
            ]
        )
    
    def execute(self, **kwargs) -> ToolResult:
        operation = kwargs.get("operation")
        
        try:
            if operation == "start":
                if self._monitor and self._monitor._running:
                    return ToolResult(status=ToolStatus.SUCCESS, data={"message": "Procmon monitor already running"})
                
                self._monitor = ProcmonMonitor()
                self._monitor_thread = threading.Thread(target=self._monitor.start, daemon=True)
                self._monitor_thread.start()
                
                return ToolResult(status=ToolStatus.SUCCESS, data={"message": "Procmon monitor started"})
            
            elif operation == "stop":
                if not self._monitor:
                    return ToolResult(status=ToolStatus.ERROR, error="Procmon monitor not running")
                
                self._monitor.stop()
                self._monitor = None
                self._monitor_thread = None
                
                return ToolResult(status=ToolStatus.SUCCESS, data={"message": "Procmon monitor stopped"})
            
            elif operation == "status":
                if not self._monitor:
                    return ToolResult(status=ToolStatus.SUCCESS, data={"running": False})
                
                heartbeat = self._monitor.get_heartbeat()
                return ToolResult(status=ToolStatus.SUCCESS, data=heartbeat)
            
            elif operation == "heartbeat":
                monitor = self._monitor if self._monitor else ProcmonMonitor()
                heartbeat = monitor.get_heartbeat()
                return ToolResult(status=ToolStatus.SUCCESS, data=heartbeat)
            
            else:
                return ToolResult(status=ToolStatus.ERROR, error=f"Unknown operation: {operation}")
        
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))


def main():
    """Main entry point."""
    monitor = ProcmonMonitor()
    
    try:
        monitor.start()
    except KeyboardInterrupt:
        monitor.stop()


if __name__ == "__main__":
    main()
