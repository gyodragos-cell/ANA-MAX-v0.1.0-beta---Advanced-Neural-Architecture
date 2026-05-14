"""
kimi_backend.py
==============
Backend pentru Kimi K2.5 - model LLM de la Moonshot AI.
Foloseste API-ul gratuit de la Puter.js sau NVIDIA NIM.

Kimi K2.5: 1T parametri MoE (32B activi), 512K context,
excelent pentru coding si reasoning.
"""
from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

PUTER_KIMI_URL = "https://api.puter.com/v1/chat/completions"
NVIDIA_KIMI_URL = "https://integrate.api.nvidia.com/v1/chat/completions"


def _get_api_key() -> str:
    return os.environ.get("KIMI_API_KEY", "")


def init(agent: Any) -> None:
    """Initializeaza backend-ul Kimi K2.5."""
    try:
        import httpx
    except ImportError:
        raise ImportError("httpx este necesar pentru kimi backend. Ruleaza: pip install httpx")

    api_key = _get_api_key()
    agent.kimi_api_key = api_key
    agent.kimi_model = "moonshotai/kimi-k2.5"
    agent.kimi_provider = "puter" if not api_key else "nvidia"

    logger.info("Kimi K2.5 backend initializat (provider: %s)", agent.kimi_provider)


def send(agent: Any, message: str) -> str:
    """Trimite mesaj catre Kimi K2.5 via Puter.js (gratuit) sau NVIDIA NIM."""
    import httpx

    provider = getattr(agent, "kimi_provider", "puter")
    api_key = getattr(agent, "kimi_api_key", "") or _get_api_key()

    headers = {
        "Content-Type": "application/json",
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    payload = {
        "model": "moonshotai/kimi-k2.5",
        "messages": [{"role": "user", "content": message}],
        "max_tokens": 4096,
        "temperature": 0.7,
    }

    if provider == "nvidia" and api_key:
        url = NVIDIA_KIMI_URL
        payload["model"] = "kimi-k2.5"
    else:
        url = PUTER_KIMI_URL

    try:
        with httpx.Client(timeout=120.0) as client:
            resp = client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
    except httpx.HTTPStatusError as exc:
        logger.error("Kimi HTTP error %s: %s", exc.response.status_code, exc.response.text[:300])
        raise
    except Exception as exc:
        logger.error("Kimi send error: %s", exc)
        raise


def stream(agent: Any, message: str):
    """Versiune streaming pentru Kimi K2.5."""
    import httpx
    import json

    provider = getattr(agent, "kimi_provider", "puter")
    api_key = getattr(agent, "kimi_api_key", "") or _get_api_key()

    headers = {
        "Content-Type": "application/json",
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    payload = {
        "model": "moonshotai/kimi-k2.5",
        "messages": [{"role": "user", "content": message}],
        "max_tokens": 4096,
        "stream": True,
    }

    if provider == "nvidia" and api_key:
        url = NVIDIA_KIMI_URL
        payload["model"] = "kimi-k2.5"
    else:
        url = PUTER_KIMI_URL

    with httpx.Client(timeout=120.0) as client:
        with client.stream("POST", url, headers=headers, json=payload) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if line.startswith("data: "):
                    if line == "data: [DONE]":
                        break
                    chunk = json.loads(line[6:])
                    content = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                    if content:
                        yield content
