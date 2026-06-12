# Session Checkpoint - 2026-05-27T03:12:38+00:00

## Agent coach recommendation upgrade

## Summary

Added `agent_coach action=recommend` as a read-only next-tool recommendation action. It combines recent observability telemetry with `tool_router` playbooks and returns a compact contract for agent IDEs: `schema`, `severity`, `headline`, `primary_tool`, `tool_stack`, `router`, `coach`, `next_action`, and optional `prompt_for_qoder`.

Also removed the old `datetime.utcnow` deprecation warning in `tools/base.py` and updated the MCP smoke case so `agent_coach` validates the new recommend path.

## Current Goal

Keep ANA MAX MCP useful through a smaller reliable core: observe, diagnose, recommend the next tool, then verify.

## Files Changed

- `ANA_MAX/tools/agent_coach_tool.py`
- `ANA_MAX/tools/base.py`
- `ANA_MAX/dev_artifacts/tests/smoke_mcp_all_tools.py`
- `tests/runtime/test_agent_coach_recommend.py`
- `docs/AGENT_MEMORY.md`
- `docs/TOOL_MATRIX.md`
- `docs/PUBLIC_RELEASE_SYNC_BACKLOG.md`
- `ANA_MAX/docs/CURRENT_SESSION_HANDOFF.md`

## Validation

```text
python -m compileall -q ANA_MAX/tools/base.py ANA_MAX/tools/agent_coach_tool.py ANA_MAX/dev_artifacts/tests/smoke_mcp_all_tools.py tests/runtime/test_agent_coach_recommend.py tests/runtime/test_tool_router_tool.py -> OK
python -m pytest tests/runtime/test_agent_coach_recommend.py tests/runtime/test_tool_router_tool.py -q -> 6 passed
MCP tools/call agent_coach action=recommend -> success, schema=ana.agent_coach.recommend.v1, primary_tool=error_radar
python ANA_MAX/dev_artifacts/tests/smoke_mcp_all_tools.py -> 64 pass, 20 skipped_unsafe, 0 fail
```

Latest MCP smoke report:

```text
ANA_MAX/dev_artifacts/reports/mcp_smoke_report_20260527_061227.json
```

## Runtime State

- MCP server restarted and healthy on `http://127.0.0.1:8766/mcp`
- `/health` reports `status=online`, `mcp_ready=True`, `tools_count=84`
- `agent_coach` schema includes actions: `coach`, `recommend`, `lessons`, `reset`
- `tool_router` remains visible through MCP

## Risks

- Worktree is still very dirty from broader existing lab changes; preserve unrelated edits.
- Public release sync is not done. Treat these changes as mother-lab until reviewed.
- ADB smoke needed a 15s timeout because daemon startup can exceed 5s.

## Lab/Release Sync Status

Mother lab only for now; public-safe candidates are tracked in `docs/PUBLIC_RELEASE_SYNC_BACKLOG.md`.
