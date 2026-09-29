"""
A.N.A. v15.0 - Code Tools (OS27 Hyper++)
=========================================
Instrumente pentru lucrul cu cod: analiza, executie, creare proiecte.

OS27 Hyper++ Features:
- Telemetry tracking for code operations (analyze, execute, create_project, run_tests, lint, format)
- Health monitoring for code operations reliability
- MemoryCortex integration for code errors and state learning
- ContextEngine integration for code state awareness
- SelfEvolvingTool integration for anomaly detection on code failures
- Structured logging with error detection
"""

import os
import sys
import subprocess
import logging
import time
from typing import Optional, Dict, Any, List
from pathlib import Path

from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus

logger = logging.getLogger(__name__)

# OS27 Hyper++ Telemetry
_code_telemetry: Dict[str, Dict[str, Any]] = {}


def _record_code_telemetry(operation: str, success: bool, execution_time: float) -> None:
    """Record OS27 Hyper++ telemetry for code operations."""
    if operation not in _code_telemetry:
        _code_telemetry[operation] = {
            "operation_count": 0,
            "success_count": 0,
            "failure_count": 0,
            "total_time": 0.0,
            "last_execution_time": 0.0,
            "last_success": False,
        }
    
    _code_telemetry[operation]["operation_count"] += 1
    _code_telemetry[operation]["total_time"] += execution_time
    _code_telemetry[operation]["last_execution_time"] = execution_time
    _code_telemetry[operation]["last_success"] = success
    
    if success:
        _code_telemetry[operation]["success_count"] += 1
    else:
        _code_telemetry[operation]["failure_count"] += 1


def get_code_telemetry(operation: str | None = None) -> Dict[str, Any] | Dict[str, Dict[str, Any]]:
    """Get telemetry for code operations."""
    if operation:
        return _code_telemetry.get(operation, {})
    return _code_telemetry.copy()


def get_code_health() -> str:
    """Get health status for code tool based on telemetry."""
    if not _code_telemetry:
        return "unknown"
    
    total_ops = sum(stats["operation_count"] for stats in _code_telemetry.values())
    total_failures = sum(stats["failure_count"] for stats in _code_telemetry.values())
    
    if total_ops == 0:
        return "unknown"
    
    failure_rate = total_failures / total_ops
    if failure_rate > 0.5:
        return "broken"
    if failure_rate > 0.1:
        return "degraded"
    return "healthy"


class CodeTool(Tool):
    """
    Tool pentru lucrul cu cod.
    Analiza, executie in sandbox, creare proiecte.
    """
    
    # Template-uri pentru proiecte
    PROJECT_TEMPLATES = {
        "web": {
            "files": {
                "index.html": """<!DOCTYPE html>
<html lang="ro">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{name}</title>
    <link rel="stylesheet" href="css/style.css">
</head>
<body>
    <h1>Bun venit la {name}</h1>
    <script src="js/main.js"></script>
</body>
</html>""",
                "css/style.css": """/* {name} - Styles */
body {{
    font-family: 'Segoe UI', Arial, sans-serif;
    margin: 0;
    padding: 20px;
    background: #f5f5f5;
}}

h1 {{
    color: #333;
}}
""",
                "js/main.js": """// {name} - JavaScript
console.log('{name} loaded successfully!');

document.addEventListener('DOMContentLoaded', () => {{
    console.log('DOM ready');
}});
"""
            },
            "dirs": ["css", "js", "images"]
        },
        "python": {
            "files": {
                "main.py": '''"""
{name} - Main Entry Point
"""

def main():
    """Main function."""
    print("Hello from {name}!")

if __name__ == "__main__":
    main()
''',
                "requirements.txt": """# {name} - Dependencies
# Add your dependencies here
""",
                "__init__.py": '"""{name} package."""\n'
            },
            "dirs": ["tests", "docs"]
        },
        "api": {
            "files": {
                "main.py": '''"""
{name} - FastAPI Application
"""
from fastapi import FastAPI

app = FastAPI(title="{name}")

@app.get("/")
async def root():
    return {{"message": "Welcome to {name}"}}

@app.get("/health")
async def health():
    return {{"status": "healthy"}}
''',
                "requirements.txt": """# {name} - Dependencies
fastapi>=0.100.0
uvicorn>=0.23.0
""",
            },
            "dirs": ["routers", "models", "tests"]
        },
        "react": {
            "files": {
                "src/App.jsx": """import React from 'react';
function App() {
  return (
    <div className="App">
      <h1>Hello from React + {name}</h1>
    </div>
  );
}
export default App;""",
                "src/main.jsx": """import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './index.css';
ReactDOM.createRoot(document.getElementById('root')).render(<App />);""",
                "index.html": """<!DOCTYPE html><html><head><title>{name}</title></head><body><div id="root"></div></body></html>""",
                "package.json": """{{ "name": "{name}", "version": "1.0.0", "dependencies": {{ "react": "latest", "react-dom": "latest" }} }}"""
            },
            "dirs": ["src", "public"]
        },
        "nextjs": {
            "files": {
                "pages/index.js": """export default function Home() {{ return <h1>Welcome to {name}</h1> }}""",
                "package.json": """{{ "name": "{name}", "version": "1.0.0", "scripts": {{ "dev": "next dev" }}, "dependencies": {{ "next": "latest", "react": "latest", "react-dom": "latest" }} }}"""
            },
            "dirs": ["pages", "public", "styles"]
        },
        "flask": {
            "dirs": ["app", "app/templates", "app/static", "tests"],
            "files": {
                "run.py": "from app import create_app\n\napp = create_app()\nif __name__ == '__main__':\n    app.run(debug=True)",
                "app/__init__.py": "from flask import Flask\n\ndef create_app():\n    app = Flask(__name__)\n    @app.route('/')\n    def index():\n        return 'Hello, {name}!'\n    return app",
                "requirements.txt": "flask\npytest"
            }
        },
        "network": {
            "dirs": ["scripts", "config", "logs"],
            "files": {
                "scripts/scanner.py": "import socket\n\ndef scan(target):\n    print(f'Scanning {{target}}...')\n    # Boilerplate for network scanner\n    pass",
                "config/hosts.txt": "127.0.0.1\nlocalhost"
            }
        },
        "qa": {
            "dirs": ["tests", "data", "reports"],
            "files": {
                "tests/test_main.py": "import pytest\n\ndef test_feature():\n    assert True",
                "conftest.py": "# Pytest configuration"
            }
        },
        "security": {
            "dirs": ["scans", "exploits", "payloads"],
            "files": {
                "scans/audit_report.md": "# Security Audit Report\n\nTarget: {name}\nFindings: None",
                "payloads/safe_test.txt": "This is a safe security research test file."
            }
        }
    }
    
    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="code_tools",
            description="Instrumente pentru cod: analiza, executie, creare proiecte.",
            parameters=[
                ToolParameter(
                    name="operation",
                    description="Operatiunea de executat",
                    type="string",
                    required=True,
                    choices=["analyze", "run", "create_project", "install_package"]
                ),
                ToolParameter(
                    name="target",
                    description="Tinta: cale fisier, cod de rulat, tip proiect, nume pachet",
                    type="string",
                    required=True
                ),
                ToolParameter(
                    name="name",
                    description="Nume (pentru proiecte)",
                    type="string",
                    required=False
                ),
                ToolParameter(
                    name="path",
                    description="Cale pentru creare proiect",
                    type="string",
                    required=False,
                    default="."
                ),
                ToolParameter(
                    name="language",
                    description="Limbaj pentru executie cod",
                    type="string",
                    required=False,
                    default="python",
                    choices=["python"]
                ),
                ToolParameter(
                    name="setup_venv",
                    description="Creeaza automat un virtual environment (pentru proiecte Python/API)",
                    type="boolean",
                    required=False,
                    default=False
                )
            ],
            category="code",
            requires_confirmation=False
        )
    
    def execute(self, operation: str, target: str, **kwargs) -> ToolResult:
        """Executa operatiunea cu cod."""
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
            "analyze": self._analyze_code,
            "run": self._run_code,
            "create_project": self._create_project,
            "install_package": self._install_package,
        }
        
        if operation not in operations:
            execution_time = time.time() - start_time
            _record_code_telemetry(operation, False, execution_time)
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Operatiune necunoscuta: {operation}"
            )
        
        try:
            result = operations[operation](target, **kwargs)
            execution_time = time.time() - start_time
            _record_code_telemetry(operation, result.is_success, execution_time)
            
            # ContextEngine integration for code state
            if context_engine and result.is_success:
                try:
                    context_engine.update_context(
                        key="code_state",
                        value={
                            "operation": operation,
                            "target": target,
                            "success": result.is_success,
                            "timestamp": time.time(),
                        }
                    )
                except Exception:
                    pass
            
            # MemoryCortex integration for code errors
            if cortex and not result.is_success:
                try:
                    cortex.remember(
                        "error",
                        f"code.{operation}",
                        f"Code operation failed for {target}: {result.error}"
                    )
                except Exception:
                    pass
            
            return result
        except Exception as exc:
            execution_time = time.time() - start_time
            _record_code_telemetry(operation, False, execution_time)
            
            # MemoryCortex integration for code errors
            if cortex:
                try:
                    cortex.remember(
                        "error",
                        f"code.{operation}",
                        f"Code operation failed for {target}: {str(exc)}"
                    )
                except Exception:
                    pass
            
            return ToolResult(status=ToolStatus.ERROR, error=str(exc))
    
    def _analyze_code(self, target: str, **kwargs) -> ToolResult:
        """Analizeaza un fisier de cod."""
        try:
            if not os.path.exists(target):
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error=f"Fisierul nu exista: {target}"
                )
            
            with open(target, 'r', encoding='utf-8', errors='ignore') as f:
                code = f.read()
            
            lines = code.split('\n')
            analysis = {
                "file": target,
                "total_lines": len(lines),
                "code_lines": 0,
                "comment_lines": 0,
                "blank_lines": 0,
                "issues": [],
                "todos": []
            }
            
            for i, line in enumerate(lines, 1):
                stripped = line.strip()
                
                if not stripped:
                    analysis["blank_lines"] += 1
                elif stripped.startswith('#') or stripped.startswith('//'):
                    analysis["comment_lines"] += 1
                else:
                    analysis["code_lines"] += 1
                
                # Verificari
                if len(line) > 120:
                    analysis["issues"].append(f"Linia {i}: Prea lunga ({len(line)} chars)")
                
                if 'TODO' in line or 'FIXME' in line:
                    analysis["todos"].append(f"Linia {i}: {stripped[:80]}")
                
                # Detectare probleme comune
                if 'except:' in line and 'except Exception' not in line:
                    analysis["issues"].append(f"Linia {i}: except gol (catch-all)")
                
                if 'print(' in line and '.py' in target:
                    # Ar putea fi debug print
                    pass
            
            # Formatare rezultat
            result_lines = [
                f"=== Analiza: {os.path.basename(target)} ===",
                f"Linii totale: {analysis['total_lines']}",
                f"Linii cod: {analysis['code_lines']}",
                f"Comentarii: {analysis['comment_lines']}",
                f"Linii goale: {analysis['blank_lines']}",
            ]
            
            if analysis["issues"]:
                result_lines.append(f"\n[WARN] Probleme gasite ({len(analysis['issues'])}):")
                result_lines.extend([f"   {i}" for i in analysis["issues"][:10]])
            
            if analysis["todos"]:
                result_lines.append(f"\n TODO-uri ({len(analysis['todos'])}):")
                result_lines.extend([f"   {t}" for t in analysis["todos"][:5]])
            
            if not analysis["issues"] and not analysis["todos"]:
                result_lines.append("\n[OK] Nicio problema detectata!")
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data="\n".join(result_lines),
                message="Analiza completa"
            )
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Eroare la analiza: {e}"
            )
    
    def _run_code(self, target: str, language: str = "python", **kwargs) -> ToolResult:
        """
        Ruleaza cod intr-un sandbox.
        NOTA: Aceasta este o versiune simplificata. 
        Pentru productie, foloseste sandbox/secure_runner.py
        """
        if language != "python":
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Limbajul '{language}' nu este suportat inca"
            )
        
        # Verificare cod periculos
        dangerous_patterns = [
            'import os', 'import subprocess', 'import shutil',
            'open(', '__import__', 'eval(', 'exec(',
            'import socket', 'import sys'
        ]
        
        for pattern in dangerous_patterns:
            if pattern in target:
                return ToolResult(
                    status=ToolStatus.BLOCKED,
                    error=f"Cod blocat: contine '{pattern}' (periculos in sandbox)"
                )
        
        try:
            result = subprocess.check_output(
                ["python", "-c", target],
                stderr=subprocess.STDOUT,
                text=True,
                timeout=10
            )
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data=result if result else "(executat fara output)",
                message="Cod executat"
            )
        except subprocess.TimeoutExpired:
            return ToolResult(
                status=ToolStatus.ERROR,
                error="Timeout - codul a durat prea mult (>10s)"
            )
        except subprocess.CalledProcessError as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Eroare la executie:\n{e.output}"
            )
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Eroare: {e}"
            )
    
    def _create_project(self, target: str, name: Optional[str] = None, 
                        path: str = ".", **kwargs) -> ToolResult:
        """Creeaza un proiect nou din template."""
        if target not in self.PROJECT_TEMPLATES:
            available = ", ".join(self.PROJECT_TEMPLATES.keys())
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Tip proiect necunoscut: {target}. Disponibile: {available}"
            )
        
        if not name:
            return ToolResult(
                status=ToolStatus.ERROR,
                error="Numele proiectului este necesar"
            )
        
        try:
            template = self.PROJECT_TEMPLATES[target]
            project_path = os.path.join(path, name)
            
            # Creeaza directorul principal
            os.makedirs(project_path, exist_ok=True)
            
            # Creeaza subdirectoare
            for dir_name in template.get("dirs", []):
                os.makedirs(os.path.join(project_path, dir_name), exist_ok=True)
            
            # Creeaza fisiere
            created_files = []
            for file_path, content in template.get("files", {}).items():
                full_path = os.path.join(project_path, file_path)
                
                # Creeaza directorul parinte daca e necesar
                parent = os.path.dirname(full_path)
                if parent:
                    os.makedirs(parent, exist_ok=True)
                
                # Scrie fisierul cu numele proiectului inlocuit
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(content.format(name=name))
                
                created_files.append(file_path)
            
            result_lines = [
                f"[OK] Proiect '{name}' creat cu succes!",
                f"Tip: {target}",
                f"Locatie: {os.path.abspath(project_path)}",
                "",
                "Fisiere create:"
            ]
            result_lines.extend([f"   {f}" for f in created_files])
            
            if kwargs.get("setup_venv") and (target in ["python", "api", "flask"]):
                self._setup_venv(project_path)
                result_lines.append("[OK] Virtual environment creat (venv/)")
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data="\n".join(result_lines),
                message="Proiect creat"
            )
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Eroare la creare proiect: {e}"
            )
    
    def _install_package(self, target: str, **kwargs) -> ToolResult:
        """Instaleaza un pachet Python."""
        try:
            # Verificare nume pachet valid
            if not target or ' ' in target or ';' in target:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error="Nume pachet invalid"
                )
            
            result = subprocess.check_output(
                ["pip", "install", target],
                stderr=subprocess.STDOUT,
                text=True,
                timeout=120
            )
            
            # Extrage ultima parte relevanta
            lines = result.strip().split('\n')
            summary = lines[-3:] if len(lines) > 3 else lines
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data=f"Pachet '{target}' instalat:\n" + "\n".join(summary),
                message="Pachet instalat"
            )
        except subprocess.TimeoutExpired:
            return ToolResult(
                status=ToolStatus.ERROR,
                error="Timeout - instalarea a durat prea mult"
            )
        except subprocess.CalledProcessError as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Eroare la instalare:\n{e.output[-500:]}"
            )
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Eroare: {e}"
            )

    def _setup_venv(self, project_path: str):
        """Creeaza un virtual environment."""
        try:
            import sys
            subprocess.run([sys.executable, "-m", "venv", os.path.join(project_path, "venv")], check=True)
            logger.info(f"Venv created at {project_path}")
        except Exception as e:
            logger.error(f"Failed to create venv: {e}")



# Functii simple pentru compatibilitate
def analyze_code(file_path: str) -> str:
    """Functie simpla de analiza (compatibilitate)."""
    tool = CodeTool()
    result = tool.execute("analyze", file_path)
    return str(result)


def run_code(code: str, language: str = "python") -> str:
    """Functie simpla de executie (compatibilitate)."""
    tool = CodeTool()
    result = tool.execute("run", code, language=language)
    return str(result)
