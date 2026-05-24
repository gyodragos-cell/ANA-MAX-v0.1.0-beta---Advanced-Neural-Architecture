"""
A.N.A. v15.0 - File Tools
=========================
Instrumente pentru operatii cu fisiere.
"""

import difflib
import glob as glob_module
import logging
import os
import re
from pathlib import Path
from typing import Optional

from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus
from tools.path_safety import is_protected_path, resolve_workspace_path, safe_display_path

logger = logging.getLogger(__name__)


class FilesTool(Tool):
    """
    Tool pentru operatii cu fisiere.
    Citire, scriere, cautare, editare.
    """

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="file_operations",
            description="Operatii cu fisiere: citire, scriere, cautare, editare, listare.",
            parameters=[
                ToolParameter(
                    name="operation",
                    description="Operatiunea de executat",
                    type="string",
                    required=True,
                    choices=["read", "write", "list", "search", "edit", "find", "info", "diff_preview", "surgical_edit"],
                ),
                ToolParameter(
                    name="path",
                    description="Calea catre fisier sau director",
                    type="string",
                    required=True,
                ),
                ToolParameter(
                    name="content",
                    description="Continut pentru scriere (doar pentru write)",
                    type="string",
                    required=False,
                ),
                ToolParameter(
                    name="pattern",
                    description="Pattern pentru cautare (pentru search, find)",
                    type="string",
                    required=False,
                ),
                ToolParameter(
                    name="search_text",
                    description="Text de cautat (pentru edit sau diff_preview)",
                    type="string",
                    required=False,
                ),
                ToolParameter(
                    name="replace_text",
                    description="Text de inlocuit (pentru edit sau diff_preview)",
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
                    description="Blocul exact care trebuie inlocuit pentru surgical_edit",
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
            ],
            category="files",
            requires_confirmation=False,
            dangerous=True,
        )

    def execute(self, operation: str, path: str, **kwargs) -> ToolResult:
        operations = {
            "read": self._read_file,
            "write": self._write_file,
            "list": self._list_directory,
            "search": self._search_in_files,
            "edit": self._edit_file,
            "find": self._find_files,
            "info": self._file_info,
            "diff_preview": self._diff_preview,
            "surgical_edit": self._surgical_edit,
        }

        if operation not in operations:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Operatiune necunoscuta: {operation}",
            )

        try:
            safe_path = resolve_workspace_path(path)
        except (OSError, ValueError) as exc:
            return ToolResult(status=ToolStatus.BLOCKED, error=str(exc))

        if operation in {"write", "edit", "diff_preview", "surgical_edit"} and is_protected_path(safe_path):
            return ToolResult(status=ToolStatus.BLOCKED, error=f"Refusing to modify protected path: {safe_display_path(safe_path)}")

        return operations[operation](str(safe_path), **kwargs)

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
                if start_line is None and end_line is None:
                    content = handle.read()
                else:
                    lines = handle.readlines()
                    start = (start_line - 1) if start_line else 0
                    end = end_line if end_line else len(lines)
                    content = "".join(lines[start:end])

            return ToolResult(
                status=ToolStatus.SUCCESS,
                data=content,
                message=f"Citit {len(content)} caractere din {path}",
            )
        except Exception as exc:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Eroare la citire: {exc}",
            )

    def _write_file(self, path: str, content: str = "", **kwargs) -> ToolResult:
        try:
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

    def _format_size(self, size: int) -> str:
        if size < 1024:
            return f"{size} B"
        if size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        if size < 1024 * 1024 * 1024:
            return f"{size / (1024 * 1024):.1f} MB"
        return f"{size / (1024 * 1024 * 1024):.1f} GB"
