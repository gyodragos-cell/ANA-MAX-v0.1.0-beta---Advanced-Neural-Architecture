"""Focused smoke test for ANA MAX running through Foundry Local.

This test validates the complete contract in layers: tool registration, valid
native function schemas, registry-mediated execution, and a real Foundry chat
turn.  It exits non-zero on failure so it is suitable for the desktop launcher
or a CI-style local check.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

ANA_ROOT = Path(__file__).resolve().parents[2]
if str(ANA_ROOT) not in sys.path:
    sys.path.insert(0, str(ANA_ROOT))
os.chdir(ANA_ROOT)

from core.backends import foundry_backend  # noqa: E402
from core.agent import ANAAgent  # noqa: E402
from tools.base import ToolRegistry  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("foundry_smoke")


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _register_runtime_tools() -> ToolRegistry:
    """Load the same shared registry that main.py uses in production."""
    import main  # noqa: WPS433

    registry = ToolRegistry()
    registry.reset()
    loaded = main._register_all_tools()
    logger.info("TOOL_REGISTRATION loaded=%d registry_total=%d", loaded, len(registry.list_tools()))
    _assert(len(registry.list_tools()) >= 20, "ANA tool registry did not load a usable tool set")
    return registry


def _check_schema(tools: list[dict[str, Any]]) -> None:
    names = {item["function"]["name"] for item in tools}
    required = {"ana_list_tools", "ana_execute_tool", "file_operations", "terminal"}
    missing = required - names
    _assert(not missing, f"Foundry tool surface missing required entries: {sorted(missing)}")

    for tool in tools:
        schema = tool["function"].get("parameters", {})
        _assert(schema.get("type") == "object", f"Invalid schema type for {tool['function']['name']}")
        _assert(isinstance(schema.get("properties"), dict), f"Missing properties for {tool['function']['name']}")
    logger.info("TOOL_SCHEMA valid_tools=%d", len(tools))


def _check_registry_execution(registry: ToolRegistry) -> None:
    raw = foundry_backend._execute_tool(
        registry,
        "file_operations",
        {"operation": "list", "path": str(ANA_ROOT)},
    )
    result = json.loads(raw)
    _assert(result.get("status") == "success", f"Registry tool execution failed: {raw}")
    logger.info("TOOL_EXECUTION file_operations=list status=success")


def _check_live_foundry() -> str:
    agent = ANAAgent(backend="foundry")
    _assert(foundry_backend._CLIENT is not None, "Foundry backend client was not initialized")

    response = agent._send_with_backend(
        "foundry",
        "Foloseste unealta file_operations pentru a lista directorul curent ANA_MAX, apoi spune pe scurt ce ai verificat.",
    )
    _assert(isinstance(response, str) and response.strip(), "Foundry returned an empty response")
    _assert("Eroare Foundry" not in response, f"Foundry response indicates failure: {response}")
    logger.info("FOUNDRY_LIVE_CHAT response_chars=%d", len(response))
    return response


def run_smoke_test() -> bool:
    logger.info("SMOKE_START root=%s model=%s", ANA_ROOT, os.environ.get("FOUNDRY_MODEL", "qwen3.5-4b"))
    try:
        registry = _register_runtime_tools()
        tools = foundry_backend._get_ana_tools(registry)
        _check_schema(tools)
        _check_registry_execution(registry)
        response = _check_live_foundry()
        logger.info("SMOKE_SUCCESS response=%s", response[:300].replace("\n", " "))
        return True
    except Exception as exc:
        logger.exception("SMOKE_FAILURE error=%s", exc)
        return False


if __name__ == "__main__":
    raise SystemExit(0 if run_smoke_test() else 1)
