# Tool Mapping

`tool_mapper.py` converts ANA MAX `/tools` metadata into bridge tool
definitions.

Input from ANA MAX:

```json
{
  "name": "file_operations",
  "description": "File operations",
  "category": "core",
  "parameters": {
    "type": "object",
    "properties": {}
  }
}
```

Bridge output:

```json
{
  "name": "file_operations",
  "description": "File operations",
  "category": "core",
  "method": "POST",
  "endpoint": "/tools/call",
  "request_template": {
    "tool": "file_operations",
    "params": {}
  },
  "input_schema": {
    "type": "object",
    "properties": {}
  }
}
```

The bridge does not invent tools. It only maps tools detected from ANA MAX.
Premium gates remain enforced by ANA MAX because tool execution is forwarded to
the ANA MAX `/execute` endpoint.

## LOCAL DEV MODE (no API key)

Tool mapping is unchanged in local dev mode. The bridge still discovers tools
from ANA MAX and still forwards execution to ANA MAX.

When `local_dev: true`, the bridge does not attach an Authorization header to
tool discovery or execution requests. This bypass is accepted only for
`127.0.0.1` traffic. When `local_dev: false`, normal Bearer-token auth is used.
