# Session Checkpoint - 2026-05-27T03:45:00+00:00

## Runtime auto-guidance now uses agent_coach recommend

## Summary

Integrated `agent_coach action=recommend` into runtime failure auto-guidance.
Failed tool results can now include `data.auto_guidance.agent_coach_recommend`
with `primary_tool`, `tool_stack`, and `next_action`, alongside the existing
`tool_router` and `coach` guidance.

This makes failed tool calls directly tell the next agent what to do next
instead of only reporting that something failed.

## Current Goal

Make ANA MAX tools self-steering enough that agents do not work blindly after
failures.

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
MCP failed tool demo -> auto_guidance keys include agent_coach_recommend, coach, tool_router
python ANA_MAX/dev_artifacts/tests/smoke_mcp_all_tools.py -> 64 pass, 20 skipped_unsafe, 0 fail
```

Latest MCP smoke report:

```text
ANA_MAX/dev_artifacts/reports/mcp_smoke_report_20260527_063659.json
```

## Runtime State

- MCP is healthy on `http://127.0.0.1:8766/mcp`
- `/health`: `status=online`, `mcp_ready=True`, `tools_count=84`
- Example failed tool guidance:
  - `primary_tool=error_radar`
  - `tool_stack=error_radar, agent_coach, ana_memory, debugger, tool_healthcheck`
  - `next_action=Call error_radar... Verify before another action.`

## Risks

- MCP was restarted, but IDE was not reloaded.
- Worktree remains dirty from broader lab work; preserve unrelated changes.

## Next Steps

- Continue without forcing IDE reload while chat continuity matters.
- Consider showing `auto_guidance.agent_coach_recommend` prominently in cockpit tool-call output later.
- Keep public release sync pending explicit review.

## Lab/Release Sync Status

Mother lab only. Public release sync pending review.
