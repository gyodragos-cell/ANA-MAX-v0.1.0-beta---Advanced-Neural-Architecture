import os
import queue
import threading
import logging
import time
from typing import Optional, Dict, Any, List
from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus
from tools.watchdog_bus import bus

logger = logging.getLogger(__name__)

# Advanced JS payload to hook Windows APIs (Memory, UI, Kernel)
FRIDA_JS_HOOK = """
function logEvent(apiName, details) {
    send({
        type: 'TELEMETRY',
        pid: Process.id,
        api: apiName,
        details: details
    });
}

function safeGetExport(modName, funcName) {
    try {
        var m = Process.getModuleByName(modName);
        return m.findExportByName(funcName);
    } catch (e) {
        return Module.findExportByName(modName, funcName);
    }
}

// ---------------- KERNEL32 ----------------
var pCreateFileW = safeGetExport('kernel32.dll', 'CreateFileW');
if (pCreateFileW) {
    Interceptor.attach(pCreateFileW, {
        onEnter: function (args) {
            this.filename = args[0].readUtf16String();
            this.desiredAccess = args[1].toInt32();
        },
        onLeave: function (retval) {
            logEvent('CreateFileW', {
                file: this.filename,
                access: this.desiredAccess,
                success: retval.toInt32() !== -1
            });
        }
    });
}

var pCreateProcessW = safeGetExport('kernel32.dll', 'CreateProcessW');
if (pCreateProcessW) {
    Interceptor.attach(pCreateProcessW, {
        onEnter: function(args) {
            var appName = args[0].isNull() ? null : args[0].readUtf16String();
            var cmdLine = args[1].isNull() ? null : args[1].readUtf16String();
            logEvent('CreateProcessW', { app: appName, cmd: cmdLine });
        }
    });
}

var pWriteProcessMemory = safeGetExport('kernel32.dll', 'WriteProcessMemory');
if (pWriteProcessMemory) {
    Interceptor.attach(pWriteProcessMemory, {
        onEnter: function(args) {
            logEvent('WriteProcessMemory', { 
                hProcess: args[0].toString(), 
                baseAddr: args[1].toString(),
                size: args[3].toInt32()
            });
        }
    });
}

var pReadProcessMemory = safeGetExport('kernel32.dll', 'ReadProcessMemory');
if (pReadProcessMemory) {
    Interceptor.attach(pReadProcessMemory, {
        onEnter: function(args) {
            logEvent('ReadProcessMemory', { 
                hProcess: args[0].toString(), 
                baseAddr: args[1].toString(),
                size: args[3].toInt32()
            });
        }
    });
}

// ---------------- ADVAPI32 ----------------
var pRegOpenKeyExW = safeGetExport('advapi32.dll', 'RegOpenKeyExW');
if (pRegOpenKeyExW) {
    Interceptor.attach(pRegOpenKeyExW, {
        onEnter: function(args) {
            var subKey = args[1].isNull() ? null : args[1].readUtf16String();
            logEvent('RegOpenKeyExW', { subkey: subKey });
        }
    });
}

// ---------------- USER32 ----------------
var pSendMessageW = safeGetExport('user32.dll', 'SendMessageW');
if (pSendMessageW) {
    Interceptor.attach(pSendMessageW, {
        onEnter: function(args) {
            logEvent('SendMessageW', {
                hWnd: args[0].toString(),
                msg: args[1].toInt32()
            });
        }
    });
}

var pGetForegroundWindow = safeGetExport('user32.dll', 'GetForegroundWindow');
if (pGetForegroundWindow) {
    Interceptor.attach(pGetForegroundWindow, {
        onLeave: function(retval) {
            logEvent('GetForegroundWindow', { hWnd: retval.toString() });
        }
    });
}

var pSetWindowTextW = safeGetExport('user32.dll', 'SetWindowTextW');
if (pSetWindowTextW) {
    Interceptor.attach(pSetWindowTextW, {
        onEnter: function(args) {
            var text = args[1].isNull() ? null : args[1].readUtf16String();
            logEvent('SetWindowTextW', {
                hWnd: args[0].toString(),
                text: text
            });
        }
    });
}

// ---------------- NTDLL ----------------
var pNtOpenProcess = safeGetExport('ntdll.dll', 'NtOpenProcess');
if (pNtOpenProcess) {
    Interceptor.attach(pNtOpenProcess, {
        onEnter: function(args) {
            logEvent('NtOpenProcess', { desiredAccess: args[1].toInt32() });
        }
    });
}

var pNtReadVirtualMemory = safeGetExport('ntdll.dll', 'NtReadVirtualMemory');
if (pNtReadVirtualMemory) {
    Interceptor.attach(pNtReadVirtualMemory, {
        onEnter: function(args) {
            logEvent('NtReadVirtualMemory', {
                hProcess: args[0].toString(),
                baseAddr: args[1].toString(),
                size: args[3].toInt32()
            });
        }
    });
}
"""

class WindowsFridaTelemetryTool(Tool):
    """
    Frida-based Windows Telemetry. Hooks into a target process to intercept APIs
    and provides God View for the agent.
    """

    def __init__(self):
        self._session = None
        self._script = None
        self._event_queue = queue.Queue(maxsize=2000)
        self._monitor_thread = None
        self._stop_event = threading.Event()
        self._is_running = False

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="windows_frida_telemetry",
            description="Native Windows Telemetry using Frida to hook APIs like CreateFile, CreateProcess.",
            parameters=[
                ToolParameter(
                    name="action",
                    description="Action to perform: start, stop, get_events",
                    type="string",
                    required=True,
                    choices=["start", "stop", "get_events"]
                ),
                ToolParameter(
                    name="target",
                    description="Target process name or PID (default: notepad.exe)",
                    type="string",
                    required=False,
                    default="notepad.exe"
                )
            ],
            category="system_intelligence"
        )

    def execute(self, action: str, target: str = "notepad.exe", **kwargs) -> ToolResult:
        try:
            import frida
        except ImportError:
            return ToolResult(status=ToolStatus.ERROR, error="frida package is not installed.")

        if action == "start":
            return self._start_telemetry(frida, target)
        elif action == "stop":
            return self._stop_telemetry()
        elif action == "get_events":
            return self._get_events()
        else:
            return ToolResult(status=ToolStatus.ERROR, error=f"Unknown action: {action}")

    def _on_message(self, message, data):
        if message.get('type') == 'send':
            payload = message.get('payload', {})
            if payload.get('type') == 'TELEMETRY':
                try:
                    event_data = {
                        'timestamp': time.strftime('%H:%M:%S'),
                        'pid': payload.get('pid'),
                        'api': payload.get('api'),
                        'details': payload.get('details')
                    }
                    self._event_queue.put_nowait(event_data)
                    bus.publish(source="FridaTelemetry", event_type="API_CALL", data=event_data)
                except queue.Full:
                    pass
        elif message.get('type') == 'error':
            logger.error(f"Frida Telemetry Error: {message.get('stack')}")

    def _start_telemetry(self, frida_module, target: str) -> ToolResult:
        if self._is_running:
            return ToolResult(status=ToolStatus.SUCCESS, message="Telemetry is already running.")

        try:
            device = frida_module.get_local_device()
            try:
                pid = int(target)
                self._session = device.attach(pid)
            except ValueError:
                self._session = device.attach(target)
            
            self._script = self._session.create_script(FRIDA_JS_HOOK)
            self._script.on('message', self._on_message)
            self._script.load()
            
            self._is_running = True
            return ToolResult(status=ToolStatus.SUCCESS, message=f"Frida telemetry started on target: {target}")
            
        except Exception as e:
            self._is_running = False
            return ToolResult(status=ToolStatus.ERROR, error=f"Failed to start telemetry: {str(e)}")

    def _stop_telemetry(self) -> ToolResult:
        if not self._is_running:
            return ToolResult(status=ToolStatus.SUCCESS, message="Telemetry is not running.")
        
        try:
            if self._script:
                self._script.unload()
                self._script = None
            if self._session:
                self._session.detach()
                self._session = None
            self._is_running = False
            return ToolResult(status=ToolStatus.SUCCESS, message="Telemetry stopped successfully.")
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=f"Failed to stop telemetry: {str(e)}")

    def _get_events(self) -> ToolResult:
        events = []
        while not self._event_queue.empty():
            try:
                events.append(self._event_queue.get_nowait())
            except queue.Empty:
                break
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={"events": events, "count": len(events)},
            message=f"Retrieved {len(events)} telemetry events."
        )

if __name__ == '__main__':
    # Simple CLI test
    import argparse
    import sys
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['start', 'stop', 'get_events'])
    parser.add_argument('--target', default='notepad.exe')
    args = parser.parse_args()
    
    tool = WindowsFridaTelemetryTool()
    res = tool.execute(action=args.action, target=args.target)
    print(f"Status: {res.status}\nMessage: {res.message}\nError: {res.error}")
    if res.data:
        print(f"Data: {res.data}")
