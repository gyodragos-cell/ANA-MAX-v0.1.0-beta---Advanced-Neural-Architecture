# Connect To Copilot

This bridge exposes ANA MAX tools through a small local HTTP service for
Copilot-style clients that can call HTTP tools.

## Start ANA MAX

From the repository root:

```powershell
python main.py
```

ANA MAX exposes:

```text
GET  /health
GET  /tools
POST /execute
POST /mcp
```

## Start The Bridge

From `ana-max-bridge`:

```powershell
python bridge_server.py
```

Default bridge URL:

```text
http://127.0.0.1:8790
```

Open the control panel:

```text
http://127.0.0.1:8790/
```

## Client Endpoints

```text
GET  /health
POST /start
POST /stop
GET  /tools/list
POST /tools/reload
POST /tools/call
POST /execute
POST /mcp
GET  /logs
```

Use `/tools/list` to discover tools, then call `/tools/call` with:

```json
{
  "tool": "workspace_situational_awareness",
  "params": {
    "path": ".",
    "max_files": 20
  }
}
```

## LOCAL DEV MODE (no API key)

`config/settings.yaml` and `ana-max-bridge/config.yaml` enable local dev mode by
default:

```yaml
local_dev: true
```

In this mode, no API key, Authorization header, or environment variable is
required. The bypass is limited to requests from `127.0.0.1`.

For production or non-local use, set `local_dev: false`, configure
`ANA_MCP_KEY` or `MCP_API_KEY`, and send `Authorization: Bearer <token>`.
Do not write tokens into `config.yaml`.
