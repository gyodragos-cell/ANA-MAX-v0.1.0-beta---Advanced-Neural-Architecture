"""
ANA MAX - Web AI Bridge Tool
===========================
Tool optional pentru conectare la provideri externi doar prin chei din mediu.
Suporta rotatie automata intre modele pentru a evita rate limits.
"""

from __future__ import annotations

import logging
import os
import random
import time
from typing import Any, Dict, Optional

import requests

from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus

logger = logging.getLogger(__name__)

ACTIVE_MODELS = [
    "big-pickle",
    "minimax-m2.5-free",
    "mimo-v2-pro-free",
    "mimo-v2-omni-free",
    "mimo-v2-flash-free",
    "qwen3.6-plus-free",
    "nemotron-3-super-free",
    "trinity-large-preview-free",
]

RESERVE_MODELS = [
    "gpt-5-nano",
    "gemini-3-flash",
]

PREMIUM_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-3-flash-preview",
    "gemma-3-4b",
    "gemma-3-12b",
    "gemma-3-27b",
    "gemma-3n-4b",
    "gemma-3n-2b",
]

ANTIGRAVITY_MODELS = [
    "antigravity-claude-sonnet-4-6",
    "antigravity-claude-opus-4-6-thinking",
    "antigravity-gemini-3-pro",
    "antigravity-gemini-3-flash",
    "antigravity-gemini-3.1-pro",
]

ALL_MODELS = ACTIVE_MODELS + RESERVE_MODELS + PREMIUM_MODELS + ANTIGRAVITY_MODELS

MAX_CONSECUTIVE_USES = 5
RESERVE_PERCENT = 30
API_KEY_COOLDOWN = 120


def load_api_keys() -> list[str]:
    keys_env = os.environ.get("OPENCODE_ZEN_API_KEYS") or os.environ.get("OPENCODE_ZEN_API_KEY") or ""
    keys = [k.strip() for k in keys_env.split(",") if k.strip()]
    return keys


ZEN_API_KEYS = load_api_keys()


class WebAIBridgeTool(Tool):
    def __init__(self) -> None:
        self.grok_conversations: dict[str, list[dict[str, str]]] = {}
        self.model_usage_count: Dict[str, int] = {m: 0 for m in ALL_MODELS}
        self.current_model_index = 0
        self.last_used_model: Optional[str] = None
        self.consecutive_failures = 0
        self.cooldown_until = 0
        self.api_keys = load_api_keys()
        self.current_key_index = 0
        self.key_failures: Dict[int, float] = {}
        
    def _get_next_api_key(self) -> Optional[str]:
        if not self.api_keys:
            return None
        
        now = time.time()
        for i, key in enumerate(self.api_keys):
            if key in self.key_failures:
                if now - self.key_failures[key] < API_KEY_COOLDOWN:
                    continue
            
            self.current_key_index = i
            return key
        
        return self.api_keys[self.current_key_index]
    
    def _report_key_failure(self, key: str) -> None:
        idx = self.api_keys.index(key) if key in self.api_keys else -1
        if idx >= 0:
            self.key_failures[key] = time.time()
            self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="web_ai_bridge",
            description="Conecteaza ANA la provideri AI externi configurati prin variabile de mediu.",
            parameters=[
                ToolParameter(
                    name="operation",
                    description="Operatie suportata",
                    type="string",
                    required=True,
                    choices=["query_gemini", "query_grok", "continue_grok_chat", "query_aimlapi", "compare_responses", "query_gemini_auto", "query_opencode_zen", "query_antigravity"],
                ),
                ToolParameter(
                    name="message",
                    description="Mesajul trimis providerului",
                    type="string",
                    required=False,
                    default="",
                ),
                ToolParameter(
                    name="chat_id",
                    description="ID de conversatie pentru Grok",
                    type="string",
                    required=False,
                    default="default",
                ),
                ToolParameter(
                    name="model",
                    description="Model optional pentru AIMLAPI sau Gemini",
                    type="string",
                    required=False,
                    default="big-pickle",
                ),
                ToolParameter(
                    name="use_reserve",
                    description="Permite folosirea modelelor din rezerva (30%)",
                    type="string",
                    required=False,
                    default="false",
                ),
            ],
            category="ai_bridge",
        )

    def execute(
        self,
        operation: str,
        message: str = "",
        chat_id: str = "default",
        model: str = "gemini-2.5-flash",
        use_reserve: str = "false",
        **_: Any,
    ) -> ToolResult:
        if operation == "query_gemini":
            return self._query_gemini(message, model)
        if operation == "query_gemini_auto":
            return self._query_gemini_auto(message, use_reserve == "true")
        if operation == "query_grok":
            return self._query_grok(message)
        if operation == "continue_grok_chat":
            return self._continue_grok_chat(chat_id, message)
        if operation == "query_aimlapi":
            return self._query_aimlapi(message, model)
        if operation == "compare_responses":
            return self._compare_ai_responses(message)
        if operation == "query_opencode_zen":
            return self._query_opencode_zen(message, model)
        if operation == "query_antigravity":
            return self._query_antigravity(message, model)
        return ToolResult(status=ToolStatus.ERROR, error=f"Operatie necunoscuta: {operation}")

    def _get_next_model(self, allow_reserve: bool = False) -> tuple[str, str]:
        if time.time() < self.cooldown_until:
            available = [m for m in ACTIVE_MODELS if self.model_usage_count.get(m, 0) < MAX_CONSECUTIVE_USES]
            if available:
                model = random.choice(available)
                return (model, "opencode_zen")
            return ("big-pickle", "opencode_zen")

        available_models = ACTIVE_MODELS.copy()
        
        if allow_reserve and random.randint(1, 100) > (100 - RESERVE_PERCENT):
            available_models.extend(RESERVE_MODELS)
        
        filtered = [m for m in available_models if self.model_usage_count.get(m, 0) < MAX_CONSECUTIVE_USES]
        
        if not filtered:
            for m in ACTIVE_MODELS:
                self.model_usage_count[m] = 0
            filtered = ACTIVE_MODELS.copy()
        
        selected = random.choice(filtered)
        self.last_used_model = selected
        
        if selected in ACTIVE_MODELS:
            return (selected, "opencode_zen")
        elif selected in ANTIGRAVITY_MODELS:
            return (selected, "antigravity")
        else:
            return (selected, "gemini")

    def _query_gemini_auto(self, message: str, allow_reserve: bool = False) -> ToolResult:
        model, provider = self._get_next_model(allow_reserve)
        
        if provider == "opencode_zen":
            result = self._query_opencode_zen(message, model)
        elif provider == "antigravity":
            result = self._query_antigravity(message, model)
        else:
            result = self._query_gemini(message, model)
        
        if result.is_success:
            self.model_usage_count[model] = self.model_usage_count.get(model, 0) + 1
            self.consecutive_failures = 0
        else:
            self.consecutive_failures += 1
            if self.consecutive_failures >= 3:
                self.cooldown_until = time.time() + 60
                self.consecutive_failures = 0
        
        return result

    def _query_gemini(self, message: str, model: str = "gemini-2.5-flash") -> ToolResult:
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            return ToolResult(status=ToolStatus.ERROR, error="Lipseste GEMINI_API_KEY sau GOOGLE_API_KEY")
        
        if model not in ALL_MODELS:
            model = "gemini-2.5-flash"
        
        try:
            import google.generativeai as genai

            genai.configure(api_key=api_key)
            model_obj = genai.GenerativeModel(model)
            response = model_obj.generate_content(message)
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"provider": "gemini", "response": response.text if response.text else "", "model": model},
                message=f"Raspuns Gemini obtinut cu modelul {model}.",
            )
        except Exception as exc:
            error_msg = str(exc)
            if "429" in error_msg or "rate" in error_msg.lower():
                self.cooldown_until = time.time() + 120
                return ToolResult(status=ToolStatus.ERROR, error=f"Rate limit atins. Asteapta 2 minute. Model: {model}")
            return ToolResult(status=ToolStatus.ERROR, error=f"Eroare Gemini ({model}): {exc}")

    def _query_grok(self, message: str) -> ToolResult:
        api_key = os.environ.get("XAI_API_KEY")
        if not api_key:
            return ToolResult(status=ToolStatus.ERROR, error="Lipseste XAI_API_KEY")
        try:
            from openai import OpenAI

            client = OpenAI(api_key=api_key, base_url="https://api.x.ai/v1")
            completion = client.chat.completions.create(
                model="grok-3-mini",
                messages=[{"role": "user", "content": message}],
            )
            text = completion.choices[0].message.content or ""
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"provider": "grok", "response": text, "model": "grok-3-mini"},
                message="Raspuns Grok obtinut.",
            )
        except Exception as exc:
            return ToolResult(status=ToolStatus.ERROR, error=f"Eroare Grok: {exc}")

    def _continue_grok_chat(self, chat_id: str, message: str) -> ToolResult:
        api_key = os.environ.get("XAI_API_KEY")
        if not api_key:
            return ToolResult(status=ToolStatus.ERROR, error="Lipseste XAI_API_KEY")
        try:
            from openai import OpenAI

            client = OpenAI(api_key=api_key, base_url="https://api.x.ai/v1")
            messages = self.grok_conversations.get(chat_id, []).copy()
            messages.append({"role": "user", "content": message})
            completion = client.chat.completions.create(model="grok-3-mini", messages=messages)
            text = completion.choices[0].message.content or ""
            messages.append({"role": "assistant", "content": text})
            self.grok_conversations[chat_id] = messages
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"provider": "grok", "response": text, "chat_id": chat_id, "message_count": len(messages)},
                message="Conversatia Grok a fost continuata.",
            )
        except Exception as exc:
            return ToolResult(status=ToolStatus.ERROR, error=f"Eroare Grok chat: {exc}")

    def _query_aimlapi(self, message: str, model: str) -> ToolResult:
        api_key = os.environ.get("AIMLAPI_KEY")
        if not api_key:
            return ToolResult(status=ToolStatus.ERROR, error="Lipseste AIMLAPI_KEY")
        try:
            response = requests.post(
                "https://api.aimlapi.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"model": model, "messages": [{"role": "user", "content": message}], "max_tokens": 1000},
                timeout=30,
            )
            response.raise_for_status()
            payload = response.json()
            text = payload["choices"][0]["message"]["content"]
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"provider": "aimlapi", "response": text, "model": model},
                message="Raspuns AIMLAPI obtinut.",
            )
        except Exception as exc:
            return ToolResult(status=ToolStatus.ERROR, error=f"Eroare AIMLAPI: {exc}")

    def _compare_ai_responses(self, message: str) -> ToolResult:
        gemini = self._query_gemini(message)
        grok = self._query_grok(message)
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={
                "gemini": {"success": gemini.is_success, "data": gemini.data, "error": gemini.error},
                "grok": {"success": grok.is_success, "data": grok.data, "error": grok.error},
            },
            message="Comparatie finalizata.",
        )

    def _query_opencode_zen(self, message: str, model: str = "big-pickle") -> ToolResult:
        api_key = self._get_next_api_key()
        if not api_key:
            return ToolResult(status=ToolStatus.ERROR, error="Lipseste OPENCODE_ZEN_API_KEY")
        
        if model not in ALL_MODELS:
            model = "big-pickle"
        
        try:
            response = requests.post(
                "https://opencode.ai/zen/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"model": model, "messages": [{"role": "user", "content": message}], "max_tokens": 4000},
                timeout=60,
            )
            
            if response.status_code == 429:
                self._report_key_failure(api_key)
                next_key = self._get_next_api_key()
                if next_key and next_key != api_key:
                    response = requests.post(
                        "https://opencode.ai/zen/v1/chat/completions",
                        headers={"Authorization": f"Bearer {next_key}", "Content-Type": "application/json"},
                        json={"model": model, "messages": [{"role": "user", "content": message}], "max_tokens": 4000},
                        timeout=60,
                    )
            
            response.raise_for_status()
            payload = response.json()
            text = payload.get("choices", [{}])[0].get("message", {}).get("content", "")
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"provider": "opencode_zen", "response": text, "model": model},
                message=f"Raspuns OpenCode Zen obtinut cu {model}.",
            )
        except Exception as exc:
            self._report_key_failure(api_key)
            return ToolResult(status=ToolStatus.ERROR, error=f"Eroare OpenCode Zen: {exc}")

    def _query_antigravity(self, message: str, model: str = "antigravity-gemini-3-flash") -> ToolResult:
        api_key = os.environ.get("ANTIGRAVITY_API_KEY")
        if not api_key:
            return ToolResult(status=ToolStatus.ERROR, error="Lipseste ANTIGRAVITY_API_KEY")
        
        if model not in ANTIGRAVITY_MODELS:
            model = "antigravity-gemini-3-flash"
        
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            model_obj = genai.GenerativeModel(model)
            response = model_obj.generate_content(message)
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"provider": "antigravity", "response": response.text if response.text else "", "model": model},
                message=f"Raspuns Antigravity obtinut cu {model}.",
            )
        except Exception as exc:
            return ToolResult(status=ToolStatus.ERROR, error=f"Eroare Antigravity ({model}): {exc}")
