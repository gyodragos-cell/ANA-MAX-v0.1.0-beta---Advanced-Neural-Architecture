# MCP (Model Context Protocol)

MCP enables IDE integration with Windsurf, Cursor, and Devin.

## Integration

Configure your IDE to use ANA MAX as MCP server:

```json
{
  "mcpServers": {
    "ana-max": {
      "command": "python",
      "args": ["ANA_MAX/mcp/mcp_stdio.py"]
    }
  }
}
```
