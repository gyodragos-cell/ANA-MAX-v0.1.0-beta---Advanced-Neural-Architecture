# Session Checkpoint - 2026-05-27T03:22:25+00:00

## Smart MCP readiness and launcher hardening

## Summary

Made MCP readiness contract-based instead of tool-count-based. Added a stdlib
readiness checker that verifies `/health`, `tools/list`, `tool_router`, and
`agent_coach action=recommend`. Wired it into launcher scripts and watchdog so a
stale MCP server fails early instead of appearing healthy.

## Current Goal

Keep agents from starting blind or using a stale MCP server. A ready server must
prove that routing and coaching work, not just that 84 tools are registered.

## Files Changed

- `ANA_MAX_Launcher/mcp_readiness_check.py`
- `ANA_MAX_Launcher/launch.bat`
- `ANA_MAX_Launcher/launch_clean.bat`
- `ANA_MAX_Launcher/launch_with_frida.bat`
- `ANA_MAX_Launcher/live_watchdog.py`
- `ANA_MAX/launcher.py`
- `docs/MCP_AGENT_READINESS_CONTRACT.md`
- `docs/NEXT_SESSION_BOOTSTRAP.md`
- `docs/AGENT_MEMORY.md`
- `ANA_MAX/docs/CURRENT_SESSION_HANDOFF.md`

## Validation

```text
python -m compileall -q ANA_MAX_Launcher/mcp_readiness_check.py ANA_MAX_Launcher/live_watchdog.py ANA_MAX/launcher.py -> OK
python ANA_MAX_Launcher/mcp_readiness_check.py --mcp-url http://127.0.0.1:8766/mcp -> OK
python ANA_MAX/dev_artifacts/tests/smoke_mcp_all_tools.py -> 64 pass, 20 skipped_unsafe, 0 fail
```

Latest MCP smoke report:

```text
ANA_MAX/dev_artifacts/reports/mcp_smoke_report_20260527_062225.json
```

## Runtime State

- MCP server is healthy on `http://127.0.0.1:8766/mcp`
- `/health` reports `status=online`, `mcp_ready=True`, `tools_count=84`
- Readiness proves:
  - `tool_router` is present and callable
  - `agent_coach` schema includes `recommend`
  - `agent_coach action=recommend` returns `schema=ana.agent_coach.recommend.v1` and `primary_tool=error_radar`

## Risks

- Batch launchers were updated but not launched end-to-end to avoid opening user windows during this coding pass.
- Worktree remains dirty from broader lab work; do not revert unrelated changes.
- Public release sync is still pending review.

## Next Good Work

- Teach the VS Code/Qoder cockpit UI to show smart readiness status.
- Use `agent_coach action=recommend` automatically in more runtime paths.
- Keep public release sync sanitized and intentional.

## Lab/Release Sync Status

Mother lab only for now; public-safe candidates are tracked in `docs/PUBLIC_RELEASE_SYNC_BACKLOG.md`.
