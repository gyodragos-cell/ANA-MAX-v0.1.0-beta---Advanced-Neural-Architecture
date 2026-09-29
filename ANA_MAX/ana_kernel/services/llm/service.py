from __future__ import annotations

import os
from typing import Any, Mapping

import httpx
from ana.core.error_model.errors import RoutingFailure, ValidationError


class RealLLMService:
    """Real LLM service supporting Ollama, OpenAI-compatible APIs, and Gemini."""

    def __init__(
        self,
        *,
        provider: str = "ollama",
        base_url: str | None = None,
        model: str | None = None,
        api_key: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.provider = provider.lower()
        self.base_url = base_url or self._default_base_url()
        self.model = model or self._default_model()
        self.api_key = api_key or os.getenv("LLM_API_KEY")
        self.timeout = timeout
        self._client: httpx.Client | None = None

    def _default_base_url(self) -> str:
        if self.provider == "ollama":
            return os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
        if self.provider == "openai":
            return os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        if self.provider == "gemini":
            return os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta")
        raise ValidationError(f"Unsupported provider: {self.provider}", source="llm")

    def _default_model(self) -> str:
        if self.provider == "ollama":
            return os.getenv("OLLAMA_MODEL", "qwen-ana:7b")
        if self.provider == "openai":
            return os.getenv("OPENAI_MODEL", "gpt-4")
        if self.provider == "gemini":
            return os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        raise ValidationError(f"Unsupported provider: {self.provider}", source="llm")

    @property
    def client(self) -> httpx.Client:
        if self._client is None:
            headers = {}
            if self.api_key:
                if self.provider == "openai":
                    headers["Authorization"] = f"Bearer {self.api_key}"
                elif self.provider == "gemini":
                    headers["x-goog-api-key"] = self.api_key
            self._client = httpx.Client(base_url=self.base_url, headers=headers, timeout=self.timeout)
        return self._client

    def complete(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        """Complete a prompt using the configured LLM provider."""
        prompt = payload.get("prompt")
        if not isinstance(prompt, str) or not prompt:
            raise ValidationError("prompt is required", source="llm")

        messages = payload.get("messages", [])
        if not messages:
            messages = [{"role": "user", "content": prompt}]

        try:
            if self.provider == "ollama":
                return self._ollama_complete(messages)
            if self.provider == "openai":
                return self._openai_complete(messages)
            if self.provider == "gemini":
                return self._gemini_complete(messages)
            raise ValidationError(f"Unsupported provider: {self.provider}", source="llm")
        except httpx.TimeoutException:
            raise RoutingFailure("LLM request timed out", source="llm", details={"provider": self.provider})
        except httpx.HTTPStatusError as exc:
            raise RoutingFailure(
                f"LLM request failed: {exc.response.status_code}",
                source="llm",
                details={"provider": self.provider, "status": exc.response.status_code},
            )
        except Exception as exc:
            raise RoutingFailure(
                f"LLM request failed: {str(exc)}",
                source="llm",
                details={"provider": self.provider},
            )

    def _ollama_complete(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        # Inject the fierce prompt if no system message exists
        has_system = any(msg.get("role") == "system" for msg in messages)
        if not has_system:
            messages.insert(0, {"role": "system", "content": "OUTPUT ONLY VALID JSON. NO TALKING. If options are provided, output only the chosen option number (1, 2, or 3)."})

        response = self.client.post(
            "/api/chat",
            json={
                "model": self.model,
                "messages": messages,
                "stream": False,
            },
        )
        response.raise_for_status()
        data = response.json()
        return {
            "text": data.get("message", {}).get("content", ""),
            "model": self.model,
            "provider": "ollama",
        }

    def _openai_complete(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        response = self.client.post(
            "/chat/completions",
            json={
                "model": self.model,
                "messages": messages,
            },
        )
        response.raise_for_status()
        data = response.json()
        return {
            "text": data.get("choices", [{}])[0].get("message", {}).get("content", ""),
            "model": self.model,
            "provider": "openai",
        }

    def _gemini_complete(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        # Convert OpenAI-style messages to Gemini format
        contents = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                contents.append({"role": "user", "parts": [{"text": f"System: {content}"}]})
            elif role == "user":
                contents.append({"role": "user", "parts": [{"text": content}]})
            elif role == "assistant":
                contents.append({"role": "model", "parts": [{"text": content}]})

        response = self.client.post(
            f"/models/{self.model}:generateContent",
            json={"contents": contents},
        )
        response.raise_for_status()
        data = response.json()
        return {
            "text": data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", ""),
            "model": self.model,
            "provider": "gemini",
        }

    def close(self) -> None:
        if self._client:
            self._client.close()
            self._client = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# Backward compatibility alias
DeterministicLLMService = RealLLMService
