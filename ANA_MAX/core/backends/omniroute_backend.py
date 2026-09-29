"""
omniroute_backend.py
=====================
ANA MAX OmniRoute Backend — Enterprise Edition.

Features:
  - Access to 230+ models via OmniRoute
  - Local endpoint (localhost:20128/v1)
  - API key authentication
  - Chat completions
  - Model routing (auto/best-coding, auto/best-reasoning, etc.)
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional
import requests

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

DEFAULT_BASE_URL = "http://localhost:20128/v1"
DEFAULT_MODEL = "oc/deepseek-v4-flash-free"
DEFAULT_API_KEY = os.environ.get("OMNIROUTE_API_KEY", "sk-68d41781bd175781-48f687-31b4501a")

DEFAULT_SYSTEM_PROMPT = (
    "You are a helpful AI assistant."
)

# ---------------------------------------------------------------------------
# OmniRoute Client
# ---------------------------------------------------------------------------

class OmniRouteClient:
    """Client pentru OmniRoute API."""
    
    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url.rstrip()  # Remove trailing whitespace
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def chat_completion(self, model: str, messages: list, **kwargs) -> dict:
        """Executa chat completion cu exponential backoff pentru 500 errors."""
        import time
        max_retries = 3
        base_timeout = 30
        retry_count = 0

        while retry_count < max_retries:
            try:
                payload = {
                    "model": model,
                    "messages": messages,
                    "stream": False,  # Disable streaming in payload
                    **kwargs
                }
                # Compact payload to reduce request size
                if "tools" in payload and len(str(payload.get("tools", []))) > 10000:
                    logger.warning("Tool descriptions too large, truncating for OmniRoute")
                    payload["tools"] = []  # Truncate large tool descriptions

                timeout = base_timeout * (2 ** retry_count)  # Exponential backoff: 30s, 60s, 120s
                logger.info(f"OmniRoute request: URL={self.base_url}/chat/completions, model={model}, retry={retry_count}/{max_retries}, timeout={timeout}s")
                response = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=payload,
                    timeout=timeout,
                    stream=False  # Disable streaming to get JSON response
                )
                logger.info(f"OmniRoute response: status={response.status_code}, body={response.text[:500]}")

                # Handle 500 errors specifically
                if response.status_code >= 500:
                    if retry_count < max_retries - 1:
                        retry_count += 1
                        wait_time = 2 ** retry_count  # Exponential backoff: 2s, 4s, 8s
                        logger.warning(f"OmniRoute returned {response.status_code}, retrying in {wait_time}s...")
                        time.sleep(wait_time)
                        continue
                    else:
                        logger.error(f"OmniRoute 500 error after {max_retries} retries, falling back to Ollama")
                        return {"error": f"OmniRoute 500 error after {max_retries} retries", "fallback_needed": True}

                response.raise_for_status()
                return response.json()

            except requests.exceptions.Timeout as e:
                if retry_count < max_retries - 1:
                    retry_count += 1
                    wait_time = 2 ** retry_count
                    logger.warning(f"OmniRoute timeout, retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"OmniRoute timeout after {max_retries} retries, falling back to Ollama")
                    return {"error": f"OmniRoute timeout after {max_retries} retries", "fallback_needed": True}

            except Exception as e:
                logger.error(f"Chat completion failed: {e}")
                return {"error": str(e)}

        return {"error": "Max retries exceeded"}
    
    def list_models(self) -> list:
        """Listeaza toate modelele disponibile."""
        try:
            response = requests.get(f"{self.base_url}/models", headers=self.headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data.get("data", [])
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            return []

# ---------------------------------------------------------------------------
# OmniRoute Backend
# ---------------------------------------------------------------------------

_client: Optional[OmniRouteClient] = None

def _get_client() -> OmniRouteClient:
    """Returneaza instanta clientului OmniRoute."""
    global _client
    if _client is None:
        api_key = os.environ.get("OMNIROUTE_API_KEY", DEFAULT_API_KEY)
        base_url = os.environ.get("OMNIROUTE_ENDPOINT", DEFAULT_BASE_URL)
        _client = OmniRouteClient(api_key, base_url)
    return _client

def generate(
    messages: List[Dict[str, str]],
    model: str = DEFAULT_MODEL,
    temperature: float = 0.7,
    max_tokens: int = 2000,
    tools: Optional[List[Dict]] = None,
    **kwargs
) -> Dict[str, Any]:
    """Genereaza raspuns folosind OmniRoute cu auto-routing nativ."""
    client = _get_client()
    
    # Foloseste modelul specific (nu suprascrie cu auto-routing)
    
    # Adauga system prompt daca nu exista
    if messages and messages[0].get("role") != "system":
        messages.insert(0, {"role": "system", "content": DEFAULT_SYSTEM_PROMPT})
    
    # Executa chat completion
    result = client.chat_completion(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        tools=tools,
        **kwargs
    )
    
    if "error" in result:
        return {
            "content": f"Error: {result['error']}",
            "finish_reason": "error"
        }
    
    # Extrage continutul
    choices = result.get("choices", [])
    if choices:
        content = choices[0].get("message", {}).get("content", "")
        finish_reason = choices[0].get("finish_reason", "stop")
    else:
        content = ""
        finish_reason = "stop"
    
    return {
        "content": content,
        "finish_reason": finish_reason,
        "model": model,
        "usage": result.get("usage", {})
    }

def get_available_models() -> List[str]:
    """Returneaza lista de modele disponibile."""
    client = _get_client()
    models = client.list_models()
    return [m.get("id", "") for m in models if m.get("id")]

def health_check() -> Dict[str, Any]:
    """Verifica sanatatea backend-ului OmniRoute."""
    try:
        client = _get_client()
        models = client.list_models()
        return {
            "status": "healthy",
            "models_count": len(models),
            "endpoint": client.base_url
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }

# ---------------------------------------------------------------------------
# Init function (called by agent.py)
# ---------------------------------------------------------------------------

def init(agent) -> None:
    """Initialize OmniRoute backend for the given agent."""
    logger.info("OmniRoute backend initializat")
    agent._client = {"type": "omniroute", "url": DEFAULT_BASE_URL, "model": DEFAULT_MODEL}

def send(agent, message: str) -> str:
    """Trimite mesaj la backend-ul OmniRoute si returneaza raspunsul."""
    try:
        # Construieste mesajul pentru API
        messages = [{"role": "user", "content": message}]
        
        # Obtine tools de la agent daca disponibile
        tools = getattr(agent, 'available_tools', None)
        
        # Genereaza raspuns
        result = generate(messages, model=DEFAULT_MODEL, tools=tools)
        
        if "error" in result:
            return f"Eroare OmniRoute: {result['error']}"
        
        return result.get("content", "")
    except Exception as e:
        logger.error(f"OmniRoute send failed: {e}")
        return f"Eroare la comunicarea cu OmniRoute: {str(e)}"
