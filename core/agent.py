"""
ANA MAX - Agent Principal
=========================
Clasa ANAAgent: wrapper peste backend-urile AI interne
care expune metoda send_message() pentru restul sistemului.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
import os
import re
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class BackendRoute:
    """Route definition for backend/model fallback."""

    backend: str
    model: Optional[str] = None
    max_requests: Optional[int] = None
    enabled: bool = True
    failures: int = 0
    requests_sent: int = 0
    cooldown_until: float = 0.0


class ANAAgent:
    """
    Agent principal A.N.A. MAX.
    Trimite mesaje catre backend-ul AI configurat si returneaza raspunsuri text.

    Parametri:
        backend (str): "gemini", "ollama", sau "none"
    """

    RETRYABLE_ERROR_TERMS = (
        "429",
        "quota",
        "resource_exhausted",
        "rate limit",
        "temporarily unavailable",
        "service unavailable",
        "deadline exceeded",
        "timeout",
        "timed out",
        "connection aborted",
        "connection refused",
        "connection reset",
        "max retries exceeded",
        "server disconnected",
    )

    def __init__(self, backend: str = "gemini"):
        self.backend = backend.lower() if backend else "none"
        self.backend_effective = self.backend
        self._client: Any = None
        self._chat = None
        self._genai_api_key: Optional[str] = None
        self._session_id = f"ana_{int(time.time())}"
        self._history: List[Dict[str, str]] = []
        self._routes: List[BackendRoute] = []
        self._active_route_index = 0

        self._routing_enabled = False
        self._route_cooldown_seconds = 300
        self._route_max_failures = 1
        self._route_rotate_at_percent = 70

        if self.backend not in (None, "", "none"):
            self._configure_routes()
            self._activate_route(0, initial=True)

        logger.info(f"ANAAgent initializat cu backend: {self.backend}")

    # ------------------------------------------------------------------
    # Routing
    # ------------------------------------------------------------------

    def _configure_routes(self) -> None:
        """Load backend routing from config."""
        from core.config import config

        routing_cfg = config.get("ai.routing", {}) or {}
        self._routing_enabled = bool(routing_cfg.get("enabled", False))
        self._route_cooldown_seconds = int(routing_cfg.get("cooldown_seconds", 300) or 300)
        self._route_max_failures = max(1, int(routing_cfg.get("max_failures", 1) or 1))
        self._route_rotate_at_percent = max(
            1,
            min(100, int(routing_cfg.get("rotate_at_percent", 70) or 70)),
        )

        configured_routes = routing_cfg.get("backends", []) if self._routing_enabled else []
        routes: List[BackendRoute] = []

        for item in configured_routes:
            route = self._parse_route(item)
            if route is not None:
                routes.append(route)

        if not routes:
            routes = self._build_default_routes()

        self._routes = [route for route in routes if route.enabled]
        if not self._routes:
            self._routes = [BackendRoute(backend=self.backend)]

        logger.info(
            "ANA routing configurat: %s",
            " -> ".join(
                f"{route.backend}({route.model or 'default'})" for route in self._routes
            ),
        )

    def _parse_route(self, item: Any) -> Optional[BackendRoute]:
        """Parse a routing entry from config."""
        if isinstance(item, str):
            backend = item.strip().lower()
            if backend:
                return BackendRoute(backend=backend)
            return None

        if not isinstance(item, dict):
            return None

        backend = str(item.get("backend", "")).strip().lower()
        if not backend:
            return None

        model = item.get("model")
        max_requests = item.get("max_requests")
        enabled = bool(item.get("enabled", True))
        try:
            max_requests = int(max_requests) if max_requests is not None else None
        except (TypeError, ValueError):
            max_requests = None

        return BackendRoute(
            backend=backend,
            model=str(model).strip() if isinstance(model, str) and model.strip() else None,
            max_requests=max_requests,
            enabled=enabled,
        )

    def _build_default_routes(self) -> List[BackendRoute]:
        """Build a conservative fallback chain when explicit routing is absent."""
        from core.config import config

        candidates = [self.backend, config.get("ai.fallback_backend", "none"), "ollama", "gemini"]
        routes: List[BackendRoute] = []
        seen: set[str] = set()

        for candidate in candidates:
            backend = str(candidate or "").strip().lower()
            if not backend or backend == "none" or backend in seen:
                continue
            seen.add(backend)
            routes.append(BackendRoute(backend=backend))

        return routes or [BackendRoute(backend=self.backend)]

    def _activate_route(self, route_index: int, initial: bool = False) -> None:
        """Activate a specific backend route."""
        route = self._routes[route_index]
        self._reset_backend_state()
        self._active_route_index = route_index
        self.backend_effective = route.backend

        try:
            self._init_backend(route.backend, route.model)
            logger.info(
                "%s backend route: %s model=%s",
                "Initializat" if initial else "Comutat pe",
                route.backend,
                route.model or "default",
            )
        except Exception:
            raise

    def _reset_backend_state(self) -> None:
        """Clear transient backend state before switching."""
        self._client = None
        self._chat = None
        self._genai_api_key = None
        for attr in ("_ollama_url", "_ollama_model"):
            if hasattr(self, attr):
                delattr(self, attr)

    def _rotate_route(self, reason: str) -> bool:
        """Switch to the next available route."""
        if len(self._routes) <= 1:
            return False

        now = time.time()
        total = len(self._routes)
        for offset in range(1, total + 1):
            next_index = (self._active_route_index + offset) % total
            route = self._routes[next_index]

            if route.cooldown_until > now:
                continue

            try:
                self._activate_route(next_index)
                logger.warning(
                    "ANA routing: comutare automata catre %s (%s)",
                    route.backend,
                    reason,
                )
                return True
            except Exception as exc:
                logger.warning(
                    "ANA routing: backend %s indisponibil in timpul comutarii: %s",
                    route.backend,
                    exc,
                )
                route.failures += 1
                route.cooldown_until = now + self._route_cooldown_seconds

        return False

    def _current_route(self) -> Optional[BackendRoute]:
        if not self._routes:
            return None
        return self._routes[self._active_route_index]

    def _maybe_rotate_for_soft_budget(self) -> None:
        """Rotate when a local request budget reaches the configured threshold."""
        route = self._current_route()
        if route is None or route.max_requests is None or route.max_requests <= 0:
            return

        usage_percent = (route.requests_sent / route.max_requests) * 100
        if usage_percent < self._route_rotate_at_percent:
            return

        self._rotate_route(
            f"prag local de utilizare atins ({usage_percent:.0f}% din {route.max_requests} cereri)"
        )

    def _mark_route_failure(self, route: BackendRoute, error: Exception) -> None:
        route.failures += 1
        if route.failures >= self._route_max_failures or self._is_retryable_error(error):
            route.cooldown_until = time.time() + self._route_cooldown_seconds

    def _mark_route_success(self, route: BackendRoute) -> None:
        route.failures = 0
        route.requests_sent += 1
        route.cooldown_until = 0.0

    def _is_retryable_error(self, error: Exception) -> bool:
        error_text = str(error).lower()
        return any(term in error_text for term in self.RETRYABLE_ERROR_TERMS)

    # ------------------------------------------------------------------
    # Initializare backend
    # ------------------------------------------------------------------

    def _init_backend(self, backend: str, model_override: Optional[str] = None) -> None:
        """Initialize the selected backend."""
        backend = (backend or "none").lower()
        self.backend_effective = backend
        self._model_override = model_override

        if backend == "gemini":
            self._init_gemini(model_override=model_override)
        elif backend == "ollama":
            self._init_ollama(model_override=model_override)
        elif backend == "opencode_zen":
            from core.backends import opencode_zen_backend

            opencode_zen_backend.init(self)
        elif backend == "kimi":
            from core.backends import kimi_backend

            kimi_backend.init(self)
        elif backend == "grok":
            from core.backends import grok_backend

            grok_backend.init(self)
        elif backend == "aimlapi":
            from core.backends import aimlapi_backend

            aimlapi_backend.init(self)
        elif backend == "adal":
            from core.backends import adal_backend

            adal_backend.init(self)
        elif backend == "nemotron_openrouter":
            from core.backends import nemotron_openrouter_backend

            nemotron_openrouter_backend.init(self)
        else:
            raise ValueError(f"Backend necunoscut: {backend}")

    def _init_gemini(self, model_override: Optional[str] = None) -> None:
        """Initialize the Google Gemini client."""
        from core.config import config
        import pathlib

        api_key_file = config.get("ai.gemini.api_key_file", "API_KEY.txt")
        api_key = None

        key_path = pathlib.Path(api_key_file)
        if not key_path.is_absolute():
            project_root = pathlib.Path(__file__).resolve().parent.parent
            key_path = project_root / api_key_file

        if key_path.exists():
            api_key = key_path.read_text(encoding="utf-8").strip()
        else:
            import os

            api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")

        if not api_key:
            raise ValueError(
                f"Cheia API Gemini nu a fost gasita in {api_key_file} sau variabilele de mediu."
            )

        model_name = model_override or config.get(
            "ai.gemini.model", "models/gemini-1.5-flash-latest"
        )

        try:
            import google.generativeai as genai

            genai.configure(api_key=api_key)
            self._client = genai.GenerativeModel(model_name)
            self._chat = self._client.start_chat(history=[])
            logger.info(f"Gemini initializat cu modelul: {model_name}")
        except ImportError:
            try:
                from google import genai as new_genai

                self._client = new_genai.Client(api_key=api_key)
                self._genai_api_key = api_key
                self._gemini_model = model_name
                logger.info("google-genai initializat cu modelul: %s", model_name)
            except ImportError as exc:
                raise ImportError(
                    "Niciun pachet Gemini disponibil. Ruleaza: pip install google-generativeai"
                ) from exc

    def _init_ollama(self, model_override: Optional[str] = None) -> None:
        """Initialize the Ollama HTTP client."""
        from core.config import config

        self._ollama_url = config.get(
            "ai.ollama.api_url", "http://localhost:11434/api/generate"
        )
        self._ollama_model = model_override or config.get("ai.ollama.model", "mistral:7b")
        self._client = {"type": "ollama", "url": self._ollama_url, "model": self._ollama_model}
        logger.info(f"Ollama configurat: {self._ollama_url} model={self._ollama_model}")

    # ------------------------------------------------------------------
    # Trimitere mesaj
    # ------------------------------------------------------------------

    def send_message(self, message: str, allow_auto_tools: bool = True) -> str:
        """
        Trimite un mesaj la backend-ul AI si returneaza raspunsul ca text.

        Parametri:
            message (str): Mesajul utilizatorului.
            allow_auto_tools (bool): Rezervat pentru utilizare viitoare.

        Returneaza:
            str: Raspunsul generat de AI.
        """
        del allow_auto_tools

        if not message or not message.strip():
            return "(mesaj gol)"

        if self.backend == "none" or not self._routes:
            return (
                "ANA functioneaza in modul tools-only. "
                "Backend-ul AI intern este dezactivat (ai.primary_backend: none). "
                "Configureaza 'gemini' sau 'ollama' in settings.yaml pentru rationament intern."
            )

        self._maybe_rotate_for_soft_budget()

        attempts = max(1, len(self._routes))
        last_error: Optional[Exception] = None

        for _ in range(attempts):
            route = self._current_route()
            if route is None:
                break

            if route.cooldown_until > time.time():
                if not self._rotate_route("backend in cooldown"):
                    continue
                route = self._current_route()
                if route is None:
                    break

            try:
                response = self._send_with_backend(route.backend, message)
                self._mark_route_success(route)
                return response
            except Exception as exc:
                last_error = exc
                self._mark_route_failure(route, exc)
                logger.warning(
                    "ANA routing: %s a esuat pentru model=%s: %s",
                    route.backend,
                    route.model or "default",
                    exc,
                )
                if not self._rotate_route(f"eroare: {exc}"):
                    break

        logger.error("Eroare la send_message (%s): %s", self.backend_effective, last_error)
        return f"Eroare la procesarea mesajului: {last_error}"

    def _send_with_backend(self, backend: str, message: str) -> str:
        if backend == "gemini":
            return self._send_gemini(message)
        if backend == "ollama":
            return self._send_ollama(message)
        if backend == "opencode_zen":
            from core.backends import opencode_zen_backend

            return opencode_zen_backend.send(self, message)
        if backend == "kimi":
            from core.backends import kimi_backend

            return kimi_backend.send(self, message)
        if backend == "grok":
            from core.backends import grok_backend

            return grok_backend.send(self, message)
        if backend == "aimlapi":
            from core.backends import aimlapi_backend

            return aimlapi_backend.send(self, message)
        if backend == "adal":
            from core.backends import adal_backend

            return adal_backend.send(self, message)
        if backend == "nemotron_openrouter":
            from core.backends import nemotron_openrouter_backend

            return nemotron_openrouter_backend.send(self, message)
        raise ValueError(f"Backend necunoscut: {backend}")

    def _send_gemini(self, message: str) -> str:
        """Send a message through Gemini and return the text response."""
        if hasattr(self, "_chat") and self._chat is not None:
            response = self._chat.send_message(message)
            return response.text

        if self._genai_api_key:
            from google import genai as new_genai

            client = new_genai.Client(api_key=self._genai_api_key)
            response = client.models.generate_content(
                model=getattr(self, "_gemini_model", "gemini-1.5-flash"),
                contents=message,
            )
            return response.text

        raise RuntimeError("Clientul Gemini nu este initializat corect.")

    def _send_ollama(self, message: str) -> str:
        """Send a message through the Ollama HTTP API."""
        import requests as req

        payload = {"model": self._ollama_model, "prompt": message, "stream": False}
        response = req.post(self._ollama_url, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        return data.get("response", "(raspuns gol de la Ollama)")

    # ------------------------------------------------------------------
    # Utilitare
    # ------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Returneaza statusul agentului."""
        return {
            "backend": self.backend,
            "effective_backend": self.backend_effective,
            "client_ready": self._client is not None,
            "session_id": self._session_id,
            "history_length": len(self._history),
            "routes": [
                {
                    "backend": route.backend,
                    "model": route.model,
                    "failures": route.failures,
                    "requests_sent": route.requests_sent,
                    "cooldown_until": route.cooldown_until,
                }
                for route in self._routes
            ],
        }

    def reset_history(self) -> None:
        """Reseteaza istoricul conversatiei."""
        self._history = []
        if self.backend_effective == "gemini" and self._client is not None:
            try:
                self._chat = self._client.start_chat(history=[])
            except Exception:
                pass
        logger.info("Istoricul conversatiei a fost resetat.")

    def __repr__(self) -> str:
        return (
            f"ANAAgent(backend={self.backend!r}, "
            f"effective={self.backend_effective!r}, ready={self._client is not None})"
        )

    @staticmethod
    def _execute_tools(self, message: str) -> List[str]:
        """
        Minimal deterministic tool executor used by engineer action tests.
        """
        del self
        lowered = message.lower()
        results: List[str] = []
        path_match = re.search(r"([A-Za-z]:\\[^\n]+|/[^\n]+)", message)
        if not path_match:
            return results

        target = path_match.group(1).strip().rstrip(".")
        if ("cree" in lowered or "create" in lowered) and "folder" in lowered:
            Path(target).mkdir(parents=True, exist_ok=True)
            results.append(f"Folder creat: {target}")

        if ("sterge" in lowered or "șterge" in lowered or "delete" in lowered or "remove" in lowered) and "folder" in lowered:
            shutil.rmtree(target, ignore_errors=True)
            results.append(f"Folder sters: {target}")

        return results
