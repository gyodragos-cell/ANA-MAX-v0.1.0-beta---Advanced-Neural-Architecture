# ANA_MAX OS-22 Tool Awareness Pack

## Tool Model

Tools are local functions with explicit contracts.
They are not magic and they are not external services.

## Source Of Truth

The source of truth is:

```text
ANA_MAX/tools/tool_manifest.json
```

## Required Tool Call Format

```text
TOOL_CALL: <tool_name> <json_arguments>
```

## Agent Rules

- Decide if a tool is required.
- Choose a tool only from the manifest.
- Use exact argument names.
- Emit one tool call only.
- Wait for the tool result.
- Use the result in the final answer.

## Useful Debug Commands

```text
/tools
/tool current_time
/tool system_info
/open <url>
```

