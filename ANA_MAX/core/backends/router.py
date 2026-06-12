from __future__ import annotations

import logging
from typing import Any, Callable, Dict

from core.backends import aimlapi_backend, gemini_backend, grok_backend, ollama_backend
from core.backends import opencode_zen_backend, kimi_backend
from core.backends import nemotron_openrouter_backend

logger = logging.getLogger(__name__)


def init_backend(agent: Any) -> None:
    """Initialize the configured backend."""
    if agent.backend == "hybrid":
        init_hybrid(agent)
        return

    initializers: Dict[str, Callable[[], None]] = {
        "gemini": lambda: gemini_backend.init(agent),
        "ollama": lambda: ollama_backend.init(agent),
        "aimlapi": lambda: aimlapi_backend.init(agent),
        "grok": lambda: grok_backend.init(agent),
        "opencode_zen": lambda: opencode_zen_backend.init(agent),
        "kimi": lambda: kimi_backend.init(agent),
        "nemotron_openrouter": lambda: nemotron_openrouter_backend.init(agent),
    }

    if agent.backend not in initializers:
        raise ValueError(f"Backend necunoscut: {agent.backend}")

    initializers[agent.backend]()


def init_hybrid(agent: Any) -> None:
    """Prefer Gemini online, otherwise fall back to Ollama."""
    online = agent._is_online()
    has_key = agent._get_api_key() is not None

    if online and has_key:
        logger.info("Hybrid Mode: [ONLINE] detectat. Pornesc Gemini Core.")
        try:
            gemini_backend.init(agent)
            agent.backend_effective = "gemini"
        except Exception as exc:
            logger.warning(f"Eroare pornire Gemini: {exc}. Fallback la Ollama.")
            ollama_backend.init(agent)
            agent.backend_effective = "ollama"
    else:
        reason = "Offline" if not online else "Lipsa API Key"
        logger.info(f"Hybrid Mode: [{reason}]. Pornesc Offline Core (Ollama).")
        ollama_backend.init(agent)
        agent.backend_effective = "ollama"
