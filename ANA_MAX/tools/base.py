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


AUTO_GUIDANCE_EXCLUDED_TOOLS = {
    "agent_coach",
    "ana_memory",
    "conversation_learning",
    "session_checkpoint",
    "session_rem_sleep",
    "memory_cortex",
    "tool_router",
    "vector_memory",
}


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


def _auto_guidance_enabled() -> bool:
    value = os.environ.get("ANA_AUTO_GUIDANCE", "1")
    return value.strip().lower() not in {"", "0", "false", "no", "off"}


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


import json
import datetime
import time

_manifest = None
_manifest_mtime = None
_manifest_source = None


def _permission_manifest_paths() -> List[str]:
    env_path = os.environ.get("ANA_PERMISSION_MANIFEST", "").strip()
    paths = []
    if env_path:
        paths.append(env_path)
    paths.extend([
        os.path.join(os.path.dirname(__file__), "..", "config", "permission_manifest.json"),
        os.path.join("config", "permission_manifest.json"),
        "permission_manifest.json"
    ])
    return paths


def _load_permission_manifest():
    global _manifest, _manifest_mtime, _manifest_source

    for path in _permission_manifest_paths():
        if os.path.exists(path):
            try:
                source = os.path.abspath(path)
                mtime = os.path.getmtime(path)
                if _manifest is not None and _manifest_source == source and _manifest_mtime == mtime:
                    return _manifest
                with open(path, 'r', encoding='utf-8') as f:
                    _manifest = json.load(f)
                    _manifest_mtime = mtime
                    _manifest_source = source
                    return _manifest
            except Exception as e:
                logger.error(f"Error loading permission manifest: {e}")
                
    _manifest = {
        "global_settings": {"readonly_mode": False, "allowlist": []},
        "tools": {}
    }
    _manifest_mtime = None
    _manifest_source = None
    return _manifest


def _profile_allows_tool(tool_conf: Dict[str, Any], global_settings: Dict[str, Any]) -> bool:
    active_profiles = global_settings.get("active_profiles", [])
    if not active_profiles:
        return True

    profile = tool_conf.get("profile")
    profiles = tool_conf.get("profiles")
    if profile and not profiles:
        profiles = [profile]
    if not profiles:
        return True

    return bool(set(profiles) & set(active_profiles))


def _log_observability(tool_name: str, args: Dict[str, Any], start_time: float, latency: float, status: ToolStatus, error: Optional[str] = None):
    try:
        log_dir = os.path.join(os.path.dirname(__file__), "..", "logs")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "observability.jsonl")
        
        masked_args = {}
        sensitive_keys = {"password", "token", "key", "api_key", "secret"}
        for k, v in args.items():
            if any(s in k.lower() for s in sensitive_keys):
                masked_args[k] = "********"
            else:
                masked_args[k] = _summarize_value(v, max_len=60)
                
        entry = {
            "timestamp": datetime.datetime.now(datetime.UTC).isoformat().replace("+00:00", "Z"),
            "tool": tool_name,
            "args": masked_args,
            "latency_sec": round(latency, 4),
            "status": status.value,
            "error": error
        }
        
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=True) + "\n")
    except Exception as e:
        logger.error(f"Failed to write observability log: {e}")

    _emit_observability_event(tool_name, masked_args, latency, status, error)


def _emit_observability_event(
    tool_name: str,
    masked_args: Dict[str, Any],
    latency: float,
    status: ToolStatus,
    error: Optional[str] = None,
) -> None:
    try:
        from core.event_stream import EventType, get_event_stream

        event_type = EventType.TOOL_RESULT if status == ToolStatus.SUCCESS else EventType.ERROR
        get_event_stream().emit(
            event_type=event_type,
            source=tool_name,
            data={
                "tool": tool_name,
                "args": masked_args,
                "status": status.value,
                "error": error,
            },
            metadata={"observer": "tools.base.safe_execute"},
            duration=round(latency, 4),
            success=status == ToolStatus.SUCCESS,
        )
    except Exception as exc:
        logger.debug("Event stream observability emit skipped: %s", exc)


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
        manifest = _load_permission_manifest()
        global_settings = manifest.get("global_settings", {})
        tool_manifests = manifest.get("tools", {})
        
        tool_conf = tool_manifests.get(self.name, {})
        
        allowed = tool_conf.get("allowed", True)
        allowlist = global_settings.get("allowlist", [])
        
        if allowlist and self.name not in allowlist:
            allowed = False
            
        if not allowed:
            res = ToolResult(
                status=ToolStatus.BLOCKED,
                error=f"Tool disabled by permission manifest: {self.name}"
            )
            _log_observability(self.name, kwargs, time.time(), 0.0, ToolStatus.BLOCKED, res.error)
            return res

        if not _profile_allows_tool(tool_conf, global_settings):
            res = ToolResult(
                status=ToolStatus.BLOCKED,
                error=f"Tool blocked by inactive profile: {self.name}"
            )
            _log_observability(self.name, kwargs, time.time(), 0.0, ToolStatus.BLOCKED, res.error)
            return res
            
        global_readonly = global_settings.get("readonly_mode", False)
        is_tool_readonly = tool_conf.get("readonly", False)
        
        if global_readonly and not is_tool_readonly:
            res = ToolResult(
                status=ToolStatus.BLOCKED,
                error=f"Tool blocked by read-only mode: {self.name}"
            )
            _log_observability(self.name, kwargs, time.time(), 0.0, ToolStatus.BLOCKED, res.error)
            return res
            
        error = self.validate_params(**kwargs)
        if error:
            res = ToolResult(
                status=ToolStatus.ERROR,
                error=error
            )
            _log_observability(self.name, kwargs, time.time(), 0.0, ToolStatus.ERROR, error)
            return res
            
        requires_confirm = tool_conf.get("requires_confirmation", self.requires_confirmation)
        if requires_confirm:
            if not kwargs.get("confirm", False):
                res = ToolResult(
                    status=ToolStatus.REQUIRES_CONFIRMATION,
                    message=f"Tool requires confirmation: call {self.name} with confirm=True"
                )
                _log_observability(self.name, kwargs, time.time(), 0.0, ToolStatus.REQUIRES_CONFIRMATION, res.message)
                return res
        
        timeout = kwargs.get('timeout', 60)
        execute_kwargs = kwargs
        try:
            execute_signature = inspect.signature(self.execute)
            accepts_extra_kwargs = any(
                param.kind == inspect.Parameter.VAR_KEYWORD
                for param in execute_signature.parameters.values()
            )
            if not accepts_extra_kwargs:
                accepted_names = set(execute_signature.parameters)
                execute_kwargs = {
                    key: value
                    for key, value in kwargs.items()
                    if key in accepted_names
                }
        except (TypeError, ValueError):
            execute_kwargs = kwargs

        started_time = time.time()
        try:
            if not self.run_in_worker_thread:
                res = self.execute(**execute_kwargs)
                if not isinstance(res, ToolResult):
                    res = ToolResult(status=ToolStatus.SUCCESS, data=res)
                latency = time.time() - started_time
                _log_observability(self.name, kwargs, started_time, latency, res.status, res.error or res.message if not res.is_success else None)
                return res

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(self.execute, **execute_kwargs)
                res = future.result(timeout=timeout)
                if not isinstance(res, ToolResult):
                    res = ToolResult(status=ToolStatus.SUCCESS, data=res)
                latency = time.time() - started_time
                _log_observability(self.name, kwargs, started_time, latency, res.status, res.error or res.message if not res.is_success else None)
                return res
        except (concurrent.futures.TimeoutError, TimeoutError):
            logger.error(f"Timeout in {self.name} (> {timeout}s)")
            res = ToolResult(
                status=ToolStatus.ERROR,
                error=f"Timeout: {self.name} exceeded {timeout}s"
            )
            latency = time.time() - started_time
            _log_observability(self.name, kwargs, started_time, latency, ToolStatus.ERROR, res.error)
            return res
        except Exception as e:
            logger.error(f"Eroare in {self.name}: {e}")
            res = ToolResult(
                status=ToolStatus.ERROR,
                error=_compact_error(e)
            )
            latency = time.time() - started_time
            _log_observability(self.name, kwargs, started_time, latency, ToolStatus.ERROR, res.error)
            return res


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
            
        # Normalizare parametri pentru robustete
        kwargs = _normalize_tool_params(name, kwargs)

        # UI v17: Rich Feedback. Disable in MCP mode and VS Code agent terminals.
        if os.environ.get("ANA_TOOL_STDOUT", "").strip().lower() in {"1", "true", "yes", "on"}:
            clean_params = {k: (v if len(str(v)) < 100 else f"<{type(v).__name__} len={len(str(v))}>") for k, v in kwargs.items()}
            print(f"  Tool execution: {name}")
            print(f"  Params: {clean_params}")
            
        logger.info("TOOL START name=%s args=%s", name, _summarize_kwargs(kwargs))
        result = tool.safe_execute(**kwargs)
        result = self._attach_auto_guidance(name, kwargs, result)
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

    def _attach_auto_guidance(self, name: str, kwargs: Dict[str, Any], result: ToolResult) -> ToolResult:
        """Attach memory/coach guidance to failed tool results without changing execution."""
        if result.is_success or not _auto_guidance_enabled():
            return result
        if name in AUTO_GUIDANCE_EXCLUDED_TOOLS:
            return result

        error_text = _compact_error(result.error or result.message)
        guidance: Dict[str, Any] = {}

        memory_tool = self.get("ana_memory")
        if memory_tool and error_text:
            try:
                memory_result = memory_tool.safe_execute(
                    action="find_error_solution",
                    error_text=error_text,
                    timeout=10,
                )
                memory_data = memory_result.data if isinstance(memory_result.data, dict) else {}
                if memory_result.is_success and memory_data.get("found"):
                    guidance["known_fix"] = memory_data.get("result")
            except Exception as exc:
                logger.debug("Auto guidance memory lookup failed: %s", exc)

        coach_tool = self.get("agent_coach")
        if coach_tool:
            try:
                recommend_result = coach_tool.safe_execute(
                    action="recommend",
                    task=f"Tool {name} failed",
                    error=error_text,
                    limit=80,
                    repeat_threshold=2,
                    max_tools=5,
                    include_prompt=False,
                    timeout=10,
                )
                recommend_data = recommend_result.data if isinstance(recommend_result.data, dict) else {}
                if recommend_result.is_success and recommend_data.get("primary_tool"):
                    guidance["agent_coach_recommend"] = {
                        "severity": recommend_data.get("severity"),
                        "headline": recommend_data.get("headline"),
                        "primary_tool": recommend_data.get("primary_tool"),
                        "tool_stack": recommend_data.get("tool_stack", []),
                        "next_action": recommend_data.get("next_action", ""),
                        "router": recommend_data.get("router", {}),
                    }
                coach_data = recommend_data.get("coach", {}) if isinstance(recommend_data.get("coach"), dict) else {}
                if recommend_result.is_success and coach_data.get("severity") in {"warn", "critical"}:
                    guidance["coach"] = {
                        "severity": coach_data.get("severity"),
                        "headline": coach_data.get("headline"),
                        "signals": coach_data.get("signals", []),
                        "advice": coach_data.get("advice", []),
                        "next_best_tools": coach_data.get("next_best_tools", []),
                    }
            except Exception as exc:
                logger.debug("Auto guidance coach lookup failed: %s", exc)

        router_tool = self.get("tool_router")
        if router_tool:
            try:
                router_result = router_tool.safe_execute(
                    task=f"Tool {name} failed",
                    error=error_text,
                    mode="auto",
                    max_tools=5,
                    timeout=10,
                )
                router_data = router_result.data if isinstance(router_result.data, dict) else {}
                if router_result.is_success and router_data.get("recommended_tools"):
                    guidance["tool_router"] = {
                        "mode": router_data.get("mode"),
                        "headline": router_data.get("headline"),
                        "recommended_tools": router_data.get("recommended_tools", []),
                        "steps": router_data.get("steps", []),
                        "guardrail": router_data.get("guardrail", ""),
                    }
            except Exception as exc:
                logger.debug("Auto guidance tool router lookup failed: %s", exc)

        if not guidance:
            return result

        if isinstance(result.data, dict):
            data = dict(result.data)
        elif result.data is None:
            data = {}
        else:
            data = {"original_data": result.data}
        data["auto_guidance"] = guidance
        summary = self._build_guidance_summary(guidance)
        if summary:
            data["guidance_summary"] = summary
        result.data = data

        if not result.message:
            result.message = "Auto guidance attached from ANA memory/coach."
        elif "Auto guidance attached" not in result.message:
            result.message = f"{result.message} Auto guidance attached from ANA memory/coach."

        return result

    def _build_guidance_summary(self, guidance: Dict[str, Any]) -> Dict[str, Any]:
        """Build a compact agent-readable summary from richer auto guidance."""
        recommend = guidance.get("agent_coach_recommend")
        if isinstance(recommend, dict) and recommend.get("primary_tool"):
            return {
                "primary_tool": recommend.get("primary_tool"),
                "tool_stack": recommend.get("tool_stack", []),
                "next_action": recommend.get("next_action", ""),
                "headline": recommend.get("headline", ""),
                "source": "agent_coach_recommend",
            }

        router = guidance.get("tool_router")
        if isinstance(router, dict) and router.get("recommended_tools"):
            tools = router.get("recommended_tools", [])
            return {
                "primary_tool": tools[0] if tools else "",
                "tool_stack": tools,
                "next_action": "Use the primary tool, inspect its result, then verify before retrying.",
                "headline": router.get("headline", ""),
                "source": "tool_router",
            }

        coach = guidance.get("coach")
        if isinstance(coach, dict):
            tools = coach.get("next_best_tools", [])
            return {
                "primary_tool": tools[0] if tools else "",
                "tool_stack": tools,
                "next_action": (coach.get("advice") or ["Read the failure and change strategy before retrying."])[0],
                "headline": coach.get("headline", ""),
                "source": "coach",
            }

        return {}
    
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


def _normalize_tool_params(name: str, kwargs: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize and map common parameter name aliases to match the tool definition."""
    params = kwargs.copy()
    
    if name == "file_operations":
        # Map key aliases to standard 'path'
        for k in ["file_path", "filepath", "file", "target"]:
            if k in params and "path" not in params:
                params["path"] = params.pop(k)
        if isinstance(params.get("path"), str):
            params["path"] = params["path"].strip().strip("'\"")
        if isinstance(params.get("operation"), str):
            params["operation"] = params["operation"].strip().strip("'\"")
        # Map 'action' to 'operation' if needed
        if "action" in params and "operation" not in params:
            params["operation"] = params.pop("action")
        # If path is missing, default to current directory
        if not params.get("path"):
            params["path"] = "."
        # Map content aliases
        for k in ["text", "text_content", "data"]:
            if k in params and "content" not in params:
                params["content"] = params.pop(k)
        # If operation is still missing, infer it
        if "operation" not in params:
            if "content" in params:
                params["operation"] = "write"
            elif "search_text" in params or "replace_text" in params:
                params["operation"] = "edit"
            elif "old_block" in params or "new_block" in params:
                params["operation"] = "surgical_edit"
            elif "pattern" in params:
                params["operation"] = "search"
            else:
                params["operation"] = "list" if os.path.isdir(params.get("path", ".")) else "read"
        # If path is directory and operation is read, default to list
        path = params.get("path")
        if path and os.path.isdir(path) and params.get("operation") == "read":
            params["operation"] = "list"
            
    elif name == "web_search":
        # Map 'action' to 'operation'
        if "action" in params and "operation" not in params:
            params["operation"] = params.pop("action")
        # If operation is missing, default to search
        if "operation" not in params:
            params["operation"] = "search"
        # Map query aliases
        for k in ["q", "search_query", "text", "url"]:
            if k in params and "query" not in params:
                params["query"] = params.pop(k)
        # If query is missing, try to get it
        if "query" not in params:
            params["query"] = "Python"
            
    elif name == "smart_search":
        # Map 'operation' to 'action'
        if "operation" in params and "action" not in params:
            params["action"] = params.pop("operation")
        # If action is missing, default to search
        if "action" not in params:
            params["action"] = "search"
        # Map query aliases
        for k in ["q", "search_query", "text", "pattern"]:
            if k in params and "query" not in params:
                params["query"] = params.pop(k)
        # If query is missing, try to get it
        if "query" not in params:
            params["query"] = ""
            
    elif name == "terminal":
        # Map command aliases
        for k in ["cmd", "run", "text"]:
            if k in params and "command" not in params:
                params["command"] = params.pop(k)
        # Ensure operation defaults to run
        if "operation" not in params:
            params["operation"] = "run"
            
    elif name == "code_tools":
        # Map target aliases
        for k in ["path", "file_path", "filepath"]:
            if k in params and "target" not in params:
                params["target"] = params.pop(k)
        if "action" in params and "operation" not in params:
            params["operation"] = params.pop("action")
        if "operation" not in params:
            params["operation"] = "analyze"
            
    elif name in ("edit", "file_patch"):
        for k in ["file_path", "filepath"]:
            if k in params and "path" not in params:
                params["path"] = params.pop(k)
                
    return params


# Singleton pentru acces global
registry = ToolRegistry()
