from __future__ import annotations

import logging
import os
from typing import Any, Optional

from core.backends.common import read_nonempty_lines
from core.config import config

logger = logging.getLogger(__name__)


def _load_api_keys(agent: Any) -> list[str]:
    keys: list[str] = []
    key_file = config.get("ai.gemini.api_key_file", "API_KEY.txt")
    if os.path.exists(key_file):
        keys = read_nonempty_lines(key_file)
    env_key = os.environ.get("GEMINI_API_KEY")
    if not keys and env_key:
        keys = [env_key]
    agent.api_keys = keys
    return keys


def init(agent: Any) -> None:
    """Initialize Gemini using the official google-generativeai SDK (API-key based)."""
    try:
        import google.generativeai as genai

        keys = _load_api_keys(agent)
        if not keys:
            raise ValueError("API key Gemini lipseste!")

        genai.configure(api_key=keys[agent.current_key_index])
        model_id = config.get("ai.gemini.model", "gemini-1.5-flash")
        agent.gemini_model = genai.GenerativeModel(model_id)
        logger.info("Gemini (google-generativeai) initializat cu succes (%s)", model_id)
    except Exception as exc:
        logger.error(f"Eroare la initializarea Gemini: {exc}")
        raise


def rotate_key(agent: Any) -> bool:
    """Rotate to the next Gemini API key."""
    keys = getattr(agent, "api_keys", []) or _load_api_keys(agent)
    if len(keys) <= 1:
        logger.warning("Nicio alta cheie API disponibila pentru rotatie.")
        return False

    import google.generativeai as genai

    agent.current_key_index = (agent.current_key_index + 1) % len(keys)
    genai.configure(api_key=keys[agent.current_key_index])
    model_id = config.get("ai.gemini.model", "gemini-1.5-flash")
    agent.gemini_model = genai.GenerativeModel(model_id)
    logger.info("Rotatie cheie reusita: se foloseste cheia #%s", agent.current_key_index + 1)
    return True


def send(agent: Any, message: str) -> str:
    """Send a message to Gemini with automatic key rotation."""
    import google.generativeai as genai

    try:
        if not getattr(agent, "gemini_model", None):
            init(agent)

        response = agent.gemini_model.generate_content(message)
        return response.text or "(fara raspuns text)"
    except Exception as exc:
        error_str = str(exc).lower()
        if any(term in error_str for term in ("429", "quota", "resource_exhausted")):
            logger.warning("Limita/eroare Gemini. Incerc rotatia cheii...")
            if rotate_key(agent):
                return send(agent, message)
        raise
