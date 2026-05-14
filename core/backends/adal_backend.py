from __future__ import annotations

import logging
from typing import Any

from tools.base import registry

logger = logging.getLogger(__name__)


def init(agent: Any) -> None:
    """Initialize the AdaL-only backend."""
    del agent

    if not registry.get("adal_integration"):
        logger.error("AdaL Integration tool nu este disponibil!")
        raise RuntimeError("AdaL Tool missing")

    logger.info("Backend AdaL Only activat.")


def send(agent: Any, message: str) -> str:
    """Send a task to the AdaL integration tool."""
    del agent

    try:
        adal_resp = registry.execute("adal_integration", operation="exec", task=message)
        return f"{adal_resp}"
    except Exception as exc:
        logger.error(f"Eroare in comunicarea directa cu AdaL: {exc}")
        raise
