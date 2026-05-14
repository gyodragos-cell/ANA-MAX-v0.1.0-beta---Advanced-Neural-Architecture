"""
ADB Tool - Android Debug Bridge Integration
Author: ANA_MAX
Date: 2026-05-12
Category: mobile

Functions:
- adb_devices: List connected devices
- adb_shell: Execute shell command on device
- adb_install: Install APK
- adb_uninstall: Uninstall package
- adb_push: Push file to device
- adb_pull: Pull file from device
- adb_screenshot: Capture screen
- adb_list_packages: List installed packages
- adb_get_props: Get device properties
"""

from __future__ import annotations

import subprocess
import re
import os
import time
import logging
from typing import Optional, List, Dict
from pathlib import Path

from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus

logger = logging.getLogger(__name__)


class ADBTool(Tool):
    """Tool pentru operatii ADB cu dispozitive Android."""

    def __init__(self) -> None:
        self._adb_path = self._find_adb()

    def _find_adb(self) -> str:
        """Gaseste calea catre adb.exe."""
        adb_paths = [
            "adb",  # In PATH
            os.path.expandvars("%LOCALAPPDATA%\\Android\\Sdk\\platform-tools\\adb.exe"),
            os.path.expandvars("%USERPROFILE%\\AppData\\Local\\Android\\Sdk\\platform-tools\\adb.exe"),
            "C:\\Android\\Sdk\\platform-tools\\adb.exe",
        ]
        for path in adb_paths:
            try:
                result = subprocess.run([path, "version"], capture_output=True, timeout=5)
                if result.returncode == 0:
                    logger.info(f"ADB found at: {path}")
                    return path
            except (subprocess.TimeoutExpired, FileNotFoundError):
                continue
        return "adb"  # Fallback to PATH

    def _run_command(self, args: List[str], timeout: int = 30) -> tuple[int, str, str]:
        """Ruleaza comanda ADB si returneaza (returncode, stdout, stderr)."""
        try:
            result = subprocess.run(
                [self._adb_path] + args,
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding="utf-8",
                errors="replace"
            )
            return result.returncode, result.stdout.strip(), result.stderr.strip()
        except subprocess.TimeoutExpired:
            return -1, "", "Command timeout"
        except FileNotFoundError:
            return -1, "", f"ADB not found at {self._adb_path}"
        except Exception as e:
            return -1, "", str(e)

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="adb_operations",
            description="Operatii ADB pentru control dispozitive Android: devices, shell, install/uninstall APK, push/pull files, screenshot.",
            parameters=[
                ToolParameter(
                    name="operation",
                    description="Operatia de executat",
                    type="string",
                    required=True,
                    choices=[
                        "devices", "shell", "install", "uninstall",
                        "push", "pull", "screenshot", "list_packages",
                        "get_props", "reboot", "forward", "reverse"
                    ],
                ),
                ToolParameter(
                    name="device",
                    description="Device ID (serial number). Daca e goala, foloseste primul device.",
                    type="string",
                    required=False,
                    default="",
                ),
                ToolParameter(
                    name="command",
                    description="Comanda shell sau argument (pentru shell, install, etc.)",
                    type="string",
                    required=False,
                    default="",
                ),
                ToolParameter(
                    name="local_path",
                    description="Calea locala (pentru push/pull)",
                    type="string",
                    required=False,
                    default="",
                ),
                ToolParameter(
                    name="remote_path",
                    description="Calea pe dispozitiv (pentru push/pull)",
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
        device = kwargs.get("device", "")
        command = kwargs.get("command", "")
        local_path = kwargs.get("local_path", "")
        remote_path = kwargs.get("remote_path", "")
        timeout = int(kwargs.get("timeout", 30))

        device_arg = ["-s", device] if device else []

        operations = {
            "devices": self._devices,
            "shell": self._shell,
            "install": self._install,
            "uninstall": self._uninstall,
            "push": self._push,
            "pull": self._pull,
            "screenshot": self._screenshot,
            "list_packages": self._list_packages,
            "get_props": self._get_props,
            "reboot": self._reboot,
            "forward": self._forward,
            "reverse": self._reverse,
        }

        if operation not in operations:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Operatie necunoscuta: {operation}"
            )

        try:
            return operations[operation](device_arg, command, local_path, remote_path, timeout)
        except Exception as e:
            logger.error(f"ADB error: {e}")
            return ToolResult(status=ToolStatus.ERROR, error=str(e))

    def _devices(self, device_arg: List, cmd: str, local: str, remote: str, timeout: int) -> ToolResult:
        """Listeaza dispozitivele conectate."""
        returncode, stdout, stderr = self._run_command(["devices", "-l"], timeout)
        
        if returncode != 0:
            return ToolResult(status=ToolStatus.ERROR, error=stderr or "ADB devices failed")

        devices = []
        lines = stdout.split("\n")
        for line in lines[1:]:
            if line.strip():
                parts = re.split(r'\s+', line)
                if len(parts) >= 2:
                    serial = parts[0]
                    state = parts[1]
                    device_id = parts[3] if len(parts) > 3 and ":" in parts[3] else ""
                    devices.append({
                        "serial": serial,
                        "state": state,
                        "product": device_id
                    })

        if not devices:
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"count": 0, "devices": []},
                message="Nu sunt dispozitive conectate"
            )

        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={"count": len(devices), "devices": devices},
            message=f"Gasite {len(devices)} dispozitive"
        )

    def _shell(self, device_arg: List, cmd: str, local: str, remote: str, timeout: int) -> ToolResult:
        """Executa comanda shell pe dispozitiv."""
        if not cmd:
            return ToolResult(status=ToolStatus.ERROR, error="Comanda shell este obligatorie")

        full_cmd = device_arg + ["shell", cmd]
        returncode, stdout, stderr = self._run_command(full_cmd, timeout)

        if returncode != 0:
            return ToolResult(status=ToolStatus.ERROR, error=stderr or "Shell command failed")

        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={"output": stdout, "command": cmd},
            message="Comanda shell executata"
        )

    def _install(self, device_arg: List, apk_path: str, local: str, remote: str, timeout: int) -> ToolResult:
        """Instaleaza APK pe dispozitiv."""
        if not apk_path:
            return ToolResult(status=ToolStatus.ERROR, error="Calea APK este obligatorie")

        if not os.path.exists(apk_path):
            return ToolResult(status=ToolStatus.ERROR, error=f"APK nu exista: {apk_path}")

        # Verify it's an APK
        if not apk_path.lower().endswith(".apk"):
            return ToolResult(status=ToolStatus.ERROR, error="Fisierul trebuie sa fie .apk")

        full_cmd = device_arg + ["install", "-r", apk_path]  # -r for reinstall
        returncode, stdout, stderr = self._run_command(full_cmd, timeout)

        if returncode != 0:
            return ToolResult(status=ToolStatus.ERROR, error=stderr or "Install failed")

        if "Success" in stdout:
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"apk": apk_path, "result": stdout},
                message="APK instalat cu succes"
            )
        else:
            return ToolResult(status=ToolStatus.ERROR, error=stdout)

    def _uninstall(self, device_arg: List, package: str, local: str, remote: str, timeout: int) -> ToolResult:
        """Dezinstaleaza pachet de pe dispozitiv."""
        if not package:
            return ToolResult(status=ToolStatus.ERROR, error="Numele pachetului este obligatoriu")

        full_cmd = device_arg + ["uninstall", package]
        returncode, stdout, stderr = self._run_command(full_cmd, timeout)

        if returncode != 0:
            return ToolResult(status=ToolStatus.ERROR, error=stderr or "Uninstall failed")

        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={"package": package, "result": stdout},
            message="Pachet dezinstalat"
        )

    def _push(self, device_arg: List, cmd: str, local: str, remote: str, timeout: int) -> ToolResult:
        """Incarca fisier pe dispozitiv."""
        if not local or not remote:
            return ToolResult(status=ToolStatus.ERROR, error="local_path si remote_path sunt obligatorii")

        if not os.path.exists(local):
            return ToolResult(status=ToolStatus.ERROR, error=f"Fisierul local nu exista: {local}")

        full_cmd = device_arg + ["push", local, remote]
        returncode, stdout, stderr = self._run_command(full_cmd, timeout)

        if returncode != 0:
            return ToolResult(status=ToolStatus.ERROR, error=stderr or "Push failed")

        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={"local": local, "remote": remote, "result": stdout},
            message="Fisier transferat pe dispozitiv"
        )

    def _pull(self, device_arg: List, cmd: str, local: str, remote: str, timeout: int) -> ToolResult:
        """Descarca fisier de pe dispozitiv."""
        if not remote or not local:
            return ToolResult(status=ToolStatus.ERROR, error="remote_path si local_path sunt obligatorii")

        # Create parent directory if needed
        parent = os.path.dirname(local)
        if parent:
            os.makedirs(parent, exist_ok=True)

        full_cmd = device_arg + ["pull", remote, local]
        returncode, stdout, stderr = self._run_command(full_cmd, timeout)

        if returncode != 0:
            return ToolResult(status=ToolStatus.ERROR, error=stderr or "Pull failed")

        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={"local": local, "remote": remote, "result": stdout},
            message="Fisier descarcat de pe dispozitiv"
        )

    def _screenshot(self, device_arg: List, cmd: str, local: str, remote: str, timeout: int) -> ToolResult:
        """Captureaza ecranul dispozitivului."""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        remote_file = f"/sdcard/screenshot_{timestamp}.png"
        local_file = local or f"screenshots/screenshot_{timestamp}.png"

        # Ensure directory exists
        os.makedirs(os.path.dirname(local_file) if os.path.dirname(local_file) else ".", exist_ok=True)

        # Take screenshot
        returncode, stdout, stderr = self._run_command(device_arg + ["shell", "screencap", "-p", remote_file], timeout)
        if returncode != 0:
            return ToolResult(status=ToolStatus.ERROR, error=f"Failed to take screenshot: {stderr}")

        # Pull to local
        returncode, stdout, stderr = self._run_command(device_arg + ["pull", remote_file, local_file], timeout)
        if returncode != 0:
            return ToolResult(status=ToolStatus.ERROR, error=f"Failed to pull screenshot: {stderr}")

        # Clean up remote
        self._run_command(device_arg + ["shell", "rm", remote_file], 10)

        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={"path": local_file, "timestamp": timestamp},
            message=f"Screenshot salvat: {local_file}"
        )

    def _list_packages(self, device_arg: List, cmd: str, local: str, remote: str, timeout: int) -> ToolResult:
        """Listeaza pachetele instalate."""
        filter_cmd = cmd if cmd else ""
        full_cmd = device_arg + ["shell", "pm", "list", "packages"]
        if filter_cmd:
            full_cmd.extend(["-3", "-e", filter_cmd])  # -3 = third party, -e = exact filter
        else:
            full_cmd.append("-3")

        returncode, stdout, stderr = self._run_command(full_cmd, timeout)

        if returncode != 0:
            return ToolResult(status=ToolStatus.ERROR, error=stderr or "List packages failed")

        packages = [line.replace("package:", "").strip() for line in stdout.split("\n") if line.startswith("package:")]

        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={"count": len(packages), "packages": packages[:100]},  # Limit to 100
            message=f"Gasite {len(packages)} pachete"
        )

    def _get_props(self, device_arg: List, cmd: str, local: str, remote: str, timeout: int) -> ToolResult:
        """Obtine proprietatile dispozitivului."""
        returncode, stdout, stderr = self._run_command(device_arg + ["shell", "getprop"], timeout)

        if returncode != 0:
            return ToolResult(status=ToolStatus.ERROR, error=stderr or "Get props failed")

        props = {}
        for line in stdout.split("\n"):
            match = re.match(r'\[(.+?)\]: \[(.*?)\]', line)
            if match:
                key, value = match.groups()
                props[key] = value

        return ToolResult(
            status=ToolStatus.SUCCESS,
            data=props,
            message=f"Gasite {len(props)} proprietati"
        )

    def _reboot(self, device_arg: List, cmd: str, local: str, remote: str, timeout: int) -> ToolResult:
        """Repornește dispozitivul."""
        mode = cmd if cmd in ["bootloader", "recovery", "sideload"] else ""
        full_cmd = device_arg + ["reboot"] + ([mode] if mode else [])
        
        returncode, stdout, stderr = self._run_command(full_cmd, timeout)
        
        return ToolResult(
            status=ToolStatus.SUCCESS if returncode == 0 else ToolStatus.ERROR,
            data={"mode": mode or "normal"},
            message=f"Dispozitiv repornit ({mode or 'normal'})" if returncode == 0 else f"Reboot failed: {stderr}"
        )

    def _forward(self, device_arg: List, cmd: str, local: str, remote: str, timeout: int) -> ToolResult:
        """Forward port local catre dispozitiv."""
        if not local or not remote:
            return ToolResult(status=ToolStatus.ERROR, error="local si remote sunt obligatorii (ex: tcp:5000 tcp:5000)")

        full_cmd = device_arg + ["forward", local, remote]
        returncode, stdout, stderr = self._run_command(full_cmd, timeout)

        if returncode != 0:
            return ToolResult(status=ToolStatus.ERROR, error=stderr or "Forward failed")

        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={"local": local, "remote": remote},
            message=f"Port forwardat: {local} -> {remote}"
        )

    def _reverse(self, device_arg: List, cmd: str, local: str, remote: str, timeout: int) -> ToolResult:
        """Reverse port - dispozitiv catre local."""
        if not local or not remote:
            return ToolResult(status=ToolStatus.ERROR, error="local si remote sunt obligatorii")

        full_cmd = device_arg + ["reverse", local, remote]
        returncode, stdout, stderr = self._run_command(full_cmd, timeout)

        if returncode != 0:
            return ToolResult(status=ToolStatus.ERROR, error=stderr or "Reverse failed")

        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={"local": local, "remote": remote},
            message=f"Port reversat: {remote} -> {local}"
        )


def smoke_test():
    """Smoke test pentru ADB tool."""
    print("[*] Testing ADB Tool...")
    
    tool = ADBTool()
    
    # Test devices
    result = tool.execute(operation="devices")
    if result.is_success:
        data = result.data
        print(f"[OK] Devices: {data.get('count', 0)} found")
        for dev in data.get('devices', []):
            print(f"    - {dev.get('serial')}: {dev.get('state')}")
    else:
        print(f"[!] Devices test: {result.error}")
    
    print("[*] ADB smoke test complete")


if __name__ == "__main__":
    smoke_test()