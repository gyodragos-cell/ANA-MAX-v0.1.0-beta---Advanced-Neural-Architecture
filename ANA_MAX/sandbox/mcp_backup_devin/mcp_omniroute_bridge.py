#!/usr/bin/env python3
"""
ANA MAX + OmniRoute MCP Bridge
===============================
Expune tool-urile OmniRoute ca server MCP (Model Context Protocol) peste
transport STDIO. Permite ANA MAX sa acceseze cele 230 modele OmniRoute.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import traceback
from typing import Any
import requests

# ---------------------------------------------------------------------------
# Configurare OmniRoute
# ---------------------------------------------------------------------------
OMNIROUTE_API_KEY = os.environ.get("OMNIROUTE_API_KEY", "sk-68d41781bd175781-278821-fcfa512a")
OMNIROUTE_ENDPOINT = os.environ.get("OMNIROUTE_ENDPOINT", "http://localhost:20128/v1")

# ---------------------------------------------------------------------------
# Logging pe stderr
# ---------------------------------------------------------------------------
logging.basicConfig(
    stream=sys.stderr,
    level=os.environ.get("OMNI_MCP_LOG_LEVEL", "INFO"),
    format="%(asctime)s [omni-mcp] %(levelname)s %(message)s",
)
log = logging.getLogger("omni-route-bridge")

# ---------------------------------------------------------------------------
# OmniRoute Client
# ---------------------------------------------------------------------------
class OmniRouteClient:
    """Client pentru OmniRoute API."""
    
    def __init__(self, api_key: str, endpoint: str):
        self.api_key = api_key
        self.endpoint = endpoint
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def list_models(self) -> list:
        """Listeaza toate modelele disponibile."""
        try:
            response = requests.get(f"{self.endpoint}/models", headers=self.headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data.get("data", [])
        except Exception as e:
            log.error(f"Failed to list models: {e}")
            return []
    
    def chat_completion(self, model: str, messages: list, **kwargs) -> dict:
        """Executa chat completion."""
        try:
            payload = {
                "model": model,
                "messages": messages,
                **kwargs
            }
            response = requests.post(
                f"{self.endpoint}/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            log.error(f"Chat completion failed: {e}")
            return {"error": str(e)}
    
    def get_health(self) -> dict:
        """Verifica starea serverului OmniRoute."""
        try:
            response = requests.get(f"{self.endpoint}/models", headers=self.headers, timeout=5)
            return {"status": "healthy" if response.status_code == 200 else "unhealthy"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

# ---------------------------------------------------------------------------
# MCP Server Implementation
# ---------------------------------------------------------------------------
try:
    from mcp.server import Server
    from mcp.types import Tool, TextContent
except ImportError:
    log.error("MCP library not installed. Install with: pip install mcp")
    sys.exit(1)

client = OmniRouteClient(OMNIROUTE_API_KEY, OMNIROUTE_ENDPOINT)

def handle_list_tools() -> list[Tool]:
    """Listeaza tool-urile OmniRoute disponibile."""
    return [
        Tool(
            name="omni_list_models",
            description="Listeaza toate modelele disponibile in OmniRoute (230+ modele)",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="omni_chat",
            description="Executa chat completion cu orice model din OmniRoute",
            inputSchema={
                "type": "object",
                "properties": {
                    "model": {
                        "type": "string",
                        "description": "Modelul de utilizat (ex: gpt-4, claude-3-opus)"
                    },
                    "messages": {
                        "type": "array",
                        "description": "Lista de mesaje pentru chat",
                        "items": {
                            "type": "object",
                            "properties": {
                                "role": {"type": "string"},
                                "content": {"type": "string"}
                            }
                        }
                    },
                    "temperature": {
                        "type": "number",
                        "description": "Temperature pentru sampling (0-2)",
                        "default": 0.7
                    },
                    "max_tokens": {
                        "type": "integer",
                        "description": "Maximum tokens",
                        "default": 1000
                    }
                },
                "required": ["model", "messages"]
            }
        ),
        Tool(
            name="omni_health",
            description="Verifica starea serverului OmniRoute",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        )
    ]

def handle_call_tool(name: str, arguments: dict) -> Any:
    """Executa un tool OmniRoute."""
    try:
        if name == "omni_list_models":
            models = client.list_models()
            return [
                TextContent(
                    type="text",
                    text=json.dumps({
                        "total": len(models),
                        "models": [{"id": m.get("id"), "name": m.get("name")} for m in models[:20]]
                    }, indent=2)
                )
            ]
        
        elif name == "omni_chat":
            model = arguments.get("model")
            messages = arguments.get("messages", [])
            temperature = arguments.get("temperature", 0.7)
            max_tokens = arguments.get("max_tokens", 1000)
            
            result = client.chat_completion(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            return [
                TextContent(
                    type="text",
                    text=json.dumps(result, indent=2)
                )
            ]
        
        elif name == "omni_health":
            health = client.get_health()
            return [
                TextContent(
                    type="text",
                    text=json.dumps(health, indent=2)
                )
            ]
        
        else:
            return [
                TextContent(
                    type="text",
                    text=f"Eroare: Tool necunoscut '{name}'"
                )
            ]
    
    except Exception as exc:
        log.error("Executie %s a esuat: %s\n%s", name, exc, traceback.format_exc())
        return [
            TextContent(
                type="text",
                text=f"Eroare la '{name}': {exc}"
            )
        ]

# ---------------------------------------------------------------------------
# Instantiere server MCP (API 1.0)
# ---------------------------------------------------------------------------
server = Server("omni-route-bridge")


@server.list_tools()
async def _mcp_list_tools() -> list[Tool]:
    """Listeaza tool-urile OmniRoute."""
    return handle_list_tools()


@server.call_tool()
async def _mcp_call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Executa un tool OmniRoute."""
    return handle_call_tool(name, arguments)

# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------
async def main():
    log.info("OmniRoute MCP Bridge pornit")
    log.info(f"Endpoint: {OMNIROUTE_ENDPOINT}")
    log.info(f"API Key: {OMNIROUTE_API_KEY[:20]}...")
    
    # Pornire server peste STDIO (fara health check blocant)
    from mcp.server.stdio import stdio_server
    async with stdio_server() as streams:
        await server.run(*streams, server.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
