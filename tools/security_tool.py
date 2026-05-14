"""
A.N.A. v15.0 - Security Tool
=============================
Instrumente pentru cercetare securitate și audit cod.
"""

import os
import re
import hashlib
import logging
from typing import Optional, Dict, Any, List
from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus

logger = logging.getLogger(__name__)

class SecurityTool(Tool):
    """
    Tool pentru audit securitate și analiză vulnerabilități.
    """
    
    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="security_audit",
            description="Audit securitate: scanare secrete (keys), vulnerabilități statice, hash-uri.",
            parameters=[
                ToolParameter(
                    name="operation",
                    description="Operațiunea: scan_secrets, static_analysis, hash_gen",
                    type="string",
                    required=True,
                    choices=["scan_secrets", "static_analysis", "hash_gen"]
                ),
                ToolParameter(
                    name="target",
                    description="Path fișier, cod sursă sau text pentru hash.",
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
        """Execută operațiunea Security."""
        handlers = {
            "scan_secrets": self._scan_secrets,
            "static_analysis": self._static_analysis,
            "hash_gen": self._hash_gen
        }
        
        if operation not in handlers:
            return ToolResult(status=ToolStatus.ERROR, error=f"Operațiune necunoscută: {operation}")
            
        return handlers[operation](target, **kwargs)

    def _scan_secrets(self, target: str, **kwargs) -> ToolResult:
        """Caută API keys, parole și secrete în fișiere."""
        if not os.path.exists(target):
            # Dacă nu e path, tratăm ca text
            content = target
            findings = self._find_secrets_in_text(content)
            if findings:
                return ToolResult(status=ToolStatus.SUCCESS, data="\n".join(findings), message="Scurgeri de date găsite!")
            return ToolResult(status=ToolStatus.SUCCESS, data="✅ Nu am găsit secrete evidente.", message="Scanare curată.")
        
        if os.path.isfile(target):
            try:
                with open(target, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                findings = self._find_secrets_in_text(content)
                if findings:
                    return ToolResult(status=ToolStatus.SUCCESS, data="\n".join(findings), message="Scurgeri de date găsite!")
                return ToolResult(status=ToolStatus.SUCCESS, data="✅ Nu am găsit secrete evidente în fișier.", message="Scanare curată.")
            except PermissionError:
                return ToolResult(status=ToolStatus.SUCCESS, data="⚠️ Permisiune refuzată pentru fișier.", message="Eroare permisiune.")
        
        # Este director - scanează recursiv
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
            return ToolResult(status=ToolStatus.SUCCESS, data="\n".join(all_findings[:50]), message=f"Scurgeri găsite în {len(all_findings)} locuri!")
        return ToolResult(status=ToolStatus.SUCCESS, data="✅ Nu am găsit secrete evidente în director.", message="Scanare curată.")
    
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
                findings.append(f"⚠️ {name} detectat! (Match: {match.group(0)[:15]}...)")
        return findings

    def _static_analysis(self, target: str, **kwargs) -> ToolResult:
        """Analiză statică simplă (echivalent Bandit light)."""
        if os.path.isfile(target):
            try:
                with open(target, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                return self._run_static_checks(content, target)
            except PermissionError:
                return ToolResult(status=ToolStatus.SUCCESS, data="⚠️ Permisiune refuzată pentru fișier.", message="Eroare permisiune.")
        
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
                return ToolResult(status=ToolStatus.SUCCESS, data="\n\n".join(all_risks[:20]), message=f"Vulnerabilități detectate în {len(all_risks)} fișiere!")
            return ToolResult(status=ToolStatus.SUCCESS, data="✅ Nu am găsit riscuri evidente în director.", message="Analiză OK.")
        
        # Nu e path valid, tratează ca text
        return self._run_static_checks(target, "text")
    
    def _run_static_checks(self, content: str, source: str) -> str:
        """Rulează verificările statice pe un conținut."""
        risks = []
        if "eval(" in content:
            risks.append("🚨 UTILIZARE eval() - Risc critic de Remote Code Execution (RCE).")
        if "os.system(" in content or ("subprocess" in content and "shell=True" in content):
            risks.append("🚨 SHELL=TRUE în subprocess - Risc de Command Injection.")
        if "pickle.load(" in content:
            risks.append("⚠️ UTILIZARE pickle - De-serializare nesigură.")
        if "md5" in content.lower():
            risks.append("⚠️ Algo slab detectat (MD5). Folosește SHA-256 sau mai nou.")
        return "\n".join(risks) if risks else ""

    def _hash_gen(self, target: str, **kwargs) -> ToolResult:
        """Generează hash pentru text/fișier."""
        algo = kwargs.get('algo', 'sha256')
        try:
            h = hashlib.new(algo)
            h.update(target.encode())
            return ToolResult(status=ToolStatus.SUCCESS, data=h.hexdigest(), message=f"Hash {algo} generat.")
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=f"Eroare hash: {e}")
