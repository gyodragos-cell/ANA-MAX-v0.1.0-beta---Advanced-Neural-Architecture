"""
A.N.A. v15.0 - Privacy Tools
============================
Instrumente pentru protecția privacy-ului.
"""

import os
import shutil
import logging
from typing import List, Optional
from pathlib import Path

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus

logger = logging.getLogger(__name__)


class PrivacyTool(Tool):
    """
    Tool pentru protecția privacy-ului (Ghost Protocol).
    Detectează, blochează și curăță servicii de telemetrie.
    """
    
    # Domenii de telemetrie de blocat
    TELEMETRY_DOMAINS = [
        "vortex.data.microsoft.com",
        "settings-win.data.microsoft.com",
        "telemetry.microsoft.com",
        "telemetry.sdk.azure-automation.net",
        "v10.events.data.microsoft.com",
        "v20.events.data.microsoft.com",
        "telemetry.vscodestatistics.com",
        "cursor-telemetry.com",
        "dc.services.visualstudio.com",
        "watson.telemetry.microsoft.com",
    ]
    
    # Servicii Windows de telemetrie
    TELEMETRY_SERVICES = [
        "DiagTrack",
        "dmwappushservice",
        "WMPNetworkSvc",
    ]
    
    # Căi pentru curățare
    CLEANUP_PATHS = [
        "%APPDATA%/Cursor/logs",
        "%APPDATA%/Code/logs",
        "%LOCALAPPDATA%/Microsoft/Windows/WebCache",
        "C:/Windows/Logs/MeasuredBoot",
    ]

    # Cuvinte cheie corporate pentru obfuscare (Corporate Safety)
    CORPORATE_KEYWORDS = [
        "internal", "confidential", "proprietary", "salary", 
        "contract", "manager", "policy", "employee"
    ]
    
    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="privacy_shield",
            description="Protejează anonimitatea Operatorului. Detectează, blochează sau curăță servicii de telemetrie și obfuschează date corporate.",
            parameters=[
                ToolParameter(
                    name="operation",
                    description="Operațiunea de executat",
                    type="string",
                    required=True,
                    choices=["scan", "block", "clean", "status", "obfuscate", "stealth_mode"]
                ),
                ToolParameter(
                    name="text",
                    description="Textul de obfuscat (pentru operațiunea 'obfuscate')",
                    type="string",
                    required=False
                )
            ],
            category="privacy",
            requires_confirmation=True,  # Operațiuni sensibile
            dangerous=False
        )

    def execute(self, operation: str, text: Optional[str] = None) -> ToolResult:
        """Execută operațiunea de privacy."""
        if operation == "scan":
            return self._scan_telemetry()
        elif operation == "block":
            return self._block_telemetry()
        elif operation == "clean":
            return self._clean_telemetry()
        elif operation == "status":
            return self._get_status()
        elif operation == "obfuscate":
            return self._obfuscate_corporate_data(text or "")
        elif operation == "stealth_mode":
            return self._toggle_stealth_mode()
        else:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Operațiune necunoscută: {operation}"
            )

    def _obfuscate_corporate_data(self, text: str) -> ToolResult:
        """Înlocuiește datele corporate sensibile cu placeholder-e."""
        if not text:
            return ToolResult(status=ToolStatus.ERROR, error="Nu a fost furnizat text pentru obfuscare.")
        
        obfuscated = text
        for kw in self.CORPORATE_KEYWORDS:
            import re
            # Folosim șablon r-string pentru regex pentru a evita SyntaxWarning în Python 3.12+
            pattern = rf"\b{kw}\b"
            obfuscated = re.sub(pattern, "[REDACTED_CORP]", obfuscated, flags=re.IGNORECASE)
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data=obfuscated,
            message="Datele corporate au fost obfuscate pentru siguranță."
        )

    def _toggle_stealth_mode(self) -> ToolResult:
        """Dezactivează logarea conversațiilor pentru sesiune (Mod Coleg Invizibil)."""
        import os
        stealth_file = "logs/.stealth_active"
        try:
            if os.path.exists(stealth_file):
                os.remove(stealth_file)
                msg = "Modul Stealth DEZACTIVAT. Conversațiile vor fi salvate."
            else:
                with open(stealth_file, "w") as f:
                    f.write("active")
                msg = "Modul Stealth ACTIVAT. Nicio conversație nu va fi salvată în baza de date locală."
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data=msg,
                message="Status Stealth actualizat."
            )
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=f"Nu am putut schimba modul stealth: {e}")
    
    def _scan_telemetry(self) -> ToolResult:
        """Scanează sistemul pentru servicii de telemetrie."""
        findings = []
        
        # Verifică servicii Windows
        if HAS_PSUTIL and os.name == 'nt':
            try:
                for service in psutil.win_service_iter():
                    if any(ts in service.name() for ts in self.TELEMETRY_SERVICES):
                        status = "ACTIV" if service.status() == "running" else "OPRIT"
                        findings.append(f"Serviciu: {service.display_name()} [{status}]")
            except Exception as e:
                logger.warning(f"Nu pot scana servicii: {e}")
        
        # Verifică fișier hosts pentru blocări existente
        hosts_path = self._get_hosts_path()
        if hosts_path and os.path.exists(hosts_path):
            try:
                with open(hosts_path, 'r') as f:
                    content = f.read()
                    blocked = [d for d in self.TELEMETRY_DOMAINS if d in content]
                    if blocked:
                        findings.append(f"Domenii deja blocate în hosts: {len(blocked)}")
                    else:
                        findings.append("⚠️ Niciun domeniu de telemetrie blocat în hosts!")
            except Exception as e:
                logger.warning(f"Nu pot citi hosts: {e}")
        
        # Verifică existența folderelor de log
        for path_template in self.CLEANUP_PATHS:
            path = os.path.expandvars(path_template)
            if os.path.exists(path):
                size = self._get_dir_size(path)
                findings.append(f"Log găsit: {path} ({size})")
        
        if not findings:
            findings.append("Nicio problemă de telemetrie detectată!")
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data="\n".join(findings),
            message="Scanare completă"
        )
    
    def _block_telemetry(self) -> ToolResult:
        """Blochează domeniile de telemetrie în fișierul hosts."""
        hosts_path = self._get_hosts_path()
        
        if not hosts_path:
            return ToolResult(
                status=ToolStatus.ERROR,
                error="Nu pot determina calea către fișierul hosts"
            )
        
        try:
            # Citește conținutul existent
            existing_content = ""
            if os.path.exists(hosts_path):
                with open(hosts_path, 'r') as f:
                    existing_content = f.read()
            
            # Backup
            backup_path = f"{hosts_path}.ana_backup"
            if not os.path.exists(backup_path):
                with open(backup_path, 'w') as f:
                    f.write(existing_content)
            
            # Verifică ce domenii trebuie adăugate
            domains_to_add = [
                d for d in self.TELEMETRY_DOMAINS 
                if d not in existing_content
            ]
            
            if not domains_to_add:
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data="Toate domeniile sunt deja blocate!",
                    message="Nimic de făcut"
                )
            
            # Adaugă domeniile noi
            with open(hosts_path, 'a') as f:
                f.write("\n\n# A.N.A. GHOST PROTOCOL - PRIVACY BLOCK\n")
                f.write(f"# Added by A.N.A. Privacy Shield\n")
                for domain in domains_to_add:
                    f.write(f"127.0.0.1 {domain}\n")
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data=f"Am blocat {len(domains_to_add)} domenii de telemetrie.\nBackup salvat: {backup_path}",
                message="Domenii blocate cu succes"
            )
            
        except PermissionError:
            return ToolResult(
                status=ToolStatus.ERROR,
                error="Lipsesc drepturile de administrator! Rulează ca Admin."
            )
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Eroare la blocare: {e}"
            )
    
    def _clean_telemetry(self) -> ToolResult:
        """Curăță log-urile de telemetrie."""
        cleaned = []
        errors = []
        
        for path_template in self.CLEANUP_PATHS:
            path = os.path.expandvars(path_template)
            
            if not os.path.exists(path):
                continue
            
            try:
                if os.path.isdir(path):
                    shutil.rmtree(path)
                else:
                    os.remove(path)
                cleaned.append(path)
            except PermissionError:
                errors.append(f"{path} (lipsesc drepturi)")
            except Exception as e:
                errors.append(f"{path} ({e})")
        
        result_text = []
        if cleaned:
            result_text.append(f"Curățate {len(cleaned)} locații:")
            result_text.extend([f"  ✓ {p}" for p in cleaned])
        if errors:
            result_text.append(f"\nErori la {len(errors)} locații:")
            result_text.extend([f"  ✗ {e}" for e in errors])
        
        if not cleaned and not errors:
            result_text.append("Nicio locație de curățat găsită.")
        
        return ToolResult(
            status=ToolStatus.SUCCESS if cleaned else ToolStatus.ERROR,
            data="\n".join(result_text),
            message=f"Curățate {len(cleaned)} locații"
        )
    
    def _get_status(self) -> ToolResult:
        """Obține statusul curent al protecției privacy."""
        status_lines = ["=== A.N.A. Privacy Status ===\n"]
        
        # Verifică Stealth Mode real
        import os
        stealth_active = os.path.exists("logs/.stealth_active")
        status_lines.append(f"Stealth Mode: {'ACTIV' if stealth_active else 'INACTIV'}")

        # Verifică hosts
        hosts_path = self._get_hosts_path()
        if hosts_path and os.path.exists(hosts_path):
            try:
                with open(hosts_path, 'r') as f:
                    content = f.read()
                blocked_count = sum(1 for d in self.TELEMETRY_DOMAINS if d in content)
                total = len(self.TELEMETRY_DOMAINS)
                status_lines.append(f"Domenii blocate: {blocked_count}/{total}")
                if blocked_count == total:
                    status_lines.append("✓ Protecție completă în hosts")
                else:
                    status_lines.append("⚠️ Protecție parțială - rulează 'block'")
            except Exception:
                status_lines.append("⚠️ Nu pot verifica hosts")
        
        # Verifică servicii
        if HAS_PSUTIL and os.name == 'nt':
            active_telemetry = 0
            try:
                for service in psutil.win_service_iter():
                    if any(ts in service.name() for ts in self.TELEMETRY_SERVICES):
                        if service.status() == "running":
                            active_telemetry += 1
                if active_telemetry > 0:
                    status_lines.append(f"⚠️ {active_telemetry} servicii de telemetrie active")
                else:
                    status_lines.append("✓ Niciun serviciu de telemetrie activ")
            except Exception:
                pass
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data="\n".join(status_lines)
        )
    
    def _get_hosts_path(self) -> Optional[str]:
        """Returnează calea către fișierul hosts."""
        if os.name == 'nt':
            return r"C:\Windows\System32\drivers\etc\hosts"
        else:
            return "/etc/hosts"
    
    def _get_dir_size(self, path: str) -> str:
        """Calculează dimensiunea unui director."""
        try:
            total = 0
            for dirpath, dirnames, filenames in os.walk(path):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    try:
                        total += os.path.getsize(fp)
                    except Exception:
                        pass
            
            if total < 1024:
                return f"{total} B"
            elif total < 1024 * 1024:
                return f"{total / 1024:.1f} KB"
            else:
                return f"{total / (1024 * 1024):.1f} MB"
        except Exception:
            return "N/A"
