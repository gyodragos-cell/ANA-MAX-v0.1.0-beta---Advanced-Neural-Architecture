"""
A.N.A. v15.0 - System Tools
===========================
Instrumente pentru monitorizare si control sistem.
"""

import os
import subprocess
import logging
from typing import Optional, Dict, Any

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

try:
    import pyttsx3
    HAS_TTS = True
except ImportError:
    HAS_TTS = False

from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus

logger = logging.getLogger(__name__)


class SystemTool(Tool):
    """
    Tool pentru monitorizare si control sistem.
    Vitals, procese, comenzi shell (cu confirmare).
    """
    
    @staticmethod
    def _translate_cmd_for_windows(cmd: str) -> str:
        """
        Normalizeaza comenzile *nix frecvente la echivalente CMD pentru
        a evita eroarea 'is not recognized' si halucinatiile de sintaxa.
        Se aplica doar aliasuri simple, fara a emula un shell POSIX complet.
        """
        if os.name != "nt":
            return cmd

        aliases = {
            "ls": "dir",
            "pwd": "cd",
            "cat": "type",
            "clear": "cls",
            "ifconfig": "ipconfig",
            "ps": "tasklist",
            "ps aux": "tasklist",
            "kill": "taskkill /PID",
            "mv": "move",
            "cp": "copy",
            "rm -rf": "rmdir /s /q",
            "rm": "del",
            "touch": "type NUL >",
            "grep": "findstr",
        }

        stripped = cmd.strip()
        lower = stripped.lower()
        for k, v in aliases.items():
            if lower.startswith(k):
                return v + stripped[len(k):]
        return cmd


    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="system_control",
            description="Monitorizare si control sistem: vitals, procese, comenzi shell.",
            parameters=[
                ToolParameter(
                    name="operation",
                    description="Operatiunea de executat",
                    type="string",
                    required=True,
                    choices=["vitals", "processes", "kill_process", "shell", "speak", "health_check"]
                ),
                ToolParameter(
                    name="target",
                    description="Tinta operatiunii (nume proces, comanda shell, text)",
                    type="string",
                    required=False
                ),
            ],
            category="system",
            requires_confirmation=False  # Doar shell va cere confirmare
        )
    
    def execute(self, operation: str, target: Optional[str] = None, **kwargs) -> ToolResult:
        """Executa operatiunea de sistem."""
        operations = {
            "vitals": self._get_vitals,
            "processes": self._list_processes,
            "kill_process": self._kill_process,
            "shell": self._execute_shell,
            "speak": self._speak,
            "health_check": self._health_check,
        }
        
        if operation not in operations:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Operatiune necunoscuta: {operation}"
            )
        
        return operations[operation](target, **kwargs)
    
    def _get_vitals(self, target: Optional[str] = None, **kwargs) -> ToolResult:
        """Obtine vitalele sistemului."""
        if not HAS_PSUTIL:
            return ToolResult(
                status=ToolStatus.ERROR,
                error="psutil nu este instalat"
            )
        
        try:
            vitals = {
                "CPU": f"{psutil.cpu_percent(interval=1)}%",
                "RAM": f"{psutil.virtual_memory().percent}%",
                "RAM_Used": f"{psutil.virtual_memory().used / (1024**3):.1f} GB",
                "RAM_Total": f"{psutil.virtual_memory().total / (1024**3):.1f} GB",
            }
            
            # Disk usage
            try:
                if os.name == 'nt':
                    disk = psutil.disk_usage('C:')
                else:
                    disk = psutil.disk_usage('/')
                vitals["Disk"] = f"{disk.percent}%"
                vitals["Disk_Free"] = f"{disk.free / (1024**3):.1f} GB"
            except Exception:
                pass
            
            # Network (optional)
            try:
                net = psutil.net_io_counters()
                vitals["Net_Sent"] = f"{net.bytes_sent / (1024**2):.1f} MB"
                vitals["Net_Recv"] = f"{net.bytes_recv / (1024**2):.1f} MB"
            except Exception:
                pass
            
            formatted = "\n".join([f"{k}: {v}" for k, v in vitals.items()])
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data=formatted,
                message="Vitals obtinute"
            )
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Eroare la obtinere vitals: {e}"
            )
    
    def _list_processes(self, target: Optional[str] = None, **kwargs) -> ToolResult:
        """Listeaza procesele active."""
        if not HAS_PSUTIL:
            return ToolResult(
                status=ToolStatus.ERROR,
                error="psutil nu este instalat"
            )
        
        try:
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    info = proc.info
                    # Filtrare optionala
                    if target and target.lower() not in info['name'].lower():
                        continue
                    processes.append({
                        'pid': info['pid'],
                        'name': info['name'],
                        'cpu': info['cpu_percent'] or 0,
                        'mem': info['memory_percent'] or 0
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # Sorteaza dupa CPU
            processes.sort(key=lambda x: x['cpu'], reverse=True)
            
            # Top 20
            formatted = []
            for p in processes[:20]:
                formatted.append(f"[{p['pid']:>6}] {p['name'][:30]:<30} CPU: {p['cpu']:>5.1f}% MEM: {p['mem']:>5.1f}%")
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data="\n".join(formatted),
                message=f"Gasite {len(processes)} procese"
            )
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Eroare la listare procese: {e}"
            )
    
    def _kill_process(self, target: Optional[str] = None, **kwargs) -> ToolResult:
        """Opreste un proces dupa nume."""
        if not target:
            return ToolResult(
                status=ToolStatus.ERROR,
                error="Numele procesului este necesar"
            )
        
        if not HAS_PSUTIL:
            return ToolResult(
                status=ToolStatus.ERROR,
                error="psutil nu este instalat"
            )
        
        try:
            killed = 0
            for proc in psutil.process_iter(['name']):
                try:
                    if target.lower() in proc.info['name'].lower():
                        proc.kill()
                        killed += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            if killed > 0:
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data=f"Oprit {killed} proces(e) '{target}'",
                    message="Procese oprite"
                )
            else:
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data=f"Nu am gasit procese cu numele '{target}'",
                    message="Niciun proces oprit"
                )
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Eroare la oprire proces: {e}"
            )
    
    def _execute_shell(self, target: Optional[str] = None, **kwargs) -> ToolResult:
        """
        Executa o comanda shell.
        ATENTIE: Aceasta functie necesita validare de securitate!
        """
        if not target:
            return ToolResult(
                status=ToolStatus.ERROR,
                error="Comanda shell este necesara"
            )
        
        # Verificare comenzi periculoase (activa cand sandbox este ACTIVAT)
        from core.config import config
        if config.get('safety.sandbox_mode', True):
            dangerous_patterns = [
                'rm -rf', 'del /s', 'format', 'mkfs', 'dd if=',
                ':(){', '> /dev/', 'chmod 777', 'sudo rm'
            ]
            
            for pattern in dangerous_patterns:
                if pattern in target.lower():
                    return ToolResult(
                        status=ToolStatus.BLOCKED,
                        error=f"Comanda blocata din motive de securitate: contine '{pattern}'"
                    )
        
        try:
            # Ajusteaza sintaxa pentru Windows CMD cand utilizatorul trimite comenzi POSIX.
            target = self._translate_cmd_for_windows(target)

            result = subprocess.check_output(
                target,
                shell=True,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=30
            )
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data=result if result else "(comanda executata fara output)",
                message="Comanda executata"
            )
        except subprocess.TimeoutExpired:
            return ToolResult(
                status=ToolStatus.ERROR,
                error="Timeout - comanda a durat prea mult (>30s)"
            )
        except subprocess.CalledProcessError as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Eroare la executie: {e.output}"
            )
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Eroare: {e}"
            )
    
    def _speak(self, target: Optional[str] = None, **kwargs) -> ToolResult:
        """Text-to-speech."""
        if not target:
            return ToolResult(
                status=ToolStatus.ERROR,
                error="Textul de rostit este necesar"
            )
        
        if not HAS_TTS:
            return ToolResult(
                status=ToolStatus.ERROR,
                error="pyttsx3 nu este instalat. Ruleaza: pip install pyttsx3"
            )
        
        try:
            engine = pyttsx3.init()
            engine.say(target)
            engine.runAndWait()
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data="Text rostit cu succes",
                message="TTS OK"
            )
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Eroare TTS: {e}"
            )

    def _health_check(self, target: Optional[str] = None, **kwargs) -> ToolResult:
        """Analizeaza sanatatea sistemului si ofera sugestii."""
        if not HAS_PSUTIL:
            return ToolResult(status=ToolStatus.ERROR, error="psutil necesar.")
            
        suggestions = []
        cpu = psutil.cpu_percent(interval=0.5)
        ram = psutil.virtual_memory().percent
        
        if cpu > 80:
            suggestions.append("⚠️ CPU foarte incarcat. Inchide procesele inutile.")
        if ram > 85:
            suggestions.append("⚠️ Memorie RAM limitata. Recomand curatarea cache-ului.")
            
        # Disk check
        try:
            disk = psutil.disk_usage('C:' if os.name == 'nt' else '/')
            if disk.percent > 90:
                suggestions.append(f"🚨 Spatiu pe disc critic ({disk.percent}%). Sterge fisiere temporare.")
        except Exception:
            pass
        
        if not suggestions:
            suggestions.append("✅ Sistemul functioneaza optim. Nicio problema detectata.")
            
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data="\n".join(suggestions),
            message="Health check complet"
        )


# Functii simple pentru compatibilitate
def get_system_vitals() -> str:
    """Functie simpla pentru vitals (compatibilitate)."""
    tool = SystemTool()
    result = tool.execute("vitals")
    return str(result)


def exec_shell(cmd: str) -> str:
    """Functie simpla pentru shell (compatibilitate)."""
    tool = SystemTool()
    result = tool.execute("shell", cmd)
    return str(result)