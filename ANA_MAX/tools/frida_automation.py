"""
Frida Automation Tool - Dynamic Instrumentation
Author: ANA_MAX
Date: 2026-05-12
Category: mobile

Functions:
- frida_list_processes: List running processes
- frida_attach: Attach to process
- frida_spawn: Spawn app with Frida
- frida_inject: Inject JavaScript
- frida_list_modules: List loaded modules
- frida_find_functions: Find function addresses
- frida_hook: Hook function calls
- frida_terminate: Detach from process

Requires: pip install frida
"""

from __future__ import annotations

import logging
import time
from typing import Optional, List, Dict, Any

from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus

logger = logging.getLogger(__name__)


class FridaTool(Tool):
    """Tool pentru instrumentare dinamica cu Frida folosind API-ul nativ Python."""

    def __init__(self) -> None:
        self._current_session: Optional[Any] = None

    def _get_device(self, device_id: str = "") -> Any:
        """Obtine un device Frida dupa ID sau tip."""
        import frida
        device_manager = frida.get_device_manager()
        if device_id:
            try:
                return device_manager.get_device(device_id)
            except Exception:
                if device_id.lower() == "usb":
                    return frida.get_usb_device()
                elif device_id.lower() == "local":
                    return frida.get_local_device()
                raise
        else:
            return frida.get_local_device()

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="frida_instrument",
            description="Instrumentare dinamica cu Frida: list procese, attach/spawn, inject JS, hook functii, enum modules.",
            parameters=[
                ToolParameter(
                    name="operation",
                    description="Operatia de executat",
                    type="string",
                    required=True,
                    choices=[
                        "list_processes", "attach", "spawn", "inject",
                        "list_modules", "find_functions", "hook", "terminate",
                        "version", "devices"
                    ],
                ),
                ToolParameter(
                    name="target",
                    description="Numele procesului sau PID (pentru attach)",
                    type="string",
                    required=False,
                    default="",
                ),
                ToolParameter(
                    name="package",
                    description="Numele pachetului Android (pentru spawn)",
                    type="string",
                    required=False,
                    default="",
                ),
                ToolParameter(
                    name="script",
                    description="Cod JavaScript pentru injectie",
                    type="string",
                    required=False,
                    default="",
                ),
                ToolParameter(
                    name="module",
                    description="Numele modulului (pentru find_functions)",
                    type="string",
                    required=False,
                    default="",
                ),
                ToolParameter(
                    name="pattern",
                    description="Pattern de cautare pentru functii",
                    type="string",
                    required=False,
                    default="",
                ),
                ToolParameter(
                    name="device",
                    description="Device ID pentru ADB (USB)",
                    type="string",
                    required=False,
                    default="",
                ),
                ToolParameter(
                    name="timeout",
                    description="Timeout in secunde",
                    type="integer",
                    required=False,
                    default=30,
                ),
            ],
            category="mobile",
            requires_confirmation=False,
        )

    def execute(self, **kwargs) -> ToolResult:
        operation = kwargs.get("operation", "")
        target = kwargs.get("target", "")
        package = kwargs.get("package", "")
        script = kwargs.get("script", "")
        module = kwargs.get("module", "")
        pattern = kwargs.get("pattern", "")
        device = kwargs.get("device", "")
        timeout = int(kwargs.get("timeout", 30))

        operations = {
            "list_processes": self._list_processes,
            "attach": self._attach,
            "spawn": self._spawn,
            "inject": self._inject,
            "list_modules": self._list_modules,
            "find_functions": self._find_functions,
            "hook": self._hook,
            "terminate": self._terminate,
            "version": self._version,
            "devices": self._devices,
        }

        if operation not in operations:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Operatie necunoscuta: {operation}"
            )

        try:
            return operations[operation](target, package, script, module, pattern, device, timeout)
        except Exception as e:
            logger.error(f"Frida error: {e}")
            return ToolResult(status=ToolStatus.ERROR, error=str(e))

    def _version(self, target: str, pkg: str, script: str, module: str, pattern: str, device: str, timeout: int) -> ToolResult:
        """Verifica versiunea Frida."""
        try:
            import frida
            v = frida.__version__
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"version": v},
                message=f"Frida {v}"
            )
        except ImportError:
            return ToolResult(
                status=ToolStatus.ERROR,
                error="Frida not installed. Run: pip install frida-tools"
            )

    def _devices(self, target: str, pkg: str, script: str, module: str, pattern: str, device: str, timeout: int) -> ToolResult:
        """Listeaza dispozitivele Frida."""
        try:
            import frida
            device_manager = frida.get_device_manager()
            devices = device_manager.enumerate_devices()
            device_ids = [d.id for d in devices]
            device_info = [{"id": d.id, "name": d.name, "type": d.type} for d in devices]

            raw_lines = ["%-16s %-16s %-16s" % ("Id", "Name", "Type")]
            for d in devices:
                raw_lines.append("%-16s %-16s %-16s" % (d.id, d.name, d.type))
            raw_output = "\n".join(raw_lines)

            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"count": len(devices), "devices": device_ids, "details": device_info, "raw": raw_output},
                message=f"Gasite {len(devices)} dispozitive"
            )
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))

    def _list_processes(self, target: str, pkg: str, script: str, module: str, pattern: str, device: str, timeout: int) -> ToolResult:
        """Listeaza procesele in curs de executie."""
        try:
            dev = self._get_device(device)
            processes = dev.enumerate_processes()
            process_list = [{"pid": p.pid, "name": p.name} for p in processes]

            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"count": len(process_list), "processes": process_list[:50]},
                message=f"Gasite {len(process_list)} procese"
            )
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))

    def _attach(self, target: str, pkg: str, script: str, module: str, pattern: str, device: str, timeout: int) -> ToolResult:
        """Ataseaza la un proces."""
        if not target:
            return ToolResult(status=ToolStatus.ERROR, error="Target (PID sau nume) este obligatoriu")

        try:
            dev = self._get_device(device)
            session = dev.attach(int(target) if target.isdigit() else target)
            self._current_session = session

            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"session_id": str(id(session)), "target": target},
                message=f"Successfully attached to {target}"
            )
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=f"Failed to attach: {str(e)}")

    def _spawn(self, target: str, pkg: str, script: str, module: str, pattern: str, device: str, timeout: int) -> ToolResult:
        """Porneste aplicatie cu Frida."""
        if not pkg:
            return ToolResult(status=ToolStatus.ERROR, error="Package name este obligatoriu")

        try:
            dev = self._get_device(device)
            pid = dev.spawn([pkg])
            dev.resume(pid)

            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"package": pkg, "pid": pid},
                message=f"Spawned {pkg} (PID: {pid})"
            )
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=f"Spawn failed: {str(e)}")

    def _inject(self, target: str, pkg: str, script: str, module: str, pattern: str, device: str, timeout: int) -> ToolResult:
        """Injecteaza script JavaScript."""
        if not script:
            return ToolResult(status=ToolStatus.ERROR, error="Script JS este obligatoriu")

        if not target:
            return ToolResult(status=ToolStatus.ERROR, error="Target (PID sau nume) este obligatoriu")

        try:
            dev = self._get_device(device)
            session = dev.attach(int(target) if target.isdigit() else target)
            script_obj = session.create_script(script)

            messages = []
            errors = []

            def on_message(message, data):
                if message['type'] == 'send':
                    messages.append(message['payload'])
                elif message['type'] == 'error':
                    errors.append(message['stack'])

            script_obj.on('message', on_message)
            script_obj.load()

            # Asteptam scurt pentru a colecta mesaje (default 1s sau 10% din timeout)
            wait_sec = min(max(timeout / 10.0, 1.0), 5.0)
            time.sleep(wait_sec)

            script_obj.unload()
            session.detach()

            if errors:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error="\n".join(errors),
                    data={"messages": messages}
                )

            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"target": target, "messages": messages},
                message=f"Script injectat cu succes. Colectate {len(messages)} mesaje."
            )
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=f"Inject failed: {str(e)}")

    def _list_modules(self, target: str, pkg: str, script: str, module: str, pattern: str, device: str, timeout: int) -> ToolResult:
        """Listeaza modulele incarcate pentru un proces."""
        if not target:
            return ToolResult(status=ToolStatus.ERROR, error="Target (PID sau nume) este obligatoriu")

        try:
            dev = self._get_device(device)
            session = dev.attach(int(target) if target.isdigit() else target)

            list_script = """
            Process.enumerateModules().forEach(function(m) {
                send(m.name + "|" + m.base + "|" + m.size);
            });
            """

            messages = []
            errors = []

            def on_message(message, data):
                if message['type'] == 'send':
                    messages.append(message['payload'])
                elif message['type'] == 'error':
                    errors.append(message['stack'])

            script_obj = session.create_script(list_script)
            script_obj.on('message', on_message)
            script_obj.load()

            time.sleep(0.5)

            script_obj.unload()
            session.detach()

            if errors:
                return ToolResult(status=ToolStatus.ERROR, error="\n".join(errors))

            modules = []
            for line in messages:
                if "|" in line:
                    parts = line.strip().split("|")
                    if len(parts) == 3:
                        modules.append({
                            "name": parts[0],
                            "base": parts[1],
                            "size": parts[2]
                        })

            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"count": len(modules), "modules": modules},
                message=f"Gasite {len(modules)} module"
            )
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))

    def _find_functions(self, target: str, pkg: str, script: str, module: str, pattern: str, device: str, timeout: int) -> ToolResult:
        """Gaseste functii exports intr-un modul."""
        if not module:
            return ToolResult(status=ToolStatus.ERROR, error="Module name este obligatoriu")

        if not target:
            return ToolResult(status=ToolStatus.ERROR, error="Target (PID sau nume) este obligatoriu")

        search_pattern = pattern or ".*"

        try:
            dev = self._get_device(device)
            session = dev.attach(int(target) if target.isdigit() else target)

            search_script = f"""
            var mod = Process.findModuleByName("{module}");
            if (mod) {{
                send("MODULE_FOUND");
                mod.enumerateExports().forEach(function(e) {{
                    if (/{search_pattern}/.test(e.name)) {{
                        send("EXPORT|" + e.name + "|" + e.type + "|" + e.address);
                    }}
                }});
            }} else {{
                send("MODULE_NOT_FOUND");
            }}
            """

            messages = []
            errors = []

            def on_message(message, data):
                if message['type'] == 'send':
                    messages.append(message['payload'])
                elif message['type'] == 'error':
                    errors.append(message['stack'])

            script_obj = session.create_script(search_script)
            script_obj.on('message', on_message)
            script_obj.load()

            time.sleep(0.5)

            script_obj.unload()
            session.detach()

            if errors:
                return ToolResult(status=ToolStatus.ERROR, error="\n".join(errors))

            if "MODULE_NOT_FOUND" in messages:
                return ToolResult(status=ToolStatus.ERROR, error=f"Module {module} not found")

            functions = []
            for line in messages:
                if line.startswith("EXPORT|"):
                    parts = line.strip().split("|")
                    if len(parts) == 4:
                        functions.append({
                            "name": parts[1],
                            "type": parts[2],
                            "address": parts[3]
                        })

            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"module": module, "count": len(functions), "functions": functions},
                message=f"Gasite {len(functions)} functii"
            )
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))

    def _hook(self, target: str, pkg: str, script: str, module: str, pattern: str, device: str, timeout: int) -> ToolResult:
        """Genereaza script de hook pentru o functie."""
        if not pattern:
            return ToolResult(status=ToolStatus.ERROR, error="Function pattern este obligatoriu")

        module_name = module or "libname.so"

        hook_script = f"""
Java.perform(function() {{
    var module = Module.findBaseAddress("{module_name}");
    if (!module) {{
        console.log("Module not found: {module_name}");
        return;
    }}
    console.log("Module base: " + module);

    // Hook all exports matching pattern
    var exports = Module.enumerateExports("{module_name}");
    exports.forEach(function(e) {{
        if (/{pattern}/.test(e.name)) {{
            console.log("Found: " + e.name + " at " + e.address);
            try {{
                Interceptor.attach(e.address, {{
                    onEnter: function(args) {{
                        console.log("Called: " + e.name);
                    }},
                    onLeave: function(retval) {{
                        console.log("Returned: " + e.name);
                    }}
                }});
            }} catch (e) {{
                console.log("Failed to hook: " + e.message);
            }}
        }}
    }});
}});
"""

        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={
                "module": module_name,
                "pattern": pattern,
                "script": hook_script
            },
            message="Script de hook generat. Foloseste 'inject' pentru a-l executa."
        )

    def _terminate(self, target: str, pkg: str, script: str, module: str, pattern: str, device: str, timeout: int) -> ToolResult:
        """Termina sesiunea curenta."""
        if self._current_session:
            try:
                self._current_session.detach()
            except Exception:
                pass
            self._current_session = None
        return ToolResult(
            status=ToolStatus.SUCCESS,
            message="Sesiune terminata"
        )


def smoke_test():
    """Smoke test pentru Frida tool."""
    print("[*] Testing Frida Tool Native...")

    tool = FridaTool()

    # Test version
    result = tool.execute(operation="version")
    if result.is_success:
        print(f"[OK] Frida version: {result.data.get('version')}")
    else:
        print(f"[!] Frida version test failed: {result.error}")
        return

    # Test devices
    result = tool.execute(operation="devices")
    if result.is_success:
        print(f"[OK] Frida devices: {result.data.get('count')} - {result.data.get('devices')}")
    else:
        print(f"[!] Devices test failed: {result.error}")

    # Test list_processes
    result = tool.execute(operation="list_processes")
    if result.is_success:
        processes = result.data.get("processes", [])
        print(f"[OK] Frida list_processes: found {result.data.get('count')} processes. First 3: {processes[:3]}")
    else:
        print(f"[!] list_processes test failed: {result.error}")

    print("[*] Frida smoke test complete")


if __name__ == "__main__":
    smoke_test()
