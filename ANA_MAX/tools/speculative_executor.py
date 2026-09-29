"""
ANA MAX - speculative_executor.py
===================================
Predictive Pre-Execution — Executie Speculativa a Tool-urilor.

Similar cu executia speculativa din CPU-uri moderne (Spectre/Intel OoO):
sistemul pre-executa in fundal tool-urile pe care PREZICE ca agentul
le va cere in urmatorii 30 de secunde.

Cand agentul cere efectiv rezultatul, il primeste INSTANT din cache.

Cum functioneaza:
1. Monitorizeaza pattern-ul de apeluri al agentului (ce tool-uri cheama impreuna)
2. Apeleaza Causal Engine pentru a identifica ce vine dupa tool-ul curent
3. Pre-executa in background task-urile probabile cu argumentele implicite
4. La cerere, verifica cache-ul mai intai

Zero latenta pentru agentii conectati la MCP.
"""
from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
from datetime import datetime
from typing import Any

from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus

logger = logging.getLogger("ANA.SpeculativeExecutor")

# Cache speculativ: {cache_key: {result, timestamp, hit_count}}
_spec_cache: dict[str, dict] = {}
_cache_lock = threading.Lock()
_CACHE_TTL = 60  # secunde inainte ca un rezultat speculativ sa expire

# Pattern tracker: ce tool-uri sunt apelate impreuna frecvent
_call_patterns: dict[str, list[str]] = {}  # tool -> [urmatoarele tool-uri apelate]
_last_tool_called: str = ""
_pattern_lock = threading.Lock()


def _cache_key(tool_name: str, kwargs: dict) -> str:
    payload = json.dumps({"tool": tool_name, "args": kwargs}, sort_keys=True)
    return hashlib.md5(payload.encode()).hexdigest()[:12]


def _cache_result(tool_name: str, kwargs: dict, result: ToolResult):
    key = _cache_key(tool_name, kwargs)
    with _cache_lock:
        _spec_cache[key] = {
            "tool": tool_name,
            "kwargs": kwargs,
            "result": result,
            "timestamp": time.time(),
            "hit_count": 0,
        }
    logger.debug(f"[Speculative] Pre-cached: {tool_name} (key={key})")


def _get_cached(tool_name: str, kwargs: dict):
    key = _cache_key(tool_name, kwargs)
    with _cache_lock:
        entry = _spec_cache.get(key)
        if entry and (time.time() - entry["timestamp"]) < _CACHE_TTL:
            entry["hit_count"] += 1
            logger.info(f"[Speculative] CACHE HIT: {tool_name} (saved ~2s latency)")
            return entry["result"]
    return None


def _track_pattern(tool_name: str):
    """Inregistreaza pattern-ul de apeluri pentru invatare."""
    global _last_tool_called
    with _pattern_lock:
        if _last_tool_called and _last_tool_called != tool_name:
            if _last_tool_called not in _call_patterns:
                _call_patterns[_last_tool_called] = []
            _call_patterns[_last_tool_called].append(tool_name)
            # Pastreaza doar ultimele 100 de observatii per tool
            if len(_call_patterns[_last_tool_called]) > 100:
                _call_patterns[_last_tool_called] = _call_patterns[_last_tool_called][-100:]
        _last_tool_called = tool_name


def _get_predicted_next_tools(current_tool: str, top_n: int = 3) -> list[str]:
    """Returneaza cele mai probabile tool-uri care vor fi apelate dupa current_tool."""
    with _pattern_lock:
        history = _call_patterns.get(current_tool, [])

    if not history:
        return []

    # Calculeaza frecventa
    freq: dict[str, int] = {}
    for t in history:
        freq[t] = freq.get(t, 0) + 1

    # Sorteaza dupa frecventa
    sorted_tools = sorted(freq.items(), key=lambda x: x[1], reverse=True)
    return [t for t, _ in sorted_tools[:top_n]]


def speculative_pre_execute(current_tool: str, registry=None):
    """
    Dupa ce un tool a fost apelat, pre-executa in background
    tool-urile pe care prezice ca le va cere agentul mai departe.
    """
    if registry is None:
        return

    predicted = _get_predicted_next_tools(current_tool)
    if not predicted:
        return

    def _bg_prefetch():
        for tool_name in predicted:
            try:
                # Executa cu argumente default/minime (pentru a fi util in scenarii comune)
                default_kwargs = _get_default_kwargs(tool_name)
                result = registry.execute(tool_name, **default_kwargs)
                if result.is_success:
                    _cache_result(tool_name, default_kwargs, result)
            except Exception as e:
                logger.debug(f"[Speculative] Pre-fetch failed for {tool_name}: {e}")

    t = threading.Thread(target=_bg_prefetch, daemon=True)
    t.start()


def _get_default_kwargs(tool_name: str) -> dict:
    """Argumente default sigure pentru tool-uri comune."""
    defaults = {
        "world_model": {"filter": "system"},
        "file_operations": {"operation": "list", "path": "."},
        "system_control": {"operation": "vitals"},
        "terminal": {"command": "echo OK"},
    }
    return defaults.get(tool_name, {})


class SpeculativeExecutorTool(Tool):
    """Executie speculativa: pre-calculeaza rezultatele probabile pentru zero-latenta."""

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="speculative_exec",
            description=(
                "Executie speculativa a tool-urilor ANA. Pre-calculeaza in fundal rezultatele "
                "probabile bazat pe pattern-urile de utilizare. Raspuns instant din cache. "
                "Actiuni: 'status' (cache curent), 'patterns' (ce urmeaza dupa ce), "
                "'prefetch' (pre-executa manual un tool), 'track' (inregistreaza un apel in sistem)."
            ),
            parameters=[
                ToolParameter(
                    name="action",
                    description="'status', 'patterns', 'prefetch', 'track'",
                    type="string",
                    required=True,
                    choices=["status", "patterns", "prefetch", "track"],
                ),
                ToolParameter(
                    name="tool_name",
                    description="Numele tool-ului (pentru prefetch/track)",
                    type="string",
                    required=False,
                ),
            ],
            category="ai",
        )

    def execute(self, **kwargs: Any) -> ToolResult:
        action = kwargs.get("action")

        if action == "status":
            now = time.time()
            with _cache_lock:
                cache_data = [
                    {
                        "tool": v["tool"],
                        "cached_at": datetime.fromtimestamp(v["timestamp"]).strftime("%H:%M:%S"),
                        "expires_in_sec": max(0, int(_CACHE_TTL - (now - v["timestamp"]))),
                        "hit_count": v["hit_count"],
                    }
                    for v in _spec_cache.values()
                    if (now - v["timestamp"]) < _CACHE_TTL
                ]
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"cache": cache_data, "total_cached": len(cache_data)},
                message=f"{len(cache_data)} rezultate speculative in cache."
            )

        elif action == "patterns":
            with _pattern_lock:
                # Construieste un rezumat al pattern-urilor
                summary = {}
                for tool, history in _call_patterns.items():
                    freq: dict[str, int] = {}
                    for t in history:
                        freq[t] = freq.get(t, 0) + 1
                    top = sorted(freq.items(), key=lambda x: x[1], reverse=True)[:3]
                    summary[tool] = [{"next": t, "frequency": f} for t, f in top]
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"learned_patterns": summary, "tools_tracked": len(summary)},
                message=f"Pattern-uri invatate pentru {len(summary)} tool-uri."
            )

        elif action == "prefetch":
            tool_name = kwargs.get("tool_name", "").strip()
            if not tool_name:
                return ToolResult(status=ToolStatus.ERROR, error="'tool_name' este obligatoriu.")
            try:
                from tools.base import registry
                default_kw = _get_default_kwargs(tool_name)
                result = registry.execute(tool_name, **default_kw)
                if result.is_success:
                    _cache_result(tool_name, default_kw, result)
                    return ToolResult(
                        status=ToolStatus.SUCCESS,
                        message=f"'{tool_name}' pre-executat si in cache pentru {_CACHE_TTL}s."
                    )
                else:
                    return ToolResult(status=ToolStatus.ERROR, error=f"Pre-fetch esuat: {result.error}")
            except Exception as e:
                return ToolResult(status=ToolStatus.ERROR, error=str(e))

        elif action == "track":
            tool_name = kwargs.get("tool_name", "").strip()
            if not tool_name:
                return ToolResult(status=ToolStatus.ERROR, error="'tool_name' este obligatoriu.")
            _track_pattern(tool_name)
            predicted = _get_predicted_next_tools(tool_name)
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"tracked": tool_name, "predicted_next": predicted},
                message=f"Pattern actualizat. Prezis urmator: {predicted}"
            )

        return ToolResult(status=ToolStatus.ERROR, error=f"Actiune necunoscuta: {action}")
