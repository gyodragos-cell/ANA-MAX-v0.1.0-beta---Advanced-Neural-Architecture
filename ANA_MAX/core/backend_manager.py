"""
ANA MAX - Backend Manager (Auto-Refresh + Fallback)
===================================================
Sistem inteligent de management backend cu:
- Auto-refresh token-uri Duck.ai
- Fallback la Ollama local daca Duck.ai esueaza
- Quality scoring per backend
- Switch transparent la failure
"""

import json
import logging
import requests
import time
import urllib3
from typing import Optional, Dict, Any
from enum import Enum

from core.session_logger import log_action, log_result, log_error, log_pattern, log_next_step

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class BackendStatus(Enum):
    """Status backend."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"
    UNKNOWN = "unknown"


class BackendType(Enum):
    """Tipuri backend."""
    DUCK_AI = "duck_ai"
    OLLAMA = "ollama"
    OPENROUTER = "openrouter"


class BackendManager:
    """Manager inteligent pentru backend-uri multiple."""
    
    def __init__(self):
        self.backends = {
            BackendType.DUCK_AI: {
                "enabled": True,
                "status": BackendStatus.UNKNOWN,
                "quality_score": 1.0,
                "last_success": None,
                "last_failure": None,
                "failure_count": 0,
                "url": "https://duck.ai/duckchat/v1/chat",
                "headers": self._get_duck_headers()
            },
            BackendType.OLLAMA: {
                "enabled": True,
                "status": BackendStatus.UNKNOWN,
                "quality_score": 0.8,  # Local, dar mai putin capabil
                "last_success": None,
                "last_failure": None,
                "failure_count": 0,
                "url": "http://127.0.0.1:11434/api/chat",
                "headers": {"Content-Type": "application/json"}
            },
            BackendType.OPENROUTER: {
                "enabled": False,  # Dezactivat pana la configurare
                "status": BackendStatus.UNKNOWN,
                "quality_score": 0.9,
                "last_success": None,
                "last_failure": None,
                "failure_count": 0,
                "url": "https://openrouter.ai/api/v1/chat/completions",
                "headers": {"Content-Type": "application/json"}
            }
        }
        self.current_backend = BackendType.DUCK_AI
        self.logger = logging.getLogger("BACKEND_MANAGER")
        
    def _get_duck_headers(self) -> Dict[str, str]:
        """Returneaza header-e Duck.ai (static + token-uri dinamice actualizate 2026-08-02 19:00)."""
        return {
            "Host": "duck.ai",
            "x-fe-version": "serp_20260731_115654_ET-3580966696c1be28c2bd21ce73c36ce330db74db",
            "x-fe-signals": "eyJzdGFydCI6MTc4NTY4OTk4OTMzMSwiZXZlbnRzIjpbeyJuYW1lIjoic3RhcnROZXdDaGF0X2ZyZWUiLCJkZWx0YSI6MTExfSx7Im5hbWUiOiJhY3Rpb24iLCJkZWx0YSI6MTc3NTgsInRydXN0ZWQiOnRydWV9XSwiZW5kIjoyMDc4MX0=",
            "sec-ch-ua-platform": '"Windows"',
            "sec-ch-ua": '"Not=A?Brand";v="99", "Brave";v="151", "Chromium";v="151"',
            "x-ddg-journey-id": "fe0f225323f9acbc94dfa639741c0e7a",
            "x-vqd-hash-1": "eyJzZXJ2ZXJfaGFzaGVzIjpbImFDckduVldVQ3dTNXhMMnZVMzBra2poQ1RIR0RpaXJVblpqdjBUbmdEWDg9IiwiMW1BSjg4N243a0F1dnltU3FYZ1l2NzFMZStSVVF5RkxPbitMRzVVUjhNRT0iLCJCWDA4akFFL2pnSmMyK0UzeEV4UlhmcUtMYVdpRURzR3lGS1JkOEdvUkYwPSJdLCJjbGllbnRfaGFzaGVzIjpbIlFKVnZDUGJKcjRPQUxzMGlZNFhHZUtCdm1WNktHZldjMVhXcHBNYXN3b2M9IiwidjM5QzRUUjVtclFZaHd6Mjhtbkd2dnRlS3dKbHY3NW9MYmpIQ0F1U0l3Zz0iLCJQOGZObFI3b1k4K1MvSnA5QmxZQ0J0MFFEY2RvWTBGM2pqOVZlZGl2RXBnPSJdLCJzaWduYWxzIjp7fSwibWV0YSI6eyJ2IjoiNCIsImNoYWxsZW5nZV9pZCI6IjJhNzVhNjcxYzA5OGZmNjY0ZTY4MTZlMmY0Y2YwNThhNGVlNzU3ZGExMzlhNzJkNzBjNmU4MzgzMGQ3MDcxMmJweGp6ciIsInRpbWVzdGFtcCI6IjE3ODU2ODk5ODk0NjUiLCJkZWJ1ZyI6Ik9cdTAwMWYiLCJvcmlnaW4iOiJodHRwczovL2R1Y2suYWkiLCJzdGFjayI6IkVycm9yXG5hdCBsIChodHRwczovL2R1Y2suYWkvZGlzdC9kdWNrYWktZGlzdC9lbnRyeS5kdWNrYWkuZDcwY2Q5N2Y1ZWZmOWQ5NzZjOWIuanM6MjoxNjA2MjIzKVxuYXQgYXN5bmMgaHR0cHM6Ly9kdWNrLmFpL2Rpc3QvZHVja2FpLWRpc3QvZW50cnkuZHVja2FpLmQ3MGNkOTdmNWVmZjlkOTc2YzliLmpzOjI6MTQzMDE5OSIsImR1cmF0aW9uIjoiMTEifX0=",
            "sec-ch-ua-mobile": "?0",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36",
            "accept": "text/event-stream",
            "dnt": "1",
            "content-type": "application/json",
            "sec-gpc": "1",
            "origin": "https://duck.ai",
            "sec-fetch-site": "same-origin",
            "sec-fetch-mode": "cors",
            "sec-fetch-dest": "empty",
            "referer": "https://duck.ai/",
            "accept-language": "en-US,en;q=0.5",
            "priority": "u=1, i"
        }
    
    def update_duck_tokens(self, tokens: Dict[str, str]):
        """Actualizeaza token-uri dinamice Duck.ai."""
        log_action("Updating Duck.ai dynamic tokens", tokens)
        self.backends[BackendType.DUCK_AI]["headers"].update(tokens)
        log_result("Duck.ai tokens updated successfully", success=True)
    
    def health_check(self, backend_type: BackendType) -> BackendStatus:
        """Verifica sanatatea unui backend."""
        backend = self.backends[backend_type]
        
        if not backend["enabled"]:
            return BackendStatus.FAILED
        
        try:
            # Simplu health check - doar ping
            response = requests.get(
                backend["url"].replace("/chat", "/status"),
                timeout=5,
                verify=False
            )
            
            if response.status_code == 200:
                backend["status"] = BackendStatus.HEALTHY
                return BackendStatus.HEALTHY
            else:
                backend["status"] = BackendStatus.DEGRADED
                return BackendStatus.DEGRADED
                
        except Exception as e:
            backend["status"] = BackendStatus.FAILED
            backend["failure_count"] += 1
            backend["last_failure"] = time.time()
            log_error(f"Health check failed for {backend_type.value}", e)
            return BackendStatus.FAILED
    
    def send_chat_request(self, messages: list, backend_type: Optional[BackendType] = None) -> Dict[str, Any]:
        """Trimite request chat cu auto-fallback."""
        backend_to_use = backend_type or self.current_backend
        
        log_action(f"Sending chat request via {backend_to_use.value}", {
            "backend": backend_to_use.value,
            "message_count": len(messages)
        })
        
        # Incearca backend-ul principal
        result = self._try_backend(backend_to_use, messages)
        
        # Daca esueaza, incearca fallback
        if not result["success"]:
            log_pattern(f"{backend_to_use.value} failed, trying fallback", "WARNING", result)
            
            # Determina fallback order
            fallback_order = self._get_fallback_order(backend_to_use)
            
            for fallback_backend in fallback_order:
                if self.backends[fallback_backend]["enabled"]:
                    log_action(f"Trying fallback: {fallback_backend.value}")
                    result = self._try_backend(fallback_backend, messages)
                    if result["success"]:
                        self.current_backend = fallback_backend
                        log_result(f"Switched to fallback backend: {fallback_backend.value}", success=True)
                        break
        
        return result
    
    def _try_backend(self, backend_type: BackendType, messages: list) -> Dict[str, Any]:
        """Incearca un singur backend."""
        backend = self.backends[backend_type]
        
        try:
            payload = self._build_payload(backend_type, messages)
            
            response = requests.post(
                backend["url"],
                headers=backend["headers"],
                json=payload,
                stream=True,
                verify=False,
                timeout=60
            )
            
            if response.status_code == 200:
                # Parseaza raspunsul
                full_text = self._parse_stream_response(response)
                
                backend["last_success"] = time.time()
                backend["failure_count"] = 0
                backend["quality_score"] = min(1.0, backend["quality_score"] + 0.1)
                
                log_result(f"Backend {backend_type.value} succeeded", success=True, context={
                    "response_length": len(full_text),
                    "quality_score": backend["quality_score"]
                })
                
                return {
                    "success": True,
                    "content": full_text,
                    "backend": backend_type.value,
                    "quality_score": backend["quality_score"]
                }
            else:
                backend["failure_count"] += 1
                backend["quality_score"] = max(0.0, backend["quality_score"] - 0.2)
                
                log_error(f"Backend {backend_type.value} returned {response.status_code}", 
                         context={"status": response.status_code, "body": response.text[:200]})
                
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}",
                    "backend": backend_type.value
                }
                
        except Exception as e:
            backend["failure_count"] += 1
            backend["quality_score"] = max(0.0, backend["quality_score"] - 0.2)
            
            log_error(f"Backend {backend_type.value} exception", e)
            
            return {
                "success": False,
                "error": str(e),
                "backend": backend_type.value
            }
    
    def _build_payload(self, backend_type: BackendType, messages: list) -> Dict[str, Any]:
        """Construieste payload specific backend-ului."""
        if backend_type == BackendType.DUCK_AI:
            # Duck.ai payload cu durableStream static
            return {
                "model": "gpt-5.4-nano",
                "metadata": {
                    "toolChoice": {
                        "NewsSearch": False,
                        "VideosSearch": False,
                        "LocalSearch": False,
                        "WeatherForecast": False
                    }
                },
                "messages": messages,
                "canUseTools": True,
                "reasoningEffort": "none",
                "canUseApproxLocation": None,
                "canDelegateImageGeneration": None,
                "durableStream": {
                    "messageId": "330a9bba-7e3f-4cae-9bc6-3600fe7dc878",
                    "conversationId": "82fb62bb-758b-4c17-b6db-5334b2b83854",
                    "publicKey": {
                        "alg": "RSA-OAEP-256",
                        "e": "AQAB",
                        "ext": True,
                        "key_ops": ["encrypt"],
                        "kty": "RSA",
                        "n": "pANL1PLHhmGepTU9B-E7ypklzrt5i6EAuE1YnDWjqPqsZm9pW4M62f4M_4sauzO-R3_kMhG1gQgTAKNsn_dSdsJxAdcXFGEs_87rzq2UXHm2Tpak0ag-PuDR0cuW95O4PHZFmoliYEALme6VSzyrc3gYbvz9s7u-Fl5jh9foXfJWWKp1yhv5MQJlgDR1Oy5LCqq686ToJsvjycDfJLbNP-hnFewjLgZda_Z-BQgDXOH7Z9IEsZvo-57Xo3aOsve5jzPIixKakCYqY2eE0td7CYrVMnLAVCn7KgEgsTMlvTBGH0CjT5OrEUbNvaCASrPMCNaIamRtbTwvOb6hZA8vsQ",
                        "use": "enc"
                    }
                }
            }
        elif backend_type == BackendType.OLLAMA:
            return {
                "model": "qwen2.5-coder:7b",
                "messages": messages,
                "stream": True
            }
        else:
            return {
                "model": "anthropic/claude-3.5-sonnet",
                "messages": messages,
                "stream": True
            }
    
    def _parse_stream_response(self, response) -> str:
        """Parseaza raspunsul stream."""
        full_text = ""
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith("data: ") and "DONE" not in line_str:
                    try:
                        data = json.loads(line_str[6:])
                        if "message" in data:
                            full_text += data["message"]
                        elif "choices" in data and data["choices"]:
                            delta = data["choices"][0].get("delta", {})
                            if "content" in delta:
                                full_text += delta["content"]
                    except:
                        continue
        return full_text
    
    def _get_fallback_order(self, failed_backend: BackendType) -> list:
        """Returneaza ordinea de fallback."""
        if failed_backend == BackendType.DUCK_AI:
            return [BackendType.OLLAMA, BackendType.OPENROUTER]
        elif failed_backend == BackendType.OLLAMA:
            return [BackendType.DUCK_AI, BackendType.OPENROUTER]
        else:
            return [BackendType.DUCK_AI, BackendType.OLLAMA]
    
    def get_status_report(self) -> Dict[str, Any]:
        """Returneaza raport status complet."""
        return {
            "current_backend": self.current_backend.value,
            "backends": {
                bt.value: {
                    "status": bd["status"].value,
                    "quality_score": bd["quality_score"],
                    "failure_count": bd["failure_count"],
                    "enabled": bd["enabled"]
                }
                for bt, bd in self.backends.items()
            }
        }


# Singleton global
_backend_manager: Optional[BackendManager] = None


def get_backend_manager() -> BackendManager:
    """Returneaza instanta globala BackendManager."""
    global _backend_manager
    if _backend_manager is None:
        _backend_manager = BackendManager()
    return _backend_manager
