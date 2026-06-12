# Session Checkpoint - 2026-05-29T05:41:46+00:00

## Autonomy Pass v1.0.41 installed

## Summary

Added lab-safe Autonomy Pass runner and Activity Bar command. Runner performs health, UI observe, code context, graph context, router, coach, tool healthcheck, error_radar, trust, report, and optional checkpoint. VSIX v1.0.41 was packaged and installed locally.

## Current Goal

Continue ANA MAX Lab Reliability and Autonomy Layer from Activity Bar + Live Console.

## Next Steps

- Reload VS Code window if the Autonomy Pass button is not visible, then run Nucleus Smoke and Autonomy Pass before larger changes.

## Files Changed

- ANA_MAX/dev_artifacts/scripts/ana_autonomy_runner.py
- ANA_MAX/dev_artifacts/scripts/lab_quality_gate.py
- vscode_extension/package.json
- vscode_extension/extension.js
- vscode_extension/CHANGELOG.md
- tests/runtime/test_ana_autonomy_runner.py
- tests/runtime/test_vscode_extension.py
- docs

## Validation

```text
Focused pytest 26/26 passed; node --check passed; Autonomy Pass real run WARN with trust 86; lab_quality_gate PASS; VSIX 1.0.41 packaged and installed.
```

## Risks

- foreground_ui_snapshot currently returns a non-blocking warn in Autonomy Pass
- deep instrumentation remains lab-only and excluded from this runner.

## Lab/Release Sync Status

Mother lab only; public release pending.

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
?? ANA_MAX/dev_artifacts/scripts/ana_autonomy_runner.py
?? ANA_MAX/dev_artifacts/scripts/ana_binary_map.py
?? ANA_MAX/dev_artifacts/scripts/ana_code_map.py
?? ANA_MAX/dev_artifacts/scripts/ana_desktop_smoke.py
?? ANA_MAX/dev_artifacts/scripts/ana_frida.py
?? ANA_MAX/dev_artifacts/scripts/ana_graph_map.py
?? ANA_MAX/dev_artifacts/scripts/ana_input_probe_spec.py
?? ANA_MAX/dev_artifacts/scripts/ana_lab_hub.py
?? ANA_MAX/dev_artifacts/scripts/ana_mcp.ps1
?? ANA_MAX/dev_artifacts/scripts/ana_mcp_call.ps1
?? ANA_MAX/dev_artifacts/scripts/ana_mcp_call.py
?? ANA_MAX/dev_artifacts/scripts/ana_mirror_watch.py
?? ANA_MAX/dev_artifacts/scripts/ana_nucleus_smoke.py
?? ANA_MAX/dev_artifacts/scripts/ana_under_hood.py
?? ANA_MAX/dev_artifacts/scripts/lab_quality_gate.py
?? ANA_MAX/docs/SESSION_CHECKPOINT_2026-05-28T165952Z0000.md
?? ANA_MAX/docs/SESSION_CHECKPOINT_2026-05-29T045820Z0000.md
?? ANA_MAX/docs/SESSION_CHECKPOINT_2026-05-29T050430Z0000.md
?? ANA_MAX/docs/SESSION_CHECKPOINT_2026-05-29T051020Z0000.md
?? ANA_MAX/docs/SESSION_CHECKPOINT_2026-05-29T051203Z0000.md
?? ANA_MAX/docs/SESSION_CHECKPOINT_2026-05-29T051527Z0000.md
?? ANA_MAX/docs/SESSION_CHECKPOINT_2026-05-29T052050Z0000.md
?? ANA_MAX/docs/SESSION_CHECKPOINT_2026-05-29T053330Z0000.md
?? ANA_MAX/docs/SESSION_CHECKPOINT_2026-05-29T054026Z0000.md
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
?? ANA_MAX/tools/graph_context_pack_tool.py
?? ANA_MAX/tools/input_api_probe_tool.py
?? ANA_MAX/tools/session_audit_tool.py
?? docs/ANA_LAB_MASTER_CONTEXT.md
?? docs/ANA_LAB_PROJECT_HISTORY.md
?? docs/CODEX_LAB_MANAGER_PROMPT.md
?? docs/DOCS_INDEX.md
?? docs/LAB_README.md
?? docs/LAB_WORKSPACE_STRUCTURE.md
?? docs/SAFETY_BOUNDARIES.md
?? tests/runtime/test_ana_autonomy_runner.py
?? tests/runtime/test_ana_code_map.py
?? tests/runtime/test_ana_graph_map.py
?? tests/runtime/test_ana_input_probe_spec.py
?? tests/runtime/test_binary_map_tool.py
?? tests/runtime/test_code_context_pack_tool.py
?? tests/runtime/test_desktop_control_tool.py
?? tests/runtime/test_error_radar_tool.py
?? tests/runtime/test_graph_context_pack_tool.py
?? tests/runtime/test_input_api_probe_tool.py
?? tests/runtime/test_session_audit_tool.py
?? vscode_extension/assets/ana-max-activity.svg
```
