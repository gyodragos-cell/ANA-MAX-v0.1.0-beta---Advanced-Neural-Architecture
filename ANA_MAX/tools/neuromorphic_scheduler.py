"""
ANA MAX - neuromorphic_scheduler.py
=====================================
Neuromorphic Process Scheduler — Inspirat din dinamica neuronala biologica.

Concept: Neuronii biologici se "obosesc" dupa ce sunt stimulati des si au
nevoie de o perioada de recuperare inainte sa fie la fel de receptivi.

Aplicat la tool-uri ANA:
- Tool-urile folosite des primesc PRIORITATE MAI MICA (se "odihnesc")
- Tool-urile rare primesc prioritate MAX cand sunt apelate
- Previne monopolizarea resurselor de catre un singur tool
- Creeaza un ecosistem de tool-uri auto-echilibrat

Parametri neuromorfici:
  - excitation: cat de "excitat" este tool-ul curent (0.0 - 1.0)
  - fatigue: oboseala acumulata din apeluri frecvente
  - recovery_rate: cat de repede isi revine dupa odihna
  - priority: prioritatea curenta de executie (calculata dinamic)
"""
from __future__ import annotations

import json
import logging
import math
import threading
import time
from collections import defaultdict
from datetime import datetime
from typing import Any

from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus

logger = logging.getLogger("ANA.NeuromorphicScheduler")

# Starea sinaptica globala a tuturor tool-urilor
_synaptic_state: dict[str, dict] = {}
_state_lock = threading.Lock()

# Parametri neuromorfici globali
FATIGUE_PER_CALL = 0.15      # cat de multa oboseala adauga un apel
RECOVERY_RATE = 0.05         # cat isi revine per secunda de inactivitate
MAX_FATIGUE = 1.0            # oboseala maxima
BASE_PRIORITY = 1.0          # prioritatea de baza


def _get_or_init_tool_state(tool_name: str) -> dict:
    with _state_lock:
        if tool_name not in _synaptic_state:
            _synaptic_state[tool_name] = {
                "fatigue": 0.0,
                "call_count": 0,
                "last_called": 0.0,
                "last_recovered": time.time(),
                "priority": BASE_PRIORITY,
            }
        return _synaptic_state[tool_name]


def _recover_tool(tool_name: str):
    """Aplica recuperarea sinaptica bazata pe timpul scurs de la ultimul apel."""
    now = time.time()
    state = _get_or_init_tool_state(tool_name)
    with _state_lock:
        elapsed = now - state.get("last_recovered", now)
        recovery = RECOVERY_RATE * elapsed
        state["fatigue"] = max(0.0, state["fatigue"] - recovery)
        state["last_recovered"] = now
        # Prioritatea scade cand oboseala creste (mai obosit = mai putina prioritate)
        state["priority"] = BASE_PRIORITY * (1.0 - state["fatigue"] * 0.8)


def record_tool_call(tool_name: str):
    """Inregistreaza un apel de tool si actualizeaza starea sinaptica."""
    _recover_tool(tool_name)
    with _state_lock:
        state = _synaptic_state[tool_name]
        state["fatigue"] = min(MAX_FATIGUE, state["fatigue"] + FATIGUE_PER_CALL)
        state["call_count"] += 1
        state["last_called"] = time.time()
        state["priority"] = BASE_PRIORITY * (1.0 - state["fatigue"] * 0.8)
        logger.debug(
            f"[Neuro] {tool_name}: fatigue={state['fatigue']:.2f}, priority={state['priority']:.2f}"
        )


def get_tool_priority(tool_name: str) -> float:
    """Returneaza prioritatea curenta a unui tool (dupa recuperare sinaptica)."""
    _recover_tool(tool_name)
    with _state_lock:
        return _synaptic_state.get(tool_name, {}).get("priority", BASE_PRIORITY)


def get_optimal_tool(candidates: list[str]) -> str:
    """Din o lista de tool-uri candidate, returneaza cel cu prioritatea cea mai mare."""
    if not candidates:
        return ""
    return max(candidates, key=get_tool_priority)


class NeuromorphicSchedulerTool(Tool):
    """Scheduler neuromorific pentru prioritizarea dinamica a tool-urilor ANA."""

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="neuro_scheduler",
            description=(
                "Scheduler neuromorific inspirat din dinamica neuronala. "
                "Tool-urile 'obosesc' dupa utilizare intensa si isi revin in timp. "
                "Actiuni: 'status' (starea sinaptica), 'recommend' (cel mai odihnit tool), "
                "'record' (inregistreaza un apel), 'reset' (reseteaza un tool)."
            ),
            parameters=[
                ToolParameter(
                    name="action",
                    description="'status', 'recommend', 'record', 'reset'",
                    type="string",
                    required=True,
                    choices=["status", "recommend", "record", "reset"],
                ),
                ToolParameter(
                    name="tool_name",
                    description="Numele tool-ului (pentru record/reset/recommend cu candidati)",
                    type="string",
                    required=False,
                ),
                ToolParameter(
                    name="candidates",
                    description="Lista JSON de tool-uri candidate pentru recomandare. Ex: '[\"terminal\", \"files\", \"web\"]'",
                    type="string",
                    required=False,
                ),
            ],
            category="system",
        )

    def execute(self, **kwargs: Any) -> ToolResult:
        action = kwargs.get("action")

        if action == "status":
            # Aplica recuperarea pentru toate tool-urile inainte de raport
            with _state_lock:
                all_tools = list(_synaptic_state.keys())
            for t in all_tools:
                _recover_tool(t)

            with _state_lock:
                snapshot = {
                    name: {
                        "fatigue": round(s["fatigue"], 3),
                        "priority": round(s["priority"], 3),
                        "call_count": s["call_count"],
                        "last_called": datetime.fromtimestamp(s["last_called"]).strftime("%H:%M:%S") if s["last_called"] else "never",
                    }
                    for name, s in sorted(
                        _synaptic_state.items(),
                        key=lambda x: x[1]["fatigue"],
                        reverse=True
                    )
                }
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"synaptic_state": snapshot, "total_tracked": len(snapshot)},
                message=f"Stare sinaptica pentru {len(snapshot)} tool-uri."
            )

        elif action == "record":
            tool_name = kwargs.get("tool_name", "").strip()
            if not tool_name:
                return ToolResult(status=ToolStatus.ERROR, error="'tool_name' este obligatoriu pentru record.")
            record_tool_call(tool_name)
            with _state_lock:
                state = _synaptic_state.get(tool_name, {})
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={
                    "tool": tool_name,
                    "fatigue": round(state.get("fatigue", 0), 3),
                    "priority": round(state.get("priority", 1), 3),
                    "call_count": state.get("call_count", 0),
                },
                message=f"Apel inregistrat pentru '{tool_name}'. Fatigue: {state.get('fatigue', 0):.2f}"
            )

        elif action == "recommend":
            candidates_raw = kwargs.get("candidates", "[]")
            try:
                candidates = json.loads(candidates_raw)
            except Exception:
                candidates = [candidates_raw] if candidates_raw else []

            if not candidates:
                return ToolResult(status=ToolStatus.ERROR, error="'candidates' este o lista JSON de tool-uri.")

            best = get_optimal_tool(candidates)
            priorities = {t: round(get_tool_priority(t), 3) for t in candidates}
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"recommended": best, "priorities": priorities},
                message=f"Tool recomandat (cel mai odihnit): '{best}' (priority={priorities[best]})"
            )

        elif action == "reset":
            tool_name = kwargs.get("tool_name", "").strip()
            with _state_lock:
                if tool_name and tool_name in _synaptic_state:
                    _synaptic_state[tool_name] = {
                        "fatigue": 0.0,
                        "call_count": 0,
                        "last_called": 0.0,
                        "last_recovered": time.time(),
                        "priority": BASE_PRIORITY,
                    }
                elif not tool_name:
                    _synaptic_state.clear()
            return ToolResult(
                status=ToolStatus.SUCCESS,
                message=f"Reset neuromorific complet pentru: {tool_name or 'TOATE tool-urile'}."
            )

        return ToolResult(status=ToolStatus.ERROR, error=f"Actiune necunoscuta: {action}")
