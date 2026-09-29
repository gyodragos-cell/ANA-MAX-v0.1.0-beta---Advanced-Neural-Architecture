from __future__ import annotations

import json
import logging
import os
import sys
import time
import traceback
from typing import Any, Dict, List, Optional

# The local Foundry SDK is installed alongside the user\'s Foundry Local runtime.
FOUNDRY_SDK_PATH = r"C:\Users\billy\Desktop\ana-manus\ANA_MAX\venv\Lib\site-packages"
if os.path.exists(FOUNDRY_SDK_PATH) and FOUNDRY_SDK_PATH not in sys.path:
    sys.path.append(FOUNDRY_SDK_PATH)

try:
    from foundry_local_sdk import Configuration, FoundryLocalManager

    HAS_FOUNDRY = True
except ImportError:
    HAS_FOUNDRY = False


logger = logging.getLogger(__name__)

_CLIENT: Any = None
_MODEL: Any = None
_EP_READY = False

# A small direct set keeps a 4B local model responsive.  Every registered ANA
# tool is still available through ana_execute_tool, so tool access is not lost.
_DIRECT_TOOL_NAMES = (
    "workspace_situational_awareness",
    "project_navigator",
    "file_operations",
    "code_tools",
    "edit",
    "file_patch",
    "terminal",
    "browser_control",
    "desktop_control",
    "foreground_ui_snapshot",
    "windows_deep_sight",
    "system_control",
    "error_radar",
    "tool_router",
    "agent_coach",
)
_MAX_TOOL_RESULT_CHARS = 6000
_MAX_HISTORY_MESSAGES = 12
_MAX_TOOL_TURNS = 6


def init(agent: Any) -> None:
    """Initialize Foundry Local once and emit explicit readiness diagnostics."""
    del agent
    global _CLIENT, _MODEL, _EP_READY

    if not HAS_FOUNDRY:
        _CLIENT = None
        _MODEL = None
        logger.error("FOUNDRY_INIT failed: Foundry Local SDK is not importable.")
        return

    if _CLIENT is not None and _MODEL is not None:
        logger.info("FOUNDRY_READY reused model_id=%s", getattr(_MODEL, "id", "unknown"))
        return

    try:
        logger.info("FOUNDRY_INIT stage=manager")
        config_sdk = Configuration(app_name="ANA_MAX")
        
        # Check if already initialized to avoid singleton error
        try:
            manager = FoundryLocalManager.instance
            if manager is None:
                raise RuntimeError("FoundryLocalManager.instance returned None")
            logger.info("FOUNDRY_INIT stage=manager_already_initialized")
        except Exception as init_exc:
            logger.warning("FOUNDRY_INIT stage=manager_reinit error=%s", init_exc)
            try:
                FoundryLocalManager.initialize(config_sdk)
                manager = FoundryLocalManager.instance
                if manager is None:
                    raise RuntimeError("FoundryLocalManager.instance returned None after initialization")
                logger.info("FOUNDRY_INIT stage=manager_newly_initialized")
            except Exception as reinit_exc:
                logger.error("FOUNDRY_INIT failed to get manager: %s", reinit_exc)
                _CLIENT = None
                _MODEL = None
                return

        if not _EP_READY:
            if os.environ.get("FOUNDRY_SKIP_EP_DOWNLOAD", "0").strip().lower() in {"1", "true", "yes"}:
                logger.warning("FOUNDRY_INIT stage=execution_providers_skipped due to FOUNDRY_SKIP_EP_DOWNLOAD environment variable.")
                _EP_READY = True # Assume ready for this session to proceed
            else:
                logger.info("FOUNDRY_INIT stage=execution_providers_start")
                try:
                    manager.download_and_register_eps()
                    _EP_READY = True
                    logger.info("FOUNDRY_INIT stage=execution_providers_complete")
                except Exception as ep_exc:
                    logger.warning("FOUNDRY_INIT stage=execution_providers_failed error=%s. Attempting to continue.", ep_exc)
                    # Do not re-raise immediately, try to proceed with model loading
                    _EP_READY = False # Mark as failed for this session


        model_alias = os.environ.get("FOUNDRY_MODEL", "qwen3.5-4b").strip()
        logger.info("FOUNDRY_INIT stage=model_lookup alias=%s", model_alias)
        
        # Check if manager has catalog attribute
        if not hasattr(manager, 'catalog'):
            logger.error("FOUNDRY_INIT manager has no catalog attribute")
            _CLIENT = None
            _MODEL = None
            return
            
        model = manager.catalog.get_model(model_alias)
        if model is None:
            # Try to find GPU variant first, then CPU
            logger.warning("FOUNDRY_INIT model not found, trying variant selection")
            try:
                # Get all models
                all_models = manager.catalog.list_models()
                target_variant = None
                
                # First try to find a GPU variant
                for m in all_models:
                    model_name = str(m) if hasattr(m, '__str__') else getattr(m, 'name', str(m))
                    if model_alias.lower() in model_name.lower() and "gpu" in model_name.lower():
                        target_variant = model_name
                        logger.info("FOUNDRY_INIT found GPU variant: %s", target_variant)
                        break
                
                # If no GPU variant, fallback to CPU variant
                if not target_variant:
                    for m in all_models:
                        model_name = str(m) if hasattr(m, '__str__') else getattr(m, 'name', str(m))
                        if model_alias.lower() in model_name.lower() and "cpu" in model_name.lower():
                            target_variant = model_name
                            logger.info("FOUNDRY_INIT found CPU variant: %s", target_variant)
                            break
                
                if target_variant:
                    model = manager.catalog.get_model(target_variant)
                    model_alias = target_variant
                else:
                    raise RuntimeError(f"Model '{model_alias}' was not found in the Foundry catalog.")
            except Exception as e:
                raise RuntimeError(f"Model '{model_alias}' was not found in the Foundry catalog. Variant search failed: {e}")

        if not getattr(model, "is_cached", False):
            logger.info("FOUNDRY_INIT stage=model_download_start alias=%s", model_alias)
            try:
                model.download()
                logger.info("FOUNDRY_INIT stage=model_download_complete alias=%s", model_alias)
            except Exception as dl_exc:
                logger.error("FOUNDRY_INIT stage=model_download_failed alias=%s error=%s", model_alias, dl_exc)
                raise dl_exc

        if not getattr(model, "is_loaded", False):
            logger.info("FOUNDRY_INIT stage=model_load_start alias=%s", model_alias)
            try:
                model.load()
                logger.info("FOUNDRY_INIT stage=model_load_complete alias=%s", model_alias)
            except Exception as load_exc:
                logger.error("FOUNDRY_INIT stage=model_load_failed alias=%s error=%s", model_alias, load_exc)
                raise load_exc

        client = model.get_chat_client()
        if client is None:
            raise RuntimeError("Foundry returned no chat client after model load.")

        _MODEL = model
        _CLIENT = client
        logger.info(
            "FOUNDRY_READY model_alias=%s model_id=%s cached=%s loaded=%s",
            model_alias,
            getattr(model, "id", model_alias),
            getattr(model, "is_cached", None),
            getattr(model, "is_loaded", None),
        )
    except Exception as exc:
        _CLIENT = None
        _MODEL = None
        logger.error("FOUNDRY_INIT failed: %s", exc)
        logger.error(traceback.format_exc())


def _get_tool_registry() -> Any:
    """Return the shared ANA registry populated by main.py at startup."""
    try:
        from tools.base import ToolRegistry

        return ToolRegistry()
    except Exception as exc:
        logger.error("FOUNDRY_TOOLS registry_unavailable error=%s", exc)
        return None


def _normalise_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure the internal ANA schema is valid JSON Schema for native calls."""
    payload = json.loads(json.dumps(schema))
    parameters = payload.setdefault("function", {}).setdefault("parameters", {})
    parameters.setdefault("type", "object")
    parameters.setdefault("properties", {})
    parameters.setdefault("required", [])

    valid_types = {"string", "number", "integer", "boolean", "object", "array", "null"}
    for prop in parameters.get("properties", {}).values():
        prop_type = str(prop.get("type", "string")).lower()
        if prop_type == "list":
            prop_type = "array"
        elif prop_type == "dict":
            prop_type = "object"
        elif prop_type == "any" or prop_type not in valid_types:
            prop_type = "string"
        prop["type"] = prop_type
    return payload


def _get_ana_tools(registry: Any = None) -> List[Dict[str, Any]]:
    """Build compact, valid native tool definitions without hiding ANA tools."""
    registry = registry or _get_tool_registry()
    if registry is None:
        return []

    direct: List[Dict[str, Any]] = []
    for name in _DIRECT_TOOL_NAMES:
        tool = registry.get(name)
        if tool is None:
            continue
        try:
            direct.append(_normalise_schema(tool.get_definition().get_ollama_format()))
        except Exception as exc:
            logger.warning("FOUNDRY_TOOLS schema_skip tool=%s error=%s", name, exc)

    generic = [
        {
            "type": "function",
            "function": {
                "name": "ana_list_tools",
                "description": "List registered ANA tools and their purposes. Use this before an unfamiliar or specialised task.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "filter": {
                            "type": "string",
                            "description": "Optional keyword used to filter tool names and descriptions.",
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum number of tools to return; default 40.",
                        },
                    },
                    "required": [],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "ana_execute_tool",
                "description": "Execute any registered ANA tool by name. Use ana_list_tools first when the needed tool is not directly offered.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "tool_name": {
                            "type": "string",
                            "description": "Exact name of a registered ANA tool.",
                        },
                        "arguments": {
                            "type": "object",
                            "description": "Arguments for that tool, following the schema returned by ana_list_tools.",
                        },
                    },
                    "required": ["tool_name"],
                },
            },
        },
    ]

    logger.info(
        "FOUNDRY_TOOLS ready direct=%d registry_total=%d full_access=ana_execute_tool",
        len(direct),
        len(registry.list_tools()),
    )
    return direct + generic


def _tool_catalog(registry: Any, max_entries: int = 120) -> str:
    """Give the model a compact map of the complete local tool registry."""
    entries: List[str] = []
    for name in sorted(registry.list_tools())[:max_entries]:
        entries.append(name)
    return ", ".join(entries)


def _system_prompt(registry: Any) -> str:
    return (
        "You are ANA MAX, a local Windows engineering agent. Reply in Romanian unless the user asks for another language. "
        "CRITICAL RULE: When asked to open a program, run a command, edit a file, or perform ANY action, YOU MUST USE THE PROVIDED TOOLS (e.g., use the 'terminal' tool to run PowerShell commands like 'Start-Process brave'). "
        "DO NOT just output text saying you executed the action. You must ACTUALLY emit a valid tool call. "
        "You have real local tool access. Do not claim that a file, folder, web page, program, or system action was completed unless a tool result confirms it. "
        "For desktop or project tasks, inspect the relevant location first, make the smallest needed changes, then verify. "
        "Use direct tools for common file, terminal, browser, desktop, project, and diagnostics work. "
        "All remaining registered ANA tools are available through ana_list_tools and ana_execute_tool; do not say a tool is unavailable without checking. "
        "Keep reasoning internal and make your final answer concise, stating completed actions and any verified paths.\n\n"
        "Complete ANA tool catalogue:\n"
        + _tool_catalog(registry)
    )


def _field(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(key, default)
    return getattr(value, key, default)


def _parse_arguments(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    if not isinstance(value, str) or not value.strip():
        return {}
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        return {"_parse_error": f"Invalid JSON tool arguments: {exc}"}
    return parsed if isinstance(parsed, dict) else {"_parse_error": "Tool arguments must be a JSON object."}


def _truncate(value: str, limit: int = _MAX_TOOL_RESULT_CHARS) -> str:
    if len(value) <= limit:
        return value
    return value[:limit] + f"\n...[truncated {len(value) - limit} characters]"


def _serialise_result(result: Any) -> str:
    status = _field(result, "status", "unknown")
    status_value = _field(status, "value", status)
    payload = {
        "status": str(status_value),
        "message": _field(result, "message", ""),
        "data": _field(result, "data", None),
        "error": _field(result, "error", None),
    }
    try:
        return _truncate(json.dumps(payload, ensure_ascii=False, default=str))
    except Exception:
        return _truncate(str(payload))


def _list_tools(registry: Any, arguments: Dict[str, Any]) -> str:
    query = str(arguments.get("filter") or "").strip().lower()
    try:
        limit = max(1, min(120, int(arguments.get("max_results", 40) or 40)))
    except (TypeError, ValueError):
        limit = 40

    items: List[Dict[str, str]] = []
    for name in sorted(registry.list_tools()):
        tool = registry.get(name)
        if tool is None:
            continue
        try:
            definition = tool.get_definition()
            description = definition.description
        except Exception:
            description = "ANA registered tool"
        searchable = f"{name} {description}".lower()
        if query and query not in searchable:
            continue
        items.append({"name": name, "description": description})
        if len(items) >= limit:
            break

    return _truncate(
        json.dumps(
            {
                "status": "success",
                "returned": len(items),
                "registry_total": len(registry.list_tools()),
                "tools": items,
            },
            ensure_ascii=False,
        )
    )


def _execute_tool(registry: Any, requested_name: str, arguments: Dict[str, Any]) -> str:
    """Run tools through ToolRegistry so validation, logging, and policy hooks apply."""
    if requested_name == "ana_list_tools":
        return _list_tools(registry, arguments)

    if requested_name == "ana_execute_tool":
        requested_name = str(arguments.pop("tool_name", "")).strip()
        nested = arguments.pop("arguments", {})
        if not isinstance(nested, dict):
            return json.dumps({"status": "error", "error": "arguments must be a JSON object"})
        arguments = nested

    if "_parse_error" in arguments:
        return json.dumps({"status": "error", "error": arguments["_parse_error"]})
    if not requested_name or requested_name in {"ana_list_tools", "ana_execute_tool"}:
        return json.dumps({"status": "error", "error": "Invalid ANA tool name"})

    safe_args = {key: value for key, value in arguments.items() if key != "name"}
    logger.info("FOUNDRY_TOOL_START name=%s arg_keys=%s", requested_name, sorted(safe_args))
    try:
        result = registry.execute(requested_name, **safe_args)
    except Exception as exc:
        logger.exception("FOUNDRY_TOOL_EXCEPTION name=%s", requested_name)
        return json.dumps({"status": "error", "error": f"Tool execution exception: {exc}"})

    text = _serialise_result(result)
    logger.info(
        "FOUNDRY_TOOL_END name=%s success=%s result_chars=%d",
        requested_name,
        bool(_field(result, "is_success", False)),
        len(text),
    )
    return text


def _is_cancelled_error(exc: Exception) -> bool:
    text = str(exc).lower()
    return "operation was cancelled" in text or "operation canceled" in text or "cancelled" in text


def _recovery_tools(tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    keep = {
        "file_operations",
        "terminal",
        "browser_control",
        "workspace_situational_awareness",
        "ana_list_tools",
        "ana_execute_tool",
    }
    return [tool for tool in tools if _field(_field(tool, "function", {}), "name") in keep]


def _complete_chat(messages: List[Dict[str, Any]], tools: List[Dict[str, Any]], attempt: int) -> Any:
    if _CLIENT is None:
        raise RuntimeError("Foundry chat client is unavailable.")
    started = time.monotonic()
    logger.info("FOUNDRY_CHAT_START attempt=%d messages=%d tools=%d", attempt, len(messages), len(tools))
    response = _CLIENT.complete_chat(messages=messages, tools=tools)
    logger.info("FOUNDRY_CHAT_END attempt=%d elapsed_s=%.3f", attempt, time.monotonic() - started)
    return response


def _append_history(agent: Any, user_message: str, assistant_message: str) -> None:
    history = getattr(agent, "_history", None)
    if not isinstance(history, list):
        return
    history.extend(
        [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": assistant_message},
        ]
    )
    if len(history) > 40:
        del history[:-40]


def send(agent: Any, message: str) -> str:
    """Send a message to Foundry and run a bounded, observable tool loop."""
    if _CLIENT is None:
        return "Eroare Foundry: backend-ul local nu este pregatit. Verifica logul ANA pentru FOUNDRY_INIT."

    registry = _get_tool_registry()
    if registry is None:
        return "Eroare Foundry: registrul ANA de unelte nu este disponibil."

    tools = _get_ana_tools(registry)
    messages: List[Dict[str, Any]] = [{"role": "system", "content": _system_prompt(registry)}]
    for item in getattr(agent, "_history", [])[-_MAX_HISTORY_MESSAGES:]:
        if isinstance(item, dict) and item.get("role") in {"user", "assistant"}:
            messages.append({"role": item["role"], "content": str(item.get("content") or "")})
    messages.append({"role": "user", "content": message})

    recovery_used = False
    for turn in range(1, _MAX_TOOL_TURNS + 1):
        try:
            response = _complete_chat(messages, tools, attempt=turn)
        except Exception as exc:
            if _is_cancelled_error(exc) and not recovery_used:
                recovery_used = True
                tools = _recovery_tools(tools)
                messages.append(
                    {
                        "role": "system",
                        "content": "The prior local inference was cancelled. Respond efficiently: use the smallest necessary tool call now and do not emit hidden analysis.",
                    }
                )
                logger.warning("FOUNDRY_CHAT_CANCELLED retrying_with_tools=%d error=%s", len(tools), exc)
                time.sleep(0.25)
                try:
                    response = _complete_chat(messages, tools, attempt=turn)
                except Exception as retry_exc:
                    logger.error("FOUNDRY_CHAT_FAILED_AFTER_RETRY error=%s", retry_exc)
                    return "Eroare Foundry: inferenta locala a fost anulata si reincercarea controlata a esuat. Verifica FOUNDRY_CHAT din logul ANA."
            else:
                logger.error("FOUNDRY_CHAT_FAILED error=%s", exc)
                logger.debug(traceback.format_exc())
                return f"Eroare Foundry la procesarea mesajului: {exc}"

        choices = _field(response, "choices", []) or []
        if not choices:
            logger.error("FOUNDRY_CHAT_INVALID_RESPONSE no_choices")
            return "Eroare Foundry: raspuns local invalid (fara alegeri)."

        assistant = _field(choices[0], "message")
        if assistant is None:
            logger.error("FOUNDRY_CHAT_INVALID_RESPONSE no_message")
            return "Eroare Foundry: raspuns local invalid (fara mesaj)."

        content = str(_field(assistant, "content", "") or "")
        tool_calls = _field(assistant, "tool_calls", None) or []
        
        # Fallback XML parser for raw <tool_call> output (e.g. from phi-4-mini)
        if not tool_calls and "<tool_call>" in content:
            import re
            matches = re.finditer(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", content, re.DOTALL)
            for m in matches:
                try:
                    import json, time
                    tc_json = json.loads(m.group(1))
                    if "name" in tc_json:
                        tool_calls.append({
                            "id": tc_json.get("id", f"call_{int(time.time())}"),
                            "function": {
                                "name": tc_json["name"],
                                "arguments": json.dumps(tc_json.get("arguments", {}))
                            }
                        })
                except Exception as parse_e:
                    logger.warning("FOUNDRY_XML_PARSE_ERROR error=%s", parse_e)

        assistant_message: Dict[str, Any] = {"role": "assistant", "content": content}
        if tool_calls:
            assistant_message["tool_calls"] = []
            for tool_call in tool_calls:
                function = _field(tool_call, "function", {})
                assistant_message["tool_calls"].append(
                    {
                        "id": _field(tool_call, "id", ""),
                        "type": "function",
                        "function": {
                            "name": _field(function, "name", ""),
                            "arguments": _field(function, "arguments", "{}"),
                        },
                    }
                )
        messages.append(assistant_message)

        if not tool_calls:
            final = content or "Am finalizat procesarea locala, dar modelul nu a returnat text."
            _append_history(agent, message, final)
            logger.info("FOUNDRY_CHAT_FINAL turn=%d chars=%d", turn, len(final))
            return final

        logger.info("FOUNDRY_TOOL_BATCH turn=%d count=%d", turn, len(tool_calls))
        for tool_call in tool_calls:
            function = _field(tool_call, "function", {})
            name = str(_field(function, "name", "") or "")
            args = _parse_arguments(_field(function, "arguments", "{}"))
            result = _execute_tool(registry, name, args)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": _field(tool_call, "id", ""),
                    "name": name,
                    "content": result,
                }
            )

    logger.warning("FOUNDRY_TOOL_LOOP_LIMIT turns=%d", _MAX_TOOL_TURNS)
    return "Eroare Foundry: limita controlata a buclei de unelte a fost atinsa. Verifica FOUNDRY_TOOL_BATCH in logul ANA."
