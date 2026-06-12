# Session Checkpoint - 2026-05-28T16:59:52+00:00

## Lab stable Activity Bar control surface

## Summary

Cockpit webview disabled as primary surface; ANA MAX Activity Bar controls plus Live Console are now the stable operator path. Fixed error_radar false auth finding caused by timestamp milliseconds such as ,403.

## Current Goal

Continue ANA MAX lab roadmap from stable Activity Bar controls: observe, route, act, verify, audit.

## Next Steps

- Use Activity Bar commands for Smart Ready, Health JSON, List Tools, Live Debug, Code Map, Trust Score, Session Audit, Binary Map, Checkpoint, REM. Next patch candidate: keep reducing noisy diagnostics and expand nucleus smoke.

## Files Changed

- vscode_extension/package.json
- vscode_extension/extension.js
- vscode_extension/CHANGELOG.md
- tests/runtime/test_vscode_extension.py
- ANA_MAX/tools/error_radar_tool.py
- tests/runtime/test_error_radar_tool.py

## Validation

```text
MCP health online with 90 tools; focused pytest 36 passed; node --check extension.js passed; tool_healthcheck 7 OK / 0 FAIL; error_radar now reports only large dirty tree.
```

## Risks

- Dirty tree is large because lab contains ongoing work
- review before any commit or public sync. Webview remains disabled in lab flow because it was host-fragile.

## Lab/Release Sync Status

Mother lab only; public release sync not requested.

## Git Snapshot

- branch: main
- clean: False

```text
M .gitignore
 M .vscode/extensions.json
 M ANA_MAX/ana_memory.db
 M ANA_MAX/dev_artifacts/scripts/package_cockpit_vsix.py
 M ANA_MAX/docs/CURRENT_SESSION_HANDOFF.md
 M ANA_MAX/main.py
 M ANA_MAX/tools/__init__.py
 M ANA_MAX/tools/agent_coach_tool.py
 M ANA_MAX/tools/base.py
 M ANA_MAX/tools/desktop_control_tool.py
 M ANA_MAX/tools/error_radar_tool.py
 M ANA_MAX/tools/event_stream_tool.py
 M ANA_MAX/tools/foreground_ui_snapshot.py
 M ANA_MAX/tools/tool_adapters.py
 M ANA_MAX/tools/tool_router_tool.py
 M docs/AGENT_MEMORY.md
 M docs/AGENT_STEROID_TOOLS.md
 M docs/NEXT_SESSION_BOOTSTRAP.md
 M docs/PUBLIC_RELEASE_SYNC_BACKLOG.md
 M tests/runtime/test_agent_coach_recommend.py
 M tests/runtime/test_tool_router_tool.py
 M tests/runtime/test_vscode_extension.py
 M vscode_extension/CHANGELOG.md
 M vscode_extension/MARKETPLACE.md
 M vscode_extension/README.md
 M vscode_extension/assets/ana-max-icon.png
 M vscode_extension/extension.js
 M vscode_extension/package.json
?? ANA_MAX/config/input_probe_authorized_targets.json
?? ANA_MAX/dev_artifacts/audit/
?? ANA_MAX/dev_artifacts/scripts/ana_agent_step.py
?? ANA_MAX/dev_artifacts/scripts/ana_binary_map.py
?? ANA_MAX/dev_artifacts/scripts/ana_code_map.py
?? ANA_MAX/dev_artifacts/scripts/ana_desktop_smoke.py
?? ANA_MAX/dev_artifacts/scripts/ana_frida.py
?? ANA_MAX/dev_artifacts/scripts/ana_input_probe_spec.py
?? ANA_MAX/dev_artifacts/scripts/ana_lab_hub.py
?? ANA_MAX/dev_artifacts/scripts/ana_mcp.ps1
?? ANA_MAX/dev_artifacts/scripts/ana_mcp_call.ps1
?? ANA_MAX/dev_artifacts/scripts/ana_mcp_call.py
?? ANA_MAX/dev_artifacts/scripts/ana_mirror_watch.py
?? ANA_MAX/dev_artifacts/scripts/ana_under_hood.py
?? ANA_MAX/docs/rem_sleep/REM_SLEEP_REPORT_2026-05-28T005329+0000.md
?? ANA_MAX/docs/rem_sleep/REM_SLEEP_REPORT_2026-05-28T005425+0000.md
?? ANA_MAX/docs/rem_sleep/REM_SLEEP_REPORT_2026-05-28T020610+0000.md
?? ANA_MAX/docs/rem_sleep/REM_SLEEP_REPORT_2026-05-28T020611+0000.md
?? ANA_MAX/docs/rem_sleep/REM_SLEEP_REPORT_2026-05-28T021312+0000.md
?? ANA_MAX/docs/rem_sleep/REM_SLEEP_REPORT_2026-05-28T023553+0000.md
?? ANA_MAX/docs/rem_sleep/REM_SLEEP_REPORT_2026-05-28T024227+0000.md
?? ANA_MAX/docs/rem_sleep/REM_SLEEP_REPORT_2026-05-28T024249+0000.md
?? ANA_MAX/docs/rem_sleep/REM_SLEEP_REPORT_2026-05-28T025442+0000.md
?? ANA_MAX/docs/rem_sleep/REM_SLEEP_REPORT_2026-05-28T030826+0000.md
?? ANA_MAX/docs/rem_sleep/REM_SLEEP_REPORT_2026-05-28T164854+0000.md
?? ANA_MAX/docs/rem_sleep/REM_SLEEP_REPORT_2026-05-28T165910+0000.md
?? ANA_MAX/tools/binary_map_tool.py
?? ANA_MAX/tools/code_context_pack_tool.py
?? ANA_MAX/tools/input_api_probe_tool.py
?? ANA_MAX/tools/session_audit_tool.py
?? tests/runtime/test_ana_code_map.py
?? tests/runtime/test_ana_input_probe_spec.py
?? tests/runtime/test_binary_map_tool.py
?? tests/runtime/test_code_context_pack_tool.py
?? tests/runtime/test_desktop_control_tool.py
?? tests/runtime/test_error_radar_tool.py
?? tests/runtime/test_input_api_probe_tool.py
?? tests/runtime/test_session_audit_tool.py
?? vscode_extension/assets/ana-max-activity.svg
```
