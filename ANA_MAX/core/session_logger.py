"""
ANA MAX - Session Logger (Full Visibility System)
==================================================
Sistem complet de logare pentru vizibilitate totala:
- Timestamps precise
- Categorii (ACTION, RESULT, ERROR, NEXT_STEP)
- Auto-logare in ANA_MEMORY.md
- Real-time dashboard feed
- Pattern detection pentru auto-repair
"""

import json
import logging
import os
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

BASE_DIR = Path(__file__).resolve().parent.parent
ANA_MEMORY_PATH = BASE_DIR / "docs" / "ANA_MEMORY.md"
SESSION_LOG_PATH = BASE_DIR / "logs" / "session.log"
ERROR_LOG_PATH = BASE_DIR / "logs" / "errors.log"


class SessionLogger:
    """Logger profesional cu vizibilitate completa."""
    
    def __init__(self):
        self.session_start = datetime.now()
        self.action_count = 0
        self.error_count = 0
        self.success_count = 0
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._lock = threading.Lock()
        
        # Setup logging
        self._setup_logging()
        
    def _setup_logging(self):
        """Configureaza logging avansat."""
        self.logger = logging.getLogger("ANA_SESSION")
        self.logger.setLevel(logging.DEBUG)
        
        # Formater profesional
        formatter = logging.Formatter(
            '[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # File handler - session log
        session_handler = logging.FileHandler(SESSION_LOG_PATH, encoding='utf-8')
        session_handler.setLevel(logging.DEBUG)
        session_handler.setFormatter(formatter)
        self.logger.addHandler(session_handler)
        
        # File handler - error log
        error_handler = logging.FileHandler(ERROR_LOG_PATH, encoding='utf-8')
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        self.logger.addHandler(error_handler)
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
    
    def action(self, message: str, context: Optional[Dict[str, Any]] = None):
        """Logare actiune executata."""
        with self._lock:
            self.action_count += 1
            self.logger.info(f"ACTION #{self.action_count}: {message}")
            if context:
                self.logger.debug(f"Context: {json.dumps(context, indent=2)}")
            self._append_to_memory("ACTION", message, context)
    
    def result(self, message: str, success: bool = True, context: Optional[Dict[str, Any]] = None):
        """Logare rezultat actiune."""
        with self._lock:
            if success:
                self.success_count += 1
                self.logger.info(f"RESULT: {message}")
            else:
                self.error_count += 1
                self.logger.error(f"RESULT FAILED: {message}")
            
            if context:
                self.logger.debug(f"Context: {json.dumps(context, indent=2)}")
            self._append_to_memory("RESULT", message, context, success)
    
    def next_step(self, message: str, priority: str = "NORMAL"):
        """Logare pas urmator."""
        with self._lock:
            self.logger.info(f"NEXT STEP [{priority}]: {message}")
            self._append_to_memory("NEXT STEP", message, {"priority": priority})
    
    def error(self, message: str, exception: Optional[Exception] = None, context: Optional[Dict[str, Any]] = None):
        """Logare eroare cu detalii complete."""
        with self._lock:
            self.error_count += 1
            error_msg = f"ERROR: {message}"
            if exception:
                error_msg += f" | Exception: {type(exception).__name__}: {str(exception)}"
            
            self.logger.error(error_msg)
            if context:
                self.logger.error(f"Error Context: {json.dumps(context, indent=2)}")
            
            self._append_to_memory("ERROR", message, {"exception": str(exception), "context": context} if exception else context)
    
    def pattern_detected(self, pattern_name: str, severity: str = "INFO", details: Optional[Dict[str, Any]] = None):
        """Logare pattern detectat pentru auto-repair."""
        with self._lock:
            self.logger.warning(f"PATTERN DETECTED [{severity}]: {pattern_name}")
            if details:
                self.logger.debug(f"Pattern Details: {json.dumps(details, indent=2)}")
            self._append_to_memory("PATTERN", pattern_name, {"severity": severity, "details": details})
    
    def checkpoint(self, message: str, state: Optional[Dict[str, Any]] = None):
        """Checkpoint pentru proiecte lungi."""
        with self._lock:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.logger.info(f"CHECKPOINT [{timestamp}]: {message}")
            if state:
                self.logger.debug(f"Checkpoint State: {json.dumps(state, indent=2)}")
            self._append_to_memory("CHECKPOINT", message, state)
    
    def _append_to_memory(self, category: str, message: str, context: Optional[Dict[str, Any]] = None, success: bool = True):
        """Adauga intrare in ANA_MEMORY.md."""
        try:
            if not ANA_MEMORY_PATH.exists():
                ANA_MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
                ANA_MEMORY_PATH.write_text("# ANA Memory - Session Logs\n\n", encoding='utf-8')
            
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            entry = f"\n## [{timestamp}] {category}\n\n"
            entry += f"**Message**: {message}\n\n"
            
            if context:
                entry += f"**Context**:\n```json\n{json.dumps(context, indent=2)}\n```\n\n"
            
            if category == "RESULT":
                status = "✅ SUCCESS" if success else "❌ FAILED"
                entry += f"**Status**: {status}\n\n"
            
            # Append to file
            with open(ANA_MEMORY_PATH, 'a', encoding='utf-8') as f:
                f.write(entry)
                
        except Exception as e:
            self.logger.error(f"Failed to append to ANA_MEMORY: {e}")
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Returneaza statistici sesiune curenta."""
        duration = datetime.now() - self.session_start
        return {
            "session_id": self.session_id,
            "duration_seconds": duration.total_seconds(),
            "actions": self.action_count,
            "successes": self.success_count,
            "errors": self.error_count,
            "success_rate": f"{(self.success_count / max(self.action_count, 1)) * 100:.1f}%"
        }
    
    def summary(self):
        """Afiseaza rezumat sesiune."""
        stats = self.get_session_stats()
        self.logger.info("=" * 60)
        self.logger.info("SESSION SUMMARY")
        self.logger.info("=" * 60)
        self.logger.info(f"Session ID: {stats['session_id']}")
        self.logger.info(f"Duration: {stats['duration_seconds']:.1f}s")
        self.logger.info(f"Actions: {stats['actions']}")
        self.logger.info(f"Successes: {stats['successes']}")
        self.logger.info(f"Errors: {stats['errors']}")
        self.logger.info(f"Success Rate: {stats['success_rate']}")
        self.logger.info("=" * 60)


# Singleton global
_session_logger: Optional[SessionLogger] = None


def get_session_logger() -> SessionLogger:
    """Returneaza instanta globala SessionLogger."""
    global _session_logger
    if _session_logger is None:
        _session_logger = SessionLogger()
    return _session_logger


def log_action(message: str, context: Optional[Dict[str, Any]] = None):
    """Helper pentru logare actiune."""
    get_session_logger().action(message, context)


def log_result(message: str, success: bool = True, context: Optional[Dict[str, Any]] = None):
    """Helper pentru logare rezultat."""
    get_session_logger().result(message, success, context)


def log_next_step(message: str, priority: str = "NORMAL"):
    """Helper pentru logare pas urmator."""
    get_session_logger().next_step(message, priority)


def log_error(message: str, exception: Optional[Exception] = None, context: Optional[Dict[str, Any]] = None):
    """Helper pentru logare eroare."""
    get_session_logger().error(message, exception, context)


def log_pattern(pattern_name: str, severity: str = "INFO", details: Optional[Dict[str, Any]] = None):
    """Helper pentru logare pattern."""
    get_session_logger().pattern_detected(pattern_name, severity, details)


def log_checkpoint(message: str, state: Optional[Dict[str, Any]] = None):
    """Helper pentru logare checkpoint."""
    get_session_logger().checkpoint(message, state)
