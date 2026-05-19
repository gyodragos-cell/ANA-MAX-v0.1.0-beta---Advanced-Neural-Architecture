"""
APK Analyzer Tool - Android APK Reverse Engineering
Author: ANA_MAX
Date: 2026-05-12
Category: mobile

Functions:
- decompile_apk: Decompile APK with apktool
- extract_manifest: Parse AndroidManifest.xml
- list_permissions: Extract all permissions
- extract_dex: Extract DEX files
- find_secrets: Search for API keys, passwords
- list_activities: Get all activities
- list_services: Get all services
- get_app_info: Get basic app info
- sign_apk: Re-sign APK after modification

Requires: apktool, aapt (Android SDK)
"""

from __future__ import annotations

import subprocess
import os
import re
import logging
import xml.etree.ElementTree as ET
from typing import Optional, List, Dict, Any
from pathlib import Path

from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus

logger = logging.getLogger(__name__)


class APKAnalyzerTool(Tool):
    """Tool pentru analiza si reverse engineering APK-uri."""

    def __init__(self) -> None:
        self._tools = self._find_tools()

    def _find_tools(self) -> Dict[str, str]:
        """Gaseste tool-urile necesare."""
        tools = {
            "apktool": "apktool",
            "aapt": "aapt",
        }
        
        # Check for apktool in common locations
        apktool_paths = [
            "apktool",
            os.path.expandvars("%LOCALAPPDATA%\\Android\\Sdk\\tools\\bin\\apktool.bat"),
            os.path.expandvars("%USERPROFILE%\\AppData\\Local\\Android\\Sdk\\tools\\bin\\apktool.bat"),
            "C:\\Android\\Sdk\\tools\\bin\\apktool.bat",
        ]
        
        # On Windows, try .bat extension
        if os.name == "nt":
            for path in apktool_paths:
                if not path.endswith(".bat") and not path.endswith(".cmd"):
                    for ext in [".bat", ".cmd"]:
                        if os.path.exists(path + ext):
                            tools["apktool"] = path + ext
                            break
        
        # Check aapt
        aapt_paths = [
            "aapt",
            os.path.expandvars("%LOCALAPPDATA%\\Android\\Sdk\\build-tools\\34.0.0\\aapt.exe"),
            os.path.expandvars("%LOCALAPPDATA%\\Android\\Sdk\\build-tools\\33.0.0\\aapt.exe"),
        ]
        
        found = {}
        for tool_name, default_path in [("aapt", aapt_paths)]:
            for path in aapt_paths:
                if os.path.exists(path):
                    found["aapt"] = path
                    break
            else:
                found["aapt"] = "aapt"  # Fallback
        
        return tools

    def _run_command(self, cmd: List[str], timeout: int = 120) -> tuple[int, str, str]:
        """Ruleaza comanda si returneaza (returncode, stdout, stderr)."""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding="utf-8",
                errors="replace"
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, "", "Command timeout"
        except FileNotFoundError:
            return -1, "", f"Tool not found: {cmd[0]}"
        except Exception as e:
            return -1, "", str(e)

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="apk_analyzer",
            description="Reverse engineering APK: decompile, parse manifest, list permissions, extract DEX, cauta secrets.",
            parameters=[
                ToolParameter(
                    name="operation",
                    description="Operatia de executat",
                    type="string",
                    required=True,
                    choices=[
                        "info", "decompile", "manifest", "permissions",
                        "dex", "secrets", "activities", "services",
                        "repack", "sign"
                    ],
                ),
                ToolParameter(
                    name="apk_path",
                    description="Calea catre fisierul APK",
                    type="string",
                    required=True,
                ),
                ToolParameter(
                    name="output_dir",
                    description="Director pentru output (pentru decompile/repack)",
                    type="string",
                    required=False,
                    default="",
                ),
                ToolParameter(
                    name="options",
                    description="Optiuni JSON (pentru advanced operations)",
                    type="string",
                    required=False,
                    default="",
                ),
                ToolParameter(
                    name="timeout",
                    description="Timeout in secunde",
                    type="integer",
                    required=False,
                    default=120,
                ),
            ],
            category="mobile",
            requires_confirmation=False,
        )

    def execute(self, **kwargs) -> ToolResult:
        operation = kwargs.get("operation", "")
        apk_path = kwargs.get("apk_path", "")
        output_dir = kwargs.get("output_dir", "")
        timeout = int(kwargs.get("timeout", 120))

        if not apk_path:
            return ToolResult(status=ToolStatus.ERROR, error="APK path este obligatoriu")

        if not os.path.exists(apk_path):
            return ToolResult(status=ToolStatus.ERROR, error=f"APK nu exista: {apk_path}")

        if not apk_path.lower().endswith(".apk"):
            return ToolResult(status=ToolStatus.ERROR, error="Fisierul trebuie sa fie .apk")

        operations = {
            "info": self._get_info,
            "decompile": self._decompile,
            "manifest": self._get_manifest,
            "permissions": self._get_permissions,
            "dex": self._extract_dex,
            "secrets": self._find_secrets,
            "activities": self._get_activities,
            "services": self._get_services,
            "repack": self._repack,
            "sign": self._sign,
        }

        if operation not in operations:
            return ToolResult(status=ToolStatus.ERROR, error=f"Operatie necunoscuta: {operation}")

        try:
            return operations[operation](apk_path, output_dir, timeout, kwargs)
        except Exception as e:
            logger.error(f"APK Analyzer error: {e}")
            return ToolResult(status=ToolStatus.ERROR, error=str(e))

    def _get_info(self, apk_path: str, output_dir: str, timeout: int, kwargs: Dict) -> ToolResult:
        """Obtine informatii de baza despre APK."""
        returncode, stdout, stderr = self._run_command(["aapt", "dump", "badging", apk_path], timeout)
        
        if returncode != 0:
            return ToolResult(status=ToolStatus.ERROR, error=f"aapt failed: {stderr}")

        info = {}
        
        # Parse package info
        package_match = re.search(r"package: name='([^']+)' versionCode='([^']+)' versionName='([^']*)'", stdout)
        if package_match:
            info["package"] = package_match.group(1)
            info["version_code"] = package_match.group(2)
            info["version_name"] = package_match.group(3)

        # Parse SDK
        sdk_match = re.search(r"sdkVersion:'(\d+)' targetSdkVersion:'(\d+)'", stdout)
        if sdk_match:
            info["min_sdk"] = sdk_match.group(1)
            info["target_sdk"] = sdk_match.group(2)

        # Parse label
        label_match = re.search(r"application-label:'([^']*)'", stdout)
        if label_match:
            info["label"] = label_match.group(1)

        # Get file size
        info["size_bytes"] = os.path.getsize(apk_path)
        info["size_mb"] = round(info["size_bytes"] / (1024 * 1024), 2)

        return ToolResult(
            status=ToolStatus.SUCCESS,
            data=info,
            message=f"APK info: {info.get('package', 'unknown')} v{info.get('version_name', '?')}"
        )

    def _decompile(self, apk_path: str, output_dir: str, timeout: int, kwargs: Dict) -> ToolResult:
        """Decompileaza APK-ul."""
        if not output_dir:
            output_dir = f"decompiled_{Path(apk_path).stem}"
        
        output_dir = os.path.abspath(output_dir)
        os.makedirs(output_dir, exist_ok=True)

        returncode, stdout, stderr = self._run_command(
            ["apktool", "d", "-f", "-o", output_dir, apk_path],
            timeout
        )

        if returncode != 0:
            return ToolResult(status=ToolStatus.ERROR, error=f"Decompile failed: {stderr}")

        # Count files
        file_count = sum(len(files) for _, _, files in os.walk(output_dir))

        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={
                "apk": apk_path,
                "output_dir": output_dir,
                "file_count": file_count
            },
            message=f"Decompilat: {file_count} fisiere in {output_dir}"
        )

    def _get_manifest(self, apk_path: str, output_dir: str, timeout: int, kwargs: Dict) -> ToolResult:
        """Extrage si parseaza AndroidManifest.xml."""
        # First try with aapt
        returncode, stdout, stderr = self._run_command(
            ["aapt", "dump", "xmltree", apk_path, "AndroidManifest.xml"],
            timeout
        )

        if returncode != 0:
            # Try decompiling first
            temp_dir = f"temp_manifest_{Path(apk_path).stem}"
            os.makedirs(temp_dir, exist_ok=True)
            
            dec_rc, _, dec_err = self._run_command(
                ["apktool", "d", "-f", "-o", temp_dir, apk_path],
                timeout
            )
            
            if dec_rc != 0:
                return ToolResult(status=ToolStatus.ERROR, error=f"Failed to decompile: {dec_err}")
            
            manifest_path = os.path.join(temp_dir, "AndroidManifest.xml")
            if os.path.exists(manifest_path):
                with open(manifest_path, "r", encoding="utf-8") as f:
                    manifest_content = f.read()
                
                # Parse XML
                try:
                    root = ET.fromstring(manifest_content)
                    ns = {"android": "http://schemas.android.com/apk/res/android"}
                    
                    result = {
                        "package": root.get("package", "unknown"),
                        "version_code": root.get("{http://schemas.android.com/apk/res/android}versionCode", "?"),
                        "version_name": root.get("{http://schemas.android.com/apk/res/android}versionName", "?"),
                        "min_sdk": root.get("{http://schemas.android.com/apk/res/android}minSdkVersion", "?"),
                        "uses_permissions": [],
                        "activities": [],
                        "services": [],
                        "receivers": [],
                    }
                    
                    # Extract uses-permission
                    for perm in root.findall(".//uses-permission"):
                        name = perm.get("{http://schemas.android.com/apk/res/android}name", "")
                        if name:
                            result["uses_permissions"].append(name)
                    
                    # Extract activities
                    for act in root.findall(".//activity"):
                        name = act.get("{http://schemas.android.com/apk/res/android}name", "")
                        if name:
                            result["activities"].append(name)
                    
                    return ToolResult(
                        status=ToolStatus.SUCCESS,
                        data=result,
                        message=f"Manifest parsed: {len(result['activities'])} activities"
                    )
                except ET.ParseError as e:
                    return ToolResult(status=ToolStatus.ERROR, error=f"XML parse error: {e}")
            else:
                return ToolResult(status=ToolStatus.ERROR, error="AndroidManifest.xml not found")

        # Parse aapt output
        manifest_data = {
            "raw": stdout[:5000],
            "parsed": True
        }
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data=manifest_data,
            message="Manifest extras"
        )

    def _get_permissions(self, apk_path: str, output_dir: str, timeout: int, kwargs: Dict) -> ToolResult:
        """Listeaza toate permisiunile."""
        returncode, stdout, stderr = self._run_command(
            ["aapt", "dump", "permissions", apk_path],
            timeout
        )

        if returncode != 0:
            return ToolResult(status=ToolStatus.ERROR, error=f"aapt failed: {stderr}")

        permissions = []
        for line in stdout.split("\n"):
            line = line.strip()
            if line:
                permissions.append(line)

        # Categorize permissions
        dangerous = [p for p in permissions if any(x in p.lower() for x in ["location", "camera", "microphone", "contacts", "sms", "phone"])]
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={
                "total": len(permissions),
                "all": permissions,
                "dangerous": dangerous,
                "dangerous_count": len(dangerous)
            },
            message=f"Gasite {len(permissions)} permisiuni ({len(dangerous)} periculoase)"
        )

    def _extract_dex(self, apk_path: str, output_dir: str, timeout: int, kwargs: Dict) -> ToolResult:
        """Extrage fisierele DEX."""
        if not output_dir:
            output_dir = f"dex_{Path(apk_path).stem}"
        
        output_dir = os.path.abspath(output_dir)
        os.makedirs(output_dir, exist_ok=True)

        # Use unzip to extract DEX files
        import zipfile
        
        if not zipfile.is_zipfile(apk_path):
            return ToolResult(status=ToolStatus.ERROR, error="Invalid APK format")

        dex_files = []
        try:
            with zipfile.ZipFile(apk_path, 'r') as zip_ref:
                for file in zip_ref.namelist():
                    if file.endswith('.dex'):
                        zip_ref.extract(file, output_dir)
                        dex_files.append(file)
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=f"Extraction failed: {e}")

        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={
                "count": len(dex_files),
                "files": dex_files,
                "output_dir": output_dir
            },
            message=f"Extrase {len(dex_files)} fisiere DEX"
        )

    def _find_secrets(self, apk_path: str, output_dir: str, timeout: int, kwargs: Dict) -> ToolResult:
        """Cauta secrets in APK (API keys, passwords, URLs)."""
        if not output_dir:
            output_dir = f"temp_secrets_{Path(apk_path).stem}"
        
        # Decompile first
        os.makedirs(output_dir, exist_ok=True)
        
        returncode, stdout, stderr = self._run_command(
            ["apktool", "d", "-f", "-o", output_dir, apk_path],
            timeout
        )

        if returncode != 0:
            return ToolResult(status=ToolStatus.ERROR, error=f"Decompile failed: {stderr}")

        secrets = {
            "api_keys": [],
            "urls": [],
            "passwords": [],
            "tokens": [],
            "aws_keys": [],
        }

        patterns = {
            "api_keys": [
                r'[A-Za-z0-9]{20,40}',  # Generic API key
                r'AIza[0-9A-Za-z_-]{35}',  # Google API key
                r'sk_live_[0-9a-zA-Z]{24,}',  # Stripe
            ],
            "urls": [
                r'https?://[^\s<>"{}|\\^`\[\]]+',
                r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',
            ],
            "passwords": [
                r'password["\s]*[=:]["\s]*[^,"\s]+',
                r'pwd["\s]*[=:]["\s]*[^,"\s]+',
            ],
            "tokens": [
                r'Bearer [A-Za-z0-9._-]+',
                r'token["\s]*[=:]["\s]*[^,"\s]+',
            ],
            "aws_keys": [
                r'AKIA[0-9A-Z]{16}',
                r'aws_access_key',
            ],
        }

        # Search in common file types
        extensions = ['.xml', '.smali', '.java', '.properties', '.cfg', '.config', '.json']
        
        for root, _, files in os.walk(output_dir):
            for file in files:
                if any(file.endswith(ext) for ext in extensions):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                            content = f.read()
                            
                            for secret_type, regexes in patterns.items():
                                for regex in regexes:
                                    matches = re.findall(regex, content, re.IGNORECASE)
                                    for match in matches:
                                        if match not in secrets[secret_type]:
                                            secrets[secret_type].append(match)
                    except Exception:
                        continue

        total_secrets = sum(len(v) for v in secrets.values())
        
        # Cleanup temp dir
        import shutil
        try:
            shutil.rmtree(output_dir)
        except Exception:
            pass

        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={
                "total_found": total_secrets,
                "secrets": secrets
            },
            message=f"Gasite {total_secrets} potentiale secrets"
        )

    def _get_activities(self, apk_path: str, output_dir: str, timeout: int, kwargs: Dict) -> ToolResult:
        """Listeaza toate activity-urile."""
        returncode, stdout, stderr = self._run_command(
            ["aapt", "dump", "badging", apk_path],
            timeout
        )

        if returncode != 0:
            return ToolResult(status=ToolStatus.ERROR, error=f"aapt failed: {stderr}")

        activities = []
        for line in stdout.split("\n"):
            if "launchable-activity:" in line.lower():
                match = re.search(r"name='([^']+)'", line)
                if match:
                    activities.append(match.group(1))

        # Also get all activities from manifest
        returncode, stdout, _ = self._run_command(
            ["aapt", "dump", "xmltree", apk_path, "AndroidManifest.xml"],
            timeout
        )

        for line in stdout.split("\n"):
            if "E: activity" in line:
                match = re.search(r"activity.*name=0x\d+\"([^\"]+)", line)
                if match and match.group(1) not in activities:
                    activities.append(match.group(1))

        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={"count": len(activities), "activities": activities},
            message=f"Gasite {len(activities)} activities"
        )

    def _get_services(self, apk_path: str, output_dir: str, timeout: int, kwargs: Dict) -> ToolResult:
        """Listeaza toate service-urile."""
        returncode, stdout, stderr = self._run_command(
            ["aapt", "dump", "xmltree", apk_path, "AndroidManifest.xml"],
            timeout
        )

        if returncode != 0:
            return ToolResult(status=ToolStatus.ERROR, error=f"Manifest parse failed: {stderr}")

        services = []
        for line in stdout.split("\n"):
            if "E: service" in line:
                match = re.search(r"service.*name=0x\d+\"([^\"]+)", line)
                if match:
                    services.append(match.group(1))

        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={"count": len(services), "services": services},
            message=f"Gasite {len(services)} services"
        )

    def _repack(self, apk_path: str, output_dir: str, timeout: int, kwargs: Dict) -> ToolResult:
        """Repack APK dupa decompilare."""
        if not output_dir:
            return ToolResult(status=ToolStatus.ERROR, error="output_dir este obligatoriu pentru repack")

        if not os.path.exists(output_dir):
            return ToolResult(status=ToolStatus.ERROR, error=f"Directorul nu exista: {output_dir}")

        output_apk = kwargs.get("options", "")
        if not output_apk:
            output_apk = f"repacked_{Path(apk_path).name}"

        returncode, stdout, stderr = self._run_command(
            ["apktool", "b", "-o", output_apk, output_dir],
            timeout
        )

        if returncode != 0:
            return ToolResult(status=ToolStatus.ERROR, error=f"Repack failed: {stderr}")

        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={"output_apk": output_apk, "size": os.path.getsize(output_apk)},
            message=f"APK repacked: {output_apk}"
        )

    def _sign(self, apk_path: str, output_dir: str, timeout: int, kwargs: Dict) -> ToolResult:
        """Semnare APK (needs zipalign and apksigner)."""
        # This is a placeholder - real implementation needs key store
        return ToolResult(
            status=ToolStatus.ERROR,
            error="Signare necesita keystore. Foloseste: jarsigner -keystore my.keystore app.apk alias_name"
        )


def smoke_test():
    """Smoke test pentru APK Analyzer."""
    print("[*] Testing APK Analyzer Tool...")
    
    tool = APKAnalyzerTool()
    
    # Check tools availability
    result = tool._run_command(["aapt", "version"], 10)
    if result[0] == 0:
        print("[OK] aapt available")
    else:
        print("[!] aapt not found - install Android SDK")
    
    result = tool._run_command(["apktool", "-version"], 10)
    if result[0] == 0:
        print("[OK] apktool available")
    else:
        print("[!] apktool not found - install from https://apktool.tech/")
    
    print("[*] APK Analyzer smoke test complete")
    print("[*] To install tools:")
    print("    1. Download apktool from https://apktool.tech/")
    print("    2. Install Android SDK build-tools for aapt")


if __name__ == "__main__":
    smoke_test()