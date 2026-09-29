"""
OS27 Telemetry Module - Professional Separation
Extracted from ollama_backend.py for better architecture
Enhanced with live debug logging for tool failure tracking
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any, Dict

logger = logging.getLogger(__name__)


class OS27Telemetry:
    """Professional OS27 telemetry injection system"""
    
    def __init__(self):
        self._cache_enabled = True
        self._cache_ttl = 30  # seconds
        self._last_injection = None
        self._cached_telemetry = {}
    
    def inject_telemetry(self, context: Any) -> Any:
        """
        Inject OS27 telemetry into AI context with caching.
        Accepts both dict and string context for compatibility.
        Professional implementation with error recovery and graceful degradation.
        """
        # Handle string context (convert to dict temporarily)
        if isinstance(context, str):
            logger.info("[OS27] Context is string, converting to dict for telemetry injection")
            temp_context = {"original_context": context}
            result_context = self._inject_telemetry_internal(temp_context)
            # Return as string with telemetry appended
            telemetry_text = self._format_telemetry_as_text(result_context)
            return f"{context}\n\n{telemetry_text}"
        
        # Handle dict context
        if not isinstance(context, dict):
            logger.warning("[OS27] Context is not dict or string, skipping telemetry injection")
            return context
        
        return self._inject_telemetry_internal(context)
    
    def _inject_telemetry_internal(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Internal method for dict context injection"""
        
        # Check cache first
        if self._cache_enabled and self._is_cache_valid():
            context.update(self._cached_telemetry)
            logger.info("[OS27] Using cached telemetry")
            return context
        
        try:
            telemetry_data = self._collect_telemetry()
            
            # Update cache
            self._cached_telemetry = telemetry_data
            self._last_injection = datetime.now()
            
            # Inject into context
            context.update(telemetry_data)
            context["os27_active"] = True
            context["os27_injection_time"] = datetime.now().isoformat()
            
            logger.info("[OS27] Telemetry injected into AI context")
            
        except Exception as e:
            logger.warning(f"[OS27] Failed to inject telemetry: {str(e)}")
            context["os27_active"] = False
            context["os27_error"] = str(e)
            context["os27_fallback_mode"] = True
        
        return context
    
    def _format_telemetry_as_text(self, context: Dict[str, Any]) -> str:
        """Format telemetry dict as readable text for string context"""
        lines = ["[OS27 TELEMETRY INJECTION]"]
        
        if context.get("os27_active"):
            lines.append("OS27 Status: ACTIVE")
            lines.append(f"Injection Time: {context.get('os27_injection_time', 'N/A')}")
            
            # Format key telemetry fields
            if "os27_system_vitals" in context:
                vitals = context["os27_system_vitals"]
                if isinstance(vitals, dict) and vitals:
                    lines.append("System Vitals:")
                    for k, v in vitals.items():
                        lines.append(f"  - {k}: {v}")
                else:
                    lines.append(f"System Vitals: {vitals}")
            
            if "os27_recent_errors" in context:
                errors = context["os27_recent_errors"]
                if isinstance(errors, list) and errors:
                    lines.append("Recent Errors:")
                    for err in errors:
                        err_str = str(err).strip()
                        if len(err_str) > 200:
                            err_str = err_str[:200] + "..."
                        lines.append(f"  - {err_str}")
                elif errors:
                    lines.append(f"Recent Errors: {errors}")
            
            if "os27_top_processes" in context:
                processes = context["os27_top_processes"]
                if isinstance(processes, list) and processes:
                    lines.append("Top Processes (by memory):")
                    for p in processes:
                        if isinstance(p, dict):
                            p_name = p.get("name", "Unknown")
                            p_pid = p.get("pid", "?")
                            p_mem = p.get("memory", 0)
                            if p_mem > 1024 * 1024:
                                p_mem_str = f"{p_mem / (1024*1024):.1f} MB"
                            else:
                                p_mem_str = f"{p_mem} bytes"
                            lines.append(f"  - {p_name} (PID: {p_pid}) - {p_mem_str}")
                        else:
                            lines.append(f"  - {p}")
        else:
            lines.append("OS27 Status: INACTIVE")
            if context.get("os27_error"):
                lines.append(f"Error: {context['os27_error']}")
            if context.get("os27_fallback_mode"):
                lines.append("Mode: FALLBACK")
        
        return "\n".join(lines)
    
    def inject_live_logs(self, context: Any) -> Any:
        """
        Inject recent log entries with error prevention.
        Accepts both dict and string context for compatibility.
        Professional implementation with graceful degradation.
        """
        # Handle string context
        if isinstance(context, str):
            logger.info("[OS27] Context is string, converting to dict for log injection")
            temp_context = {"original_context": context}
            result_context = self._inject_live_logs_internal(temp_context)
            # Return as string with logs appended
            logs_text = self._format_logs_as_text(result_context)
            return f"{context}\n\n{logs_text}"
        
        # Handle dict context
        if not isinstance(context, dict):
            logger.warning("[OS27] Context is not dict or string, skipping log injection")
            return context
        
        return self._inject_live_logs_internal(context)
    
    def inject_live_debug_status(self, context: Any) -> Any:
        """
        Inject live debug status from OS27 Live Logger for tool failure tracking.
        This helps the AI model understand which tools are failing and why.
        """
        try:
            from core.backends.os27_live_logger import get_os27_live_logger
            live_logger = get_os27_live_logger()
            status = live_logger.get_live_status()
            analysis = live_logger.get_failure_analysis()
            
            # Convert to dict for injection
            debug_context = {
                "os27_live_debug": {
                    "active_failures": status.get("active_failures", {}),
                    # OS27 UNCENSORED MODE - No blocked_tools
                    "error_patterns": status.get("error_patterns", {}),
                    "total_failures": analysis.get("total_failures", 0),
                    "recommendations": analysis.get("recommendations", [])
                },
                "os27_debug_injection_time": datetime.now().isoformat()
            }
            
            # Handle string context
            if isinstance(context, str):
                debug_text = self._format_debug_as_text(debug_context)
                return f"{context}\n\n[OS27 LIVE DEBUG]\n{debug_text}"
            
            # Handle dict context
            if isinstance(context, dict):
                context.update(debug_context)
                return context
            
            return context
            
        except Exception as e:
            logger.warning(f"[OS27] Failed to inject live debug status: {e}")
            return context
    
    def _inject_live_logs_internal(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Internal method for dict log injection"""
        try:
            log_data = self._collect_recent_logs()
            context.update(log_data)
            context["os27_log_injection_time"] = datetime.now().isoformat()
            logger.info("[OS27] Live logs injected into AI context")
            
        except Exception as e:
            logger.warning(f"[OS27] Failed to inject logs: {str(e)}")
            context["os27_logs_error"] = str(e)
        
        return context
    
    def _format_logs_as_text(self, context: Dict[str, Any]) -> str:
        """Format logs as readable text for string context"""
        lines = ["[OS27 LIVE LOGS INJECTION]"]
        
        if "os27_recent_logs" in context:
            logs = context["os27_recent_logs"]
            if isinstance(logs, list):
                lines.append(f"Recent Log Entries: {len(logs)} captured")
                for log in logs[-5:]:  # Show last 5
                    log_str = log.strip()
                    if len(log_str) > 200:
                        log_str = log_str[:200] + "..."
                    lines.append(f"  {log_str}")
            else:
                log_str = str(logs)
                if len(log_str) > 1000:
                    log_str = log_str[:1000] + "..."
                lines.append(f"Recent Logs: {log_str}")
        
        return "\n".join(lines)
    
    def _format_debug_as_text(self, debug_context: Dict[str, Any]) -> str:
        """Format live debug status as readable text for string context"""
        lines = ["[OS27 LIVE DEBUG STATUS]"]
        
        debug_data = debug_context.get("os27_live_debug", {})
        
        # Active failures
        failures = debug_data.get("active_failures", {})
        if failures:
            lines.append(f"Active Tool Failures: {len(failures)}")
            for tool, count in sorted(failures.items(), key=lambda x: x[1], reverse=True):
                lines.append(f"  - {tool}: {count} failures")

        # OS27 UNCENSORED MODE - No blocked tools section

        # Error patterns
        patterns = debug_data.get("error_patterns", {})
        if patterns:
            lines.append(f"Error Patterns: {len(patterns)}")
            for pattern, count in sorted(patterns.items(), key=lambda x: x[1], reverse=True):
                lines.append(f"  - {pattern}: {count} occurrences")
        
        # Recommendations
        recommendations = debug_data.get("recommendations", [])
        if recommendations:
            lines.append("Recommendations:")
            for rec in recommendations:
                lines.append(f"  - {rec}")
        
        return "\n".join(lines)
        if "os27_logs_error" in context:
            lines.append(f"Logs Error: {context['os27_logs_error']}")
        
        return "\n".join(lines)
    
    def _collect_telemetry(self) -> Dict[str, Any]:
        """Collect telemetry from OS27 components"""
        telemetry = {}
        
        try:
            from tools.system import SystemTool
            system_tool = SystemTool()
            vitals_result = system_tool.execute(operation="vitals")
            
            if vitals_result.status.value == "success":
                # SystemTool.vitals returns formatted string, parse it into dict
                if isinstance(vitals_result.data, str):
                    vitals_dict = {}
                    for line in vitals_result.data.splitlines():
                        if ":" in line:
                            k, v = line.split(":", 1)
                            vitals_dict[k.strip()] = v.strip()
                    telemetry["os27_system_vitals"] = vitals_dict
                elif isinstance(vitals_result.data, dict):
                    telemetry["os27_system_vitals"] = vitals_result.data.get("vitals", vitals_result.data)
        except Exception as e:
            logger.warning(f"[OS27] System telemetry failed: {str(e)}")
            telemetry["os27_system_error"] = str(e)
        
        try:
            # Direct usage of ANAMemoryCortex to query recent episodic errors
            from core.memory_cortex import get_memory_cortex
            cortex = get_memory_cortex()
            errors = cortex.get_recent_errors(limit=5)
            telemetry["os27_recent_errors"] = errors
        except Exception as e:
            logger.warning(f"[OS27] Memory telemetry failed: {str(e)}")
            telemetry["os27_memory_error"] = str(e)
        
        try:
            import psutil
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
                try:
                    info = proc.info
                    mem = info['memory_info'].rss if info['memory_info'] else 0
                    processes.append({
                        'pid': info['pid'],
                        'name': info['name'],
                        'memory': mem
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            # Sorteaza dupa memorie reala (RSS) descrescator si ia top 8
            top_processes = sorted(processes, key=lambda x: x['memory'], reverse=True)[:8]
            telemetry["os27_top_processes"] = top_processes
        except Exception as e:
            logger.warning(f"[OS27] Process telemetry failed: {str(e)}")
            telemetry["os27_frida_error"] = str(e)
        
        return telemetry
    
    def _collect_recent_logs(self) -> Dict[str, Any]:
        """Collect recent log entries"""
        log_data = {}
        
        try:
            log_path = os.path.join(os.path.dirname(__file__), "..", "..", "logs", "ana_max.log")
            
            if os.path.exists(log_path):
                with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                
                recent_logs = lines[-20:] if len(lines) > 20 else lines
                log_data["os27_recent_logs"] = recent_logs
            else:
                log_data["os27_logs_status"] = "log_file_not_found"
                
        except Exception as e:
            log_data["os27_logs_error"] = str(e)
        
        return log_data
    
    def _is_cache_valid(self) -> bool:
        """Check if cached telemetry is still valid"""
        if self._last_injection is None:
            return False
        
        age = (datetime.now() - self._last_injection).total_seconds()
        return age < self._cache_ttl
    
    def clear_cache(self):
        """Clear telemetry cache"""
        self._cached_telemetry = {}
        self._last_injection = None
        logger.info("[OS27] Telemetry cache cleared")


# Singleton instance for efficient telemetry collection
_os27_telemetry_instance = None

def get_os27_telemetry() -> OS27Telemetry:
    """Get singleton OS27 telemetry instance"""
    global _os27_telemetry_instance
    if _os27_telemetry_instance is None:
        _os27_telemetry_instance = OS27Telemetry()
    return _os27_telemetry_instance
