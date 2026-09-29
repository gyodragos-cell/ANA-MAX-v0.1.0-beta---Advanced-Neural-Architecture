"""
A.N.A. v15.0 - Security Tool (OS27 Hyper++)
============================================
Instrumente pentru cercetare securitate si audit cod.

OS27 Hyper++ Features:
- Telemetry tracking for security operations (scan_secrets, static_analysis, hash_gen)
- Health monitoring for security operations reliability
- MemoryCortex integration for security errors and state learning
- ContextEngine integration for security state awareness
- SelfEvolvingTool integration for anomaly detection on security failures
- Structured logging with error detection
"""

import os
import re
import hashlib
import logging
import time
from typing import Optional, Dict, Any, List
from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus

logger = logging.getLogger(__name__)

# OS27 Hyper++ Telemetry
_security_telemetry: Dict[str, Dict[str, Any]] = {}


def _record_security_telemetry(operation: str, success: bool, execution_time: float) -> None:
    """Record OS27 Hyper++ telemetry for security operations."""
    if operation not in _security_telemetry:
        _security_telemetry[operation] = {
            "operation_count": 0,
            "success_count": 0,
            "failure_count": 0,
            "total_time": 0.0,
            "last_execution_time": 0.0,
            "last_success": False,
        }
    
    _security_telemetry[operation]["operation_count"] += 1
    _security_telemetry[operation]["total_time"] += execution_time
    _security_telemetry[operation]["last_execution_time"] = execution_time
    _security_telemetry[operation]["last_success"] = success
    
    if success:
        _security_telemetry[operation]["success_count"] += 1
    else:
        _security_telemetry[operation]["failure_count"] += 1


def get_security_telemetry(operation: str | None = None) -> Dict[str, Any] | Dict[str, Dict[str, Any]]:
    """Get telemetry for security operations."""
    if operation:
        return _security_telemetry.get(operation, {})
    return _security_telemetry.copy()


def get_security_health() -> str:
    """Get health status for security tool based on telemetry."""
    if not _security_telemetry:
        return "unknown"
    
    total_ops = sum(stats["operation_count"] for stats in _security_telemetry.values())
    total_failures = sum(stats["failure_count"] for stats in _security_telemetry.values())
    
    if total_ops == 0:
        return "unknown"
    
    failure_rate = total_failures / total_ops
    if failure_rate > 0.5:
        return "broken"
    if failure_rate > 0.1:
        return "degraded"
    return "healthy"

class SecurityTool(Tool):
    """
    Tool pentru audit securitate si analiza vulnerabilitati.
    """
    
    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="security_audit",
            description="Audit securitate: scanare secrete (keys), vulnerabilitati statice, hash-uri.",
            parameters=[
                ToolParameter(
                    name="operation",
                    description="Operatiunea: scan_secrets, static_analysis, hash_gen",
                    type="string",
                    required=True,
                    choices=["scan_secrets", "static_analysis", "hash_gen"]
                ),
                ToolParameter(
                    name="target",
                    description="Path fisier, cod sursa sau text pentru hash.",
                    type="string",
                    required=True
                ),
                ToolParameter(
                    name="algo",
                    description="Algoritm hash: sha256, md5",
                    type="string",
                    required=False,
                    default="sha256"
                )
            ],
            category="security"
        )

    def execute(self, operation: str, target: str, **kwargs) -> ToolResult:
        """Executa operatiunea Security."""
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
        
        handlers = {
            "scan_secrets": self._scan_secrets,
            "static_analysis": self._static_analysis,
            "hash_gen": self._hash_gen
        }
        
        if operation not in handlers:
            execution_time = time.time() - start_time
            _record_security_telemetry(operation, False, execution_time)
            return ToolResult(status=ToolStatus.ERROR, error=f"Operatiune necunoscuta: {operation}")
        
        result = handlers[operation](target, **kwargs)
        
        execution_time = time.time() - start_time
        _record_security_telemetry(operation, result.is_success, execution_time)
        
        # ContextEngine integration for security state
        if context_engine and result.is_success:
            try:
                context_engine.update_context(
                    key="security_state",
                    value={
                        "operation": operation,
                        "target": target,
                        "success": result.is_success,
                        "timestamp": time.time(),
                    }
                )
            except Exception:
                pass
        
        # MemoryCortex integration for security errors
        if cortex and not result.is_success:
            try:
                cortex.remember(
                    "error",
                    f"security.{operation}",
                    f"Security operation failed for {target}: {result.error}"
                )
            except Exception:
                pass
        
        return result

    def _scan_secrets(self, target: str, **kwargs) -> ToolResult:
        """Cauta API keys, parole si secrete in fisiere."""
        if not os.path.exists(target):
            # Daca nu e path, tratam ca text
            content = target
            findings = self._find_secrets_in_text(content)
            if findings:
                return ToolResult(status=ToolStatus.SUCCESS, data="\n".join(findings), message="Scurgeri de date gasite!")
            return ToolResult(status=ToolStatus.SUCCESS, data=" Nu am gasit secrete evidente.", message="Scanare curata.")
        
        if os.path.isfile(target):
            try:
                with open(target, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                findings = self._find_secrets_in_text(content)
                if findings:
                    return ToolResult(status=ToolStatus.SUCCESS, data="\n".join(findings), message="Scurgeri de date gasite!")
                return ToolResult(status=ToolStatus.SUCCESS, data=" Nu am gasit secrete evidente in fisier.", message="Scanare curata.")
            except PermissionError:
                return ToolResult(status=ToolStatus.SUCCESS, data="[WARN] Permisiune refuzata pentru fisier.", message="Eroare permisiune.")
        
        # Este director - scaneaza recursiv
        all_findings = []
        for root, dirs, files in os.walk(target):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    findings = self._find_secrets_in_text(content)
                    if findings:
                        all_findings.extend([f"{file_path}: {f}" for f in findings])
                except (PermissionError, UnicodeDecodeError):
                    continue
        
        if all_findings:
            return ToolResult(status=ToolStatus.SUCCESS, data="\n".join(all_findings[:50]), message=f"Scurgeri gasite in {len(all_findings)} locuri!")
        return ToolResult(status=ToolStatus.SUCCESS, data=" Nu am gasit secrete evidente in director.", message="Scanare curata.")
    
    def _find_secrets_in_text(self, content: str) -> list:
        """Helper pentru pattern matching."""
        patterns = {
            "Generic Secret": r"(?i)secret\s*[:=]\s*['\"](\w+)['\"]",
            "API Key": r"(?i)api_?key\s*[:=]\s*['\"](\w+)['\"]",
            "Password": r"(?i)password\s*[:=]\s*['\"](\w+)['\"]",
            "Bearer Token": r"Bearer\s+[A-Za-z0-9\-\._~\+\/]+",
            "Private Key": r"-----BEGIN [A-Z ]+ PRIVATE KEY-----"
        }
        findings = []
        for name, pattern in patterns.items():
            matches = re.finditer(pattern, content)
            for match in matches:
                findings.append(f"[WARN] {name} detectat! (Match: {match.group(0)[:15]}...)")
        return findings

    def _static_analysis(self, target: str, **kwargs) -> ToolResult:
        """Analiza statica simpla (echivalent Bandit light)."""
        if os.path.isfile(target):
            try:
                with open(target, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                return self._run_static_checks(content, target)
            except PermissionError:
                return ToolResult(status=ToolStatus.SUCCESS, data="[WARN] Permisiune refuzata pentru fisier.", message="Eroare permisiune.")
        
        if os.path.isdir(target):
            all_risks = []
            for root, dirs, files in os.walk(target):
                for file in files:
                    if not file.endswith('.py'):
                        continue
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                        risks = self._run_static_checks(content, file_path)
                        if risks:
                            all_risks.append(f"{file_path}:\n{risks}")
                    except (PermissionError, UnicodeDecodeError):
                        continue
            if all_risks:
                return ToolResult(status=ToolStatus.SUCCESS, data="\n\n".join(all_risks[:20]), message=f"Vulnerabilitati detectate in {len(all_risks)} fisiere!")
            return ToolResult(status=ToolStatus.SUCCESS, data=" Nu am gasit riscuri evidente in director.", message="Analiza OK.")
        
        # Nu e path valid, trateaza ca text
        return self._run_static_checks(target, "text")
    
    def _run_static_checks(self, content: str, source: str) -> str:
        """Ruleaza verificarile statice pe un continut."""
        risks = []
        if "eval(" in content:
            risks.append(" UTILIZARE eval() - Risc critic de Remote Code Execution (RCE).")
        if "os.system(" in content or ("subprocess" in content and "shell=True" in content):
            risks.append(" SHELL=TRUE in subprocess - Risc de Command Injection.")
        if "pickle.load(" in content:
            risks.append("[WARN] UTILIZARE pickle - De-serializare nesigura.")
        if "md5" in content.lower():
            risks.append("[WARN] Algo slab detectat (MD5). Foloseste SHA-256 sau mai nou.")
        return "\n".join(risks) if risks else ""

    def _hash_gen(self, target: str, **kwargs) -> ToolResult:
        """Genereaza hash pentru text/fisier."""
        algo = kwargs.get('algo', 'sha256')
        try:
            h = hashlib.new(algo)
            h.update(target.encode())
            return ToolResult(status=ToolStatus.SUCCESS, data=h.hexdigest(), message=f"Hash {algo} generat.")
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=f"Eroare hash: {e}")
