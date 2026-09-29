"""
A.N.A. v15.0 - System Tools (OS27 Hyper++)
===========================================
Instrumente pentru monitorizare si control sistem.

OS27 Hyper++ Features:
- Telemetry tracking for system operations (vitals, processes, kill_process, shell, speak, health_check, empty_recycle_bin)
- Health monitoring for system operations reliability
- MemoryCortex integration for system errors and state learning
- ContextEngine integration for system state awareness
- SelfEvolvingTool integration for anomaly detection on system failures
- Structured logging with error detection
"""

import os
import subprocess
import logging
import time
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

# OS27 Hyper++ Telemetry
_system_telemetry: Dict[str, Dict[str, Any]] = {}


def _record_system_telemetry(operation: str, success: bool, execution_time: float) -> None:
    """Record OS27 Hyper++ telemetry for system operations."""
    if operation not in _system_telemetry:
        _system_telemetry[operation] = {
            "operation_count": 0,
            "success_count": 0,
            "failure_count": 0,
            "total_time": 0.0,
            "last_execution_time": 0.0,
            "last_success": False,
        }
    
    _system_telemetry[operation]["operation_count"] += 1
    _system_telemetry[operation]["total_time"] += execution_time
    _system_telemetry[operation]["last_execution_time"] = execution_time
    _system_telemetry[operation]["last_success"] = success
    
    if success:
        _system_telemetry[operation]["success_count"] += 1
    else:
        _system_telemetry[operation]["failure_count"] += 1


def get_system_telemetry(operation: str | None = None) -> Dict[str, Any] | Dict[str, Dict[str, Any]]:
    """Get telemetry for system operations."""
    if operation:
        return _system_telemetry.get(operation, {})
    return _system_telemetry.copy()


def get_system_health() -> str:
    """Get health status for system tool based on telemetry."""
    if not _system_telemetry:
        return "unknown"
    
    total_ops = sum(stats["operation_count"] for stats in _system_telemetry.values())
    total_failures = sum(stats["failure_count"] for stats in _system_telemetry.values())
    
    if total_ops == 0:
        return "unknown"
    
    failure_rate = total_failures / total_ops
    if failure_rate > 0.5:
        return "broken"
    if failure_rate > 0.1:
        return "degraded"
    return "healthy"


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

    @staticmethod
    def _shell_command(command: str) -> list[str]:
        if os.name == "nt":
            return ["cmd.exe", "/d", "/s", "/c", command]
        return ["/bin/sh", "-c", command]

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
                    choices=["vitals", "processes", "kill_process", "shell", "speak", "health_check", "empty_recycle_bin"]
                ),
                ToolParameter(
                    name="target",
                    description="Tinta operatiunii (nume proces, comanda shell, text)",
                    type="string",
                    required=False
                ),
                ToolParameter(
                    name="confirm",
                    description="Seteaza true pentru operatii mutante: shell, kill_process sau empty_recycle_bin",
                    type="boolean",
                    required=False,
                    default=False,
                ),
            ],
            category="system",
            requires_confirmation=False,
            dangerous=True,
        )
    
    def execute(self, operation: str, target: Optional[str] = None, **kwargs) -> ToolResult:
        """Executa operatiunea de sistem."""
        start_time = time.time()
        
        # AI Core hooks (lazy import for safety)
        cortex = None
        context_engine = None
        evolver = None
        try:
            from tools.memory_cortex import MemoryCortex
            cortex = MemoryCortex()
        except Exception:
            pass
        try:
            from tools.context_engine import ContextEngine
            context_engine = ContextEngine()
        except Exception:
            pass
        try:
            from tools.self_evolving_tool import SelfEvolvingTool
            evolver = SelfEvolvingTool()
        except Exception:
            pass
        
        operations = {
            "vitals": self._get_vitals,
            "processes": self._list_processes,
            "kill_process": self._kill_process,
            "shell": self._execute_shell,
            "speak": self._speak,
            "health_check": self._health_check,
            "empty_recycle_bin": self._empty_recycle_bin,
        }

        if operation not in operations:
            logger.warning(f"Operatiune invalida '{operation}' ceruta de LLM, fallback la 'vitals'")
            operation = "vitals"

        if operation in {"shell", "kill_process", "empty_recycle_bin"} and not kwargs.get("confirm", False):
            execution_time = time.time() - start_time
            _record_system_telemetry(operation, False, execution_time)
            return ToolResult(
                status=ToolStatus.REQUIRES_CONFIRMATION,
                error=f"Operatiunea '{operation}' necesita confirm=true",
                message="Confirm required for mutating system operation",
            )

        result = operations[operation](target, **kwargs)
        
        execution_time = time.time() - start_time
        _record_system_telemetry(operation, result.is_success, execution_time)
        
        # ContextEngine integration for system state
        if context_engine and result.is_success:
            try:
                context_engine.update_context(
                    key="system_state",
                    value={
                        "operation": operation,
                        "target": target,
                        "success": result.is_success,
                        "timestamp": time.time(),
                    }
                )
            except Exception:
                pass
        
        # MemoryCortex integration for system errors
        if cortex and not result.is_success:
            try:
                cortex.remember(
                    "error",
                    f"system.{operation}",
                    f"System operation failed for {target}: {result.error}"
                )
            except Exception:
                pass
        
        return result
    
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
            except Exception as exc:
                logger.debug("Disk vitals unavailable: %s", exc)
            
            # Network (optional)
            try:
                net = psutil.net_io_counters()
                vitals["Net_Sent"] = f"{net.bytes_sent / (1024**2):.1f} MB"
                vitals["Net_Recv"] = f"{net.bytes_recv / (1024**2):.1f} MB"
            except Exception as exc:
                logger.debug("Network vitals unavailable: %s", exc)
            
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
                ':(){', '> /dev/', 'chmod 777', 'sudo rm',
                'remove-item -recurse', 'rd /s', 'rmdir /s',
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
                self._shell_command(target),
                shell=False,
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
            suggestions.append("[WARN] CPU foarte incarcat. Inchide procesele inutile.")
        if ram > 85:
            suggestions.append("[WARN] Memorie RAM limitata. Recomand curatarea cache-ului.")

        # Disk check
        try:
            disk = psutil.disk_usage('C:' if os.name == 'nt' else '/')
            if disk.percent > 90:
                suggestions.append(f" Spatiu pe disc critic ({disk.percent}%). Sterge fisiere temporare.")
        except Exception as exc:
            logger.debug("Disk health check unavailable: %s", exc)

        if not suggestions:
            suggestions.append(" Sistemul functioneaza optim. Nicio problema detectata.")

        return ToolResult(
            status=ToolStatus.SUCCESS,
            data="\n".join(suggestions),
            message="Health check complet"
        )

    def _empty_recycle_bin(self, target: Optional[str] = None, **kwargs) -> ToolResult:
        """Goleste cosul de gunoi (Recycle Bin)."""
        try:
            if os.name == 'nt':
                # Windows - folosim PowerShell Clear-RecycleBin
                result = subprocess.run(
                    ['powershell', '-Command', 'Clear-RecycleBin -Force'],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                if result.returncode == 0:
                    return ToolResult(
                        status=ToolStatus.SUCCESS,
                        data="Cosul de gunoi a fost golit cu succes",
                        message="Recycle bin emptied"
                    )
                else:
                    return ToolResult(
                        status=ToolStatus.ERROR,
                        error=f"Eroare la golirea cosului: {result.stderr}"
                    )
            else:
                # Linux/Mac - folosim trash-cli sau rm
                try:
                    result = subprocess.run(
                        ['trash-empty'],
                        capture_output=True,
                        text=True,
                        timeout=60
                    )
                    if result.returncode == 0:
                        return ToolResult(
                            status=ToolStatus.SUCCESS,
                            data="Cosul de gunoi a fost golit cu succes",
                            message="Recycle bin emptied"
                        )
                except FileNotFoundError:
                    # Fallback pentru Linux fara trash-cli
                    return ToolResult(
                        status=ToolStatus.ERROR,
                        error="Comanda trash-empty nu este disponibila. Instaleaza trash-cli: sudo apt install trash-cli"
                    )
        except subprocess.TimeoutExpired:
            return ToolResult(
                status=ToolStatus.ERROR,
                error="Timeout la golirea cosului de gunoi"
            )
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Eroare la golirea cosului: {e}"
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
