# Session Checkpoint - 2026-05-27T04:00:00+00:00

## Top-level MCP guidance summary

## Summary

Exposed `guidance_summary` at the top level of MCP `tools/call` payloads when a
failed result has guidance. The nested `data.guidance_summary` remains for
backward compatibility. This makes it easier for cockpit/agents to display the
next action without parsing nested tool data.

Readiness now requires the top-level summary on a controlled failed tool call.

## Files Changed

- `ANA_MAX/main.py`
- `ANA_MAX/mcp_stdio.py`
- `ANA_MAX_Launcher/mcp_readiness_check.py`
- `docs/MCP_AGENT_READINESS_CONTRACT.md`
- `docs/AGENT_MEMORY.md`
- `ANA_MAX/docs/CURRENT_SESSION_HANDOFF.md`

## Validation

```text
python -m compileall -q ANA_MAX/main.py ANA_MAX/mcp_stdio.py ANA_MAX_Launcher/mcp_readiness_check.py -> OK
python -m pytest tests/runtime/test_tool_router_tool.py tests/runtime/test_agent_coach_recommend.py -q -> 7 passed
MCP restart on 127.0.0.1:8766 -> OK
MCP failed tool demo -> top-level guidance_summary present, primary_tool=error_radar
python ANA_MAX_Launcher/mcp_readiness_check.py --mcp-url http://127.0.0.1:8766/mcp -> OK
python ANA_MAX/dev_artifacts/tests/smoke_mcp_all_tools.py -> 64 pass, 20 skipped_unsafe, 0 fail
```

Latest MCP smoke report:

```text
ANA_MAX/dev_artifacts/reports/mcp_smoke_report_20260527_064553.json
```

## Runtime State

- MCP is healthy on `http://127.0.0.1:8766/mcp`
- `/health`: `status=online`, `mcp_ready=True`, `tools_count=84`
- Failed MCP tool payloads now expose:
  - `guidance_summary`
  - `data.guidance_summary`
  - `data.auto_guidance`

## Next Steps

- Later, cockpit output can display top-level `guidance_summary` prominently.
- Continue without forcing IDE reload while chat continuity matters.
- Keep public release sync pending explicit review.

## Lab/Release Sync Status

Mother lab only. Public release sync pending review.
