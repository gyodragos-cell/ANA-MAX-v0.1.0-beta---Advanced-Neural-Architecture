"""Windows-local utility tools for ANA_MAX OS-22."""

from __future__ import annotations

import ast
import csv
import importlib.util
import json
import operator
import os
import platform
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

try:
    import winreg
except Exception:  # pragma: no cover - non-Windows fallback
    winreg = None


ROOT = Path(__file__).resolve().parents[2]
LOG_DIR = ROOT / "ANA_MAX" / "logs"

APP_ALLOWLIST: dict[str, tuple[str, ...]] = {
    "calculator": ("calc.exe",),
    "calc": ("calc.exe",),
    "notepad": ("notepad.exe",),
    "paint": ("mspaint.exe",),
    "explorer": ("explorer.exe",),
}
APP_ALIASES: dict[str, str] = {
    "brave_browser": "brave",
    "browser_brave": "brave",
    "google_chrome": "chrome",
    "chrome_browser": "chrome",
    "browser_chrome": "chrome",
    "calc": "calculator",
}
BROWSER_CANDIDATES: dict[str, tuple[str, ...]] = {
    "brave": (
        r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe",
        r"%PROGRAMFILES%\BraveSoftware\Brave-Browser\Application\brave.exe",
        r"%PROGRAMFILES(X86)%\BraveSoftware\Brave-Browser\Application\brave.exe",
    ),
    "chrome": (
        r"%PROGRAMFILES%\Google\Chrome\Application\chrome.exe",
        r"%PROGRAMFILES(X86)%\Google\Chrome\Application\chrome.exe",
        r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe",
    ),
    "edge": (
        r"%PROGRAMFILES(X86)%\Microsoft\Edge\Application\msedge.exe",
        r"%PROGRAMFILES%\Microsoft\Edge\Application\msedge.exe",
        r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe",
    ),
}

OPERATORS: dict[type[ast.AST], Callable[[Any, Any], Any]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
UNARY_OPERATORS: dict[type[ast.AST], Callable[[Any], Any]] = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


def _safe_name(value: str) -> str:
    candidate = re.sub(r"[^a-zA-Z0-9_.-]+", "_", str(value or "").strip().lower())
    return candidate.strip("._-") or "calculator"


def _normalize_app_name(value: str) -> str:
    key = _safe_name(value)
    return APP_ALIASES.get(key, key)


def _expand_candidate(value: str) -> Path:
    return Path(os.path.expandvars(value)).expanduser()


def _browser_command(app_name: str) -> tuple[str, ...] | None:
    for candidate in BROWSER_CANDIDATES.get(app_name, ()):
        path = _expand_candidate(candidate)
        if path.is_file():
            return (str(path),)
    return None


def find_app(app_name: str) -> dict[str, Any]:
    key = _normalize_app_name(app_name)
    command = APP_ALLOWLIST.get(key) or _browser_command(key)
    if command is None:
        return {
            "schema": "ana.os22.find_app.v1",
            "success": False,
            "app_name": key,
            "error": "app_not_found_or_not_allowed",
            "allowed_apps": sorted(set(APP_ALLOWLIST) | set(BROWSER_CANDIDATES)),
            "local_only": True,
            "metadata_only": True,
        }
    executable = command[0]
    return {
        "schema": "ana.os22.find_app.v1",
        "success": True,
        "app_name": key,
        "command": list(command),
        "executable": executable,
        "exists": Path(executable).is_file() if "\\" in executable or "/" in executable else shutil.which(executable) is not None,
        "local_only": True,
        "metadata_only": True,
    }


def open_windows_app(app_name: str) -> dict[str, Any]:
    key = _normalize_app_name(app_name)
    command = APP_ALLOWLIST.get(key) or _browser_command(key)
    if command is None:
        return {
            "schema": "ana.os22.open_windows_app.v1",
            "success": False,
            "app_name": key,
            "error": "app_not_allowed",
            "allowed_apps": sorted(set(APP_ALLOWLIST) | set(BROWSER_CANDIDATES)),
        }
    process = subprocess.Popen(command)  # noqa: S603
    return {
        "schema": "ana.os22.open_windows_app.v1",
        "success": True,
        "app_name": key,
        "command": list(command),
        "pid": int(getattr(process, "pid", 0) or 0),
        "local_only": True,
    }


def open_url_in_windows_app(app_name: str, url: str) -> dict[str, Any]:
    key = _normalize_app_name(app_name)
    parsed = urlparse(str(url or "").strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return {
            "schema": "ana.os22.open_url_in_windows_app.v1",
            "success": False,
            "app_name": key,
            "url": str(url or ""),
            "error": "invalid_http_url",
            "local_only": True,
        }
    command = _browser_command(key)
    if command is None:
        return {
            "schema": "ana.os22.open_url_in_windows_app.v1",
            "success": False,
            "app_name": key,
            "url": parsed.geturl(),
            "error": "browser_not_found_or_not_allowed",
            "allowed_browsers": sorted(BROWSER_CANDIDATES),
            "local_only": True,
        }
    process = subprocess.Popen([command[0], parsed.geturl()])  # noqa: S603
    return {
        "schema": "ana.os22.open_url_in_windows_app.v1",
        "success": True,
        "app_name": key,
        "command": [command[0], parsed.geturl()],
        "url": parsed.geturl(),
        "pid": int(getattr(process, "pid", 0) or 0),
        "local_only": True,
    }


def list_processes(name_filter: str | None = None, max_items: int = 50) -> dict[str, Any]:
    query = _safe_name(name_filter).replace("_", "").lower() if name_filter else ""
    limit = max(1, min(int(max_items or 50), 200))
    try:
        completed = subprocess.run(
            ["tasklist", "/fo", "csv", "/nh"],
            capture_output=True,
            check=False,
            text=True,
            timeout=10,
        )
    except Exception as exc:
        return {
            "schema": "ana.os22.process_list.v1",
            "success": False,
            "error": str(exc),
            "processes": [],
            "local_only": True,
            "metadata_only": True,
        }

    processes: list[dict[str, Any]] = []
    if completed.returncode == 0:
        for row in csv.reader(completed.stdout.splitlines()):
            if len(row) < 5:
                continue
            image_name = str(row[0]).strip()
            normalized_name = _safe_name(image_name).replace("_", "").lower()
            if query and query not in normalized_name:
                continue
            try:
                pid = int(str(row[1]).strip())
            except ValueError:
                pid = 0
            processes.append(
                {
                    "image_name": image_name,
                    "pid": pid,
                    "session_name": str(row[2]).strip(),
                    "session_number": str(row[3]).strip(),
                    "memory_usage": str(row[4]).strip(),
                }
            )
            if len(processes) >= limit:
                break

    return {
        "schema": "ana.os22.process_list.v1",
        "success": completed.returncode == 0,
        "returncode": int(completed.returncode),
        "filter": name_filter or "",
        "count": len(processes),
        "processes": processes,
        "stderr": completed.stderr.strip()[:500],
        "local_only": True,
        "metadata_only": True,
    }


def _registry_app_entries() -> list[dict[str, Any]]:
    if winreg is None:
        return []
    roots = (
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
    )
    entries: list[dict[str, Any]] = []
    for hive, subkey_path in roots:
        try:
            with winreg.OpenKey(hive, subkey_path) as root_key:
                index = 0
                while True:
                    try:
                        child_name = winreg.EnumKey(root_key, index)
                    except OSError:
                        break
                    index += 1
                    try:
                        with winreg.OpenKey(root_key, child_name) as child_key:
                            display_name = str(winreg.QueryValueEx(child_key, "DisplayName")[0]).strip()
                    except Exception:
                        continue
                    if not display_name:
                        continue
                    entry: dict[str, Any] = {"name": display_name}
                    for value_name, output_name in (
                        ("DisplayVersion", "version"),
                        ("Publisher", "publisher"),
                        ("InstallLocation", "install_location"),
                        ("DisplayIcon", "display_icon"),
                    ):
                        try:
                            value = str(winreg.QueryValueEx(child_key, value_name)[0]).strip()
                        except Exception:
                            value = ""
                        if value:
                            entry[output_name] = value
                    entries.append(entry)
        except Exception:
            continue
    return entries


def list_installed_apps(query: str | None = None, max_items: int = 50) -> dict[str, Any]:
    text_query = _safe_name(query).replace("_", "").lower() if query else ""
    limit = max(1, min(int(max_items or 50), 200))
    entries = _registry_app_entries()
    filtered: list[dict[str, Any]] = []
    seen: set[str] = set()
    for entry in sorted(entries, key=lambda item: str(item.get("name", "")).lower()):
        name = str(entry.get("name", "")).strip()
        normalized_name = _safe_name(name).replace("_", "").lower()
        if text_query and text_query not in normalized_name:
            continue
        if normalized_name in seen:
            continue
        seen.add(normalized_name)
        filtered.append(entry)
        if len(filtered) >= limit:
            break
    return {
        "schema": "ana.os22.installed_apps.v1",
        "success": True,
        "query": query or "",
        "count": len(filtered),
        "apps": filtered,
        "local_only": True,
        "metadata_only": True,
    }


def _memory_status() -> dict[str, Any]:
    if sys.platform != "win32":
        return {}
    try:
        import ctypes

        class MemoryStatusEx(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

        status = MemoryStatusEx()
        status.dwLength = ctypes.sizeof(MemoryStatusEx)
        if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            return {}
        return {
            "total_physical_bytes": int(status.ullTotalPhys),
            "available_physical_bytes": int(status.ullAvailPhys),
            "memory_load_percent": int(status.dwMemoryLoad),
            "total_page_file_bytes": int(status.ullTotalPageFile),
            "available_page_file_bytes": int(status.ullAvailPageFile),
        }
    except Exception:
        return {}


def _disk_statuses() -> list[dict[str, Any]]:
    disks: list[dict[str, Any]] = []
    for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        drive = f"{letter}:\\"
        if not Path(drive).exists():
            continue
        try:
            total_disk, used_disk, free_disk = shutil.disk_usage(drive)
        except Exception:
            continue
        disks.append(
            {
                "drive": drive,
                "total_bytes": int(total_disk),
                "used_bytes": int(used_disk),
                "free_bytes": int(free_disk),
            }
        )
    return disks


def _powershell_json(script: str, timeout: int = 10) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
            capture_output=True,
            check=False,
            text=True,
            timeout=timeout,
        )
    except Exception as exc:
        return {"success": False, "error": str(exc)}
    if completed.returncode != 0:
        return {"success": False, "error": completed.stderr.strip()[:500], "returncode": int(completed.returncode)}
    raw = completed.stdout.strip()
    if not raw:
        return {"success": False, "error": "empty_powershell_output"}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        return {"success": False, "error": f"invalid_powershell_json:{exc}", "raw": raw[:500]}
    if isinstance(payload, dict):
        payload["success"] = True
        return payload
    return {"success": True, "data": payload}


def _collect_hardware_snapshot() -> dict[str, Any]:
    script = r"""
$ErrorActionPreference = 'SilentlyContinue'
$os = Get-CimInstance Win32_OperatingSystem | Select-Object Caption,Version,BuildNumber,OSArchitecture,LastBootUpTime,TotalVisibleMemorySize,FreePhysicalMemory
$cs = Get-CimInstance Win32_ComputerSystem | Select-Object Manufacturer,Model,Name,Domain,TotalPhysicalMemory,NumberOfLogicalProcessors
$cpu = Get-CimInstance Win32_Processor | Select-Object -First 1 Name,NumberOfCores,NumberOfLogicalProcessors,MaxClockSpeed
$gpu = @(Get-CimInstance Win32_VideoController | Select-Object Name,AdapterRAM,DriverVersion)
[pscustomobject]@{
  operating_system = $os
  computer_system = $cs
  cpu = $cpu
  gpus = $gpu
} | ConvertTo-Json -Depth 5 -Compress
"""
    return _powershell_json(script)


def system_overview() -> dict[str, Any]:
    disks = _disk_statuses()
    first_disk = disks[0] if disks else {}
    hardware = _collect_hardware_snapshot()
    memory = _memory_status()
    operating_system = hardware.get("operating_system") if isinstance(hardware.get("operating_system"), dict) else {}
    computer_system = hardware.get("computer_system") if isinstance(hardware.get("computer_system"), dict) else {}
    cpu = hardware.get("cpu") if isinstance(hardware.get("cpu"), dict) else {}
    gpus = hardware.get("gpus", [])
    if isinstance(gpus, dict):
        gpus = [gpus]
    if not isinstance(gpus, list):
        gpus = []
    return {
        "schema": "ana.os22.system_overview.v1",
        "success": True,
        "platform": sys.platform,
        "windows_version": sys.getwindowsversion().platform_version if hasattr(sys, "getwindowsversion") else "",
        "python": sys.version.split()[0],
        "processor": os.environ.get("PROCESSOR_IDENTIFIER", ""),
        "cpu_count": os.cpu_count() or 0,
        "workspace_root": str(ROOT),
        "disk_total_bytes": int(first_disk.get("total_bytes", 0) or 0),
        "disk_used_bytes": int(first_disk.get("used_bytes", 0) or 0),
        "disk_free_bytes": int(first_disk.get("free_bytes", 0) or 0),
        "os": {
            "name": operating_system.get("Caption") or platform.platform(),
            "version": operating_system.get("Version") or platform.version(),
            "build": operating_system.get("BuildNumber") or "",
            "architecture": operating_system.get("OSArchitecture") or platform.machine(),
            "last_boot": operating_system.get("LastBootUpTime") or "",
        },
        "computer": {
            "name": computer_system.get("Name") or os.environ.get("COMPUTERNAME", ""),
            "manufacturer": computer_system.get("Manufacturer") or "",
            "model": computer_system.get("Model") or "",
            "domain": computer_system.get("Domain") or "",
        },
        "cpu": {
            "name": cpu.get("Name") or os.environ.get("PROCESSOR_IDENTIFIER", ""),
            "cores": int(cpu.get("NumberOfCores", 0) or 0),
            "logical_processors": int(cpu.get("NumberOfLogicalProcessors", 0) or os.cpu_count() or 0),
            "max_clock_mhz": int(cpu.get("MaxClockSpeed", 0) or 0),
        },
        "memory": memory,
        "gpus": gpus,
        "disks": disks,
        "hardware_probe": {
            "success": bool(hardware.get("success")),
            "error": str(hardware.get("error", "")),
        },
        "local_only": True,
        "metadata_only": True,
    }


def frida_status() -> dict[str, Any]:
    spec = importlib.util.find_spec("frida")
    if spec is None:
        return {
            "schema": "ana.os22.frida_status.v1",
            "success": True,
            "available": False,
            "version": "",
            "note": "frida_python_module_not_available",
            "local_only": True,
            "metadata_only": True,
        }
    try:
        import frida  # type: ignore

        version = str(getattr(frida, "__version__", ""))
    except Exception as exc:
        return {
            "schema": "ana.os22.frida_status.v1",
            "success": False,
            "available": False,
            "version": "",
            "error": str(exc),
            "local_only": True,
            "metadata_only": True,
        }
    return {
        "schema": "ana.os22.frida_status.v1",
        "success": True,
        "available": True,
        "version": version,
        "capability": "status_only_no_attach",
        "local_only": True,
        "metadata_only": True,
    }


def capture_desktop_screenshot(output_dir: str | Path | None = None) -> dict[str, Any]:
    target_dir = Path(output_dir) if output_dir else LOG_DIR / "screenshots"
    target_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = target_dir / f"desktop_{timestamp}.png"
    try:
        from PIL import ImageGrab
    except Exception as exc:
        return {
            "schema": "ana.os22.desktop_screenshot.v1",
            "success": False,
            "error": f"pil_imagegrab_unavailable:{exc}",
            "local_only": True,
        }
    image = ImageGrab.grab()
    image.save(path)
    return {
        "schema": "ana.os22.desktop_screenshot.v1",
        "success": True,
        "path": str(path),
        "width": int(image.width),
        "height": int(image.height),
        "local_only": True,
    }


def _normalize_expression(expression: str) -> str:
    text = str(expression or "").lower()
    text = text.replace("x", "*")
    text = text.replace("=", "")
    text = re.sub(r"[^0-9+\-*/().% ]+", " ", text)
    return " ".join(text.split())


def _eval_node(node: ast.AST) -> float | int:
    if isinstance(node, ast.Expression):
        return _eval_node(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in OPERATORS:
            raise ValueError("operator_not_allowed")
        left = _eval_node(node.left)
        right = _eval_node(node.right)
        return OPERATORS[op_type](left, right)
    if isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in UNARY_OPERATORS:
            raise ValueError("unary_operator_not_allowed")
        return UNARY_OPERATORS[op_type](_eval_node(node.operand))
    raise ValueError("expression_not_allowed")


def calculate_expression(expression: str) -> dict[str, Any]:
    normalized = _normalize_expression(expression)
    if not normalized:
        return {
            "schema": "ana.os22.calculate_expression.v1",
            "success": False,
            "expression": str(expression or ""),
            "error": "empty_expression",
        }
    try:
        tree = ast.parse(normalized, mode="eval")
        value = _eval_node(tree)
    except Exception as exc:
        return {
            "schema": "ana.os22.calculate_expression.v1",
            "success": False,
            "expression": str(expression or ""),
            "normalized": normalized,
            "error": str(exc),
        }
    result: int | float = int(value) if isinstance(value, float) and value.is_integer() else value
    return {
        "schema": "ana.os22.calculate_expression.v1",
        "success": True,
        "expression": str(expression or ""),
        "normalized": normalized,
        "result": result,
        "text": f"{normalized} = {result}",
    }


def dumps_result(result: dict[str, Any]) -> str:
    return json.dumps(result, ensure_ascii=True, sort_keys=True)
