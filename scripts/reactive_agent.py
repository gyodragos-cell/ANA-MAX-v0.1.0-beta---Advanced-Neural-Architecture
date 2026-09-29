"""
Reactive Qwen Agent (Faza 4+1)
================================
Combina BackgroundWatcher + QwenExecutor.
Cand clipboard-ul se schimba sau fereastra activa se schimba,
Qwen primeste automat contextul si poate reactiona.

Usage:
    python reactive_agent.py
    # Copiaza ceva in clipboard -> Qwen analizeaza automat
    # Ctrl+C pentru oprire
"""
import sys
import os
import time
import threading

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "ANA_MAX"))

from bridge.background_watcher import BackgroundWatcher
from bridge.qwen_executor import QwenExecutor

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
CLIPBOARD_MIN_LEN  = 20      # ignora texte mai scurte (accidentale)
CLIPBOARD_MAX_LEN  = 2000    # trunchiem continut masiv
QWEN_MAX_STEPS     = 4       # max pasi per reactie
DEBOUNCE_SECONDS   = 3.0     # asteptam 3s dupa ultima schimbare inainte sa trimitem la Qwen
REACT_ON_CLIPBOARD = True
REACT_ON_WINDOW    = False   # dezactivat implicit (zgomot mare)

class ReactiveAgent:
    def __init__(self):
        self.watcher = BackgroundWatcher(poll_interval=1.5, rag_enabled=False)
        self.qwen    = QwenExecutor(model="qwen2.5-coder:7b")
        self._last_processed_clipboard = None
        self._last_processed_window    = None
        self._debounce_timer: threading.Timer | None = None
        self._lock = threading.Lock()
        self._running = False

    def _handle_clipboard(self, event: dict):
        text = event["data"].get("text", "").strip()

        # Filtreaza texte prea scurte sau identice cu ultimul procesat
        if len(text) < CLIPBOARD_MIN_LEN:
            return
        if text == self._last_processed_clipboard:
            return

        # Trunchiem continut masiv
        if len(text) > CLIPBOARD_MAX_LEN:
            text = text[:CLIPBOARD_MAX_LEN] + "... [TRUNCHIAT]"

        self._last_processed_clipboard = text

        # Anulam timer-ul anterior (debounce)
        with self._lock:
            if self._debounce_timer:
                self._debounce_timer.cancel()
            self._debounce_timer = threading.Timer(
                DEBOUNCE_SECONDS,
                self._react_clipboard,
                args=[text]
            )
            self._debounce_timer.start()

    def _handle_window(self, event: dict):
        title = event["data"].get("title", "")
        if title == self._last_processed_window:
            return
        self._last_processed_window = title
        print(f"\n[CONTEXT] Fereastra activa: {title}")

    def _react_clipboard(self, text: str):
        """Trimite continutul clipboard-ului catre Qwen pentru analiza."""
        print(f"\n{'='*60}")
        print(f"[REACTIVE] Clipboard nou detectat ({len(text)} chars). Trimit la Qwen...")
        print(f"{'='*60}")

        import ollama
        client = ollama.Client(host="http://127.0.0.1:11434")

        prompt = (
            f"CLIPBOARD TEXT:\n```\n{text}\n```\n\n"
            "Raspunde in 2-4 randuri: ce tip de continut este (cod/eroare/URL/comanda/text), "
            "in ce limbaj/format si ce actiune recomanzi utilizatorului."
        )
        try:
            resp = client.chat(
                model="qwen2.5-coder:7b",
                messages=[{"role": "user", "content": prompt}]
                # fara tools — vrem doar analiza text pura
            )
            analysis = resp.get("message", {}).get("content", "N/A")
            print(f"\n[QWEN ANALYSIS]\n{analysis}\n")
        except Exception as e:
            print(f"[ERROR] Qwen analysis failed: {e}")

    def _poll_events(self):
        """Loop care consuma evenimentele noi din watcher."""
        seen_count = 0
        while self._running:
            events = self.watcher.get_events()
            new_events = events[seen_count:]
            seen_count = len(events)

            for event in new_events:
                if REACT_ON_CLIPBOARD and event["type"] == "clipboard_change":
                    self._handle_clipboard(event)
                if REACT_ON_WINDOW and event["type"] == "window_change":
                    self._handle_window(event)

            time.sleep(0.5)

    def start(self):
        self._running = True
        self.watcher.start()
        poll_thread = threading.Thread(target=self._poll_events, daemon=True, name="reactive-poll")
        poll_thread.start()
        print("\n[REACTIVE AGENT] Activ. Copiaza orice text (>20 chars) si Qwen va analiza automat.")
        print("[REACTIVE AGENT] Ctrl+C pentru oprire.\n")

    def stop(self):
        self._running = False
        if self._debounce_timer:
            self._debounce_timer.cancel()
        self.watcher.stop()
        print("[REACTIVE AGENT] Oprit.")


if __name__ == "__main__":
    agent = ReactiveAgent()
    agent.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        agent.stop()
