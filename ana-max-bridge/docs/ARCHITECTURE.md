# Architecture

`ana-max-bridge` is a local companion service for ANA MAX.

## Components

- `bridge_server.py` runs the Flask HTTP API and UI host.
- `tool_mapper.py` maps ANA MAX tool metadata for external clients.
- `watchdog.py` validates requests and responses before returning them.
- `config.yaml` contains local non-secret defaults.
- `ui/` contains the control panel.
- `schemas/` contains common tool input schema examples.
- `tests/` contains unit tests for the bridge.

## Request Flow

```text
Copilot-style client -> ana-max-bridge -> ANA MAX MCP server -> tool registry
```

The bridge forwards execution to ANA MAX rather than importing tool instances.
This preserves registry validation, logging, and premium license gates.

## Safety Model

The bridge watchdog blocks missing tool names, configured blocked tools, large
payloads, and obvious destructive command patterns. ANA MAX remains the source
of truth for deeper tool validation and license checks.

## LOCAL DEV MODE (no API key)

`config.yaml` enables local dev mode by default:

```yaml
local_dev: true
```

When `local_dev` is true, the bridge does not send an `Authorization` header to
ANA MAX. The bridge also rejects non-local requests in this mode, so the bypass
is limited to `127.0.0.1`.

Production auth logic is not deleted. When `local_dev` is false, the bridge
reads `ANA_MCP_KEY` or `MCP_API_KEY` from the environment and sends it as
`Authorization: Bearer <token>` to ANA MAX. The key is never stored in the
repository.
