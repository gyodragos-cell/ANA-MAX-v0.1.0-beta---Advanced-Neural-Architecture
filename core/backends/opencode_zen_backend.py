"""
opencode_zen_backend.py
=======================
Backend pentru OpenCode Zen API - modele free si premium.
Compatibil cu OpenAI API format (v1/chat/completions).
"""
from __future__ import annotations

import logging
import os
from typing import Any

from core.config import config

logger = logging.getLogger(__name__)

OPENCODE_ZEN_BASE_URL = "https://opencode.ai/zen/v1"


def _get_api_key() -> str:
    import random
    # Incearca mai intai lista de chei pentru rotatie
    keys_env = os.environ.get("OPENCODE_ZEN_API_KEYS", "")
    if keys_env:
        keys = [k.strip() for k in keys_env.split(",") if k.strip()]
        if keys:
            return random.choice(keys)
            
    # Fallback la cheia singulara
    key = os.environ.get("OPENCODE_ZEN_API_KEY", "")
    if not key:
        key = os.environ.get("OPENCODE_API_KEY", "")
    return key


def init(agent: Any) -> None:
    """Initializeaza backend-ul OpenCode Zen."""
    try:
        import httpx  # noqa: F401 - verificam disponibilitatea
        key = _get_api_key()
        agent.opencode_zen_api_key = key
        model = getattr(agent, "_model_override", None) or config.get(
            "ai.routing.backends[0].model", "minimax-m2.5-free"
        )
        agent.opencode_zen_model = model
        logger.info("OpenCode Zen backend initializat cu modelul: %s", model)
    except ImportError:
        raise ImportError("httpx este necesar pentru opencode_zen backend. Ruleaza: pip install httpx")
    except Exception as exc:
        logger.error("Eroare la initializarea OpenCode Zen: %s", exc)
        raise


def send(agent: Any, message: str) -> str:
    """Trimite mesaj catre OpenCode Zen API."""
    import httpx

    # Obtine o cheie noua la fiecare cerere pentru rotatie reala
    api_key = _get_api_key()
    model = getattr(agent, "opencode_zen_model", "minimax-m2.5-free")
    
    if api_key:
        logger.debug("OpenCode Zen: foloseste cheia %s...", api_key[:10])

    headers = {
        "Content-Type": "application/json",
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": message}],
        "max_tokens": 2048,
    }

    try:
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(
                f"{OPENCODE_ZEN_BASE_URL}/chat/completions",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
    except httpx.HTTPStatusError as exc:
        logger.error("OpenCode Zen HTTP error %s: %s", exc.response.status_code, exc.response.text[:300])
        raise
    except Exception as exc:
        logger.error("OpenCode Zen send error: %s", exc)
        raise
