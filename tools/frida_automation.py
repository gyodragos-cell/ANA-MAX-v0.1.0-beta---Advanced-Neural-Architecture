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

import subprocess
import json
import re
import os
import logging
from typing import Optional, List, Dict, Any

from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus

logger = logging.getLogger(__name__)


class FridaTool(Tool):
    """Tool pentru instrumentare dinamica cu Frida."""

    def __init__(self) -> None:
        self._current_session: Optional[str] = None
        self._frida_path = self._find_frida()

    def _find_frida(self) -> str:
        """Verifica daca Frida e instalat."""
        paths = [
            "frida",
            os.path.expandvars("%APPDATA%\\Python\\Python312\\Scripts\\frida.exe"),
            os.path.expandvars("%LOCALAPPDATA%\\Python\\Python312\\Scripts\\frida.exe"),
            "C:\\Program Files\\Python312\\Scripts\\frida.exe"
        ]
        for p in paths:
            try:
                result = subprocess.run([p, "--version"], capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    return p
            except Exception:
                continue
        return "frida"  # Fallback

    def _run_frida_tool(self, tool_name: str, args: List[str], timeout: int = 30) -> tuple[int, str, str]:
        """Ruleaza un tool din frida-tools via python -m."""
        try:
            result = subprocess.run(
                ["python", "-m", f"frida_tools.{tool_name}"] + args,
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding="utf-8",
                errors="replace"
            )
            return result.returncode, result.stdout, result.stderr
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, "", "Command timeout"
        except FileNotFoundError:
            return -1, "", "Frida not installed. Run: pip install frida-tools"
        except Exception as e:
            return -1, "", str(e)

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
        returncode, stdout, stderr = self._run_frida_tool("frida", ["--version"], timeout)
        
        if returncode == 0:
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"version": stdout.strip()},
                message=f"Frida {stdout.strip()}"
            )
        else:
            return ToolResult(
                status=ToolStatus.ERROR,
                error="Frida not installed. Run: pip install frida-tools"
            )

    def _devices(self, target: str, pkg: str, script: str, module: str, pattern: str, device: str, timeout: int) -> ToolResult:
        """Listeaza dispozitivele Frida."""
        returncode, stdout, stderr = self._run_frida_tool("ls_devices", [], timeout)
        
        if returncode == 0:
            devices = []
            for line in stdout.split("\n"):
                if line.strip() and not line.startswith("Proxies"):
                    match = re.match(r'(USB|Local).*?(\w+)', line)
                    if match:
                        devices.append(match.group(2))
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"count": len(devices), "devices": devices, "raw": stdout},
                message=f"Gasite {len(devices)} dispozitive"
            )
        else:
            return ToolResult(status=ToolStatus.ERROR, error=stderr)

    def _list_processes(self, target: str, pkg: str, script: str, module: str, pattern: str, device: str, timeout: int) -> ToolResult:
        """Listeaza procesele in curs de executie."""
        device_arg = ["-D", device] if device else []
        returncode, stdout, stderr = self._run_frida_tool("ps", device_arg, timeout)
        
        if returncode != 0:
            return ToolResult(status=ToolStatus.ERROR, error=stderr or "List processes failed")

        processes = []
        for line in stdout.split("\n"):
            line = line.strip()
            if line and not line.startswith("Process"):
                parts = line.split()
                if len(parts) >= 2 and parts[0].isdigit():
                    processes.append({
                        "pid": parts[0],
                        "name": parts[1] if len(parts) > 1 else "unknown"
                    })

        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={"count": len(processes), "processes": processes[:50]},
            message=f"Gasite {len(processes)} procese"
        )

    def _attach(self, target: str, pkg: str, script: str, module: str, pattern: str, device: str, timeout: int) -> ToolResult:
        """Ataseaza la un proces."""
        if not target:
            return ToolResult(status=ToolStatus.ERROR, error="Target (PID sau nume) este obligatoriu")

        device_arg = ["-D", device] if device else []
        
        # Check if it's a PID or name
        if target.isdigit():
            attach_cmd = device_arg + ["-p", target]
        else:
            attach_cmd = device_arg + ["-n", target]

        returncode, stdout, stderr = self._run_frida_tool("frida", attach_cmd, timeout)
        
        if returncode == 0:
            self._current_session = target
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"attached_to": target, "output": stdout[:500]},
                message=f"Atasat la {target}"
            )
        else:
            return ToolResult(status=ToolStatus.ERROR, error=f"Failed to attach: {stderr}")

    def _spawn(self, target: str, pkg: str, script: str, module: str, pattern: str, device: str, timeout: int) -> ToolResult:
        """Porneste aplicatie cu Frida."""
        if not pkg:
            return ToolResult(status=ToolStatus.ERROR, error="Package name este obligatoriu")

        device_arg = ["-D", device] if device else ["-f"]
        returncode, stdout, stderr = self._run_frida_tool("frida", device_arg + [pkg], timeout)
        
        if returncode == 0:
            # Extract PID from output
            match = re.search(r'pid=(\d+)', stdout)
            pid = match.group(1) if match else "unknown"
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"package": pkg, "pid": pid, "output": stdout[:500]},
                message=f"Spawned {pkg} (PID: {pid})"
            )
        else:
            return ToolResult(status=ToolStatus.ERROR, error=f"Spawn failed: {stderr}")

    def _inject(self, target: str, pkg: str, script: str, module: str, pattern: str, device: str, timeout: int) -> ToolResult:
        """Injecteaza script JavaScript."""
        if not script:
            return ToolResult(status=ToolStatus.ERROR, error="Script JS este obligatoriu")

        if not target:
            return ToolResult(status=ToolStatus.ERROR, error="Target (PID) este obligatoriu")

        # Create temporary script file
        script_path = "frida_temp_script.js"
        try:
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(script)

            device_arg = ["-D", device] if device else []
            returncode, stdout, stderr = self._run_frida_tool(
                "frida",
                device_arg + ["-p", target, "-l", script_path], 
                timeout
            )

            return ToolResult(
                status=ToolStatus.SUCCESS if returncode == 0 else ToolStatus.ERROR,
                data={"target": target, "script_file": script_path, "output": stdout[:1000]},
                message="Script injectat" if returncode == 0 else f"Inject failed: {stderr}"
            )
        finally:
            # Cleanup
            if os.path.exists(script_path):
                try:
                    os.remove(script_path)
                except Exception:
                    pass

    def _list_modules(self, target: str, pkg: str, script: str, module: str, pattern: str, device: str, timeout: int) -> ToolResult:
        """Listeaza modulele incarcate pentru un proces."""
        if not target:
            return ToolResult(status=ToolStatus.ERROR, error="Target (PID sau nume) este obligatoriu")

        device_arg = ["-D", device] if device else []
        
        # Create listing script
        list_script = """
        Process.enumerateModules().forEach(function(m) {
            console.log(m.name + "|" + m.base + "|" + m.size);
        });
        """
        
        script_path = "frida_modules_script.js"
        try:
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(list_script)

            if target.isdigit():
                cmd = device_arg + ["-p", target, "-l", script_path]
            else:
                cmd = device_arg + ["-n", target, "-l", script_path]

            returncode, stdout, stderr = self._run_frida_tool("frida", cmd, timeout)

            modules = []
            for line in stdout.split("\n"):
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
        finally:
            if os.path.exists(script_path):
                try:
                    os.remove(script_path)
                except Exception:
                    pass

    def _find_functions(self, target: str, pkg: str, script: str, module: str, pattern: str, device: str, timeout: int) -> ToolResult:
        """Gaseste functii intr-un modul."""
        if not module:
            return ToolResult(status=ToolStatus.ERROR, error="Module name este obligatoriu")

        if not target:
            return ToolResult(status=ToolStatus.ERROR, error="Target (PID) este obligatoriu")

        search_pattern = pattern or ".*"
        
        # Create search script
        search_script = f"""
        var mod = Process.findModuleByName("{module}");
        if (mod) {{
            console.log("Module: " + mod.name);
            mod.enumerateExports().forEach(function(e) {{
                if (/{search_pattern}/.test(e.name)) {{
                    console.log("EXPORT|" + e.name + "|" + e.type + "|" + e.address);
                }}
            }});
        }} else {{
            console.log("MODULE_NOT_FOUND");
        }}
        """

        script_path = "frida_find_script.js"
        try:
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(search_script)

            device_arg = ["-D", device] if device else ["-p", target]
            returncode, stdout, stderr = self._run_frida_tool("frida", device_arg + ["-l", script_path], timeout)

            if "MODULE_NOT_FOUND" in stdout:
                return ToolResult(status=ToolStatus.ERROR, error=f"Module {module} not found")

            functions = []
            for line in stdout.split("\n"):
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
        finally:
            if os.path.exists(script_path):
                try:
                    os.remove(script_path)
                except Exception:
                    pass

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
        self._current_session = None
        return ToolResult(
            status=ToolStatus.SUCCESS,
            message="Sesiune terminata"
        )


def smoke_test():
    """Smoke test pentru Frida tool."""
    print("[*] Testing Frida Tool...")
    
    tool = FridaTool()
    
    # Test version
    result = tool.execute(operation="version")
    if result.is_success:
        print(f"[OK] Frida version: {result.data.get('version')}")
    else:
        print(f"[!] Frida not installed: {result.error}")
        print("    Install with: pip install frida-tools")
        return
    
    # Test devices
    result = tool.execute(operation="devices")
    if result.is_success:
        print(f"[OK] Frida devices: {result.data.get('count')}")
    else:
        print(f"[?] Devices: {result.error}")
    
    print("[*] Frida smoke test complete")


if __name__ == "__main__":
    smoke_test()