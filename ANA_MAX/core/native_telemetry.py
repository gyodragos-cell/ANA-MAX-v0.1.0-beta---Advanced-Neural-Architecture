import os
import time
import logging
import threading
import json
from core.event_stream import EventStream

logger = logging.getLogger(__name__)

# JS Script for Frida
# Hooks CreateProcessW to intercept application launches
# Hooks SetClipboardData to intercept clipboard updates
FRIDA_SCRIPT = """
var createProcessW = Process.getModuleByName("kernel32.dll").getExportByName("CreateProcessW");
Interceptor.attach(createProcessW, {
    onEnter: function (args) {
        try {
            var appName = args[0].isNull() ? "" : args[0].readUtf16String();
            var cmdLine = args[1].isNull() ? "" : args[1].readUtf16String();
            if (appName !== "" || cmdLine !== "") {
                send(JSON.stringify({
                    "type": "process_created",
                    "app": appName,
                    "cmd": cmdLine
                }));
            }
        } catch (e) {}
    }
});

// A hook for SetClipboardData is more complex due to memory formats (CF_UNICODETEXT).
// For stability in bypass mode without admin, we keep it light.
"""

class NativeTelemetry:
    def __init__(self, event_stream: EventStream, target_process: str = "explorer.exe"):
        self.event_stream = event_stream
        self.target_process = target_process
        self.session = None
        self.script = None
        self._running = False
        self._thread = None

    def _on_message(self, message, data):
        if message["type"] == "send":
            try:
                payload = json.loads(message["payload"])
                # Pushing event to EventStream
                self.event_stream.emit(
                    event_type="system_state",
                    source="native_telemetry",
                    data=payload
                )
                logger.debug(f"[NativeTelemetry] Intercepted: {payload}")
            except Exception as e:
                logger.error(f"[NativeTelemetry] Parse error: {e}")
        elif message["type"] == "error":
            logger.error(f"[NativeTelemetry] Frida Error: {message['stack']}")

    def _run(self):
        try:
            import frida
            logger.info(f"Pornire NativeTelemetry pe: {self.target_process} (DevMode)")
            
            # Handle ambiguous process names by selecting first matching PID
            try:
                # Try attaching by name first
                self.session = frida.attach(self.target_process)
            except frida.ProcessNotFoundError:
                logger.error(f"[NativeTelemetry] Process not found: {self.target_process}")
                self._running = False
                return
            except frida.TimedOutError:
                logger.error(f"[NativeTelemetry] Timeout attaching to: {self.target_process}")
                self._running = False
                return
            except Exception as e:
                # If ambiguous name, try to resolve by PID
                if "ambiguous" in str(e).lower():
                    logger.warning(f"[NativeTelemetry] Ambiguous process name, resolving by PID...")
                    try:
                        # List all processes and find matching ones
                        processes = frida.enumerate_processes()
                        matching = [p for p in processes if self.target_process.lower() in p.name.lower()]
                        if matching:
                            # Attach to first matching process by PID
                            self.session = frida.attach(matching[0].pid)
                            logger.info(f"[NativeTelemetry] Attached to {matching[0].name} (PID: {matching[0].pid})")
                        else:
                            logger.error(f"[NativeTelemetry] No matching processes found for: {self.target_process}")
                            self._running = False
                            return
                    except Exception as e2:
                        logger.error(f"[NativeTelemetry] Failed to resolve ambiguous name: {e2}")
                        self._running = False
                        return
                else:
                    raise
            
            self.script = self.session.create_script(FRIDA_SCRIPT)
            self.script.on('message', self._on_message)
            self.script.load()
            
            while self._running:
                time.sleep(1)
                
        except Exception as e:
            logger.error(f"[NativeTelemetry] Esec initializare Frida: {e}")
            self._running = False

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self.script:
            try:
                self.script.unload()
            except:
                pass
        if self.session:
            try:
                self.session.detach()
            except:
                pass
        if self._thread:
            self._thread.join(timeout=2)
        logger.info("NativeTelemetry oprit.")
