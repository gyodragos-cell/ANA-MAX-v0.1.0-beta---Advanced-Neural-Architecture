from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


def init(agent: Any) -> None:
    """Initialize the AIMLAPI backend."""
    logger.info("AIMLAPI backend initializat")
    agent.backend_effective = "aimlapi"


def send(agent: Any, message: str) -> str:
    """Send a message to AIMLAPI."""
    del agent

    try:
        import requests

        api_key = os.environ.get("AIMLAPI_KEY")
        if not api_key:
            logger.warning("AIMLAPI backend cerut, dar AIMLAPI_KEY nu este setata.")
            return "Eroare: AIMLAPI_KEY nu este setata. OpenCode foloseste autlogin separat; acest backend necesita explicit variabila de mediu."

        response = requests.post(
            "https://api.aimlapi.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "gemma-3-4b",
                "messages": [{"role": "user", "content": message}],
                "max_tokens": 1000,
            },
            timeout=30,
        )

        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["message"]["content"]
        return f"Eroare API: {response.status_code} - {response.text}"
    except Exception as exc:
        logger.error(f"Eroare AIMLAPI: {exc}")
        return f"Eroare AIMLAPI: {exc}"
