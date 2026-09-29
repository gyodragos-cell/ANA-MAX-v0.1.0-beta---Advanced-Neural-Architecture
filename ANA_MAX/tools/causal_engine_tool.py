"""
ANA MAX - causal_engine_tool.py
================================
Causal Reasoning Engine — Nu corelatie, ci cauze reale.

Construieste un graf cauzal din logurile de erori si telemetria ANA.
Detecteaza pattern-uri de tip: "de fiecare data cand X se intampla,
Y urmeaza in < 30 secunde" si le promoveaza la reguli cauzale.

Capabilitati:
- Observa evenimente din EventBus si logs
- Calculeaza probabilitati conditionale P(Y|X)
- Prezice erori inainte sa apara
- Sugereaza actiuni preventive
"""
from __future__ import annotations

import json
import logging
import re
import sqlite3
import time
from collections import defaultdict, deque
from datetime import datetime
from pathlib import Path
from typing import Any

from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus

logger = logging.getLogger("ANA.CausalEngine")

DB_PATH = Path(__file__).parent.parent / "causal_memory.db"
WINDOW_SEC = 30  # fereastra de cauzalitate in secunde
MIN_COUNT = 3    # minim de observatii pentru a considera o relatie cauzala
MIN_PROB = 0.7   # probabilitate minima pentru a considera o cauza


def _init_db():
    with sqlite3.connect(str(DB_PATH)) as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                event_type TEXT NOT NULL,
                details TEXT
            );
            CREATE TABLE IF NOT EXISTS causal_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cause TEXT NOT NULL,
                effect TEXT NOT NULL,
                count INTEGER DEFAULT 1,
                probability REAL DEFAULT 0.0,
                avg_delay_sec REAL DEFAULT 0.0,
                last_seen TEXT,
                UNIQUE(cause, effect)
            );
            CREATE INDEX IF NOT EXISTS idx_events_ts ON events(timestamp);
            CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type);
        """)


_init_db()


def _observe_event(event_type: str, details: str = ""):
    """Inregistreaza un eveniment si cauta relatii cauzale cu evenimentele recente."""
    now = time.time()
    with sqlite3.connect(str(DB_PATH)) as conn:
        # Salveaza evenimentul curent
        conn.execute(
            "INSERT INTO events (timestamp, event_type, details) VALUES (?, ?, ?)",
            (now, event_type, details[:500])
        )

        # Cauta evenimente anterioare in fereastra de cauzalitate
        recent = conn.execute(
            "SELECT event_type, timestamp FROM events WHERE timestamp > ? AND event_type != ? ORDER BY timestamp DESC LIMIT 20",
            (now - WINDOW_SEC, event_type)
        ).fetchall()

        for prev_type, prev_ts in recent:
            delay = now - prev_ts
            cause = prev_type
            effect = event_type

            existing = conn.execute(
                "SELECT id, count, avg_delay_sec FROM causal_rules WHERE cause=? AND effect=?",
                (cause, effect)
            ).fetchone()

            if existing:
                rule_id, count, avg_delay = existing
                new_count = count + 1
                new_avg = (avg_delay * count + delay) / new_count
                # Calculeaza probabilitatea: cat de des apare effect dupa cause
                cause_total = conn.execute(
                    "SELECT COUNT(*) FROM events WHERE event_type=?", (cause,)
                ).fetchone()[0]
                prob = min(new_count / max(cause_total, 1), 1.0)
                conn.execute(
                    "UPDATE causal_rules SET count=?, avg_delay_sec=?, probability=?, last_seen=? WHERE id=?",
                    (new_count, round(new_avg, 2), round(prob, 3), datetime.now().isoformat(), rule_id)
                )
            else:
                conn.execute(
                    "INSERT INTO causal_rules (cause, effect, count, probability, avg_delay_sec, last_seen) VALUES (?,?,1,0.0,?,?)",
                    (cause, effect, round(delay, 2), datetime.now().isoformat())
                )

        # Curata evenimente vechi (pastreaza ultimele 24h)
        conn.execute("DELETE FROM events WHERE timestamp < ?", (now - 86400,))


def _get_predictions(event_type: str) -> list[dict]:
    """Returneaza predictiile cauzale pentru un eveniment dat."""
    with sqlite3.connect(str(DB_PATH)) as conn:
        rules = conn.execute(
            """SELECT effect, probability, avg_delay_sec, count 
               FROM causal_rules 
               WHERE cause=? AND count>=? AND probability>=?
               ORDER BY probability DESC LIMIT 5""",
            (event_type, MIN_COUNT, MIN_PROB)
        ).fetchall()
    return [
        {
            "predicted_event": r[0],
            "probability": r[1],
            "avg_delay_sec": r[2],
            "observations": r[3],
        }
        for r in rules
    ]


def _get_all_rules() -> list[dict]:
    with sqlite3.connect(str(DB_PATH)) as conn:
        rules = conn.execute(
            """SELECT cause, effect, probability, avg_delay_sec, count, last_seen
               FROM causal_rules WHERE count>=? ORDER BY probability DESC LIMIT 50""",
            (MIN_COUNT,)
        ).fetchall()
    return [
        {"cause": r[0], "effect": r[1], "probability": r[2],
         "avg_delay_sec": r[3], "observations": r[4], "last_seen": r[5]}
        for r in rules
    ]


class CausalEngineTool(Tool):
    """Motor de rationament cauzal — detecteaza cauze reale, nu corelatie."""

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="causal_engine",
            description=(
                "Motor de rationament cauzal pentru ANA OS. "
                "Observa evenimente, construieste un graf cauzal si prezice erori/evenimente "
                "inainte sa apara. Actiuni: 'observe', 'predict', 'rules', 'scan_logs'."
            ),
            parameters=[
                ToolParameter(
                    name="action",
                    description="'observe' (inregistreaza un eveniment), 'predict' (ce urmeaza dupa X?), 'rules' (arata toate regulile), 'scan_logs' (analizeaza logurile ANA automat)",
                    type="string",
                    required=True,
                    choices=["observe", "predict", "rules", "scan_logs"],
                ),
                ToolParameter(
                    name="event",
                    description="Tipul evenimentului (pentru observe/predict). Ex: 'tool_error', 'high_ram', 'frida_connect'",
                    type="string",
                    required=False,
                ),
                ToolParameter(
                    name="details",
                    description="Detalii suplimentare despre eveniment (pentru observe)",
                    type="string",
                    required=False,
                ),
            ],
            category="ai",
        )

    def execute(self, **kwargs: Any) -> ToolResult:
        action = kwargs.get("action", "rules")

        if action == "observe":
            event = kwargs.get("event", "").strip()
            if not event:
                return ToolResult(status=ToolStatus.ERROR, error="'event' este obligatoriu pentru observe.")
            details = kwargs.get("details", "")
            _observe_event(event, details)
            predictions = _get_predictions(event)
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"event_recorded": event, "predictions": predictions},
                message=f"Eveniment '{event}' inregistrat. {len(predictions)} predictii cauzale identificate."
            )

        elif action == "predict":
            event = kwargs.get("event", "").strip()
            if not event:
                return ToolResult(status=ToolStatus.ERROR, error="'event' este obligatoriu pentru predict.")
            predictions = _get_predictions(event)
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"trigger_event": event, "predictions": predictions},
                message=f"{len(predictions)} evenimente predicted dupa '{event}'."
            )

        elif action == "rules":
            rules = _get_all_rules()
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"causal_rules": rules, "total": len(rules)},
                message=f"Graf cauzal: {len(rules)} relatii cauza-efect descoperite."
            )

        elif action == "scan_logs":
            # Scaneaza logurile ANA si injecteaza evenimentele automat
            log_file = Path(__file__).parent.parent / "logs" / "ana_max.log"
            injected = 0
            if log_file.exists():
                with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f.readlines()[-500:]:  # ultimele 500 linii
                        if "ERROR" in line or "FAIL" in line:
                            _observe_event("log_error", line[:200])
                            injected += 1
                        elif "tool_factory" in line.lower():
                            _observe_event("tool_factory_call", line[:200])
                            injected += 1
                        elif "warning" in line.lower():
                            _observe_event("log_warning", line[:200])
                            injected += 1
            rules = _get_all_rules()
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"events_injected": injected, "causal_rules_discovered": len(rules), "top_rules": rules[:5]},
                message=f"Scanat {injected} evenimente din loguri. {len(rules)} relatii cauzale identificate."
            )

        return ToolResult(status=ToolStatus.ERROR, error=f"Actiune necunoscuta: {action}")
