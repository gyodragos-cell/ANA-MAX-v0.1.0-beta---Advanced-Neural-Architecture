"""
verdent_tools.py
================
Tool-uri inspirate din capabilitatile Verdent AI:
- bash_exec   : executie comenzi shell cu timeout
- glob_search : cautare fisiere cu pattern glob
- grep_content: cautare continut cu regex + context
- grep_file   : listeaza fisierele care contin un pattern
- web_fetch   : descarca si returneaza continut web
"""

from __future__ import annotations

import glob as glob_module
import logging
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional

from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# BashExecTool
# ---------------------------------------------------------------------------
class BashExecTool(Tool):
    """Executa comenzi shell (cmd/powershell) si returneaza output-ul."""

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="bash_exec",
            description=(
                "Executa o comanda shell si returneaza stdout+stderr. "
                "Suporta PowerShell pe Windows, bash pe Linux/Mac. "
                "Foloseste pentru git, npm, python, etc."
            ),
            parameters=[
                ToolParameter("command", "Comanda de executat", "string", True),
                ToolParameter("timeout", "Timeout in secunde (default 60)", "integer", False, 60),
                ToolParameter("cwd", "Director de lucru (optional)", "string", False, None),
                ToolParameter("shell_type", "Tipul shell: auto/powershell/cmd/bash", "string", False, "auto"),
            ],
            category="system",
            requires_confirmation=False,
        )

    def execute(self, command: str, timeout: int = 60, cwd: Optional[str] = None, shell_type: str = "auto", **kwargs) -> ToolResult:
        try:
            work_dir = cwd or os.getcwd()

            if shell_type == "auto":
                use_shell = True
                if sys.platform == "win32":
                    cmd = ["powershell", "-NoProfile", "-Command", command]
                    use_shell = False
                else:
                    cmd = command
            elif shell_type == "powershell":
                cmd = ["powershell", "-NoProfile", "-Command", command]
                use_shell = False
            elif shell_type == "cmd":
                cmd = ["cmd", "/c", command]
                use_shell = False
            else:
                cmd = command
                use_shell = True

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=int(timeout),
                cwd=work_dir,
                shell=use_shell,
                encoding="utf-8",
                errors="replace",
            )

            output = result.stdout or ""
            if result.stderr:
                output += f"\n[STDERR]\n{result.stderr}"

            if result.returncode != 0:
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data=output.strip(),
                    message=f"Comanda terminata cu exit code {result.returncode}",
                    error=f"Exit code: {result.returncode}",
                )

            return ToolResult(
                status=ToolStatus.SUCCESS,
                data=output.strip(),
                message=f"Comanda executata cu succes (exit 0)",
            )
        except subprocess.TimeoutExpired:
            return ToolResult(status=ToolStatus.ERROR, error=f"Timeout dupa {timeout}s")
        except Exception as exc:
            return ToolResult(status=ToolStatus.ERROR, error=str(exc))


# ---------------------------------------------------------------------------
# GlobSearchTool
# ---------------------------------------------------------------------------
class GlobSearchTool(Tool):
    """Cauta fisiere cu pattern glob recursiv."""

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="glob_search",
            description=(
                "Cauta fisiere cu pattern glob. Suporta ** recursiv si {a,b} brace expansion. "
                "Exemple: **/*.py, src/**/*.{js,ts}, config/*.yaml"
            ),
            parameters=[
                ToolParameter("pattern", "Pattern glob (ex: **/*.py)", "string", True),
                ToolParameter("dir_path", "Director de start (default: cwd)", "string", False, None),
                ToolParameter("limit", "Numar maxim de rezultate (default 200)", "integer", False, 200),
                ToolParameter("exclude", "Pattern-uri de exclus separate prin virgula", "string", False, None),
            ],
            category="files",
            requires_confirmation=False,
        )

    def execute(self, pattern: str, dir_path: Optional[str] = None, limit: int = 200, exclude: Optional[str] = None, **kwargs) -> ToolResult:
        try:
            base = Path(dir_path or os.getcwd())
            full_pattern = str(base / pattern)

            # Brace expansion manual pentru {a,b}
            patterns = self._expand_braces(full_pattern)
            files = []
            for p in patterns:
                files.extend(glob_module.glob(p, recursive=True))

            # Deduplicare si sortare
            files = sorted(set(files))

            # Excluderi
            if exclude:
                excl_patterns = [e.strip() for e in exclude.split(",") if e.strip()]
                def should_exclude(f):
                    for ep in excl_patterns:
                        if glob_module.fnmatch.fnmatch(os.path.basename(f), ep):
                            return True
                    return False
                files = [f for f in files if not should_exclude(f)]

            files = files[:int(limit)]

            if not files:
                return ToolResult(status=ToolStatus.SUCCESS, data="Niciun fisier gasit", message="0 rezultate")

            result_str = "\n".join(files)
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data=result_str,
                message=f"Gasite {len(files)} fisiere",
            )
        except Exception as exc:
            return ToolResult(status=ToolStatus.ERROR, error=str(exc))

    def _expand_braces(self, pattern: str):
        """Expandeaza {a,b,c} in pattern-uri multiple."""
        m = re.search(r'\{([^}]+)\}', pattern)
        if not m:
            return [pattern]
        parts = m.group(1).split(',')
        result = []
        for part in parts:
            expanded = pattern[:m.start()] + part.strip() + pattern[m.end():]
            result.extend(self._expand_braces(expanded))
        return result


# ---------------------------------------------------------------------------
# GrepContentTool
# ---------------------------------------------------------------------------
class GrepContentTool(Tool):
    """Cauta continut cu regex si returneaza liniile potrivite cu numere de linie."""

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="grep_content",
            description=(
                "Cauta un regex in fisiere si returneaza liniile care se potrivesc cu numere de linie. "
                "Suporta context before/after, glob pentru filtrare fisiere, ignore_case."
            ),
            parameters=[
                ToolParameter("regex", "Expresia regulata de cautat", "string", True),
                ToolParameter("search_path", "Fisier sau director de cautat (default: cwd)", "string", False, None),
                ToolParameter("glob", "Filtru glob pentru fisiere (ex: *.py)", "string", False, None),
                ToolParameter("before", "Linii de context inainte de match", "integer", False, 0),
                ToolParameter("after", "Linii de context dupa match", "integer", False, 0),
                ToolParameter("ignore_case", "Cautare case-insensitive", "boolean", False, False),
                ToolParameter("limit", "Numar maxim de linii output", "integer", False, 500),
            ],
            category="files",
            requires_confirmation=False,
        )

    def execute(self, regex: str, search_path: Optional[str] = None, glob: Optional[str] = None,
                before: int = 0, after: int = 0, ignore_case: bool = False, limit: int = 500, **kwargs) -> ToolResult:
        try:
            base = Path(search_path or os.getcwd())
            flags = re.IGNORECASE if ignore_case else 0
            compiled = re.compile(regex, flags)

            # Colecteaza fisierele
            if base.is_file():
                files = [base]
            else:
                if glob:
                    pattern = str(base / "**" / glob) if "**" not in glob else str(base / glob)
                    files = [Path(f) for f in glob_module.glob(pattern, recursive=True) if os.path.isfile(f)]
                else:
                    files = [Path(f) for f in glob_module.glob(str(base / "**" / "*"), recursive=True) if os.path.isfile(f)]

            results = []
            for fpath in files[:200]:
                try:
                    lines = fpath.read_text(encoding="utf-8", errors="ignore").splitlines()
                except Exception:
                    continue

                for i, line in enumerate(lines):
                    if compiled.search(line):
                        start = max(0, i - int(before))
                        end = min(len(lines), i + int(after) + 1)
                        for j in range(start, end):
                            prefix = ">" if j == i else " "
                            results.append(f"{fpath}:{j+1}{prefix} {lines[j]}")
                        if int(before) or int(after):
                            results.append("--")

            if not results:
                return ToolResult(status=ToolStatus.SUCCESS, data="Niciun rezultat gasit", message="0 potriviri")

            output = "\n".join(results[:int(limit)])
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data=output,
                message=f"Gasite potriviri in {len(results)} linii",
            )
        except re.error as exc:
            return ToolResult(status=ToolStatus.ERROR, error=f"Regex invalid: {exc}")
        except Exception as exc:
            return ToolResult(status=ToolStatus.ERROR, error=str(exc))


# ---------------------------------------------------------------------------
# GrepFileTool
# ---------------------------------------------------------------------------
class GrepFileTool(Tool):
    """Returneaza lista de fisiere care contin un pattern regex."""

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="grep_file",
            description=(
                "Returneaza lista de fisiere care contin cel putin un match pentru regex. "
                "Mai rapid decat grep_content cand ai nevoie doar de nume de fisiere."
            ),
            parameters=[
                ToolParameter("regex", "Expresia regulata de cautat", "string", True),
                ToolParameter("search_path", "Director de cautat (default: cwd)", "string", False, None),
                ToolParameter("glob", "Filtru glob pentru fisiere (ex: *.py)", "string", False, None),
                ToolParameter("ignore_case", "Cautare case-insensitive", "boolean", False, False),
                ToolParameter("limit", "Numar maxim de fisiere returnate", "integer", False, 100),
            ],
            category="files",
            requires_confirmation=False,
        )

    def execute(self, regex: str, search_path: Optional[str] = None, glob: Optional[str] = None,
                ignore_case: bool = False, limit: int = 100, **kwargs) -> ToolResult:
        try:
            base = Path(search_path or os.getcwd())
            flags = re.IGNORECASE if ignore_case else 0
            compiled = re.compile(regex, flags)

            if glob:
                pattern = str(base / "**" / glob) if "**" not in glob else str(base / glob)
                files = [Path(f) for f in glob_module.glob(pattern, recursive=True) if os.path.isfile(f)]
            else:
                files = [Path(f) for f in glob_module.glob(str(base / "**" / "*"), recursive=True) if os.path.isfile(f)]

            matching = []
            for fpath in files[:500]:
                try:
                    content = fpath.read_text(encoding="utf-8", errors="ignore")
                    if compiled.search(content):
                        matching.append(str(fpath))
                except Exception:
                    continue

            matching = matching[:int(limit)]

            if not matching:
                return ToolResult(status=ToolStatus.SUCCESS, data="Niciun fisier gasit", message="0 rezultate")

            return ToolResult(
                status=ToolStatus.SUCCESS,
                data="\n".join(matching),
                message=f"Gasite {len(matching)} fisiere",
            )
        except re.error as exc:
            return ToolResult(status=ToolStatus.ERROR, error=f"Regex invalid: {exc}")
        except Exception as exc:
            return ToolResult(status=ToolStatus.ERROR, error=str(exc))


# ---------------------------------------------------------------------------
# WebFetchTool
# ---------------------------------------------------------------------------
class WebFetchTool(Tool):
    """Descarca o pagina web si returneaza continutul (HTML -> text markdown)."""

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="web_fetch",
            description=(
                "Descarca o pagina web si returneaza continutul text/markdown. "
                "Util pentru documentatie, API reference, pagini de stiri. "
                "Diferit de web_search - acesta descarca URL-ul exact."
            ),
            parameters=[
                ToolParameter("url", "URL-ul de descarcat", "string", True),
                ToolParameter("timeout", "Timeout in secunde (default 30)", "integer", False, 30),
                ToolParameter("max_chars", "Numar maxim de caractere returnate (default 8000)", "integer", False, 8000),
            ],
            category="web",
            requires_confirmation=False,
        )

    def execute(self, url: str, timeout: int = 30, max_chars: int = 8000, **kwargs) -> ToolResult:
        try:
            import urllib.request
            import urllib.error
            import html

            # Asigura https
            if url.startswith("http://"):
                url = "https://" + url[7:]

            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 (ANA-MAX/1.0)"},
            )
            with urllib.request.urlopen(req, timeout=int(timeout)) as resp:
                raw = resp.read()
                encoding = resp.headers.get_content_charset("utf-8")
                content = raw.decode(encoding, errors="replace")

            # Strip HTML basic
            text = self._html_to_text(content)
            text = text[:int(max_chars)]

            return ToolResult(
                status=ToolStatus.SUCCESS,
                data=text,
                message=f"Descarcat {len(text)} caractere de la {url}",
            )
        except Exception as exc:
            return ToolResult(status=ToolStatus.ERROR, error=f"Eroare fetch {url}: {exc}")

    def _html_to_text(self, html_content: str) -> str:
        """Conversie HTML simpla la text."""
        import html as html_module
        # Sterge script/style
        text = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
        # Inlocuieste tag-uri heading cu newlines
        text = re.sub(r'<h[1-6][^>]*>', '\n## ', text, flags=re.IGNORECASE)
        text = re.sub(r'</h[1-6]>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'<p[^>]*>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'<li[^>]*>', '\n- ', text, flags=re.IGNORECASE)
        # Sterge toate celelalte tag-uri
        text = re.sub(r'<[^>]+>', '', text)
        # Decode HTML entities
        text = html_module.unescape(text)
        # Curata spatii multiple
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r'[ \t]{2,}', ' ', text)
        return text.strip()
