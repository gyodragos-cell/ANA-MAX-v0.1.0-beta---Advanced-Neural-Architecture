"""
A.N.A. v18.0 MAX - Jupyter Sandbox (Inspirat de Open Interpreter)
=================================================================
Execuție interactivă de cod Python într-un kernel Jupyter izolat.
ANA poate testa fragmente de cod "în memorie" înainte de a le scrie în fișiere.
Vede erorile în real-time și le repară instant.
"""

import os
import logging
import asyncio
import threading
import queue
from typing import Optional, Dict, Any, Tuple

logger = logging.getLogger(__name__)

# Verificăm disponibilitatea Jupyter
try:
    from jupyter_client import KernelManager
    JUPYTER_AVAILABLE = True
except ImportError:
    JUPYTER_AVAILABLE = False
    logger.warning("jupyter-client nu este instalat. JupyterSandbox va folosi exec() fallback.")


class JupyterSandbox:
    """
    Sandbox interactiv cu stare persistentă (stateful) - inspirat de Open Interpreter.
    
    Diferența față de sandbox-ul clasic ANA:
    - STATEFUL: variabilele persistă între execuții (ca într-un notebook)
    - REAL-TIME: vede output și erori instant
    - SAFE: kernelul e izolat, nu afectează procesul principal ANA
    
    Optimizat pentru hardware modest (GTX 1650): kernelul folosește CPU, nu GPU.
    """
    
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.kernel_manager: Optional[Any] = None
        self.kernel_client: Optional[Any] = None
        self._started = False
        self._namespace: Dict[str, Any] = {}  # Fallback namespace pentru exec()
        self.execution_history: list = []
        self.stats = {"executions": 0, "errors_caught": 0, "auto_fixes": 0}
    
    def start_kernel(self) -> bool:
        """Pornește kernelul Jupyter (dacă e disponibil)."""
        if not JUPYTER_AVAILABLE:
            logger.info("🐍 JupyterSandbox: Mod fallback (exec) - jupyter-client indisponibil")
            self._started = True
            return True
        
        try:
            self.kernel_manager = KernelManager(kernel_name='python3')
            self.kernel_manager.start_kernel()
            self.kernel_client = self.kernel_manager.client()
            self.kernel_client.start_channels()
            
            # Așteaptă să fie gata
            self.kernel_client.wait_for_ready(timeout=10)
            self._started = True
            logger.info("🧪 JupyterSandbox: Kernel Jupyter pornit cu succes")
            return True
        except Exception as e:
            logger.warning(f"Nu pot porni kernel Jupyter: {e}. Folosesc fallback exec().")
            self._started = True
            self.kernel_manager = None
            return True
    
    def stop_kernel(self):
        """Oprește kernelul Jupyter."""
        if self.kernel_client:
            self.kernel_client.stop_channels()
        if self.kernel_manager and self.kernel_manager.is_alive():
            self.kernel_manager.shutdown_kernel(now=True)
        self._started = False
        logger.info("🧪 JupyterSandbox: Kernel oprit")
    
    def execute(self, code: str, auto_fix: bool = True) -> Dict[str, Any]:
        """
        Execută cod Python în sandbox.
        
        Args:
            code: Codul Python de executat
            auto_fix: Dacă e True, încearcă să repare automat erorile simple
            
        Returns:
            Dict cu: output, error, success, fix_applied
        """
        if not self._started:
            self.start_kernel()
        
        self.stats["executions"] += 1
        
        if self.kernel_manager and self.kernel_manager.is_alive():
            return self._execute_jupyter(code, auto_fix)
        else:
            return self._execute_fallback(code, auto_fix)
    
    def _execute_jupyter(self, code: str, auto_fix: bool) -> Dict[str, Any]:
        """Execuție prin kernel Jupyter (stateful, izolat)."""
        result = {"output": "", "error": None, "success": True, "fix_applied": False}
        
        try:
            msg_id = self.kernel_client.execute(code)
            
            outputs = []
            while True:
                try:
                    msg = self.kernel_client.get_iopub_msg(timeout=self.timeout)
                except queue.Empty:
                    result["error"] = "Timeout - execuția a durat prea mult"
                    result["success"] = False
                    break
                
                msg_type = msg['header']['msg_type']
                content = msg['content']
                
                if msg_type == 'stream':
                    outputs.append(content.get('text', ''))
                elif msg_type == 'execute_result':
                    outputs.append(content.get('data', {}).get('text/plain', ''))
                elif msg_type == 'error':
                    error_text = '\n'.join(content.get('traceback', []))
                    result["error"] = error_text
                    result["success"] = False
                    self.stats["errors_caught"] += 1
                    break
                elif msg_type == 'status' and content.get('execution_state') == 'idle':
                    break
            
            result["output"] = ''.join(outputs)
            
        except Exception as e:
            result["error"] = str(e)
            result["success"] = False
        
        self.execution_history.append({"code": code, "result": result})
        return result
    
    def _execute_fallback(self, code: str, auto_fix: bool) -> Dict[str, Any]:
        """Execuție prin exec() builtin (fallback simplu dar funcțional)."""
        import io
        import contextlib
        
        result = {"output": "", "error": None, "success": True, "fix_applied": False}
        
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        
        try:
            with contextlib.redirect_stdout(stdout_capture), contextlib.redirect_stderr(stderr_capture):
                exec(code, self._namespace)
            
            result["output"] = stdout_capture.getvalue()
            stderr_out = stderr_capture.getvalue()
            if stderr_out:
                result["output"] += f"\n[stderr]: {stderr_out}"
                
        except SyntaxError as e:
            result["error"] = f"SyntaxError: {e}"
            result["success"] = False
            self.stats["errors_caught"] += 1
            
            # Auto-fix simplu pentru erori comune
            if auto_fix:
                fixed = self._try_auto_fix_syntax(code, str(e))
                if fixed:
                    result["fix_applied"] = True
                    self.stats["auto_fixes"] += 1
                    fix_result = self._execute_fallback(fixed, auto_fix=False)
                    if fix_result["success"]:
                        result = fix_result
                        result["fix_applied"] = True
                        result["output"] = f"[AUTO-FIX aplicat]\n{fix_result['output']}"
                    
        except Exception as e:
            result["error"] = f"{type(e).__name__}: {e}"
            result["success"] = False
            self.stats["errors_caught"] += 1
        
        self.execution_history.append({"code": code, "result": result})
        return result
    
    def _try_auto_fix_syntax(self, code: str, error: str) -> Optional[str]:
        """Încearcă reparări automate pentru erori comune."""
        # Fix: lipsă ':' la if/for/while/def/class
        if "expected ':'" in error.lower() or "expected ':'":
            lines = code.split('\n')
            for i, line in enumerate(lines):
                stripped = line.rstrip()
                if stripped and any(stripped.startswith(kw) for kw in ['if ', 'for ', 'while ', 'def ', 'class ', 'elif ', 'else', 'try', 'except', 'finally']):
                    if not stripped.endswith(':'):
                        lines[i] = stripped + ':'
            return '\n'.join(lines)
        
        # Fix: paranteză neînchisă
        if "unexpected EOF" in error or "parenthesis" in error.lower():
            open_count = code.count('(') - code.count(')')
            if open_count > 0:
                return code + ')' * open_count
        
        return None
    
    def test_code_before_write(self, code: str, description: str = "") -> Dict[str, Any]:
        """
        Testează un fragment de cod ÎNAINTE de a-l scrie în fișier.
        Aceasta e ideea cheie din Open Interpreter: testezi în memorie, scrii doar ce merge.
        
        Returns:
            Dict cu: safe_to_write, output, issues
        """
        result = self.execute(code, auto_fix=True)
        
        return {
            "safe_to_write": result["success"],
            "output": result["output"],
            "error": result.get("error"),
            "fix_applied": result.get("fix_applied", False),
            "description": description
        }
    
    def reset_state(self):
        """Resetează starea sandbox-ului (curăță variabilele)."""
        if self.kernel_manager and self.kernel_manager.is_alive():
            self.kernel_client.execute("%reset -f")
        else:
            self._namespace.clear()
            self._namespace['__builtins__'] = __builtins__
    
    def get_stats(self) -> Dict:
        return self.stats.copy()
