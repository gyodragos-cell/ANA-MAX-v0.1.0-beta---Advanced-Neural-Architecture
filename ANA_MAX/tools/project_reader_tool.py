"""
ANA MAX - Project Reader Tool
==============================
Citeste tot proiectul ANA (ana-manus) - asta e "magia"
Suporta: .py, .json, .md, .tt si toate formatele din proiect
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus

logger = logging.getLogger(__name__)


class ProjectReaderTool(Tool):
    """
    Tool care citeste tot proiectul ANA.
    "Magia" - intelege structura completa a proiectului.
    """

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="project_reader",
            description="Read entire ANA project structure and content. 'Magia' - understands complete project structure. Supports .py, .json, .md, .tt and all formats.",
            parameters=[
                ToolParameter(
                    name="project_path",
                    description="Path to ANA project (default: C:\\Users\\billy\\Desktop\\ana-manus)",
                    type="string",
                    required=False
                ),
                ToolParameter(
                    name="file_types",
                    description="File types to read (default: .py,.json,.md,.tt,.yaml,.txt)",
                    type="string",
                    required=False
                ),
                ToolParameter(
                    name="max_files",
                    description="Maximum files to read (default: 100)",
                    type="integer",
                    required=False
                ),
                ToolParameter(
                    name="output_file",
                    description="Optional path to save project summary",
                    type="string",
                    required=False
                )
            ],
            category="analysis"
        )

    def execute(self, **kwargs) -> ToolResult:
        project_path = kwargs.get("project_path", r"C:\Users\billy\Desktop\ana-manus")
        file_types_str = kwargs.get("file_types", ".py,.json,.md,.tt,.yaml,.txt")
        max_files = kwargs.get("max_files", 100)
        output_file = kwargs.get("output_file")

        try:
            base_dir = Path(project_path)
            if not base_dir.exists():
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error=f"Project path not found: {project_path}"
                )

            # Parse file types
            file_types = [ft.strip() for ft in file_types_str.split(",")]

            # Citim proiectul
            project_data = self._read_project(base_dir, file_types, max_files)

            # Generam summary
            summary = self._generate_summary(project_data)

            # Salvam daca necesar
            if output_file:
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(project_data, f, indent=2, default=str)

            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={
                    "project_data": project_data,
                    "summary": summary,
                    "project_path": str(base_dir),
                    "files_read": len(project_data["files"])
                },
                message=f"Project read successfully: {len(project_data['files'])} files processed"
            )

        except Exception as e:
            logger.exception("Project reading failed")
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Project reading failed: {e}"
            )

    def _read_project(self, base_dir: Path, file_types: List[str], max_files: int) -> Dict[str, Any]:
        """Citeste tot proiectul."""
        project_data = {
            "timestamp": datetime.now().isoformat(),
            "project_path": str(base_dir),
            "files": [],
            "structure": {},
            "stats": {
                "total_files": 0,
                "by_type": {},
                "total_size": 0
            }
        }

        file_count = 0

        # Excludem directoare care nu ne intereseaza
        exclude_dirs = {
            "venv", "venv_corrupted", "__pycache__", ".git",
            "node_modules", "archives", "sandbox", "logs"
        }

        for root, dirs, files in os.walk(base_dir):
            # Filtram directoare
            dirs[:] = [d for d in dirs if d not in exclude_dirs]

            for file in files:
                if file_count >= max_files:
                    break

                file_path = Path(root) / file
                file_ext = file_path.suffix.lower()

                if file_ext in file_types:
                    try:
                        content = self._read_file_content(file_path)
                        relative_path = file_path.relative_to(base_dir)

                        file_info = {
                            "path": str(relative_path),
                            "absolute_path": str(file_path),
                            "type": file_ext,
                            "size": file_path.stat().st_size,
                            "content": content,
                            "language": self._detect_language(file_ext)
                        }

                        project_data["files"].append(file_info)
                        project_data["stats"]["total_files"] += 1
                        project_data["stats"]["total_size"] += file_path.stat().st_size
                        project_data["stats"]["by_type"][file_ext] = project_data["stats"]["by_type"].get(file_ext, 0) + 1

                        # Adaugam la structura
                        self._add_to_structure(project_data["structure"], relative_path, file_info)

                        file_count += 1

                    except Exception as e:
                        logger.warning(f"Failed to read {file_path}: {e}")

        return project_data

    def _read_file_content(self, file_path: Path) -> str:
        """Citeste continutul fisierului."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            # Pentru fisiere mari, returnam doar inceputul
            if len(content) > 10000:
                return content[:10000] + "\n\n... [TRUNCATED - File too large] ..."

            return content
        except Exception as e:
            return f"[ERROR READING FILE: {e}]"

    def _detect_language(self, file_ext: str) -> str:
        """Detecteaza limbajul dupa extensie."""
        language_map = {
            ".py": "python",
            ".json": "json",
            ".md": "markdown",
            ".tt": "template",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".txt": "text",
            ".js": "javascript",
            ".ts": "typescript",
            ".html": "html",
            ".css": "css",
            ".bat": "batch",
            ".ps1": "powershell"
        }
        return language_map.get(file_ext, "unknown")

    def _add_to_structure(self, structure: Dict, relative_path: Path, file_info: Dict):
        """Adauga fisier la structura de directoare."""
        parts = relative_path.parts
        current = structure

        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]

        current[parts[-1]] = file_info

    def _generate_summary(self, project_data: Dict) -> str:
        """Genereaza summary simplu."""
        stats = project_data["stats"]

        summary = f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    ANA PROJECT READER - PROJECT SUMMARY                          ║
╚══════════════════════════════════════════════════════════════════════════════╝

📁 PROJECT PATH: {project_data['project_path']}
📅 TIMESTAMP: {project_data['timestamp']}

📊 STATISTICS:
• Total Files: {stats['total_files']}
• Total Size: {stats['total_size'] / 1024 / 1024:.2f} MB

📝 FILES BY TYPE:
"""
        for file_type, count in sorted(stats['by_type'].items()):
            summary += f"• {file_type}: {count} files\n"

        summary += f"""
🔍 STRUCTURE OVERVIEW:
{self._format_structure(project_data['structure'], level=0)}

╔══════════════════════════════════════════════════════════════════════════════╗
║                        ℹ️  THIS IS "THE MAGIC"                                  ║
║  Complete project understanding - agents can see everything                  ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
        return summary

    def _format_structure(self, structure: Dict, level: int) -> str:
        """Formateaza structura pentru display."""
        output = ""
        indent = "  " * level

        for key, value in structure.items():
            if isinstance(value, dict):
                output += f"{indent}📁 {key}/\n"
                output += self._format_structure(value, level + 1)
            else:
                output += f"{indent}📄 {key} ({value.get('language', 'unknown')})\n"

        return output


class ProjectAnalyzerTool(Tool):
    """
    Tool care analizeaza proiectul si gaseste patterns.
    "Intelege magia" - detecteaza patterns in cod.
    """

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="project_analyzer",
            description="Analyze ANA project and detect patterns. 'Intelege magia' - detect patterns in code.",
            parameters=[
                ToolParameter(
                    name="project_data",
                    description="Project data from project_reader (optional, will read if not provided)",
                    type="object",
                    required=False
                ),
                ToolParameter(
                    name="analyze_imports",
                    description="Analyze import patterns (default: true)",
                    type="boolean",
                    required=False
                ),
                ToolParameter(
                    name="analyze_functions",
                    description="Analyze function patterns (default: true)",
                    type="boolean",
                    required=False
                )
            ],
            category="analysis"
        )

    def execute(self, **kwargs) -> ToolResult:
        project_data = kwargs.get("project_data")
        analyze_imports = kwargs.get("analyze_imports", True)
        analyze_functions = kwargs.get("analyze_functions", True)

        try:
            # Daca nu avem project_data, citim proiectul
            if not project_data:
                reader = ProjectReaderTool()
                reader_result = reader.execute()
                if reader_result.status != ToolStatus.SUCCESS:
                    return ToolResult(
                        status=ToolStatus.ERROR,
                        error="Failed to read project for analysis"
                    )
                project_data = reader_result.data["project_data"]

            # Analizam
            analysis = {
                "timestamp": datetime.now().isoformat(),
                "patterns": {}
            }

            if analyze_imports:
                analysis["patterns"]["imports"] = self._analyze_imports(project_data)

            if analyze_functions:
                analysis["patterns"]["functions"] = self._analyze_functions(project_data)

            return ToolResult(
                status=ToolStatus.SUCCESS,
                data=analysis,
                message="Project analysis completed successfully"
            )

        except Exception as e:
            logger.exception("Project analysis failed")
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Analysis failed: {e}"
            )

    def _analyze_imports(self, project_data: Dict) -> Dict:
        """Analizeaza import patterns."""
        import_patterns = {
            "common_imports": {},
            "external_dependencies": set(),
            "internal_dependencies": set()
        }

        for file_info in project_data["files"]:
            if file_info["type"] == ".py":
                content = file_info["content"]
                lines = content.split("\n")

                for line in lines:
                    line = line.strip()
                    if line.startswith("import ") or line.startswith("from "):
                        # Extragem import
                        if line.startswith("from "):
                            parts = line.split(" ")
                            if len(parts) >= 2:
                                module = parts[1]
                                if "." in module:
                                    import_patterns["external_dependencies"].add(module.split(".")[0])
                                else:
                                    import_patterns["common_imports"][module] = import_patterns["common_imports"].get(module, 0) + 1

        # Convertim set in list pentru JSON
        import_patterns["external_dependencies"] = list(import_patterns["external_dependencies"])
        import_patterns["internal_dependencies"] = list(import_patterns["internal_dependencies"])

        return import_patterns

    def _analyze_functions(self, project_data: Dict) -> Dict:
        """Analizeaza function patterns."""
        function_patterns = {
            "total_functions": 0,
            "by_file": {},
            "common_names": {}
        }

        for file_info in project_data["files"]:
            if file_info["type"] == ".py":
                content = file_info["content"]
                functions = self._extract_functions(content)

                if functions:
                    function_patterns["total_functions"] += len(functions)
                    function_patterns["by_file"][file_info["path"]] = len(functions)

                    for func in functions:
                        func_name = func["name"]
                        function_patterns["common_names"][func_name] = function_patterns["common_names"].get(func_name, 0) + 1

        return function_patterns

    def _extract_functions(self, content: str) -> List[Dict]:
        """Extrage functii din cod Python."""
        functions = []
        lines = content.split("\n")

        for i, line in enumerate(lines):
            line = line.strip()
            if line.startswith("def ") or line.startswith("async def "):
                func_name = line.split("(")[0].replace("def ", "").replace("async def ", "")
                functions.append({
                    "name": func_name,
                    "line": i + 1,
                    "signature": line
                })

        return functions


class ProjectSearchTool(Tool):
    """
    Tool care cauta in proiect.
    "Gaseste in toata magia" - search complet.
    """

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="project_search",
            description="Search across entire ANA project. 'Gaseste in toata magia' - complete search.",
            parameters=[
                ToolParameter(
                    name="search_term",
                    description="Term to search for",
                    type="string",
                    required=True
                ),
                ToolParameter(
                    name="project_path",
                    description="Path to ANA project (default: C:\\Users\\billy\\Desktop\\ana-manus)",
                    type="string",
                    required=False
                ),
                ToolParameter(
                    name="file_types",
                    description="File types to search (default: .py,.json,.md,.tt)",
                    type="string",
                    required=False
                )
            ],
            category="analysis"
        )

    def execute(self, **kwargs) -> ToolResult:
        search_term = kwargs.get("search_term")
        project_path = kwargs.get("project_path", r"C:\Users\billy\Desktop\ana-manus")
        file_types_str = kwargs.get("file_types", ".py,.json,.md,.tt")

        if not search_term:
            return ToolResult(
                status=ToolStatus.ERROR,
                error="search_term is required"
            )

        try:
            base_dir = Path(project_path)
            file_types = [ft.strip() for ft in file_types_str.split(",")]

            results = self._search_project(base_dir, search_term, file_types)

            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={
                    "search_term": search_term,
                    "results": results,
                    "total_matches": len(results)
                },
                message=f"Found {len(results)} matches for '{search_term}'"
            )

        except Exception as e:
            logger.exception("Project search failed")
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Search failed: {e}"
            )

    def _search_project(self, base_dir: Path, search_term: str, file_types: List[str]) -> List[Dict]:
        """Cauta in proiect."""
        results = []
        search_lower = search_term.lower()

        exclude_dirs = {
            "venv", "venv_corrupted", "__pycache__", ".git",
            "node_modules", "archives", "sandbox", "logs"
        }

        for root, dirs, files in os.walk(base_dir):
            dirs[:] = [d for d in dirs if d not in exclude_dirs]

            for file in files:
                file_path = Path(root) / file
                file_ext = file_path.suffix.lower()

                if file_ext in file_types:
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()

                        if search_lower in content.lower():
                            lines = content.split("\n")
                            matches = []

                            for i, line in enumerate(lines):
                                if search_lower in line.lower():
                                    matches.append({
                                        "line": i + 1,
                                        "content": line.strip()[:100]
                                    })

                            if matches:
                                results.append({
                                    "file": str(file_path.relative_to(base_dir)),
                                    "matches": matches
                                })

                    except Exception as e:
                        logger.warning(f"Failed to search {file_path}: {e}")

        return results
