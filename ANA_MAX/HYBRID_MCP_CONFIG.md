# ANA MAX Hybrid MCP Config

Single runtime:

```text
http://127.0.0.1:8766/mcp
```

Use one ANA MAX MCP server for all clients:

```text
ANA MAX MCP 8766
  -> Codex server name: anamax
  -> VS Code ANA Cockpit: anaMax.runtimeUrl
  -> Antigravity/Qoder server name: anamax
  -> Windsurf/Cursor/VS Code-compatible MCP server name: anamax
```

Codex config:

```toml
[mcp_servers.anamax]
url = "http://127.0.0.1:8766/mcp"
```

Antigravity / Qoder / Windsurf MCP config:

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

Windsurf or Cursor-style MCP UIs usually ask for the same three values:

```text
Name: anamax
Type: HTTP / remote MCP
URL: http://127.0.0.1:8766/mcp
```

Extension identity:

```text
Display name: ANA MAX Hybrid AI Cockpit
Publisher: d4d8176a-bb85-66ef-93dd-a58bc9ddfdad
Extension id: d4d8176a-bb85-66ef-93dd-a58bc9ddfdad.ana-antigravity-chat
Marketplace: https://marketplace.visualstudio.com/items?itemName=d4d8176a-bb85-66ef-93dd-a58bc9ddfdad.ana-antigravity-chat
Current local VSIX: vscode_extension/ana-antigravity-chat-1.0.9.vsix
Repository: https://github.com/gyodragos-cell/ANA-MAX-v0.1.0-beta---Advanced-Neural-Architecture
Live site: https://gyodragos-cell.github.io/ANA-MAX-v0.1.0-beta---Advanced-Neural-Architecture/
Author: Dragos / gyodragos-cell with Codex
License: MIT
Icon: vscode_extension/assets/ana-max-icon.png
```

Notes:

- Do not start a second MCP server unless the main runtime is offline.
- Use VS Code MCP restart only after code changes or connection errors.
- The `.bat` launcher is optional when the MCP extension already manages the server.
