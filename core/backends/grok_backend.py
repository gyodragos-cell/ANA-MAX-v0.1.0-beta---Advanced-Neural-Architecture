from __future__ import annotations

import logging
import os
from typing import Any, List

from core.backends.common import read_nonempty_lines
from core.config import config

logger = logging.getLogger(__name__)


def init(agent: Any) -> None:
    """Initialize Grok using the OpenAI-compatible xAI API."""
    from openai import OpenAI  # type: ignore

    agent.grok_api_keys = []
    agent.grok_current_key_index = 0

    key_file = config.get("ai.grok.api_key_file", "keys/grok_keys.txt")
    if os.path.exists(key_file):
        try:
            agent.grok_api_keys = read_nonempty_lines(key_file)
        except Exception as exc:
            logger.warning(f"Nu pot citi fisierul de chei Grok ({key_file}): {exc}")

    api_key_env_name = config.get("ai.grok.api_key_env", "XAI_API_KEY")
    env_key = os.environ.get(api_key_env_name)
    if env_key and env_key not in agent.grok_api_keys:
        agent.grok_api_keys.append(env_key)

    if not agent.grok_api_keys:
        raise ValueError(
            f"Nicio cheie Grok nu a fost gasita.\n"
            f"- Adauga cel putin o cheie in {key_file} (cate una pe linie), SAU\n"
            f"- seteaza variabila de mediu {api_key_env_name}.\n"
            f"Chei poti genera din consola xAI: https://console.x.ai/"
        )

    base_url = config.get("ai.grok.base_url", "https://api.x.ai/v1")
    model = config.get("ai.grok.model", "grok-4-1-fast-reasoning")

    agent.ai_client = OpenAI(
        api_key=agent.grok_api_keys[agent.grok_current_key_index],
        base_url=base_url,
    )
    agent.grok_model = model

    logger.info(
        "Grok backend initializat (model: %s, chei: %s)",
        model,
        len(agent.grok_api_keys),
    )


def rotate_key(agent: Any) -> bool:
    """Rotate to the next Grok API key."""
    from openai import OpenAI  # type: ignore

    grok_api_keys: List[str] = getattr(agent, "grok_api_keys", [])
    if len(grok_api_keys) <= 1:
        logger.warning("Nu exista alte chei Grok pentru rotatie.")
        return False

    base_url = config.get("ai.grok.base_url", "https://api.x.ai/v1")

    agent.grok_current_key_index = (agent.grok_current_key_index + 1) % len(grok_api_keys)
    new_key = grok_api_keys[agent.grok_current_key_index]

    try:
        agent.ai_client = OpenAI(api_key=new_key, base_url=base_url)
        logger.info(
            "Rotatie cheie Grok reusita. Se foloseste cheia #%s",
            agent.grok_current_key_index + 1,
        )
        return True
    except Exception as exc:
        logger.error(f"Eroare la rotatia cheii Grok: {exc}")
        return False


def send(agent: Any, message: str) -> str:
    """Send a prompt to Grok via the OpenAI-compatible client."""
    history = agent.memory.get_conversation_history(agent.session_id, limit=20)
    messages = [{"role": "system", "content": agent._get_system_prompt()}]

    for msg in history:
        role = "assistant" if msg["role"] == "model" else msg["role"]
        messages.append({"role": role, "content": msg["content"]})

    messages.append({"role": "user", "content": message})

    try:
        completion = agent.ai_client.chat.completions.create(
            model=getattr(agent, "grok_model", config.get("ai.grok.model", "grok-4-1-fast-reasoning")),
            messages=messages,
            timeout=60,
        )
    except Exception as exc:
        error_str = str(exc).lower()
        if "429" in error_str or "insufficient_quota" in error_str or "rate limit" in error_str:
            logger.warning("Grok rate-limit / cota atinsa. Incerc rotatia cheii...")
            if rotate_key(agent):
                completion = agent.ai_client.chat.completions.create(
                    model=getattr(
                        agent,
                        "grok_model",
                        config.get("ai.grok.model", "grok-4-1-fast-reasoning"),
                    ),
                    messages=messages,
                    timeout=60,
                )
            else:
                raise
        else:
            raise

    content = completion.choices[0].message.content
    if isinstance(content, list):
        return "".join(part.get("text", "") for part in content)
    return content
