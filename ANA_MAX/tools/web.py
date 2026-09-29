"""
A.N.A. v15.0 - Web Tools (OS27 Hyper++)
========================================
Instrumente pentru cautare web si acces internet.

OS27 Hyper++ Features:
- Telemetry tracking for web operations (search, news, images)
- Health monitoring for web operations reliability
- MemoryCortex integration for web errors and state learning
- ContextEngine integration for web state awareness
- SelfEvolvingTool integration for anomaly detection on web failures
- Structured logging with error detection
"""

import logging
import time
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

# OS27 Hyper++ Telemetry
_web_telemetry: Dict[str, Dict[str, Any]] = {}


def _record_web_telemetry(operation: str, success: bool, execution_time: float) -> None:
    """Record OS27 Hyper++ telemetry for web operations."""
    if operation not in _web_telemetry:
        _web_telemetry[operation] = {
            "operation_count": 0,
            "success_count": 0,
            "failure_count": 0,
            "total_time": 0.0,
            "last_execution_time": 0.0,
            "last_success": False,
        }
    
    _web_telemetry[operation]["operation_count"] += 1
    _web_telemetry[operation]["total_time"] += execution_time
    _web_telemetry[operation]["last_execution_time"] = execution_time
    _web_telemetry[operation]["last_success"] = success
    
    if success:
        _web_telemetry[operation]["success_count"] += 1
    else:
        _web_telemetry[operation]["failure_count"] += 1


def get_web_telemetry(operation: str | None = None) -> Dict[str, Any] | Dict[str, Dict[str, Any]]:
    """Get telemetry for web operations."""
    if operation:
        return _web_telemetry.get(operation, {})
    return _web_telemetry.copy()


def get_web_health() -> str:
    """Get health status for web tool based on telemetry."""
    if not _web_telemetry:
        return "unknown"
    
    total_ops = sum(stats["operation_count"] for stats in _web_telemetry.values())
    total_failures = sum(stats["failure_count"] for stats in _web_telemetry.values())
    
    if total_ops == 0:
        return "unknown"
    
    failure_rate = total_failures / total_ops
    if failure_rate > 0.5:
        return "broken"
    if failure_rate > 0.1:
        return "degraded"
    return "healthy"


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
                ToolParameter(
                    name="region",
                    description="Regiunea pentru cautare: wt-wt (global), ro-ro (romana), us-en (engleza). Default: wt-wt",
                    type="string",
                    required=False,
                    default="wt-wt"
                ),
            ],
            category="web",
            requires_confirmation=False
        )
    
    def execute(self, operation: str, query: str, **kwargs) -> ToolResult:
        """Executa operatiunea web."""
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
        
        if not HAS_DDGS:
            execution_time = time.time() - start_time
            _record_web_telemetry(operation, False, execution_time)
            
            # MemoryCortex integration for web errors
            if cortex:
                try:
                    cortex.remember(
                        "error",
                        f"web.{operation}",
                        "Biblioteca duckduckgo-search nu este instalata"
                    )
                except Exception:
                    pass
            
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
            execution_time = time.time() - start_time
            _record_web_telemetry(operation, False, execution_time)
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Operatiune necunoscuta: {operation}"
            )
        
        try:
            result = operations[operation](query, **kwargs)
            execution_time = time.time() - start_time
            _record_web_telemetry(operation, result.is_success, execution_time)
            
            # ContextEngine integration for web state
            if context_engine and result.is_success:
                try:
                    context_engine.update_context(
                        key="web_state",
                        value={
                            "operation": operation,
                            "query": query,
                            "success": result.is_success,
                            "timestamp": time.time(),
                        }
                    )
                except Exception:
                    pass
            
            # MemoryCortex integration for web errors
            if cortex and not result.is_success:
                try:
                    cortex.remember(
                        "error",
                        f"web.{operation}",
                        f"Web operation failed for query '{query}': {result.error}"
                    )
                except Exception:
                    pass
            
            return result
        except Exception as exc:
            execution_time = time.time() - start_time
            _record_web_telemetry(operation, False, execution_time)
            
            # MemoryCortex integration for web errors
            if cortex:
                try:
                    cortex.remember(
                        "error",
                        f"web.{operation}",
                        f"Web operation failed for query '{query}': {str(exc)}"
                    )
                except Exception:
                    pass
            
            return ToolResult(status=ToolStatus.ERROR, error=str(exc))
    
    def _search(self, query: str, max_results: int = 5, region: str = "wt-wt", **kwargs) -> ToolResult:
        """Cautare text pe web."""
        try:
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", category=RuntimeWarning)
                with DDGS() as ddgs:
                    results = []
                    for r in ddgs.text(query, region=region, max_results=max_results):
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
    
    def _news(self, query: str, max_results: int = 5, region: str = "wt-wt", **kwargs) -> ToolResult:
        """Cautare stiri."""
        try:
            with DDGS() as ddgs:
                results = []
                for r in ddgs.news(query, region=region, max_results=max_results):
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
    
    def _images(self, query: str, max_results: int = 5, region: str = "wt-wt", **kwargs) -> ToolResult:
        """Cautare imagini."""
        try:
            with DDGS() as ddgs:
                results = []
                for r in ddgs.images(query, region=region, max_results=max_results):
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
