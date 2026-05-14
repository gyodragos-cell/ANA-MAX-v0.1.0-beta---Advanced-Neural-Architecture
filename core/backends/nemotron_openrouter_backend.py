"""
nemotron_openrouter_backend.py
==============================
Backend OpenRouter pentru modelul Nemotron.
Separat de OpenCode si compatibil cu ANAAgent.
"""
from __future__ import annotations

import logging
import os
import time
from typing import Any

from core.config import config

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "nvidia/nemotron-3-super-120b-a12b:free"
API_KEY_COOLDOWN_SECONDS = 120
DEFAULT_SYSTEM_PROMPT = (
    "Esti ANA MAX ruland pe backend Nemotron. "
    "Raspunde implicit in limba romana, clar si util. "
    "Daca utilizatorul cere alta limba, respecta cererea."
)


def _load_api_keys() -> list[str]:
    keys: list[str] = []
    for raw in (os.environ.get("OPENROUTER_API_KEYS", ""), os.environ.get("OPENROUTER_API_KEY", "")):
        for item in raw.split(","):
            key = item.strip()
            if key and key not in keys:
                keys.append(key)
    return keys


def _get_available_keys(agent: Any) -> list[str]:
    now = time.time()
    available: list[str] = []
    failures = getattr(agent, "nemotron_key_failures", {})
    for key in agent.nemotron_api_keys:
        failed_at = failures.get(key)
        if failed_at is None or now - failed_at >= API_KEY_COOLDOWN_SECONDS:
            available.append(key)
    return available or list(agent.nemotron_api_keys)


def _should_retry_with_next_key(exc: Exception) -> bool:
    status = getattr(exc, "status_code", None) or getattr(exc, "status", None)
    if status in {401, 402, 429}:
        return True

    text = str(exc).lower()
    retry_terms = (
        "rate limit",
        "quota",
        "credit",
        "billing",
        "invalid api key",
        "incorrect api key",
        "authentication",
    )
    return any(term in text for term in retry_terms)


def init(agent: Any) -> None:
    try:
        from openai import OpenAI  # noqa: F401
    except ImportError as exc:
        raise ImportError("Pachetul openai este necesar pentru nemotron_openrouter backend.") from exc

    api_keys = _load_api_keys()
    if not api_keys:
        raise ValueError("Lipseste OPENROUTER_API_KEY sau OPENROUTER_API_KEYS pentru Nemotron.")

    agent.nemotron_api_keys = api_keys
    agent.nemotron_key_failures = {}
    agent.nemotron_base_url = config.get("ai.nemotron_openrouter.base_url", DEFAULT_BASE_URL)
    agent.nemotron_model = getattr(agent, "_model_override", None) or config.get(
        "ai.nemotron_openrouter.model",
        DEFAULT_MODEL,
    )
    agent.nemotron_site_url = os.environ.get("OPENROUTER_SITE_URL", "http://localhost").strip() or "http://localhost"
    agent.nemotron_app_name = os.environ.get("OPENROUTER_APP_NAME", "ANA MAX Nemotron").strip() or "ANA MAX Nemotron"
    agent.nemotron_system_prompt = (
        os.environ.get("OPENROUTER_SYSTEM_PROMPT", "").strip() or DEFAULT_SYSTEM_PROMPT
    )
    agent.backend_effective = "nemotron_openrouter"

    logger.info(
        "Nemotron OpenRouter backend initializat (model=%s, chei=%s)",
        agent.nemotron_model,
        len(agent.nemotron_api_keys),
    )


def send(agent: Any, message: str) -> str:
    from openai import OpenAI

    api_keys = getattr(agent, "nemotron_api_keys", None) or _load_api_keys()
    if not api_keys:
        raise ValueError("Lipseste OPENROUTER_API_KEY sau OPENROUTER_API_KEYS pentru Nemotron.")

    model = getattr(agent, "nemotron_model", DEFAULT_MODEL)
    base_url = getattr(agent, "nemotron_base_url", DEFAULT_BASE_URL)
    site_url = getattr(agent, "nemotron_site_url", "http://localhost")
    app_name = getattr(agent, "nemotron_app_name", "ANA MAX Nemotron")
    system_prompt = getattr(agent, "nemotron_system_prompt", DEFAULT_SYSTEM_PROMPT)

    last_error: Exception | None = None
    for index, api_key in enumerate(_get_available_keys(agent), start=1):
        client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            default_headers={
                "HTTP-Referer": site_url,
                "X-Title": app_name,
            },
        )

        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message},
                ],
                max_tokens=2048,
            )
            if response.choices:
                choice = response.choices[0]
                if choice.message and choice.message.content:
                    return choice.message.content
            return "(fara raspuns text de la Nemotron)"
        except Exception as exc:
            last_error = exc
            if _should_retry_with_next_key(exc) and index < len(_get_available_keys(agent)):
                agent.nemotron_key_failures[api_key] = time.time()
                logger.warning("Nemotron key %s failed, rotating to next key: %s", index, exc)
                continue
            break

    raise last_error if last_error else RuntimeError("Nemotron backend failed fara detalii.")
