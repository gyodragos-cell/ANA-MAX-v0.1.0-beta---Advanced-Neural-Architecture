"""
A.N.A. v15.0 - Security Tool
=============================
Instrumente pentru cercetare securitate si audit cod.
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
        handlers = {
            "scan_secrets": self._scan_secrets,
            "static_analysis": self._static_analysis,
            "hash_gen": self._hash_gen
        }
        
        if operation not in handlers:
            return ToolResult(status=ToolStatus.ERROR, error=f"Operatiune necunoscuta: {operation}")
            
        return handlers[operation](target, **kwargs)

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
