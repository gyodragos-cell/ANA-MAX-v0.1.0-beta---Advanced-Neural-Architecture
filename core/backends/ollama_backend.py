from __future__ import annotations

import logging
import subprocess
from typing import Any

from core.config import config

logger = logging.getLogger(__name__)


def init(agent: Any) -> None:
    """Initialize the local Ollama backend."""
    import requests

    api_url = config.get("ai.ollama.api_url", "http://127.0.0.1:11434/api/generate")
    host = api_url.split("/api/", 1)[0]

    try:
        response = requests.get(f"{host}/api/tags", timeout=5)
        if response.status_code != 200:
            raise ConnectionError("Ollama nu raspunde corect")
    except requests.exceptions.ConnectionError:
        raise ConnectionError("Ollama nu ruleaza! Porneste-l cu: ollama serve")

    agent.ai_client = {
        "url": api_url,
        "model": config.get("ai.ollama.model", "mistral:7b"),
    }

    load_model(agent)
    logger.info("Ollama initialized with model: %s", agent.ai_client["model"])


def load_model(agent: Any) -> None:
    """Warn if the configured Ollama model is missing."""
    model_name = agent.ai_client["model"]

    try:
        result = subprocess.run(
            ["ollama", "ps"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if model_name in result.stdout:
            logger.info("Model %s deja incarcat", model_name)
            return

        installed = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if model_name in installed.stdout:
            logger.info(
                "Modelul %s este instalat si va fi incarcat automat la prima cerere.",
                model_name,
            )
            return

        logger.warning("Modelul %s nu este instalat in Ollama.", model_name)
        logger.warning(
            "Ruleaza 'ollama pull %s' sau 'ollama run %s' inainte de a folosi ANA.",
            model_name,
            model_name,
        )
    except Exception as exc:
        logger.error(f"Eroare verificare model {model_name}: {exc}")


def send(agent: Any, message: str) -> str:
    """Send a prompt to the Ollama generate endpoint."""
    import requests

    history = agent.memory.get_conversation_history(agent.session_id, limit=10)
    messages = [{"role": "system", "content": agent._get_system_prompt()}]

    for msg in history:
        role = "assistant" if msg["role"] == "model" else msg["role"]
        messages.append({"role": role, "content": msg["content"]})

    messages.append({"role": "user", "content": message})
    prompt = agent._format_messages_to_prompt(messages)

    payload = {
        "model": agent.ai_client["model"],
        "prompt": prompt,
        "stream": False,
    }

    try:
        response = requests.post(agent.ai_client["url"], json=payload, timeout=120)
        if response.status_code != 200:
            raise Exception(f"Ollama error: {response.status_code}")

        result = response.json()
        return result.get("response", "(fara raspuns)")
    except Exception as exc:
        logger.error(f"Eroare Ollama communication: {exc}")
        raise
