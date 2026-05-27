# ANA MAX Hybrid AI Cockpit

Local-first MCP cockpit for ANA MAX. One runtime can serve Codex, Antigravity/Qoder, Windsurf, Cursor, VS Code-compatible agent IDEs, and the ANA cockpit.

## Public Project

- Author: Dragos / `gyodragos-cell`, built with Codex as the main engineering copilot
- Repository: https://github.com/gyodragos-cell/ANA-MAX-v0.1.0-beta---Advanced-Neural-Architecture
- Live site: https://gyodragos-cell.github.io/ANA-MAX-v0.1.0-beta---Advanced-Neural-Architecture/
- License: MIT
- Public release: v0.1.0-beta
- Public runtime: 80-tool public baseline; full local lab/dev mode can expose more tools

## What It Does

ANA MAX is a local helper layer for AI agents. It gives an agent tools to observe your project, inspect the Windows desktop, run checks, choose the right tool, verify work, and remember useful lessons.

## Caracteristici

- Full local MCP bridge to ANA MAX tools.
- Smart readiness checks for `tool_router`, `agent_coach`, and `session_rem_sleep`.
- Next-tool recommendations so agents do not scan every tool blindly.
- Checkpoint and REM Sleep controls for durable session memory.
- Hybrid config helper for Codex, Antigravity/Qoder, Windsurf, Cursor, and VS Code-compatible MCP clients.

## Beginner Install

1. Download or clone ANA MAX.
2. Start the MCP runtime:

```powershell
cd ANA_MAX
python main.py --host 127.0.0.1 --port 8766
```

3. Install the VSIX:

```powershell
code --install-extension .\vscode_extension\ana-antigravity-1.0.8.vsix --force
```

For Qoder:

```powershell
qoder --install-extension .\vscode_extension\ana-antigravity-1.0.8.vsix --force
```

4. Reload the IDE window.
5. Run `ANA & Antigravity: Open Cockpit`.
6. Press `Smart Ready`.

Expected health:

```text
status=online
mcp_ready=true
tools_count=80 public baseline / 85 full local lab
```

## Porturi Implicite

- **MCP Server**: `http://127.0.0.1:8766/mcp`
- **Dashboard**: `http://127.0.0.1:8787`

## Hybrid MCP Config

Codex:

```toml
[mcp_servers.anamax]
url = "http://127.0.0.1:8766/mcp"
```

Antigravity / Qoder / Windsurf / Cursor:

```json
{
  "mcpServers": {
    "anamax": {
      "type": "http",
      "url": "http://127.0.0.1:8766/mcp"
    }
  }
}
```

If your IDE asks for fields instead of JSON:

```text
Name: anamax
Type: HTTP / remote MCP
URL: http://127.0.0.1:8766/mcp
```

## Marketplace Keywords

`mcp`, `model-context-protocol`, `ai-agent`, `agent-ide`, `codex`, `antigravity`, `qoder`, `windsurf`, `local-ai`, `windows-automation`, `qa`, `debugging`, `tool-router`, `desktop-ai`, `ana-max`
