"""
A.N.A. v15.0 - Web Tools
========================
Instrumente pentru cautare web si acces internet.
"""

import logging
from typing import List, Optional, Dict, Any

import warnings
try:
    from ddgs import DDGS  # New package name
    HAS_DDGS = True
except ImportError:
    try:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=RuntimeWarning)
            from duckduckgo_search import DDGS  # Fallback to old name
        HAS_DDGS = True
    except ImportError:
        HAS_DDGS = False

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus

logger = logging.getLogger(__name__)
# Reduce noisy connection errors from duckduckgo_search on startup
logging.getLogger("duckduckgo_search").setLevel(logging.ERROR)
logging.getLogger("duckduckgo_search.DDGS").setLevel(logging.ERROR)
logging.getLogger("duckduckgo_search").propagate = False
logging.getLogger("duckduckgo_search.DDGS").propagate = False


class WebTool(Tool):
    """
    Tool pentru cautare web si acces internet.
    Foloseste DuckDuckGo pentru cautari anonime.
    """
    
    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="web_search",
            description="Cauta informatii pe web folosind DuckDuckGo (anonim).",
            parameters=[
                ToolParameter(
                    name="operation",
                    description="Operatiunea de executat",
                    type="string",
                    required=True,
                    choices=["search", "news", "images"]
                ),
                ToolParameter(
                    name="query",
                    description="Interogarea de cautare",
                    type="string",
                    required=True
                ),
                ToolParameter(
                    name="max_results",
                    description="Numarul maxim de rezultate (implicit: 5)",
                    type="integer",
                    required=False,
                    default=5
                ),
            ],
            category="web",
            requires_confirmation=False
        )
    
    def execute(self, operation: str, query: str, **kwargs) -> ToolResult:
        """Executa operatiunea web."""
        if not HAS_DDGS:
            return ToolResult(
                status=ToolStatus.ERROR,
                error="Biblioteca duckduckgo-search nu este instalata. Ruleaza: pip install duckduckgo-search"
            )
        
        operations = {
            "search": self._search,
            "news": self._news,
            "images": self._images,
        }
        
        if operation not in operations:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Operatiune necunoscuta: {operation}"
            )
        
        return operations[operation](query, **kwargs)
    
    def _search(self, query: str, max_results: int = 5, **kwargs) -> ToolResult:
        """Cautare text pe web."""
        try:
            with DDGS() as ddgs:
                results = []
                for r in ddgs.text(query, max_results=max_results):
                    results.append({
                        "title": r.get("title", ""),
                        "body": r.get("body", ""),
                        "url": r.get("href", "")
                    })
            
            if not results:
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data="Nu am gasit rezultate pentru aceasta cautare.",
                    message="Niciun rezultat"
                )
            
            # Formateaza rezultatele
            formatted = []
            for i, r in enumerate(results, 1):
                formatted.append(f"[{i}] {r['title']}\n{r['body']}\nURL: {r['url']}")
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data="\n\n".join(formatted),
                message=f"Gasite {len(results)} rezultate"
            )
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Eroare la cautare: {e}"
            )
    
    def _news(self, query: str, max_results: int = 5, **kwargs) -> ToolResult:
        """Cautare stiri."""
        try:
            with DDGS() as ddgs:
                results = []
                for r in ddgs.news(query, max_results=max_results):
                    results.append({
                        "title": r.get("title", ""),
                        "body": r.get("body", ""),
                        "url": r.get("url", ""),
                        "date": r.get("date", "")
                    })
            
            if not results:
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data="Nu am gasit stiri pentru aceasta cautare.",
                    message="Niciun rezultat"
                )
            
            formatted = []
            for i, r in enumerate(results, 1):
                formatted.append(f"[{i}] {r['title']} ({r['date']})\n{r['body']}\nURL: {r['url']}")
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data="\n\n".join(formatted),
                message=f"Gasite {len(results)} stiri"
            )
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Eroare la cautare stiri: {e}"
            )
    
    def _images(self, query: str, max_results: int = 5, **kwargs) -> ToolResult:
        """Cautare imagini."""
        try:
            with DDGS() as ddgs:
                results = []
                for r in ddgs.images(query, max_results=max_results):
                    results.append({
                        "title": r.get("title", ""),
                        "url": r.get("image", ""),
                        "source": r.get("source", "")
                    })
            
            if not results:
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data="Nu am gasit imagini pentru aceasta cautare.",
                    message="Niciun rezultat"
                )
            
            formatted = []
            for i, r in enumerate(results, 1):
                formatted.append(f"[{i}] {r['title']}\nURL: {r['url']}\nSursa: {r['source']}")
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data="\n\n".join(formatted),
                message=f"Gasite {len(results)} imagini"
            )
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Eroare la cautare imagini: {e}"
            )


# Functie simpla pentru compatibilitate cu codul vechi
def web_search(query: str, max_results: int = 3) -> str:
    """Functie simpla de cautare web (pentru compatibilitate)."""
    tool = WebTool()
    result = tool.execute("search", query, max_results=max_results)
    return str(result)
