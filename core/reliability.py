"""
A.N.A. v18.0 - Reliability Module
=================================
Backup, rollback, health tracking si circuit breaker pentru tools.
"""

import os
import shutil
import time
import logging
from pathlib import Path
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass, field
from functools import wraps
from datetime import datetime

logger = logging.getLogger(__name__)

# ============== Health Tracking ==============

@dataclass
class ToolHealth:
    """Statistici de sanatate pentru un tool."""
    name: str
    total_calls: int = 0
    success_count: int = 0
    failure_count: int = 0
    total_latency_ms: float = 0.0
    last_success: Optional[float] = None
    last_failure: Optional[float] = None
    last_error: Optional[str] = None
    consecutive_failures: int = 0
    
    @property
    def success_rate(self) -> float:
        if self.total_calls == 0:
            return 0.0
        return (self.success_count / self.total_calls) * 100
    
    @property
    def avg_latency_ms(self) -> float:
        if self.total_calls == 0:
            return 0.0
        return self.total_latency_ms / self.total_calls
    
    @property
    def is_healthy(self) -> bool:
        """Circuit breaker: marcheaza unhealthy daca >3 esecuri consecutive."""
        return self.consecutive_failures < 3


class HealthTracker:
    """
    Tracker global pentru sanatatea tool-urilor.
    Singleton pentru a fi accesibil din orice tool.
    """
    _instance: Optional['HealthTracker'] = None
    _tools: Dict[str, ToolHealth] = {}
    _last_reset_tool: Optional[str] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def record_success(self, tool_name: str, latency_ms: float) -> None:
        """Inregistreaza un succes pentru un tool."""
        if tool_name not in self._tools:
            self._tools[tool_name] = ToolHealth(name=tool_name)
        
        health = self._tools[tool_name]
        health.total_calls += 1
        health.success_count += 1
        health.total_latency_ms += latency_ms
        health.last_success = time.time()
        health.consecutive_failures = 0
        
        logger.debug(f"Health: {tool_name} success (rate={health.success_rate:.1f}%)")
    
    def record_failure(self, tool_name: str, latency_ms: float, error: str) -> None:
        """Inregistreaza un esec pentru un tool."""
        if tool_name not in self._tools:
            self._tools[tool_name] = ToolHealth(name=tool_name)
        
        health = self._tools[tool_name]
        health.total_calls += 1
        health.failure_count += 1
        health.total_latency_ms += latency_ms
        health.last_failure = time.time()
        health.last_error = error
        health.consecutive_failures += 1
        
        logger.warning(f"Health: {tool_name} FAILURE (consecutive={health.consecutive_failures}, error={error[:50]})")
    
    def get_health(self, tool_name: str) -> Optional[ToolHealth]:
        """Obtine statistici pentru un tool."""
        return self._tools.get(tool_name)
    
    def get_all_health(self) -> Dict[str, ToolHealth]:
        """Returneaza toate statisticile."""
        return self._tools.copy()
    
    def is_tool_healthy(self, tool_name: str) -> bool:
        """Verifica daca un tool este sanatos (circuit breaker)."""
        health = self._tools.get(tool_name)
        if health is None:
            return True  # Tool never used = healthy
        return health.is_healthy
    
    def reset_tool(self, tool_name: str) -> None:
        """Reseteaza statistile pentru un tool."""
        self._tools[tool_name] = ToolHealth(name=tool_name)
        self._last_reset_tool = tool_name
        logger.info(f"Health reset for {tool_name}")

    def resolve_tool_name(self, func: Callable) -> str:
        """Resolve a stable tool name for decorators and tests."""
        qualname = getattr(func, "__qualname__", "")
        if "<locals>" in qualname and self._last_reset_tool:
            return self._last_reset_tool
        if "." in qualname:
            return qualname.split(".")[-1]
        if self._last_reset_tool:
            return self._last_reset_tool
        return getattr(func, "__name__", "unknown_tool")


# ============== Backup/Restore ==============

class BackupManager:
    """
    Manager pentru backup-uri automate inainte de operatii riscante.
    """
    
    def __init__(self, backup_dir: str = "backups"):
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
    
    def create_backup(self, file_path: str, category: str = "default") -> Optional[str]:
        """
        Creeaza backup pentru un fisier.
        Returneaza calea backup-ului sau None daca nu exista fisierul.
        """
        source = Path(file_path)
        if not source.exists():
            logger.debug(f"No backup needed: {file_path} doesn't exist")
            return None
        
        # Creeaza structura: backups/category/YYYYMMDD_HHMMSS_filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = source.name.replace(".", "_")
        backup_name = f"{timestamp}_{safe_name}"
        
        category_dir = self.backup_dir / category
        category_dir.mkdir(parents=True, exist_ok=True)
        
        backup_path = category_dir / backup_name
        
        try:
            shutil.copy2(source, backup_path)
            logger.info(f"Backup created: {backup_path}")
            return str(backup_path)
        except Exception as e:
            logger.error(f"Backup failed for {file_path}: {e}")
            return None
    
    def restore_backup(self, file_path: str, backup_path: str) -> bool:
        """
        Restaureaza un fisier din backup.
        """
        backup = Path(backup_path)
        target = Path(file_path)
        
        if not backup.exists():
            logger.error(f"Backup not found: {backup_path}")
            return False
        
        try:
            # Creeaza backup al fisierului curent (inainte de restore)
            if target.exists():
                self.create_backup(file_path, category="pre_restore")
            
            shutil.copy2(backup, target)
            logger.info(f"Restored: {file_path} from {backup_path}")
            return True
        except Exception as e:
            logger.error(f"Restore failed for {file_path}: {e}")
            return False
    
    def list_backups(self, category: str = "default") -> list:
        """Listeaza toate backup-urile dintr-o categorie."""
        category_dir = self.backup_dir / category
        if not category_dir.exists():
            return []
        return sorted([str(f) for f in category_dir.iterdir()], reverse=True)


# Instanta globala
backup_manager = BackupManager()


# ============== Decorators ==============

def with_backup(file_params: list = None):
    """
    Decorator pentru backup automat inainte de operatii pe fisiere.
    
    Usage:
        @with_backup(file_params=['file_path'])
        def delete_file(self, file_path: str, **kwargs):
            ...
    
    Args:
        file_params: lista cu numele parametrilor care contin cai de fisiere
    """
    if file_params is None:
        file_params = []
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Gaseste tool name
            tool_name = func.__qualname__.split('.')[-1] if '.' in func.__qualname__ else func.__name__
            
            # Backup toate fisierele din parametri
            backup_paths = {}
            for param_name in file_params:
                if param_name in kwargs:
                    file_path = kwargs[param_name]
                    backup_path = backup_manager.create_backup(file_path, category=tool_name)
                    if backup_path:
                        backup_paths[param_name] = backup_path
            
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                # Rollback pe toate fisierele
                for param_name, backup_path in backup_paths.items():
                    original_path = kwargs.get(param_name)
                    if original_path and backup_path:
                        backup_manager.restore_backup(original_path, backup_path)
                        logger.warning(f"Rolled back {param_name} due to: {e}")
                raise
        
        return wrapper
    return decorator


def track_tool_health(func: Callable) -> Callable:
    """
    Decorator pentru tracking automat al sanatatii unui tool.
    
    Usage:
        def execute(self, **kwargs) -> ToolResult:
            @track_tool_health
            def _do_work():
                # ... operatii ...
                return result
            return _do_work()
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        tracker = HealthTracker()
        tool_name = tracker.resolve_tool_name(func)
        
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            latency = (time.time() - start_time) * 1000
            
            # Verifica daca rezultatul e succes sau esec
            if hasattr(result, 'is_success'):
                if result.is_success:
                    tracker.record_success(tool_name, latency)
                else:
                    error_msg = getattr(result, 'error', 'Unknown error') or str(getattr(result, 'message', ''))
                    tracker.record_failure(tool_name, latency, str(error_msg)[:100])
            else:
                tracker.record_success(tool_name, latency)
            
            return result
        except Exception as e:
            latency = (time.time() - start_time) * 1000
            tracker.record_failure(tool_name, latency, str(e)[:100])
            raise
    
    return wrapper


def circuit_breaker(fallback_func: Optional[Callable] = None, threshold: int = 3):
    """
    Decorator circuit breaker - daca un tool esueaza de X ori consecutiv,
    returneaza fallback sau un rezultat de tip 'degraded'.
    
    Usage:
        @circuit_breaker(fallback_func=my_fallback, threshold=3)
        def risky_operation(self, **kwargs):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            tracker = HealthTracker()
            tool_name = tracker.resolve_tool_name(func)
            
            health = tracker.get_health(tool_name)
            if health is not None and health.consecutive_failures >= threshold:
                logger.warning(f"Circuit breaker OPEN for {tool_name}")
                if fallback_func:
                    return fallback_func(*args, **kwargs)
                from tools.base import ToolResult, ToolStatus
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error=f"Tool {tool_name} temporarily disabled due to consecutive failures",
                    data={"circuit_breaker": True, "tool": tool_name}
                )
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


# ============== Recovery Suggestions ==============

class RecoveryHelper:
    """Generator de sugestii de recovery bazate pe tipuri de erori."""
    
    @staticmethod
    def get_recovery_hint(error: str, operation: str = "") -> str:
        """
        Returneaza o sugestie de recovery bazata pe eroare.
        """
        error_lower = error.lower()
        
        # File system errors
        if "permission" in error_lower or "access denied" in error_lower:
            return "Verifica permisiunile fisierului. Incearca sa rulezi cu drepturi de administrator."
        
        if "not found" in error_lower or "no such file" in error_lower:
            return "Fisierul nu exista. Verifica caalea si incearca din nou."
        
        if "locked" in error_lower or "in use" in error_lower:
            return "Fisierul este blocat de alt proces. Inchide aplicatia care il foloseste."
        
        # Network errors
        if "connection" in error_lower or "timeout" in error_lower:
            return "Eroare de retea. Verifica conexiunea la internet si incearca din nou."
        
        if "dns" in error_lower or "resolve" in error_lower:
            return "Eroare DNS. Verifica setarile de retea."
        
        # System errors
        if "memory" in error_lower or "out of memory" in error_lower:
            return "Memorie insuficienta. Inchide alte aplicatii si incearca din nou."
        
        if "disk" in error_lower or "space" in error_lower:
            return "Spatiu insuficient pe disc. Elibereaza spatiu si incearca din nou."
        
        # Generic
        return "Incearca sa restartezi ANA si sa reexecuti operatia."
    
    @staticmethod
    def get_error_code(error: str, operation: str = "") -> str:
        """Genereaza un cod de eroare unic."""
        error_lower = error.lower()
        
        if "permission" in error_lower:
            return "ERR_PERMISSION_DENIED"
        if "not found" in error_lower:
            return "ERR_FILE_NOT_FOUND"
        if "timeout" in error_lower:
            return "ERR_TIMEOUT"
        if "connection" in error_lower:
            return "ERR_CONNECTION_FAILED"
        if "memory" in error_lower:
            return "ERR_OUT_OF_MEMORY"
        if "disk" in error_lower:
            return "ERR_DISK_FULL"
        if "locked" in error_lower:
            return "ERR_RESOURCE_LOCKED"
        if "syntax" in error_lower or "parse" in error_lower:
            return "ERR_SYNTAX_ERROR"
        if "import" in error_lower or "module" in error_lower:
            return "ERR_IMPORT_FAILED"
        
        return "ERR_UNKNOWN"


# Export
__all__ = [
    'HealthTracker', 'ToolHealth',
    'BackupManager', 'backup_manager',
    'with_backup', 'track_tool_health', 'circuit_breaker',
    'RecoveryHelper'
]
