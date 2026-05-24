"""
A.N.A. v18.0 MAX - Base Tool Classes
================================
Clase de baza pentru sistemul de tools.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Type
import concurrent.futures
from enum import Enum
import logging
import inspect
import os

logger = logging.getLogger(__name__)


def _is_vscode_agent_session() -> bool:
    value = os.environ.get("VSCODE_AGENT", "")
    return value.strip().lower() not in {"", "0", "false", "no"}


def _summarize_value(value: Any, max_len: int = 120) -> str:
    """Produce un rezumat scurt si sigur pentru logging."""
    text = repr(value)
    if len(text) > max_len:
        return f"<{type(value).__name__} len={len(text)}>"
    return text


def _summarize_kwargs(kwargs: Dict[str, Any]) -> Dict[str, str]:
    return {key: _summarize_value(value) for key, value in kwargs.items()}


def _compact_error(error: Any, max_len: int = 500) -> str:
    text = str(error or "").replace("\r", " ").replace("\n", " ").strip()
    if len(text) > max_len:
        return text[: max_len - 3] + "..."
    return text


def _is_bool_like(value: Any) -> bool:
    if isinstance(value, bool):
        return True
    if isinstance(value, (int, float)):
        return value in {0, 1}
    if isinstance(value, str):
        return value.strip().lower() in {"1", "0", "true", "false", "yes", "no", "on", "off"}
    return False


def _matches_param_type(value: Any, expected: str) -> bool:
    expected = (expected or "string").lower()
    if value is None or expected == "any":
        return True
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        if isinstance(value, bool):
            return False
        if isinstance(value, int):
            return True
        if isinstance(value, str):
            try:
                int(value.strip())
                return True
            except ValueError:
                return False
        return False
    if expected == "number":
        if isinstance(value, bool):
            return False
        if isinstance(value, (int, float)):
            return True
        if isinstance(value, str):
            try:
                float(value.strip())
                return True
            except ValueError:
                return False
        return False
    if expected == "boolean":
        return _is_bool_like(value)
    if expected in {"array", "list"}:
        return isinstance(value, list)
    if expected in {"object", "dict"}:
        return isinstance(value, dict)
    return True


class ToolStatus(Enum):
    """Status pentru rezultatul unui tool."""
    SUCCESS = "success"
    ERROR = "error"
    REQUIRES_CONFIRMATION = "requires_confirmation"
    BLOCKED = "blocked"


@dataclass
class ToolResult:
    """Rezultatul executiei unui tool."""
    status: ToolStatus
    data: Any = None
    message: str = ""
    error: Optional[str] = None
    
    @property
    def is_success(self) -> bool:
        return self.status == ToolStatus.SUCCESS
    
    def __str__(self) -> str:
        if self.is_success:
            return str(self.data) if self.data else self.message
        return f"Error: {self.error or self.message}"


@dataclass
class ToolParameter:
    """Descrierea unui parametru pentru tool."""
    name: str
    description: str
    type: str = "string"
    required: bool = True
    default: Any = None
    choices: Optional[List[str]] = None


@dataclass
class ToolDefinition:
    """Definitia completa a unui tool pentru AI."""
    name: str
    description: str
    parameters: List[ToolParameter] = field(default_factory=list)
    category: str = "general"
    requires_confirmation: bool = False
    dangerous: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Converteste la dict pentru AI (schema interna)."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                p.name: {
                    "description": p.description,
                    "type": p.type,
                    "required": p.required,
                    "default": p.default,
                    "choices": p.choices
                }
                for p in self.parameters
            }
        }

    def get_ollama_format(self) -> Dict[str, Any]:
        """Converteste la formatul Ollama/OpenAI compatibil."""
        properties = {}
        required = []
        for p in self.parameters:
            properties[p.name] = {
                "type": p.type if p.type != "any" else "string",
                "description": p.description
            }
            if p.choices:
                properties[p.name]["enum"] = p.choices
            if p.required:
                required.append(p.name)

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required
                }
            }
        }


class Tool(ABC):
    """
    Clasa de baza pentru toate tool-urile.
    Fiecare tool trebuie sa implementeze execute() si get_definition().
    """
    
    @abstractmethod
    def get_definition(self) -> ToolDefinition:
        """Returneaza definitia tool-ului."""
        pass
    
    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        """Executa tool-ul cu argumentele date."""
        pass
    
    @property
    def name(self) -> str:
        """Numele tool-ului."""
        return self.get_definition().name
    
    @property
    def requires_confirmation(self) -> bool:
        """Daca necesita confirmare inainte de executie."""
        return self.get_definition().requires_confirmation

    @property
    def run_in_worker_thread(self) -> bool:
        """Whether safe_execute may wrap this tool in a worker thread."""
        return True
    
    def validate_params(self, **kwargs) -> Optional[str]:
        """Valideaza parametrii. Returneaza eroare sau None daca e OK."""
        definition = self.get_definition()
        
        for param in definition.parameters:
            if param.required and param.name not in kwargs:
                return f"Missing required parameter: {param.name}"
            
            if param.choices and param.name in kwargs:
                if kwargs[param.name] not in param.choices:
                    return f"Invalid value for {param.name}: {kwargs[param.name]!r}. Choices: {param.choices}"

            if param.name in kwargs and not _matches_param_type(kwargs[param.name], param.type):
                return f"Invalid type for {param.name}: expected {param.type}, got {type(kwargs[param.name]).__name__}"
        
        return None
    
    def safe_execute(self, **kwargs) -> ToolResult:
        """Executa cu validare si error handling."""
        # Validare parametri
        error = self.validate_params(**kwargs)
        if error:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=error
            )
        
        # Verifica confirmare
        if self.requires_confirmation:
            if not kwargs.get("confirm", False):
                return ToolResult(
                    status=ToolStatus.REQUIRES_CONFIRMATION,
                    message=f"Tool requires confirmation: call {self.name} with confirm=True"
                )
        
        # Executie cu timeout
        timeout = kwargs.get('timeout', 60) # Default 60s
        try:
            if not self.run_in_worker_thread:
                result = self.execute(**kwargs)
                if not isinstance(result, ToolResult):
                    result = ToolResult(status=ToolStatus.SUCCESS, data=result)
                return result

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(self.execute, **kwargs)
                result = future.result(timeout=timeout)
                if not isinstance(result, ToolResult):
                    result = ToolResult(status=ToolStatus.SUCCESS, data=result)
                return result
        except (concurrent.futures.TimeoutError, TimeoutError):
            logger.error(f"Timeout in {self.name} (> {timeout}s)")
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Timeout: {self.name} exceeded {timeout}s"
            )
        except Exception as e:
            logger.error(f"Eroare in {self.name}: {e}")
            return ToolResult(
                status=ToolStatus.ERROR,
                error=_compact_error(e)
            )


class ToolRegistry:
    """
    Registru central pentru toate tool-urile.
    Permite inregistrare dinamica si lookup.
    """
    
    _instance: Optional['ToolRegistry'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._tools: Dict[str, Tool] = {}
            cls._instance._categories: Dict[str, List[str]] = {}
        return cls._instance
    
    def register(self, tool: Tool) -> None:
        """Inregistreaza un tool."""
        definition = tool.get_definition()
        self._tools[definition.name] = tool
        
        # Adauga la categorie
        category = definition.category
        if category not in self._categories:
            self._categories[category] = []
        if definition.name not in self._categories[category]:
            self._categories[category].append(definition.name)
        
        logger.debug(f"Tool inregistrat: {definition.name} ({category})")
    
    def register_function(self, func: Callable, name: Optional[str] = None,
                          description: Optional[str] = None,
                          category: str = "general",
                          requires_confirmation: bool = False) -> None:
        """Inregistreaza o functie simpla ca tool."""
        
        tool_name = name or func.__name__
        tool_desc = description or func.__doc__ or f"Functia {tool_name}"
        
        # Extrage parametrii din semnatura functiei
        sig = inspect.signature(func)
        params = []
        for param_name, param in sig.parameters.items():
            params.append(ToolParameter(
                name=param_name,
                description=f"Parametrul {param_name}",
                required=param.default == inspect.Parameter.empty,
                default=None if param.default == inspect.Parameter.empty else param.default
            ))
        
        # Creeaza un wrapper Tool
        class FunctionTool(Tool):
            def __init__(self, fn, fn_name, fn_desc, fn_params, fn_cat, fn_confirm):
                self._func = fn
                self._name = fn_name
                self._desc = fn_desc
                self._params = fn_params
                self._cat = fn_cat
                self._confirm = fn_confirm
            
            def get_definition(self) -> ToolDefinition:
                return ToolDefinition(
                    name=self._name,
                    description=self._desc,
                    parameters=self._params,
                    category=self._cat,
                    requires_confirmation=self._confirm
                )
            
            def execute(self, **kwargs) -> ToolResult:
                try:
                    result = self._func(**kwargs)
                    return ToolResult(
                        status=ToolStatus.SUCCESS,
                        data=result
                    )
                except Exception as e:
                    return ToolResult(
                        status=ToolStatus.ERROR,
                        error=str(e)
                    )
        
        tool = FunctionTool(func, tool_name, tool_desc, params, category, requires_confirmation)
        self.register(tool)
    
    def get(self, name: str) -> Optional[Tool]:
        """Obtine un tool dupa nume."""
        return self._tools.get(name)
    
    def get_tool(self, name: str) -> Optional[Tool]:
        """Alias pentru get()."""
        return self.get(name)
    
    def execute(self, name: str, **kwargs) -> ToolResult:
        """Executa un tool dupa nume."""
        tool = self.get(name)
        if not tool:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Unknown tool: {name}"
            )

        try:
            from core.license_manager import check_premium_access

            allowed, message = check_premium_access(name)
            if not allowed:
                logger.warning("TOOL BLOCKED name=%s reason=%s", name, message)
                return ToolResult(
                    status=ToolStatus.BLOCKED,
                    message=message,
                    error=message,
                )
        except Exception as exc:
            logger.warning("Premium access check failed for %s: %s", name, exc)
            
        # UI v17: Rich Feedback. Disabled by default for agent-friendly output.
        if os.environ.get("ANA_TOOL_STDOUT", "").strip().lower() in {"1", "true", "yes", "on"}:
            try:
                from rich.console import Console
                from rich.panel import Panel
                console = Console()
                clean_params = {k: (v if len(str(v)) < 100 else f"<{type(v).__name__} len={len(str(v))}>") for k, v in kwargs.items()}
                console.print(Panel(
                    f"[bold cyan]Tool execution:[/bold cyan] [bold yellow]{name}[/bold yellow]\n[dim]Params: {clean_params}[/dim]",
                    border_style="blue",
                    padding=(0, 2)
                ))
            except (ImportError, UnicodeEncodeError, OSError):
                pass
            
        logger.info("TOOL START name=%s args=%s", name, _summarize_kwargs(kwargs))
        result = tool.safe_execute(**kwargs)
        if result.is_success:
            logger.info(
                "TOOL END name=%s status=%s message=%s",
                name,
                result.status.value,
                _summarize_value(result.message or result.data),
            )
        else:
            logger.warning(
                "TOOL END name=%s status=%s error=%s",
                name,
                result.status.value,
                _summarize_value(result.error or result.message),
            )
        return result
    
    def list_tools(self, category: Optional[str] = None) -> List[str]:
        """Listeaza toate tool-urile (optional filtrate pe categorie)."""
        if category:
            return self._categories.get(category, [])
        return list(self._tools.keys())
    
    def list_categories(self) -> List[str]:
        """Listeaza toate categoriile."""
        return list(self._categories.keys())

    def reset(self) -> None:
        """Reseteaza registrul pentru un nou runtime."""
        self._tools = {}
        self._categories = {}
    
    def get_all_definitions(self) -> List[Dict[str, Any]]:
        """Obtine definitiile tuturor tool-urilor (pentru AI)."""
        return [
            tool.get_definition().to_dict()
            for tool in self._tools.values()
        ]
    
    def get_tools_for_ai(self) -> List[Callable]:
        """Returneaza functiile pentru AI tool calling."""
        functions = []
        for tool in self._tools.values():
            def make_wrapper(t):
                def wrapper(**kwargs):
                    result = t.safe_execute(**kwargs)
                    return str(result)
                wrapper.__name__ = t.name
                wrapper.__doc__ = t.get_definition().description
                return wrapper
            functions.append(make_wrapper(tool))
        return functions


# Singleton pentru acces global
registry = ToolRegistry()
