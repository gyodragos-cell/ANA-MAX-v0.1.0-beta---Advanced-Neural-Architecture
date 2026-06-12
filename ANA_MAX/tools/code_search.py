"""
Code Search Tool - Advanced Code Search & Analysis
Author: ANA_MAX
Date: 2026-05-12
Category: development

Functions:
- grep: Search with regex support
- search_symbol: Find function/class definitions
- find_usages: Where is a symbol used
- semantic_search: NLP-based code search
- search_imports: Find import statements
- count_matches: Count occurrences

Requires: sentence-transformers (optional for semantic)
"""

from __future__ import annotations

import re
import os
import logging
from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path
from collections import defaultdict

from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus

logger = logging.getLogger(__name__)


class CodeSearchTool(Tool):
    """Tool pentru cautare avansata in cod."""

    def __init__(self) -> None:
        self._semantic_available = self._check_semantic()

    def _check_semantic(self) -> bool:
        """Verifica daca sentence-transformers e disponibil."""
        try:
            from sentence_transformers import SentenceTransformer
            return True
        except ImportError:
            return False

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="code_search",
            description="Cautare avansata in cod: grep cu regex, symbol lookup, find usages, semantic search, count.",
            parameters=[
                ToolParameter(
                    name="operation",
                    description="Operatia de executat",
                    type="string",
                    required=True,
                    choices=[
                        "grep", "search_symbol", "find_usages",
                        "semantic_search", "search_imports", "count",
                        "list_files", "search_codebase"
                    ],
                ),
                ToolParameter(
                    name="path",
                    description="Director sau fisier pentru cautare",
                    type="string",
                    required=True,
                    default=".",
                ),
                ToolParameter(
                    name="pattern",
                    description="Pattern pentru cautare (regex pentru grep)",
                    type="string",
                    required=False,
                    default="",
                ),
                ToolParameter(
                    name="file_type",
                    description="Tip de fisier (ex: .py, .js, .java)",
                    type="string",
                    required=False,
                    default="*",
                ),
                ToolParameter(
                    name="context",
                    description="Numar linii context (inainte si dupa)",
                    type="integer",
                    required=False,
                    default=0,
                ),
                ToolParameter(
                    name="case_sensitive",
                    description="Cautare case-sensitive",
                    type="boolean",
                    required=False,
                    default=False,
                ),
                ToolParameter(
                    name="max_results",
                    description="Numar maxim de rezultate",
                    type="integer",
                    required=False,
                    default=100,
                ),
                ToolParameter(
                    name="whole_word",
                    description="Cauta doar cuvant intreg",
                    type="boolean",
                    required=False,
                    default=False,
                ),
            ],
            category="development",
            requires_confirmation=False,
        )

    def execute(self, **kwargs) -> ToolResult:
        operation = kwargs.get("operation", "")
        path = kwargs.get("path", ".")
        pattern = kwargs.get("pattern", "")
        file_type = kwargs.get("file_type", "*")
        context = int(kwargs.get("context", 0))
        case_sensitive = bool(kwargs.get("case_sensitive", False))
        max_results = int(kwargs.get("max_results", 100))
        whole_word = bool(kwargs.get("whole_word", False))

        operations = {
            "grep": self._grep,
            "search_symbol": self._search_symbol,
            "find_usages": self._find_usages,
            "semantic_search": self._semantic_search,
            "search_imports": self._search_imports,
            "count": self._count,
            "list_files": self._list_files,
            "search_codebase": self._search_codebase,
        }

        if operation not in operations:
            return ToolResult(status=ToolStatus.ERROR, error=f"Operatie necunoscuta: {operation}")

        try:
            return operations[operation](path, pattern, file_type, context, case_sensitive, max_results, whole_word, kwargs)
        except Exception as e:
            logger.error(f"Code search error: {e}")
            return ToolResult(status=ToolStatus.ERROR, error=str(e))

    def _grep(self, path: str, pattern: str, file_type: str, context: int, case_sensitive: bool, max_results: int, whole_word: bool, kwargs: Dict) -> ToolResult:
        """Cautare cu regex."""
        if not pattern:
            return ToolResult(status=ToolStatus.ERROR, error="Pattern este obligatoriu")

        if not os.path.exists(path):
            return ToolResult(status=ToolStatus.ERROR, error=f"Path nu exista: {path}")

        flags = 0 if case_sensitive else re.IGNORECASE
        if whole_word:
            pattern = r'\b' + re.escape(pattern) + r'\b'

        try:
            regex = re.compile(pattern, flags)
        except re.error as e:
            return ToolResult(status=ToolStatus.ERROR, error=f"Regex invalid: {e}")

        results = []
        is_dir = os.path.isdir(path)
        search_path = path if is_dir else os.path.dirname(path)
        file_pattern = f"**/*{file_type}" if is_dir else os.path.basename(path)

        files = list(Path(search_path).glob(file_pattern)) if is_dir else [Path(path)]
        
        for file_path in files:
            if not file_path.is_file():
                continue
                
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()
                    
                for i, line in enumerate(lines, 1):
                    if regex.search(line):
                        match = regex.search(line)
                        start = max(0, match.start() - context * 50)
                        end = min(len(line), match.end() + context * 50)
                        
                        results.append({
                            "file": str(file_path),
                            "line": i,
                            "content": line.strip(),
                            "column": match.start()
                        })
                        
                        if len(results) >= max_results:
                            break
                            
            except Exception:
                continue

        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={
                "count": len(results),
                "pattern": pattern,
                "results": results
            },
            message=f"Gasite {len(results)} potriviri pentru '{pattern}'"
        )

    def _search_symbol(self, path: str, pattern: str, file_type: str, context: int, case_sensitive: bool, max_results: int, whole_word: bool, kwargs: Dict) -> ToolResult:
        """Cauta definitii de functii, clase."""
        if not pattern:
            return ToolResult(status=ToolStatus.ERROR, error="Pattern este obligatoriu")

        if not os.path.exists(path):
            return ToolResult(status=ToolStatus.ERROR, error=f"Path nu exista: {path}")

        # Patterns for different languages
        symbol_patterns = {
            "py": [
                r'^class\s+(\w+)',
                r'^def\s+(\w+)\s*\(',
                r'^async\s+def\s+(\w+)',
                r'^class\s+(\w+)\s*[\(:]',
            ],
            "js": [
                r'function\s+(\w+)',
                r'const\s+(\w+)\s*=',
                r'let\s+(\w+)\s*=',
                r'class\s+(\w+)',
                r'=>',
            ],
            "ts": [
                r'function\s+(\w+)',
                r'const\s+(\w+)\s*=',
                r'class\s+(\w+)',
                r'interface\s+(\w+)',
                r'type\s+(\w+)\s*=',
            ],
            "java": [
                r'public\s+class\s+(\w+)',
                r'private\s+class\s+(\w+)',
                r'class\s+(\w+)',
                r'public\s+\w+\s+(\w+)\s*\(',
            ],
            "go": [
                r'func\s+(\w+)',
                r'type\s+(\w+)\s+struct',
                r'type\s+(\w+)\s+interface',
            ],
            "cpp": [
                r'\w+\s+(\w+)\s*\(',
                r'class\s+(\w+)',
                r'struct\s+(\w+)',
            ],
            "c": [
                r'\w+\s+(\w+)\s*\(',
                r'#define\s+(\w+)',
            ],
            "rb": [
                r'def\s+(\w+)',
                r'class\s+(\w+)',
                r'module\s+(\w+)',
            ],
            "rs": [
                r'fn\s+(\w+)',
                r'struct\s+(\w+)',
                r'impl\s+(\w+)',
            ],
        }

        results = []
        is_dir = os.path.isdir(path)
        search_path = path if is_dir else os.path.dirname(path)
        
        ext = file_type.lstrip(".")
        
        for file_path in Path(search_path).rglob(f"*.{ext}" if ext else "*"):
            if not file_path.is_file():
                continue
                
            file_ext = file_path.suffix.lstrip(".")
            patterns = symbol_patterns.get(file_ext, [r'(\w+)\s*\('])
            
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    for i, line in enumerate(f, 1):
                        for pattern_item in patterns:
                            matches = re.findall(pattern_item, line, re.MULTILINE)
                            for match in matches:
                                if pattern.lower() in str(match).lower():
                                    results.append({
                                        "file": str(file_path),
                                        "line": i,
                                        "name": match if isinstance(match, str) else match[0] if match else "",
                                        "definition": line.strip(),
                                        "type": file_ext
                                    })
                                    
                                    if len(results) >= max_results:
                                        break
            except Exception:
                continue

        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={
                "count": len(results),
                "pattern": pattern,
                "symbols": results
            },
            message=f"Gasite {len(results)} simboluri pentru '{pattern}'"
        )

    def _find_usages(self, path: str, pattern: str, file_type: str, context: int, case_sensitive: bool, max_results: int, whole_word: bool, kwargs: Dict) -> ToolResult:
        """Gaseste unde e folosit un simbol."""
        if not pattern:
            return ToolResult(status=ToolStatus.ERROR, error="Pattern este obligatoriu")

        if whole_word:
            pattern = r'\b' + re.escape(pattern) + r'\b'
        
        return self._grep(path, pattern, file_type, context, case_sensitive, max_results, False, kwargs)

    def _semantic_search(self, path: str, query: str, file_type: str, context: int, case_sensitive: bool, max_results: int, whole_word: bool, kwargs: Dict) -> ToolResult:
        """Cautare NLP (daca e disponibil sentence-transformers)."""
        if not self._semantic_available:
            return ToolResult(
                status=ToolStatus.ERROR,
                error="Semantic search necesita: pip install sentence-transformers"
            )

        if not query:
            return ToolResult(status=ToolStatus.ERROR, error="Query este obligatoriu")

        if not os.path.exists(path):
            return ToolResult(status=ToolStatus.ERROR, error=f"Path nu exista: {path}")

        try:
            from sentence_transformers import SentenceTransformer
            from sklearn.metrics.pairwise import cosine_similarity
            import numpy as np

            model = SentenceTransformer('all-MiniLM-L6-v2')
            
            # Index all files
            documents = []
            file_map = {}
            
            search_path = Path(path)
            for file_path in search_path.rglob(f"*{file_type}"):
                if not file_path.is_file():
                    continue
                    
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                        # Chunk content
                        chunks = [content[i:i+500] for i in range(0, min(len(content), 5000), 500)]
                        for chunk in chunks:
                            documents.append(chunk)
                            file_map[len(documents) - 1] = str(file_path)
                except Exception:
                    continue

            if not documents:
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data={"count": 0, "results": []},
                    message="Nu s-au gasit fisiere"
                )

            # Encode query and documents
            query_embedding = model.encode([query])
            doc_embeddings = model.encode(documents)
            
            # Calculate similarities
            similarities = cosine_similarity(query_embedding, doc_embeddings)[0]
            
            # Get top results
            top_indices = np.argsort(similarities)[::-1][:max_results]
            
            results = []
            for idx in top_indices:
                if similarities[idx] > 0.3:
                    results.append({
                        "file": file_map.get(idx, "unknown"),
                        "score": float(similarities[idx]),
                        "content": documents[idx][:200]
                    })

            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={
                    "count": len(results),
                    "query": query,
                    "results": results
                },
                message=f"Semantic search: {len(results)} rezultate"
            )
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=f"Semantic search failed: {e}")

    def _search_imports(self, path: str, pattern: str, file_type: str, context: int, case_sensitive: bool, max_results: int, whole_word: bool, kwargs: Dict) -> ToolResult:
        """Cauta statement-uri de import."""
        if not pattern:
            return ToolResult(status=ToolStatus.ERROR, error="Pattern este obligatoriu")

        import_patterns = {
            "py": [
                r'^import\s+(\w+)',
                r'^from\s+([\w.]+)\s+import',
            ],
            "js": [
                r"require\s*\(\s*['\"]([^'\"]+)['\"]\s*\)",
                r"import\s+.*\s+from\s+['\"]([^'\"]+)['\"]",
            ],
            "ts": [
                r"import\s+.*\s+from\s+['\"]([^'\"]+)['\"]",
                r"export\s+from\s+['\"]([^'\"]+)['\"]",
            ],
            "go": [
                r'"([^"]+)"',
            ],
            "java": [
                r'import\s+([\w.]+);',
            ],
        }

        results = []
        is_dir = os.path.isdir(path)
        search_path = path if is_dir else os.path.dirname(path)
        
        ext = file_type.lstrip(".") or "py"
        
        for file_path in Path(search_path).rglob(f"*.{ext}"):
            if not file_path.is_file():
                continue
                
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    for i, line in enumerate(f, 1):
                        patterns = import_patterns.get(ext, [])
                        for pat in patterns:
                            matches = re.findall(pat, line)
                            for match in matches:
                                if pattern.lower() in str(match).lower():
                                    results.append({
                                        "file": str(file_path),
                                        "line": i,
                                        "import": match,
                                        "content": line.strip()
                                    })
            except Exception:
                continue

        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={
                "count": len(results),
                "results": results
            },
            message=f"Gasite {len(results)} imports"
        )

    def _count(self, path: str, pattern: str, file_type: str, context: int, case_sensitive: bool, max_results: int, whole_word: bool, kwargs: Dict) -> ToolResult:
        """Numara aparitiile unui pattern."""
        if not pattern:
            return ToolResult(status=ToolStatus.ERROR, error="Pattern este obligatoriu")

        if not os.path.exists(path):
            return ToolResult(status=ToolStatus.ERROR, error=f"Path nu exista: {path}")

        flags = 0 if case_sensitive else re.IGNORECASE
        if whole_word:
            pattern = r'\b' + re.escape(pattern) + r'\b'

        try:
            regex = re.compile(pattern, flags)
        except re.error as e:
            return ToolResult(status=ToolStatus.ERROR, error=f"Regex invalid: {e}")

        counts = defaultdict(int)
        total = 0
        
        search_path = Path(path)
        for file_path in search_path.rglob(f"*{file_type}"):
            if not file_path.is_file():
                continue
                
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    count = len(regex.findall(content))
                    if count > 0:
                        counts[str(file_path)] = count
                        total += count
            except Exception:
                continue

        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={
                "total": total,
                "by_file": dict(counts)
            },
            message=f"'{pattern}' gasit de {total} ori"
        )

    def _list_files(self, path: str, pattern: str, file_type: str, context: int, case_sensitive: bool, max_results: int, whole_word: bool, kwargs: Dict) -> ToolResult:
        """Listeaza fisierele care contin un pattern."""
        if not os.path.exists(path):
            return ToolResult(status=ToolStatus.ERROR, error=f"Path nu exista: {path}")

        pattern_input = pattern or "."
        
        results = []
        search_path = Path(path)
        
        for file_path in search_path.rglob(f"*{file_type}"):
            if not file_path.is_file():
                continue
                
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    
                if pattern_input != ".":
                    flags = 0 if case_sensitive else re.IGNORECASE
                    if not re.search(pattern_input, content, flags):
                        continue
                        
                results.append({
                    "file": str(file_path),
                    "size": os.path.getsize(file_path),
                    "lines": content.count('\n') + 1
                })
            except Exception:
                continue

        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={
                "count": len(results),
                "files": results[:max_results]
            },
            message=f"Gasite {len(results)} fisiere"
        )

    def _search_codebase(self, path: str, query: str, file_type: str, context: int, case_sensitive: bool, max_results: int, whole_word: bool, kwargs: Dict) -> ToolResult:
        """Alias pentru semantic_search."""
        return self._semantic_search(path, query, file_type, context, case_sensitive, max_results, whole_word, kwargs)


def smoke_test():
    """Smoke test pentru Code Search tool."""
    print("[*] Testing Code Search Tool...")
    
    tool = CodeSearchTool()
    
    # Test list files
    result = tool.execute(operation="list_files", path="tools", file_type=".py")
    if result.is_success:
        print(f"[OK] Found {result.data.get('count', 0)} Python files in tools/")
    else:
        print(f"[!] List files: {result.error}")
    
    # Test grep
    result = tool.execute(operation="grep", path="tools", pattern="class Tool", file_type=".py")
    if result.is_success:
        print(f"[OK] Grep found {result.data.get('count', 0)} matches for 'class Tool'")
    else:
        print(f"[!] Grep: {result.error}")
    
    # Check semantic availability
    print(f"[*] Semantic search: {'Available' if tool._semantic_available else 'Not installed'}")
    
    print("[*] Code Search smoke test complete")


if __name__ == "__main__":
    smoke_test()