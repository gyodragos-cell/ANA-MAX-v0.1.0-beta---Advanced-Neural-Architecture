"""
Zero-UI Background Watcher (Faza 1)
Monitorizeaza clipboard-ul si fereastra activa in background.
Emite evenimente in coada locala + optional in RAG episodic memory.

Usage:
    watcher = BackgroundWatcher()
    watcher.start()
    # ... mai tarziu
    events = watcher.get_events()
    watcher.stop()
"""
import sys
import os
import time
import threading
import json
import logging
from datetime import datetime
from collections import deque
from typing import List, Dict, Any, Optional

ANA_MAX_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
if ANA_MAX_ROOT not in sys.path:
    sys.path.insert(0, ANA_MAX_ROOT)

log = logging.getLogger("background_watcher")

class BackgroundWatcher:
    """
    Watcher background pentru clipboard si fereastra activa.
    Fara UI, fara notificari vizuale — pur event-based.
    """

    def __init__(
        self,
        poll_interval: float = 2.0,
        max_events: int = 500,
        rag_enabled: bool = True
    ):
        self.poll_interval = poll_interval
        self.max_events = max_events
        self.rag_enabled = rag_enabled

        self._events: deque = deque(maxlen=max_events)
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

        # State tracking pentru detectare schimbari
        self._last_clipboard: Optional[str] = None
        self._last_window: Optional[str] = None

        # Lazy import bridge
        self._bridge = None
        self._rag = None

    def _get_bridge(self):
        if self._bridge is None:
            from bridge.direct_bridge import DirectBridge
            self._bridge = DirectBridge()
        return self._bridge

    def _get_rag(self):
        if self._rag is None and self.rag_enabled:
            try:
                from ana_kernel.rag_cpu_engine import RAGCPUEngine
                self._rag = RAGCPUEngine()
            except Exception:
                self.rag_enabled = False
        return self._rag

    def _emit(self, event_type: str, data: Dict[str, Any]):
        """Stocheaza evenimentul in coada si optional in RAG."""
        event = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        self._events.append(event)
        log.debug(f"[WATCHER] {event_type}: {str(data)[:80]}")

        # Injecteaza in RAG episodic daca e disponibil
        rag = self._get_rag()
        if rag:
            try:
                rag.ingest(
                    source="background_watcher",
                    event_type=event_type,
                    content=json.dumps(data, default=str)
                )
            except Exception:
                pass

    def _poll_clipboard(self, bridge):
        """Citeste clipboard-ul si emite eveniment daca s-a schimbat."""
        try:
            result = bridge.execute_tool("clipboard_manager", {"action": "get"})
            if result.get("success"):
                text = result.get("data", {})
                # data poate fi string sau dict
                if isinstance(text, dict):
                    text = text.get("text") or text.get("content") or str(text)
                text = str(text).strip()

                if text and text != self._last_clipboard and len(text) > 0:
                    self._last_clipboard = text
                    self._emit("clipboard_change", {
                        "text": text[:500],  # limiteaza marimea
                        "length": len(text)
                    })
        except Exception as e:
            log.warning(f"clipboard poll error: {e}")

    def _poll_window(self, bridge):
        """Citeste fereastra activa si emite eveniment daca s-a schimbat."""
        try:
            result = bridge.execute_tool("window_manager", {"action": "list"})
            if result.get("success"):
                data = result.get("data", {})
                # Extragem fereastra focusata/activa
                active = None
                if isinstance(data, dict):
                    windows = data.get("windows") or data.get("active") or []
                    if isinstance(windows, list) and windows:
                        # Prima fereastra e de obicei cea activa
                        first = windows[0]
                        if isinstance(first, dict):
                            active = first.get("title") or first.get("name") or str(first)
                        else:
                            active = str(first)
                    elif isinstance(data, str):
                        active = data

                if active and active != self._last_window:
                    self._last_window = active
                    self._emit("window_change", {
                        "title": active[:200],
                        "all_data": str(data)[:300]
                    })
        except Exception as e:
            log.warning(f"window poll error: {e}")

    def _run_loop(self):
        """Loop principal de polling in thread separat."""
        bridge = self._get_bridge()
        log.info("[WATCHER] Started background polling loop.")
        while not self._stop_event.is_set():
            self._poll_clipboard(bridge)
            self._poll_window(bridge)
            self._stop_event.wait(timeout=self.poll_interval)
        log.info("[WATCHER] Polling loop stopped.")

    def start(self):
        """Porneste watcher-ul in background thread."""
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="ana-watcher")
        self._thread.start()
        print("[WATCHER] Started (clipboard + window monitor active).")

    def stop(self):
        """Opreste watcher-ul."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        print("[WATCHER] Stopped.")

    def get_events(self, event_type: Optional[str] = None, limit: int = 50) -> List[Dict]:
        """Returneaza ultimele N evenimente, optional filtrate pe tip."""
        events = list(self._events)
        if event_type:
            events = [e for e in events if e["type"] == event_type]
        return events[-limit:]

    def get_status(self) -> Dict[str, Any]:
        """Status curent al watcher-ului."""
        return {
            "running": self._thread is not None and self._thread.is_alive(),
            "total_events": len(self._events),
            "last_clipboard": (self._last_clipboard or "")[:100],
            "last_window": self._last_window,
            "rag_enabled": self.rag_enabled,
            "poll_interval": self.poll_interval
        }
