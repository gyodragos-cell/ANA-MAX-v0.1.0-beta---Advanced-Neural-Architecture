# ANA MAX — Core Engine (OS-27)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![MCP HTTP](https://img.shields.io/badge/MCP-HTTP%208765-green.svg)](#)
[![Tools: 121+](https://img.shields.io/badge/Tools-121%2B-orange.svg)](#)

> Core engine of ANA MAX OS-27. See root [`README.md`](../README.md) for full documentation.

## This directory

`ANA_MAX/` contains the HTTP MCP server and all tool implementations:

- **`main.py`** — HTTP MCP server, port `8765`. Loads and exposes 121+ tools via `/execute` endpoint.
- **`tools/`** — 173 Python tool modules (browser, vision, memory, DLL injection, network, orchestration...)
- **`core/omnisense.py`** — OmniSense vision daemon (delta-based screen monitoring)
- **`mcp/os27_mcp_server.py`** — MCP stdio server (28 OS27 system tools)
- **`docs/ANA_MEMORY.md`** — Full session history (12,000+ lines, September 2026)
- **`CHANGELOG.md`** — Version changelog

## Quick start

```powershell
cd ANA_MAX
.\venv\Scripts\activate
python main.py
# HTTP MCP server running on http://127.0.0.1:8765
```

## API format

```python
# POST http://127.0.0.1:8765/execute
{
    "tool": "<tool_name>",
    "args": {
        "operation": "<op>",
        # ... tool-specific params
    }
}
```

List all tools: `GET http://127.0.0.1:8765/tools`

## Architecture note

ANA MAX is **not an AI**. It is an **OS for AI**.

| Level | What | Example |
|-------|------|---------|
| AI (Model) | Inference system | Claude, Qwen, GPT-4 |
| ANA OS-27 | Operating system | Orchestrates, executes, sees, remembers |
| Relation | OS serves AI | Like Windows serves apps |

## Resource system

`resources/texts/` — localization JSON (EN + RO)
`resources/themes/` — light/dark theme JSON
`core/resource_loader.py` — safe fallback loader (missing → English / light theme)

## Security

God Mode. Full local system access. **DO NOT** expose ports to the internet.
All enterprise tools (DLL injection, memory patching) use safe-mode validation by default.

---

*Part of ANA MAX OS-27 — see [root README](../README.md) for full documentation.*
