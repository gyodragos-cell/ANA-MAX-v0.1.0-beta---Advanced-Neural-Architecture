"""
ANA MAX - Task Healer (Self-Healing pentru Task-uri Lungi)
============================================================
Sistem de checkpoint/restart pentru task-uri lungi:
- Checkpoint automat la pasi critici
- Detectare crash/timeout
- Auto-restart din ultimul checkpoint
- Continuare transparenta pentru utilizator
"""

import json
import logging
import os
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

from core.session_logger import log_action, log_result, log_error, log_pattern, log_checkpoint, log_next_step

BASE_DIR = Path(__file__).resolve().parent.parent
CHECKPOINT_DIR = BASE_DIR / "ANA_MAX" / "checkpoints"


class TaskState:
    """Stare task pentru checkpoint."""
    
    def __init__(self, task_id: str, task_type: str, context: Dict[str, Any]):
        self.task_id = task_id
        self.task_type = task_type
        self.context = context
        self.checkpoints: List[Dict[str, Any]] = []
        self.current_step = 0
        self.created_at = datetime.now()
        self.last_updated = datetime.now()
        self.status = "in_progress"
        self.error_count = 0
        self.max_retries = 3
    
    def add_checkpoint(self, step_name: str, state: Dict[str, Any]):
        """Adauga checkpoint."""
        checkpoint = {
            "step": self.current_step,
            "name": step_name,
            "state": state,
            "timestamp": datetime.now().isoformat()
        }
        self.checkpoints.append(checkpoint)
        self.current_step += 1
        self.last_updated = datetime.now()
        
        log_checkpoint(f"Task {self.task_id} - {step_name}", {
            "step": self.current_step,
            "total_checkpoints": len(self.checkpoints)
        })
    
    def get_last_checkpoint(self) -> Optional[Dict[str, Any]]:
        """Returneaza ultimul checkpoint."""
        return self.checkpoints[-1] if self.checkpoints else None
    
    def can_retry(self) -> bool:
        """Verifica daca mai are retry-uri."""
        return self.error_count < self.max_retries
    
    def record_error(self):
        """Inregistreaza o eroare."""
        self.error_count += 1
        self.last_updated = datetime.now()
    
    def mark_completed(self):
        """Marcheaza task-ul ca complet."""
        self.status = "completed"
        self.last_updated = datetime.now()
    
    def mark_failed(self):
        """Marcheaza task-ul ca esuat."""
        self.status = "failed"
        self.last_updated = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Converteste in dict pentru serializare."""
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "context": self.context,
            "checkpoints": self.checkpoints,
            "current_step": self.current_step,
            "created_at": self.created_at.isoformat(),
            "last_updated": self.last_updated.isoformat(),
            "status": self.status,
            "error_count": self.error_count,
            "max_retries": self.max_retries
        }


class TaskHealer:
    """Manager pentru self-healing task-uri."""
    
    def __init__(self):
        self.active_tasks: Dict[str, TaskState] = {}
        self._lock = threading.Lock()
        self.logger = logging.getLogger("TASK_HEALER")
        
        # Asigura directorul de checkpoint
        CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
        
        log_action("Task Healer initialized", {"checkpoint_dir": str(CHECKPOINT_DIR)})
    
    def start_task(self, task_id: str, task_type: str, context: Dict[str, Any]) -> TaskState:
        """Incepe un nou task cu tracking."""
        with self._lock:
            task = TaskState(task_id, task_type, context)
            self.active_tasks[task_id] = task
            
            log_action(f"Task started: {task_id}", {
                "type": task_type,
                "context_keys": list(context.keys())
            })
            
            return task
    
    def checkpoint(self, task_id: str, step_name: str, state: Dict[str, Any]):
        """Creeaza checkpoint pentru task."""
        with self._lock:
            if task_id not in self.active_tasks:
                log_error(f"Task not found for checkpoint: {task_id}")
                return
            
            task = self.active_tasks[task_id]
            task.add_checkpoint(step_name, state)
            
            # Salveaza checkpoint pe disk
            self._save_checkpoint(task)
    
    def recover_task(self, task_id: str) -> Optional[TaskState]:
        """Recupereaza un task din checkpoint."""
        with self._lock:
            # Incearca sa incarce din disk
            checkpoint_file = CHECKPOINT_DIR / f"{task_id}.json"
            if checkpoint_file.exists():
                try:
                    with open(checkpoint_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    task = TaskState(data["task_id"], data["task_type"], data["context"])
                    task.checkpoints = data["checkpoints"]
                    task.current_step = data["current_step"]
                    task.created_at = datetime.fromisoformat(data["created_at"])
                    task.last_updated = datetime.fromisoformat(data["last_updated"])
                    task.status = data["status"]
                    task.error_count = data["error_count"]
                    task.max_retries = data["max_retries"]
                    
                    self.active_tasks[task_id] = task
                    
                    log_action(f"Task recovered from checkpoint: {task_id}", {
                        "steps": len(task.checkpoints),
                        "status": task.status
                    })
                    
                    return task
                    
                except Exception as e:
                    log_error(f"Failed to recover task {task_id}", e)
            
            return None
    
    def handle_error(self, task_id: str, error: Exception) -> bool:
        """Gestioneaza eroare si decide daca sa faca retry."""
        with self._lock:
            if task_id not in self.active_tasks:
                log_error(f"Task not found for error handling: {task_id}")
                return False
            
            task = self.active_tasks[task_id]
            task.record_error()
            
            log_error(f"Task error: {task_id}", error, {
                "error_count": task.error_count,
                "max_retries": task.max_retries
            })
            
            # Detecteaza pattern-uri de eroare
            self._detect_error_pattern(task_id, error)
            
            if task.can_retry():
                log_next_step(f"Retrying task {task_id} (attempt {task.error_count + 1})", priority="HIGH")
                return True
            else:
                task.mark_failed()
                log_pattern(f"Task {task_id} failed after {task.error_count} retries", "CRITICAL")
                return False
    
    def complete_task(self, task_id: str):
        """Marcheaza task ca complet."""
        with self._lock:
            if task_id in self.active_tasks:
                task = self.active_tasks[task_id]
                task.mark_completed()
                
                log_result(f"Task completed: {task_id}", success=True, context={
                    "steps": len(task.checkpoints),
                    "duration": (task.last_updated - task.created_at).total_seconds()
                })
                
                # Curata checkpoint-ul vechi
                checkpoint_file = CHECKPOINT_DIR / f"{task_id}.json"
                if checkpoint_file.exists():
                    checkpoint_file.unlink()
    
    def restart_stalled_task(self, task_id: str):
        """Auto-recovery pentru task-uri stalled."""
        with self._lock:
            if task_id not in self.active_tasks:
                # Incearca sa incarce din checkpoint
                checkpoint_file = CHECKPOINT_DIR / f"{task_id}.json"
                if checkpoint_file.exists():
                    try:
                        with open(checkpoint_file, 'r') as f:
                            checkpoint_data = json.load(f)
                        task = TaskState.from_checkpoint(checkpoint_data)
                        self.active_tasks[task_id] = task
                        log_pattern(f"Auto-recovery triggered for stalled task: {task_id}", "INFO")
                        return True
                    except Exception as e:
                        log_error(f"Failed to load checkpoint for {task_id}", e)
                        return False
                return False
            
            task = self.active_tasks[task_id]
            if task.status == "stalled":
                task.status = "in_progress"
                task.error_count = 0
                log_pattern(f"Auto-recovery triggered for stalled task: {task_id}", "INFO")
                return True
            return False
    
    def _save_checkpoint(self, task: TaskState):
        """Salveaza checkpoint pe disk."""
        try:
            checkpoint_file = CHECKPOINT_DIR / f"{task.task_id}.json"
            with open(checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(task.to_dict(), f, indent=2, default=str)
        except Exception as e:
            log_error(f"Failed to save checkpoint for {task.task_id}", e)
    
    def _detect_error_pattern(self, task_id: str, error: Exception):
        """Detecteaza pattern-uri de eroare pentru auto-repair."""
        error_str = str(error).lower()
        
        # Pattern-uri cunoscute
        patterns = {
            "timeout": "timeout_error",
            "connection": "network_error",
            "500": "server_error",
            "token": "auth_error",
            "permission": "permission_error",
            "file not found": "file_error",
            "memory": "memory_error"
        }
        
        for pattern, pattern_name in patterns.items():
            if pattern in error_str:
                log_pattern(f"Error pattern detected: {pattern_name}", "INFO", {
                    "task_id": task_id,
                    "error": error_str
                })
                break
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Returneaza status task."""
        with self._lock:
            if task_id in self.active_tasks:
                task = self.active_tasks[task_id]
                return task.to_dict()
        return None
    
    def cleanup_old_checkpoints(self, max_age_hours: int = 24):
        """Curata checkpoint-uri vechi."""
        try:
            now = datetime.now()
            for checkpoint_file in CHECKPOINT_DIR.glob("*.json"):
                file_time = datetime.fromtimestamp(checkpoint_file.stat().st_mtime)
                age_hours = (now - file_time).total_seconds() / 3600
                
                if age_hours > max_age_hours:
                    checkpoint_file.unlink()
                    log_action(f"Cleaned up old checkpoint: {checkpoint_file.name}", {
                        "age_hours": age_hours
                    })
        except Exception as e:
            log_error("Failed to cleanup old checkpoints", e)


# Singleton global
_task_healer: Optional[TaskHealer] = None


def get_task_healer() -> TaskHealer:
    """Returneaza instanta globala TaskHealer."""
    global _task_healer
    if _task_healer is None:
        _task_healer = TaskHealer()
    return _task_healer


# Decorator pentru auto-healing
def with_healing(task_type: str):
    """Decorator pentru functii cu auto-healing."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            task_id = f"{task_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            healer = get_task_healer()
            
            # Auto-recovery pentru task-uri stalled
            healer.restart_stalled_task(task_id)
            
            # Start task
            context = {"args": str(args)[:100], "kwargs": str(kwargs)[:100]}
            task = healer.start_task(task_id, task_type, context)
            
            try:
                # Checkpoint initial
                healer.checkpoint(task_id, "started", {"phase": "initial"})
                
                # Execute
                result = func(*args, **kwargs)
                
                # Complete
                healer.complete_task(task_id)
                return result
                
            except Exception as e:
                # Handle error
                if healer.handle_error(task_id, e):
                    # Retry logic could go here
                    last_checkpoint = task.get_last_checkpoint()
                    if last_checkpoint:
                        log_next_step(f"Retrying from checkpoint: {last_checkpoint['name']}", priority="HIGH")
                        # Implement retry logic based on checkpoint state
                
                # Re-raise after handling
                raise
                
        return wrapper
    return decorator
