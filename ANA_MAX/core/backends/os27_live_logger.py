#!/usr/bin/env python3
"""
OS27 Live Log System - Enterprise Debugging Layer
Real-time logging pentru debugging agent/tool failures si blocaje
"""

import os
import sys
import json
import time
import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import deque

# Paths
ANA_ROOT = Path(__file__).parent.parent
LOG_DIR = ANA_ROOT / "ANA_MAX" / "logs"
LIVE_LOG_FILE = LOG_DIR / "os27_live_debug.log"
LIVE_LOG_JSON = LOG_DIR / "os27_live_debug.json"

# Log retention
MAX_LOG_LINES = 1000
MAX_JSON_ENTRIES = 100
MAX_MEMORY_EVENTS = 50

class OS27LiveLogger:
    """Enterprise live logging system pentru debugging OS27"""
    
    def __init__(self):
        self._lock = threading.Lock()
        self._memory_events = deque(maxlen=MAX_MEMORY_EVENTS)
        self._active_failures = {}  # tool_name -> failure_count
        self._last_success_times = {}  # tool_name -> timestamp
        self._error_patterns = {}  # error_pattern -> count
        # OS27 UNCENSORED MODE - No blocked tools
        self._startup_time = datetime.now()
        
        # Setup logging
        self._setup_logging()
        
    def _setup_logging(self):
        """Setup logging cu file handler si console handler"""
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        
        # File handler
        file_handler = logging.FileHandler(LIVE_LOG_FILE, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(name)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter('[%(levelname)s] %(message)s')
        console_handler.setFormatter(console_formatter)
        
        # Setup logger
        self._logger = logging.getLogger('OS27_Live')
        self._logger.setLevel(logging.DEBUG)
        self._logger.addHandler(file_handler)
        self._logger.addHandler(console_handler)
        
    def log_agent_start(self, message: str, model: str = "qwen2.5-coder:7b"):
        """Log start sesiune agent"""
        with self._lock:
            event = {
                "timestamp": datetime.now().isoformat(),
                "type": "agent_start",
                "message": message[:200],
                "model": model,
                "session_id": self._generate_session_id()
            }
            self._memory_events.append(event)
            self._logger.info(f"AGENT START: {message[:100]} (model: {model})")
            self._write_json_log()
    
    def log_agent_thought(self, thought: str):
        """Log thought block pentru debugging"""
        with self._lock:
            event = {
                "timestamp": datetime.now().isoformat(),
                "type": "agent_thought",
                "thought": thought[:500],
                "length": len(thought)
            }
            self._memory_events.append(event)
            self._logger.debug(f"THOUGHT: {thought[:200]}...")
    
    def log_tool_start(self, tool_name: str, args: Dict[str, Any]):
        """Log start tool pentru debugging"""
        with self._lock:
            event = {
                "timestamp": datetime.now().isoformat(),
                "type": "tool_start",
                "tool": tool_name,
                "args": self._sanitize_args(args),
                "session_time": (datetime.now() - self._startup_time).total_seconds()
            }
            self._memory_events.append(event)
            self._logger.info(f"TOOL START: {tool_name} (args: {str(args)[:100]})")
    
    def log_tool_success(self, tool_name: str, result: str, duration_ms: float):
        """Log success tool cu timing"""
        with self._lock:
            event = {
                "timestamp": datetime.now().isoformat(),
                "type": "tool_success",
                "tool": tool_name,
                "result_length": len(result),
                "duration_ms": duration_ms,
                "session_time": (datetime.now() - self._startup_time).total_seconds()
            }
            self._memory_events.append(event)
            self._last_success_times[tool_name] = datetime.now()
            
            # Reset failure count pe success
            if tool_name in self._active_failures:
                del self._active_failures[tool_name]
            
            # OS27 UNCENSORED MODE - No blocked tools tracking
            
            self._logger.info(f"TOOL SUCCESS: {tool_name} ({duration_ms:.0f}ms, {len(result)} chars)")
    
    def log_tool_failure(self, tool_name: str, error: str, args: Dict[str, Any]):
        """Log failure tool cu pattern detection"""
        with self._lock:
            event = {
                "timestamp": datetime.now().isoformat(),
                "type": "tool_failure",
                "tool": tool_name,
                "error": error[:500],
                "args": self._sanitize_args(args),
                "session_time": (datetime.now() - self._startup_time).total_seconds()
            }
            self._memory_events.append(event)
            
            # Track failure count
            self._active_failures[tool_name] = self._active_failures.get(tool_name, 0) + 1
            
            # Pattern detection
            self._detect_error_patterns(error)

            # OS27 UNCENSORED MODE - No tool blocking, allow infinite retries
            # Tools never get blocked regardless of failure count
            # Removed: if self._active_failures[tool_name] >= 3: self._blocked_tools.add(tool_name)

            self._logger.error(f"TOOL FAILURE: {tool_name} - {error[:200]}")
    
    def log_agent_decision(self, decision: str, confidence: float = 0.0):
        """Log decision agent pentru debugging"""
        with self._lock:
            event = {
                "timestamp": datetime.now().isoformat(),
                "type": "agent_decision",
                "decision": decision[:300],
                "confidence": confidence,
                "session_time": (datetime.now() - self._startup_time).total_seconds()
            }
            self._memory_events.append(event)
            self._logger.info(f"DECISION: {decision[:150]} (confidence: {confidence:.2f})")
    
    def log_context_injection(self, context_type: str, data: Dict[str, Any]):
        """Log context injection pentru debugging"""
        with self._lock:
            event = {
                "timestamp": datetime.now().isoformat(),
                "type": "context_injection",
                "context_type": context_type,
                "data_keys": list(data.keys()),
                "data_size": len(str(data)),
                "session_time": (datetime.now() - self._startup_time).total_seconds()
            }
            self._memory_events.append(event)
            self._logger.debug(f"CONTEXT: {context_type} (keys: {list(data.keys())})")
    
    def log_blockage_detected(self, blockage_type: str, details: str):
        """Log detectare blockage pentru debugging"""
        with self._lock:
            event = {
                "timestamp": datetime.now().isoformat(),
                "type": "blockage_detected",
                "blockage_type": blockage_type,
                "details": details[:500],
                "session_time": (datetime.now() - self._startup_time).total_seconds()
            }
            self._memory_events.append(event)
            self._logger.critical(f"BLOCKAGE: {blockage_type} - {details[:200]}")
    
    def get_live_status(self) -> Dict[str, Any]:
        """Returneaza status live pentru debugging"""
        with self._lock:
            uptime = (datetime.now() - self._startup_time).total_seconds()
            
            return {
                "uptime_seconds": uptime,
                "memory_events_count": len(self._memory_events),
                "active_failures": dict(self._active_failures),
                # OS27 UNCENSORED MODE - No blocked tools
                "last_success_times": {k: v.isoformat() for k, v in self._last_success_times.items()},
                "error_patterns": dict(self._error_patterns),
                "recent_events": list(self._memory_events)[-10:]  # Last 10 events
            }
    
    def get_failure_analysis(self) -> Dict[str, Any]:
        """Analiza failures pentru debugging"""
        with self._lock:
            analysis = {
                "total_failures": sum(self._active_failures.values()),
                "most_failing_tools": sorted(
                    self._active_failures.items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:5],
                # OS27 UNCENSORED MODE - No blocked tools
                "common_error_patterns": sorted(
                    self._error_patterns.items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:5],
                "recommendations": self._generate_recommendations()
            }
            return analysis
    
    def _sanitize_args(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize args pentru logging (elimina sensitive data)"""
        sanitized = {}
        for k, v in args.items():
            if k.lower() in ['password', 'token', 'secret', 'key', 'api_key']:
                sanitized[k] = "***REDACTED***"
            elif isinstance(v, str) and len(v) > 200:
                sanitized[k] = v[:200] + "... (truncated)"
            else:
                sanitized[k] = v
        return sanitized
    
    def _detect_error_patterns(self, error: str):
        """Detecteaza pattern-uri comune de erori"""
        error_lower = error.lower()
        
        patterns = {
            'timeout': ['timeout', 'timed out', 'time limit'],
            'permission': ['permission denied', 'access denied', 'forbidden'],
            'not_found': ['not found', 'no such file', 'does not exist'],
            'connection': ['connection refused', 'connection error', 'network'],
            'memory': ['memory', 'out of memory', 'heap'],
            'syntax': ['syntax error', 'invalid syntax', 'parse error'],
            'import': ['import error', 'module not found', 'no module'],
        }
        
        for pattern_name, keywords in patterns.items():
            if any(keyword in error_lower for keyword in keywords):
                self._error_patterns[pattern_name] = self._error_patterns.get(pattern_name, 0) + 1
    
    def _generate_recommendations(self) -> List[str]:
        """Genereaza recomandari bazate pe failures"""
        recommendations = []

        # OS27 UNCENSORED MODE - No blocked tools recommendations

        # Check pentru error patterns
        if self._error_patterns.get('timeout', 0) > 2:
            recommendations.append("Prea multe timeout-uri - considera marirea timeout-ului")
        
        if self._error_patterns.get('permission', 0) > 2:
            recommendations.append("Probleme permisiuni - verifica drepturile de fisier/sistem")
        
        if self._error_patterns.get('import', 0) > 2:
            recommendations.append("Probleme import - verifica dependente si venv")
        
        # Check pentru repeated failures
        for tool, count in self._active_failures.items():
            if count >= 3:
                recommendations.append(f"Tool {tool} a esuat de {count} ori - considera abordare alternativa")
        
        return recommendations
    
    def _generate_session_id(self) -> str:
        """Genereaza session ID unic"""
        return f"session_{int(datetime.now().timestamp())}"
    
    def _write_json_log(self):
        """Scrie log in format JSON pentru parsing"""
        try:
            with self._lock:
                recent_events = list(self._memory_events)[-MAX_JSON_ENTRIES:]
                log_data = {
                    "session_start": self._startup_time.isoformat(),
                    "last_update": datetime.now().isoformat(),
                    "events": recent_events,
                    "status": self.get_live_status()
                }
                
                with open(LIVE_LOG_JSON, 'w', encoding='utf-8') as f:
                    json.dump(log_data, f, indent=2, default=str)
        except Exception as e:
            self._logger.error(f"Failed to write JSON log: {e}")
    
    def tail_live_log(self, lines: int = 20) -> List[str]:
        """Returneaza ultimele linii din log pentru live viewing"""
        try:
            if LIVE_LOG_FILE.exists():
                with open(LIVE_LOG_FILE, 'r', encoding='utf-8', errors='ignore') as f:
                    all_lines = f.readlines()
                return all_lines[-lines:] if len(all_lines) > lines else all_lines
            return []
        except Exception as e:
            self._logger.error(f"Failed to tail log: {e}")
            return []

# Singleton instance
_os27_live_logger = None

def get_os27_live_logger() -> OS27LiveLogger:
    """Get singleton OS27 Live Logger instance"""
    global _os27_live_logger
    if _os27_live_logger is None:
        _os27_live_logger = OS27LiveLogger()
    return _os27_live_logger