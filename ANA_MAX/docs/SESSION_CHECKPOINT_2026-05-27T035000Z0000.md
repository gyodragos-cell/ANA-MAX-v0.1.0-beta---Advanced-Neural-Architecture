# Session Checkpoint - 2026-05-27T03:50:00+00:00

## Compact guidance summary for failed tools

## Summary

Added `data.guidance_summary` to failed tool results when auto-guidance is
available. The summary is derived from `agent_coach_recommend` first, then
falls back to `tool_router` or `coach`. This gives agents and cockpit surfaces a
simple stable field to display without parsing the full `auto_guidance` object.

Example live MCP result:

```json
{
  "primary_tool": "error_radar",
  "tool_stack": ["error_radar", "agent_coach", "ana_memory", "debugger", "tool_healthcheck"],
  "next_action": "Call error_radar, then Read the normalized error and auto_guidance if present. Verify before another action.",
  "source": "agent_coach_recommend"
}
```

## Current Goal

Make failed tool results self-explanatory and easy for agents/UI to act on.

## Files Changed

- `ANA_MAX/tools/base.py`
- `tests/runtime/test_tool_router_tool.py`
- `docs/AGENT_MEMORY.md`
- `ANA_MAX/docs/CURRENT_SESSION_HANDOFF.md`

## Validation

```text
python -m compileall -q ANA_MAX/tools/base.py tests/runtime/test_tool_router_tool.py -> OK
python -m pytest tests/runtime/test_tool_router_tool.py tests/runtime/test_agent_coach_recommend.py -q -> 7 passed
MCP restart on 127.0.0.1:8766 -> OK
MCP failed tool demo -> data.guidance_summary present, source=agent_coach_recommend
python ANA_MAX/dev_artifacts/tests/smoke_mcp_all_tools.py -> 64 pass, 20 skipped_unsafe, 0 fail
```

Latest MCP smoke report:

```text
ANA_MAX/dev_artifacts/reports/mcp_smoke_report_20260527_064028.json
```

## Runtime State

- MCP is healthy on `http://127.0.0.1:8766/mcp`
- `/health`: `status=online`, `mcp_ready=True`, `tools_count=84`
- No IDE reload performed.

## Next Steps

- Later, cockpit output can display `data.guidance_summary` prominently.
- Continue without forcing IDE reload while chat continuity matters.
- Keep public release sync pending explicit review.

## Lab/Release Sync Status

Mother lab only. Public release sync pending review.
