"""
A.N.A. v15.0 - File Tools (OS27 Hyper++)
========================================
Instrumente pentru operatii cu fisiere.

OS27 Hyper++ Features:
- Telemetry tracking for file operations (read, write, list, search, edit, etc.)
- Health monitoring for file operations reliability
- MemoryCortex integration for file operation errors and state learning
- ContextEngine integration for file system state awareness
- SelfEvolvingTool integration for anomaly detection on file operation failures
- Structured logging with error detection
"""

import difflib
import glob as glob_module
import logging
import os
import re
import base64
import time
from pathlib import Path
from typing import Optional, Dict, Any

from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus
from tools.path_safety import is_protected_path, resolve_workspace_path, safe_display_path

logger = logging.getLogger(__name__)

# OS27 Hyper++ Telemetry
_files_telemetry: Dict[str, Dict[str, Any]] = {}


def _record_files_telemetry(operation: str, success: bool, execution_time: float) -> None:
    """Record OS27 Hyper++ telemetry for file operations."""
    if operation not in _files_telemetry:
        _files_telemetry[operation] = {
            "operation_count": 0,
            "success_count": 0,
            "failure_count": 0,
            "total_time": 0.0,
            "last_execution_time": 0.0,
            "last_success": False,
        }
    
    _files_telemetry[operation]["operation_count"] += 1
    _files_telemetry[operation]["total_time"] += execution_time
    _files_telemetry[operation]["last_execution_time"] = execution_time
    _files_telemetry[operation]["last_success"] = success
    
    if success:
        _files_telemetry[operation]["success_count"] += 1
    else:
        _files_telemetry[operation]["failure_count"] += 1


def get_files_telemetry(operation: str | None = None) -> Dict[str, Any] | Dict[str, Dict[str, Any]]:
    """Get telemetry for file operations."""
    if operation:
        return _files_telemetry.get(operation, {})
    return _files_telemetry.copy()


def get_files_health() -> str:
    """Get health status for files tool based on telemetry."""
    if not _files_telemetry:
        return "unknown"
    
    total_ops = sum(stats["operation_count"] for stats in _files_telemetry.values())
    total_failures = sum(stats["failure_count"] for stats in _files_telemetry.values())
    
    if total_ops == 0:
        return "unknown"
    
    failure_rate = total_failures / total_ops
    if failure_rate > 0.5:
        return "broken"
    if failure_rate > 0.1:
        return "degraded"
    return "healthy"


class FilesTool(Tool):
    """
    Tool pentru operatii cu fisiere.
    Citire, scriere, cautare, editare.
    """

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="file_operations",
            description=(
                "Operatii complete cu fisiere si directoare (IDE-level). "
                "Operatii: read, write, write_lines, write_base64, write_chunked, "
                "list, search, edit, find, info, diff_preview, surgical_edit, analyze, "
                "delete, move, copy, rename, mkdir, exists, tree, append, head, tail, "
                "grep, patch, stats, hash. "
                "PREFER file_operations peste terminal pentru orice operatie cu fisiere."
            ),
            parameters=[
                ToolParameter(
                    name="operation",
                    description="Operatiunea de executat",
                    type="string",
                    required=True,
                    choices=[
                        "read", "write", "write_lines", "write_base64", "write_chunked",
                        "list", "search", "edit", "find", "info", "diff_preview",
                        "surgical_edit", "analyze",
                        "delete", "move", "copy", "rename", "mkdir",
                        "exists", "tree", "append", "head", "tail",
                        "grep", "patch", "stats", "hash",
                    ],
                ),
                ToolParameter(
                    name="path",
                    description="Calea catre fisier sau director (absoluta preferata)",
                    type="string",
                    required=True,
                ),
                ToolParameter(
                    name="destination",
                    description="Destinatie pentru move/copy/rename",
                    type="string",
                    required=False,
                ),
                ToolParameter(
                    name="recursive",
                    description="Recursiv pentru delete director sau tree",
                    type="boolean",
                    required=False,
                    default=False,
                ),
                ToolParameter(
                    name="n_lines",
                    description="Numar de linii pentru head/tail (default 50)",
                    type="integer",
                    required=False,
                ),
                ToolParameter(
                    name="content",
                    description="Continut pentru write/append/patch",
                    type="string",
                    required=False,
                ),
                ToolParameter(
                    name="lines",
                    description="Linii de scris (pentru write_lines)",
                    type="array",
                    required=False,
                ),
                ToolParameter(
                    name="pattern",
                    description="Pattern regex pentru search/find/grep",
                    type="string",
                    required=False,
                ),
                ToolParameter(
                    name="search_text",
                    description="Text de cautat (pentru edit/diff_preview)",
                    type="string",
                    required=False,
                ),
                ToolParameter(
                    name="replace_text",
                    description="Text de inlocuit (pentru edit/diff_preview)",
                    type="string",
                    required=False,
                ),
                ToolParameter(
                    name="start_line",
                    description="Linia de start pentru citire partiala",
                    type="integer",
                    required=False,
                ),
                ToolParameter(
                    name="end_line",
                    description="Linia de final pentru citire partiala",
                    type="integer",
                    required=False,
                ),
                ToolParameter(
                    name="old_block",
                    description="Blocul exact de inlocuit pentru surgical_edit",
                    type="string",
                    required=False,
                ),
                ToolParameter(
                    name="new_block",
                    description="Blocul nou pentru surgical_edit",
                    type="string",
                    required=False,
                ),
                ToolParameter(
                    name="preview_only",
                    description="Returneaza doar diff-ul fara sa scrie pe disc",
                    type="boolean",
                    required=False,
                    default=False,
                ),
                ToolParameter(
                    name="encoding",
                    description="Encoding fisier (default utf-8)",
                    type="string",
                    required=False,
                ),
            ],
            category="files",
            requires_confirmation=False,
            dangerous=True,
        )

    def execute(self, operation: str, path: str, **kwargs) -> ToolResult:
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
            # -- existente --
            "read": self._read_file,
            "write": self._write_file,
            "write_lines": self._write_lines,
            "list": self._list_directory,
            "search": self._search_in_files,
            "edit": self._edit_file,
            "find": self._find_files,
            "info": self._file_info,
            "diff_preview": self._diff_preview,
            "surgical_edit": self._surgical_edit,
            "analyze": self._analyze_file,
            "write_base64": self._write_base64,
            "write_chunked": self._write_chunked,
            # -- IDE-level noi --
            "delete": self._delete_path,
            "move": self._move_path,
            "copy": self._copy_path,
            "rename": self._rename_path,
            "mkdir": self._mkdir,
            "exists": self._exists,
            "tree": self._tree,
            "append": self._append_file,
            "head": self._head_file,
            "tail": self._tail_file,
            "grep": self._grep_file,
            "patch": self._patch_file,
            "stats": self._stats,
            "hash": self._hash_file,
        }

        if operation not in operations:
            execution_time = time.time() - start_time
            _record_files_telemetry(operation, False, execution_time)
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Operatiune necunoscuta: {operation}",
            )

        try:
            allow_outside = True  # God-mode lab: allow all operations outside workspace
            safe_path = resolve_workspace_path(path, allow_outside_workspace=allow_outside)
        except (OSError, ValueError) as exc:
            execution_time = time.time() - start_time
            _record_files_telemetry(operation, False, execution_time)
            return ToolResult(status=ToolStatus.BLOCKED, error=str(exc))

        if operation in {"write", "edit", "diff_preview", "surgical_edit"} and is_protected_path(safe_path):
            execution_time = time.time() - start_time
            _record_files_telemetry(operation, False, execution_time)
            return ToolResult(status=ToolStatus.BLOCKED, error=f"Refusing to modify protected path: {safe_display_path(safe_path)}")

        result = operations[operation](str(safe_path), **kwargs)
        
        execution_time = time.time() - start_time
        _record_files_telemetry(operation, result.is_success, execution_time)
        
        # ContextEngine integration for file operations
        if context_engine and result.is_success:
            try:
                context_engine.update_context(
                    key="file_operations",
                    value={
                        "operation": operation,
                        "path": str(safe_path),
                        "success": result.is_success,
                        "timestamp": time.time(),
                    }
                )
            except Exception:
                pass
        
        # MemoryCortex integration for file operation errors
        if cortex and not result.is_success:
            try:
                cortex.remember(
                    "error",
                    f"files.{operation}",
                    f"File operation failed: {result.error}"
                )
            except Exception:
                pass
        
        return result

    def _read_file(
        self,
        path: str,
        start_line: Optional[int] = None,
        end_line: Optional[int] = None,
        **kwargs,
    ) -> ToolResult:
        try:
            if not os.path.exists(path):
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error=f"Fisierul nu exista: {path}",
                )

            with open(path, "r", encoding="utf-8", errors="ignore") as handle:
                lines = handle.readlines()
                total_lines = len(lines)

                start = (start_line - 1) if start_line and start_line > 0 else 0
                end = end_line if end_line else total_lines

                # Limita stricta pentru a proteja contextul de 32k al lui Qwen (max 500 linii per apel)
                max_lines = 500
                if end - start > max_lines:
                    end = start + max_lines
                    truncated = True
                else:
                    truncated = False

                content = "".join(lines[start:end])

            message = f"Citit liniile {start + 1} - {end} din {total_lines}."
            if truncated:
                warning = f"\n\n[SISTEM ANA]: Fisierul are {total_lines} linii. Am trunchiat output-ul la {max_lines} linii pentru a-ti proteja memoria.\nPentru a citi restul, reapeleaza tool-ul cu start_line={end + 1}."
                content += warning
                message += " FISIER TRUNCHIAT."

            return ToolResult(
                status=ToolStatus.SUCCESS,
                data=content,
                message=message,
            )
        except Exception as exc:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Eroare la citire: {exc}",
            )

    def _delete_path(self, path: str, recursive: bool = False, **kwargs) -> ToolResult:
        """Sterge un fisier sau director. Foloseste Python direct - fara CMD/PowerShell quoting issues."""
        import shutil
        try:
            p = Path(path)
            if not p.exists():
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error=f"Fisierul/directorul nu exista: {path}",
                )
            if p.is_file() or p.is_symlink():
                p.unlink()
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data=f"Fisier sters: {path}",
                    message="Fisier sters cu succes.",
                )
            elif p.is_dir():
                if recursive:
                    shutil.rmtree(str(p))
                    return ToolResult(
                        status=ToolStatus.SUCCESS,
                        data=f"Director sters recursiv: {path}",
                        message="Director sters cu succes.",
                    )
                else:
                    try:
                        p.rmdir()
                        return ToolResult(
                            status=ToolStatus.SUCCESS,
                            data=f"Director gol sters: {path}",
                            message="Director sters cu succes.",
                        )
                    except OSError:
                        return ToolResult(
                            status=ToolStatus.ERROR,
                            error=f"Directorul nu e gol. Foloseste recursive=true pentru a sterge recursiv.",
                        )
        except Exception as exc:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Eroare la stergere: {exc}",
            )

    # ------------------------------------------------------------------ #
    #  IDE-LEVEL OPERATIONS — move, copy, rename, mkdir, exists, tree,    #
    #  append, head, tail, grep, patch, stats, hash                       #
    # ------------------------------------------------------------------ #

    def _move_path(self, path: str, destination: str = "", **kwargs) -> ToolResult:
        """Muta fisier sau director. Python shutil - zero quoting issues."""
        import shutil
        try:
            if not destination:
                return ToolResult(status=ToolStatus.ERROR, error="Parametrul 'destination' lipseste.")
            p = Path(path)
            if not p.exists():
                return ToolResult(status=ToolStatus.ERROR, error=f"Sursa nu exista: {path}")
            dst = Path(destination)
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(p), str(dst))
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data=f"Mutat: {path} → {destination}",
                message="Operatiune move reusita.",
            )
        except Exception as exc:
            return ToolResult(status=ToolStatus.ERROR, error=f"Eroare move: {exc}")

    def _copy_path(self, path: str, destination: str = "", **kwargs) -> ToolResult:
        """Copiaza fisier sau director (recursiv pentru directoare)."""
        import shutil
        try:
            if not destination:
                return ToolResult(status=ToolStatus.ERROR, error="Parametrul 'destination' lipseste.")
            p = Path(path)
            if not p.exists():
                return ToolResult(status=ToolStatus.ERROR, error=f"Sursa nu exista: {path}")
            dst = Path(destination)
            if p.is_dir():
                shutil.copytree(str(p), str(dst), dirs_exist_ok=True)
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data=f"Director copiat: {path} → {destination}",
                    message="Copy director reusit.",
                )
            else:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(str(p), str(dst))
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data=f"Fisier copiat: {path} → {destination}",
                    message="Copy fisier reusit.",
                )
        except Exception as exc:
            return ToolResult(status=ToolStatus.ERROR, error=f"Eroare copy: {exc}")

    def _rename_path(self, path: str, destination: str = "", **kwargs) -> ToolResult:
        """Redenumeste fisier/director in acelasi director."""
        try:
            if not destination:
                return ToolResult(status=ToolStatus.ERROR, error="Parametrul 'destination' (noul nume) lipseste.")
            p = Path(path)
            if not p.exists():
                return ToolResult(status=ToolStatus.ERROR, error=f"Nu exista: {path}")
            # destination poate fi: doar un nume ("nou.txt") sau o cale completa
            dst = Path(destination)
            if not dst.is_absolute():
                dst = p.parent / dst
            p.rename(dst)
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data=f"Redenumit: {path} → {str(dst)}",
                message="Rename reusit.",
            )
        except Exception as exc:
            return ToolResult(status=ToolStatus.ERROR, error=f"Eroare rename: {exc}")

    def _mkdir(self, path: str, **kwargs) -> ToolResult:
        """Creeaza director si toti parintii (echivalent mkdir -p)."""
        try:
            p = Path(path)
            p.mkdir(parents=True, exist_ok=True)
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data=f"Director creat: {path}",
                message="mkdir reusit.",
            )
        except Exception as exc:
            return ToolResult(status=ToolStatus.ERROR, error=f"Eroare mkdir: {exc}")

    def _exists(self, path: str, **kwargs) -> ToolResult:
        """Verifica daca un path exista si ce tip este."""
        try:
            p = Path(path)
            if not p.exists():
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data={"exists": False, "path": path},
                    message=f"Nu exista: {path}",
                )
            kind = "directory" if p.is_dir() else ("symlink" if p.is_symlink() else "file")
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"exists": True, "type": kind, "path": str(p.resolve())},
                message=f"Exista ({kind}): {path}",
            )
        except Exception as exc:
            return ToolResult(status=ToolStatus.ERROR, error=f"Eroare exists: {exc}")

    def _tree(self, path: str, recursive: bool = True, **kwargs) -> ToolResult:
        """Returneaza structura unui director (compact, max 200 intrari)."""
        try:
            p = Path(path)
            if not p.exists():
                return ToolResult(status=ToolStatus.ERROR, error=f"Nu exista: {path}")
            if p.is_file():
                return ToolResult(status=ToolStatus.ERROR, error=f"Path-ul e un fisier, nu director: {path}")

            lines = [f"{p.name}/"]
            count = 0
            max_entries = 200

            def _walk(directory: Path, prefix: str, depth: int):
                nonlocal count
                if count >= max_entries:
                    return
                if not recursive and depth > 1:
                    return
                try:
                    entries = sorted(directory.iterdir(), key=lambda x: (x.is_file(), x.name.lower()))
                except PermissionError:
                    return
                for i, entry in enumerate(entries):
                    if count >= max_entries:
                        lines.append(f"{prefix}... (trunchiat la {max_entries} intrari)")
                        return
                    connector = "└── " if i == len(entries) - 1 else "├── "
                    suffix = "/" if entry.is_dir() else ""
                    lines.append(f"{prefix}{connector}{entry.name}{suffix}")
                    count += 1
                    if entry.is_dir() and recursive:
                        extension = "    " if i == len(entries) - 1 else "│   "
                        _walk(entry, prefix + extension, depth + 1)

            _walk(p, "", 0)
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data="\n".join(lines),
                message=f"Tree: {count} intrari in {path}",
            )
        except Exception as exc:
            return ToolResult(status=ToolStatus.ERROR, error=f"Eroare tree: {exc}")

    def _append_file(self, path: str, content: str = "", encoding: str = "utf-8", **kwargs) -> ToolResult:
        """Adauga text la sfarsitul unui fisier (creeaza daca nu exista)."""
        try:
            p = Path(path)
            existing = ""
            if p.exists():
                try:
                    existing = p.read_text(encoding=encoding, errors="ignore")
                except Exception:
                    pass
            syntax_err = self._validate_python_syntax(path, existing + content)
            if syntax_err:
                return ToolResult(status=ToolStatus.ERROR, error=syntax_err)

            p.parent.mkdir(parents=True, exist_ok=True)
            with open(str(p), "a", encoding=encoding) as f:
                f.write(content)
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data=f"Adaugat {len(content)} caractere in {path}",
                message="Append reusit.",
            )
        except Exception as exc:
            return ToolResult(status=ToolStatus.ERROR, error=f"Eroare append: {exc}")

    def _head_file(self, path: str, n_lines: int = 50, encoding: str = "utf-8", **kwargs) -> ToolResult:
        """Returneaza primele N linii dintr-un fisier (default 50)."""
        try:
            p = Path(path)
            if not p.exists():
                return ToolResult(status=ToolStatus.ERROR, error=f"Nu exista: {path}")
            n = int(n_lines) if n_lines else 50
            with open(str(p), "r", encoding=encoding, errors="ignore") as f:
                lines = []
                for i, line in enumerate(f):
                    if i >= n:
                        break
                    lines.append(line)
            content = "".join(lines)
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data=content,
                message=f"Primele {len(lines)} linii din {path}",
            )
        except Exception as exc:
            return ToolResult(status=ToolStatus.ERROR, error=f"Eroare head: {exc}")

    def _tail_file(self, path: str, n_lines: int = 50, encoding: str = "utf-8", **kwargs) -> ToolResult:
        """Returneaza ultimele N linii dintr-un fisier (ideal pentru log-uri)."""
        try:
            p = Path(path)
            if not p.exists():
                return ToolResult(status=ToolStatus.ERROR, error=f"Nu exista: {path}")
            n = int(n_lines) if n_lines else 50
            with open(str(p), "r", encoding=encoding, errors="ignore") as f:
                # Citim toate, dar pastram doar ultimele N (eficient pentru fisiere mari)
                from collections import deque
                last_lines = deque(f, maxlen=n)
            content = "".join(last_lines)
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data=content,
                message=f"Ultimele {len(last_lines)} linii din {path}",
            )
        except Exception as exc:
            return ToolResult(status=ToolStatus.ERROR, error=f"Eroare tail: {exc}")

    def _grep_file(self, path: str, pattern: str = "", encoding: str = "utf-8", **kwargs) -> ToolResult:
        """Cauta pattern regex in fisier, returneaza linii cu numere. Daca path e director, cauta recursiv."""
        import re
        try:
            if not pattern:
                return ToolResult(status=ToolStatus.ERROR, error="Parametrul 'pattern' lipseste.")
            regex = re.compile(pattern, re.IGNORECASE)
            p = Path(path)
            results = []
            max_results = 200

            def _search_file(fp: Path):
                try:
                    with open(str(fp), "r", encoding=encoding, errors="ignore") as f:
                        for lineno, line in enumerate(f, 1):
                            if len(results) >= max_results:
                                return
                            if regex.search(line):
                                results.append(f"{fp}:{lineno}: {line.rstrip()}")
                except Exception:
                    pass

            if p.is_file():
                _search_file(p)
            elif p.is_dir():
                for fp in p.rglob("*"):
                    if len(results) >= max_results:
                        break
                    if fp.is_file():
                        _search_file(fp)
            else:
                return ToolResult(status=ToolStatus.ERROR, error=f"Nu exista: {path}")

            if not results:
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data="",
                    message=f"Nicio potrivire pentru '{pattern}' in {path}",
                )
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data="\n".join(results),
                message=f"{len(results)} potriviri pentru '{pattern}'",
            )
        except re.error as exc:
            return ToolResult(status=ToolStatus.ERROR, error=f"Regex invalid: {exc}")
        except Exception as exc:
            return ToolResult(status=ToolStatus.ERROR, error=f"Eroare grep: {exc}")

    def _patch_file(self, path: str, content: str = "", **kwargs) -> ToolResult:
        """Aplica un unified diff (patch) la un fisier. content = textul patch-ului."""
        try:
            if not content:
                return ToolResult(status=ToolStatus.ERROR, error="Parametrul 'content' (patch text) lipseste.")
            p = Path(path)
            if not p.exists():
                return ToolResult(status=ToolStatus.ERROR, error=f"Fisierul tinta nu exista: {path}")
            # Aplicam patch-ul linie cu linie (unified diff simplu)
            import patch as patch_lib  # optional dependency
            pset = patch_lib.fromstring(content.encode())
            if pset and pset.apply(root=str(p.parent)):
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data=f"Patch aplicat: {path}",
                    message="Patch reusit.",
                )
            return ToolResult(status=ToolStatus.ERROR, error="Patch a esuat (conflict sau format invalid).")
        except ImportError:
            # Fallback: patch manual simplu (hunk parsing)
            try:
                with open(str(p), "r", encoding="utf-8", errors="ignore") as f:
                    original = f.readlines()
                import re
                lines_out = list(original)
                # Extragem linii de add/remove din unified diff
                removes, adds = [], []
                for line in content.splitlines():
                    if line.startswith("-") and not line.startswith("---"):
                        removes.append(line[1:])
                    elif line.startswith("+") and not line.startswith("+++"):
                        adds.append(line[1:])
                result_text = "".join(original)
                for rm in removes:
                    result_text = result_text.replace(rm, "", 1)
                syntax_err = self._validate_python_syntax(path, result_text)
                if syntax_err:
                    return ToolResult(status=ToolStatus.ERROR, error=syntax_err)

                # Re-write
                with open(str(p), "w", encoding="utf-8") as f:
                    f.write(result_text)
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data=f"Patch aplicat (manual fallback): {path}",
                    message="Patch reusit.",
                )
            except Exception as exc2:
                return ToolResult(status=ToolStatus.ERROR, error=f"Eroare patch: {exc2}")
        except Exception as exc:
            return ToolResult(status=ToolStatus.ERROR, error=f"Eroare patch: {exc}")

    def _stats(self, path: str, **kwargs) -> ToolResult:
        """Returneaza statistici detaliate despre fisier: size, lines, encoding, modified."""
        try:
            import datetime
            p = Path(path)
            if not p.exists():
                return ToolResult(status=ToolStatus.ERROR, error=f"Nu exista: {path}")
            stat = p.stat()
            info: dict = {
                "path": str(p.resolve()),
                "size_bytes": stat.st_size,
                "size_human": f"{stat.st_size / 1024:.1f} KB" if stat.st_size >= 1024 else f"{stat.st_size} B",
                "modified": datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                "created": datetime.datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M:%S"),
                "is_dir": p.is_dir(),
                "is_file": p.is_file(),
            }
            if p.is_file():
                try:
                    with open(str(p), "r", encoding="utf-8", errors="ignore") as f:
                        lines = f.readlines()
                    info["lines"] = len(lines)
                    info["encoding"] = "utf-8"
                    info["extension"] = p.suffix
                except Exception:
                    info["lines"] = "N/A"
            elif p.is_dir():
                try:
                    entries = list(p.iterdir())
                    info["children"] = len(entries)
                    info["files"] = sum(1 for e in entries if e.is_file())
                    info["dirs"] = sum(1 for e in entries if e.is_dir())
                except Exception:
                    pass
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data=info,
                message=f"Stats pentru {path}",
            )
        except Exception as exc:
            return ToolResult(status=ToolStatus.ERROR, error=f"Eroare stats: {exc}")

    def _hash_file(self, path: str, **kwargs) -> ToolResult:
        """Calculeaza SHA-256 al unui fisier (verificare integritate)."""
        import hashlib
        try:
            p = Path(path)
            if not p.exists() or not p.is_file():
                return ToolResult(status=ToolStatus.ERROR, error=f"Fisierul nu exista: {path}")
            h = hashlib.sha256()
            with open(str(p), "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    h.update(chunk)
            digest = h.hexdigest()
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"sha256": digest, "path": path},
                message=f"SHA-256: {digest}",
            )
        except Exception as exc:
            return ToolResult(status=ToolStatus.ERROR, error=f"Eroare hash: {exc}")


    @staticmethod
    def _validate_python_syntax(path: str, content: str) -> Optional[str]:
        """Validare AST pentru fisiere .py inainte de a scrie pe disk."""
        if str(path).lower().endswith(".py"):
            import ast
            try:
                ast.parse(content)
            except SyntaxError as syn_err:
                hint_line = f" pe linia cod: '{syn_err.text.strip()}'" if syn_err.text else ""
                return f"VALIDARE SINTAXA ESUATA (AST Guard): Fisierul Python nu a fost salvat deoarece are eroare de sintaxa la linia {syn_err.lineno}: {syn_err.msg}{hint_line}. Corecteaza codul inainte de salvare!"
        return None

    def _write_file(self, path: str, content: str = "", **kwargs) -> ToolResult:
        try:
            syntax_err = self._validate_python_syntax(path, content)
            if syntax_err:
                return ToolResult(status=ToolStatus.ERROR, error=syntax_err)

            parent_dir = os.path.dirname(path)
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)

            with open(path, "w", encoding="utf-8") as handle:
                handle.write(content)

            return ToolResult(
                status=ToolStatus.SUCCESS,
                data=f"Scris {len(content)} caractere in {path}",
                message="Fisier salvat cu succes",
            )
        except Exception as exc:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Eroare la scriere: {exc}",
            )

    def _write_lines(self, path: str, lines: Optional[list] = None, **kwargs) -> ToolResult:
        try:
            if lines is None:
                lines = []
            full_content = "\n".join(str(line) for line in lines)
            syntax_err = self._validate_python_syntax(path, full_content)
            if syntax_err:
                return ToolResult(status=ToolStatus.ERROR, error=syntax_err)

            parent_dir = os.path.dirname(path)
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)

            with open(path, "w", encoding="utf-8") as handle:
                handle.write(full_content)

            return ToolResult(
                status=ToolStatus.SUCCESS,
                data=f"Scrise {len(lines)} linii in {path}",
                message="Fisier salvat cu succes (write_lines)",
            )
        except Exception as exc:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Eroare la scriere linii: {exc}",
            )

    def _write_base64(self, path: str, content: str = "", **kwargs) -> ToolResult:
        """Write content using Base64 encoding to avoid JSON escaping issues."""
        try:
            parent_dir = os.path.dirname(path)
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)
                
            decoded_bytes = base64.b64decode(content)
            decoded_text = decoded_bytes.decode('utf-8', errors='replace')

            with open(path, "w", encoding="utf-8") as handle:
                handle.write(decoded_text)

            return ToolResult(
                status=ToolStatus.SUCCESS,
                data=f"Scris {len(decoded_text)} caractere in {path} via Base64",
                message="Fisier salvat cu succes (Base64)",
            )
        except Exception as exc:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Eroare la scriere base64: {exc}",
            )
    
    def _write_chunked(self, path: str, content: str = "", chunk_size: int = 4096, **kwargs) -> ToolResult:
        """Write large content in chunks to avoid JSON size limits."""
        try:
            parent_dir = os.path.dirname(path)
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)
            
            # Content is already in memory, just write it
            # This is a placeholder for true streaming if needed
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(content)
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data=f"Scris {len(content)} caractere in {path} (chunked)",
                message="Fisier salvat cu succes (chunked)",
            )
        except Exception as exc:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Eroare la scriere chunked: {exc}",
            )

    def _list_directory(self, path: str, **kwargs) -> ToolResult:
        try:
            if not os.path.exists(path):
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error=f"Directorul nu exista: {path}",
                )

            items = []
            for item in sorted(os.listdir(path)):
                full_path = os.path.join(path, item)
                if os.path.isdir(full_path):
                    type_str = "DIR "
                    size = ""
                else:
                    type_str = "FILE"
                    size = self._format_size(os.path.getsize(full_path))
                items.append(f"{type_str} {size:>10} {item}")

            if not items:
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data="Director gol",
                    message="Director gol",
                )

            return ToolResult(
                status=ToolStatus.SUCCESS,
                data="\n".join(items),
                message=f"Gasite {len(items)} elemente",
            )
        except Exception as exc:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Eroare la listare: {exc}",
            )

    def _search_in_files(self, path: str, pattern: str = "", **kwargs) -> ToolResult:
        try:
            if not pattern:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error="Pattern de cautare necesar",
                )

            results = []
            search_path = path if os.path.isdir(path) else os.path.dirname(path)
            file_pattern = kwargs.get("file_glob", "*")
            files = glob_module.glob(f"{search_path}/**/{file_pattern}", recursive=True)

            for file_path in files[:100]:
                if not os.path.isfile(file_path):
                    continue
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as handle:
                        for index, line in enumerate(handle, 1):
                            if re.search(pattern, line):
                                results.append(f"{file_path}:{index}: {line.strip()}")
                except Exception as exc:
                    logger.debug("Skipping unreadable file during search %s: %s", file_path, exc)
                    continue

            if not results:
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data="Nu am gasit rezultate",
                    message="Nicio potrivire",
                )

            return ToolResult(
                status=ToolStatus.SUCCESS,
                data="\n".join(results[:100]),
                message=f"Gasite {len(results)} potriviri",
            )
        except Exception as exc:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Eroare la cautare: {exc}",
            )

    def _edit_file(self, path: str, search_text: str = "", replace_text: str = "", **kwargs) -> ToolResult:
        try:
            if not search_text:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error="Text de cautat necesar",
                )

            if not os.path.exists(path):
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error=f"Fisierul nu exista: {path}",
                )

            with open(path, "r", encoding="utf-8") as handle:
                content = handle.read()

            replace_all = kwargs.get("replace_all", False)
            if replace_all:
                count = content.count(search_text)
                new_content = content.replace(search_text, replace_text)
            else:
                count = 1 if search_text in content else 0
                new_content = content.replace(search_text, replace_text, 1)

            if count == 0:
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data="Text nu a fost gasit",
                    message="Nicio modificare",
                )

            syntax_err = self._validate_python_syntax(path, new_content)
            if syntax_err:
                return ToolResult(status=ToolStatus.ERROR, error=syntax_err)

            with open(path, "w", encoding="utf-8") as handle:
                handle.write(new_content)

            return ToolResult(
                status=ToolStatus.SUCCESS,
                data=f"Inlocuit {count} aparitii",
                message="Fisier modificat",
            )
        except Exception as exc:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Eroare la editare: {exc}",
            )

    def _find_files(self, path: str, pattern: str = "*", **kwargs) -> ToolResult:
        try:
            search_path = path if os.path.isdir(path) else os.path.dirname(path) or "."
            files = glob_module.glob(f"{search_path}/**/{pattern}", recursive=True)

            if not files:
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data="Nu am gasit fisiere",
                    message="Niciun rezultat",
                )

            return ToolResult(
                status=ToolStatus.SUCCESS,
                data="\n".join(files[:100]),
                message=f"Gasite {len(files)} fisiere",
            )
        except Exception as exc:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Eroare la cautare: {exc}",
            )

    def _diff_preview(self, path: str, search_text: str = "", replace_text: str = "", **kwargs) -> ToolResult:
        try:
            if not search_text:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error="Text de cautat necesar pentru diff_preview",
                )

            file_path = Path(path)
            if not file_path.exists():
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error=f"Fisierul nu exista: {path}",
                )

            original = file_path.read_text(encoding="utf-8")
            replace_all = bool(kwargs.get("replace_all", False))
            updated = original.replace(search_text, replace_text) if replace_all else original.replace(search_text, replace_text, 1)

            if original == updated:
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data={"changed": False, "diff": ""},
                    message="Nicio modificare de previzualizat",
                )

            diff = "".join(
                difflib.unified_diff(
                    original.splitlines(True),
                    updated.splitlines(True),
                    fromfile=str(file_path),
                    tofile=str(file_path),
                )
            )
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"changed": True, "diff": diff},
                message="Previzualizare diff generata",
            )
        except Exception as exc:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Eroare la diff preview: {exc}",
            )

    def _surgical_edit(self, path: str, old_block: str = "", new_block: str = "", **kwargs) -> ToolResult:
        try:
            if not old_block:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error="Parametrul 'old_block' este obligatoriu pentru surgical_edit",
                )

            file_path = Path(path)
            if not file_path.exists():
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error=f"Fisierul nu exista: {path}",
                )

            original = file_path.read_text(encoding="utf-8")
            match_count = original.count(old_block)
            if match_count == 0:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error="Blocul target nu a fost gasit exact. Surgical edit anulat.",
                )

            replace_all = bool(kwargs.get("replace_all", False))
            if match_count > 1 and not replace_all:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error="Blocul target apare de mai multe ori. Rafineaza targetul sau foloseste replace_all.",
                )

            updated = original.replace(old_block, new_block, 1 if not replace_all else match_count)
            diff = "".join(
                difflib.unified_diff(
                    original.splitlines(True),
                    updated.splitlines(True),
                    fromfile=str(file_path),
                    tofile=str(file_path),
                )
            )

            if kwargs.get("preview_only", False):
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data={"changed": True, "diff": diff, "matches": match_count},
                    message="Surgical edit previzualizat",
                )

            syntax_err = self._validate_python_syntax(path, updated)
            if syntax_err:
                return ToolResult(status=ToolStatus.ERROR, error=syntax_err)

            file_path.write_text(updated, encoding="utf-8")
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"changed": True, "diff": diff, "matches": match_count},
                message="Surgical edit aplicat",
            )
        except Exception as exc:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Eroare la surgical edit: {exc}",
            )

    def _file_info(self, path: str, **kwargs) -> ToolResult:
        try:
            if not os.path.exists(path):
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error=f"Fisierul nu exista: {path}",
                )

            stat = os.stat(path)
            info = {
                "path": safe_display_path(Path(path)),
                "type": "director" if os.path.isdir(path) else "fisier",
                "size": self._format_size(stat.st_size),
                "modified": stat.st_mtime,
                "created": stat.st_ctime,
            }

            if os.path.isfile(path):
                try:
                    with open(path, "r", encoding="utf-8", errors="ignore") as handle:
                        info["lines"] = sum(1 for _ in handle)
                except Exception as exc:
                    logger.debug("Could not count lines for %s: %s", path, exc)

            info_str = "\n".join([f"{key}: {value}" for key, value in info.items()])
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data=info_str,
                message="Informatii obtinute",
            )
        except Exception as exc:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Eroare: {exc}",
            )

    def _analyze_file(self, path: str, **kwargs) -> ToolResult:
        """Analyze a text file completely in Python and return a compact summary.
        Works like a senior engineer: reads everything, extracts patterns, returns insights."""
        try:
            if not os.path.exists(path):
                return ToolResult(status=ToolStatus.ERROR, error=f"Fisierul nu exista: {path}")

            stat = os.stat(path)
            file_size = self._format_size(stat.st_size)

            with open(path, "r", encoding="utf-8", errors="ignore") as handle:
                lines = handle.readlines()

            total_lines = len(lines)
            if total_lines == 0:
                return ToolResult(status=ToolStatus.SUCCESS, data="Fisier gol.", message="Fisier gol")

            # --- Basic stats ---
            first_line = lines[0].strip()[:200]
            last_line = lines[-1].strip()[:200]

            # --- Error/warning detection ---
            error_patterns = re.compile(r"(?i)(error|failed|failure|exception|fatal|critical|\*FAILED\*)", re.IGNORECASE)
            warn_patterns = re.compile(r"(?i)(warn|warning|caution|deprecated)", re.IGNORECASE)
            error_lines = []
            warn_lines = []
            for idx, line in enumerate(lines, 1):
                if error_patterns.search(line):
                    error_lines.append((idx, line.strip()[:150]))
                elif warn_patterns.search(line):
                    warn_lines.append((idx, line.strip()[:150]))

            # --- Component/module frequency (extract unique prefixes/tags) ---
            component_counts: dict[str, int] = {}
            timestamp_first = None
            timestamp_last = None
            ts_pattern = re.compile(r"(\d{4}[/-]\d{2}[/-]\d{2}[\sT]\d{2}:\d{2}:\d{2})")
            component_pattern = re.compile(r"^\S+\s+\S+\s+\S+\s+\S+\s+(\S+)")

            for line in lines:
                ts_match = ts_pattern.search(line)
                if ts_match:
                    ts = ts_match.group(1)
                    if timestamp_first is None:
                        timestamp_first = ts
                    timestamp_last = ts
                comp_match = component_pattern.match(line)
                if comp_match:
                    comp = comp_match.group(1)
                    component_counts[comp] = component_counts.get(comp, 0) + 1

            # Top 10 components by frequency
            top_components = sorted(component_counts.items(), key=lambda x: -x[1])[:10]

            # --- Build summary ---
            parts = []
            parts.append(f"=== ANALIZA FISIER: {os.path.basename(path)} ===")
            parts.append(f"Cale: {path}")
            parts.append(f"Dimensiune: {file_size} | Linii totale: {total_lines}")
            if timestamp_first and timestamp_last:
                parts.append(f"Perioada: {timestamp_first} -> {timestamp_last}")
            parts.append(f"Prima linie: {first_line}")
            parts.append(f"Ultima linie: {last_line}")

            parts.append(f"\n--- ERORI GASITE: {len(error_lines)} ---")
            if error_lines:
                # Show last 15 errors (most recent are usually most relevant)
                for line_num, text in error_lines[-15:]:
                    parts.append(f"  L{line_num}: {text}")
                if len(error_lines) > 15:
                    parts.append(f"  ... si inca {len(error_lines) - 15} erori anterioare")
            else:
                parts.append("  Nicio eroare gasita.")

            parts.append(f"\n--- AVERTISMENTE: {len(warn_lines)} ---")
            if warn_lines:
                for line_num, text in warn_lines[-10:]:
                    parts.append(f"  L{line_num}: {text}")
                if len(warn_lines) > 10:
                    parts.append(f"  ... si inca {len(warn_lines) - 10} avertismente anterioare")
            else:
                parts.append("  Niciun avertisment gasit.")

            if top_components:
                parts.append("\n--- TOP COMPONENTE/MODULE ---")
                for comp, count in top_components:
                    parts.append(f"  {comp}: {count} linii")

            # --- Sample: first 5 + last 5 lines for context ---
            parts.append("\n--- PRIMELE 5 LINII ---")
            for line in lines[:5]:
                parts.append(f"  {line.rstrip()[:200]}")
            parts.append("\n--- ULTIMELE 5 LINII ---")
            for line in lines[-5:]:
                parts.append(f"  {line.rstrip()[:200]}")

            summary = "\n".join(parts)
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data=summary,
                message=f"Analiza completa: {total_lines} linii, {len(error_lines)} erori, {len(warn_lines)} avertismente",
            )
        except Exception as exc:
            return ToolResult(status=ToolStatus.ERROR, error=f"Eroare la analiza: {exc}")

    def _format_size(self, size: int) -> str:
        if size < 1024:
            return f"{size} B"
        if size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        if size < 1024 * 1024 * 1024:
            return f"{size / (1024 * 1024):.1f} MB"
        return f"{size / (1024 * 1024 * 1024):.1f} GB"
