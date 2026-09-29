"""
ANA MAX - latent_telepathy_tool.py
====================================
Latent Space Communication (Telepatie Matematica)

Simuleaza comunicarea intre agenti la nivel sub-vocal (fara text).
In loc sa parsam text sau JSON-uri mari, transformam starea/conceptul
intr-un vector matematic comprimat (latent space) si il decodam instant.
"""
from __future__ import annotations

import base64
import json
import logging
import random
import zlib
from typing import Any

from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus

logger = logging.getLogger("ANA.LatentTelepathy")


def _encode_latent_state(payload: dict) -> str:
    """Transforma un dict complex intr-un tensor latent mock si il comprima."""
    raw_json = json.dumps(payload, separators=(',', ':'))
    # Simulam adaugarea de zgomot latent/embedding
    latent_tensor = f"LATENT_TENSOR_V1|{random.random()}|{raw_json}"
    compressed = zlib.compress(latent_tensor.encode('utf-8'), level=9)
    return base64.b85encode(compressed).decode('ascii')


def _decode_latent_state(encoded: str) -> dict:
    """Prelucreaza string-ul b85 si returneaza starea decodata."""
    compressed = base64.b85decode(encoded.encode('ascii'))
    latent_tensor = zlib.decompress(compressed).decode('utf-8')
    parts = latent_tensor.split('|', 2)
    if len(parts) == 3 and parts[0] == "LATENT_TENSOR_V1":
        return json.loads(parts[2])
    raise ValueError("Invalid latent tensor format")


class LatentTelepathyTool(Tool):
    """Comunicare sub-vocala super-rapida pentru agenti."""

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="latent_telepathy",
            description="Transfera starea completa intre agenti fara text, folosind matrici comprimate. Actiuni: 'encode', 'decode'.",
            parameters=[
                ToolParameter(
                    name="action",
                    description="'encode' sau 'decode'",
                    type="string",
                    required=True,
                    choices=["encode", "decode"],
                ),
                ToolParameter(
                    name="payload",
                    description="Text JSON pentru encode, sau string latent pentru decode.",
                    type="string",
                    required=True,
                ),
            ],
            category="ai",
        )

    def execute(self, **kwargs: Any) -> ToolResult:
        action = kwargs.get("action")
        payload_str = kwargs.get("payload", "")

        try:
            if action == "encode":
                data = json.loads(payload_str)
                encoded = _encode_latent_state(data)
                compression_ratio = len(encoded) / len(payload_str)
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data={"latent_vector": encoded, "compression_ratio": round(compression_ratio, 2)},
                    message="Stare codificata in spatiul latent."
                )
            elif action == "decode":
                decoded = _decode_latent_state(payload_str)
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data={"decoded_state": decoded},
                    message="Stare decodata cu succes din spatiul latent."
                )
            else:
                return ToolResult(status=ToolStatus.ERROR, error="Actiune necunoscuta.")
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=f"Eroare de procesare telepatica: {str(e)}")
