# Session Checkpoint - 2026-05-29T05:15:27+00:00

## Docs organized without moving active markdown

## Summary

Organized docs safely: created docs/DOCS_INDEX.md as the central discovery point for all documentation, kept active root/package markdown files in place because scripts and READMEs reference them, linked DOCS_INDEX from ANA_LAB_MASTER_CONTEXT and NEXT_SESSION_BOOTSTRAP, archived root media files under workspace_cleanup_20260529/root_media, and verified Nucleus Smoke PASS.

## Current Goal

Keep documentation discoverable from docs/ while avoiding path-breaking moves. Continue cleanup conservatively without affecting code or mother-lab runtime.

## Next Steps

- Use docs/DOCS_INDEX.md to find docs
- only move markdown physically after updating references deliberately. Continue cleaning ignored artifacts/logs into dev_artifacts archives.

## Files Changed

- docs/DOCS_INDEX.md
- docs/ANA_LAB_MASTER_CONTEXT.md
- docs/NEXT_SESSION_BOOTSTRAP.md
- archived root media under ANA_MAX/dev_artifacts/archives/workspace_cleanup_20260529/root_media

## Validation

```text
Nucleus Smoke PASS 9/9; docs index exists and points to root/package/extension docs; root video files archived; code/runtime untouched.
```

## Risks

- Do not move root markdown blindly because core/context_builder.py, README.md, and quality scripts reference exact root paths.

## Lab/Release Sync Status

Mother lab cleanup only; public/GitHub pending.

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
?? ANA_MAX/dev_artifacts/scripts/ana_graph_map.py
?? ANA_MAX/dev_artifacts/scripts/ana_input_probe_spec.py
?? ANA_MAX/dev_artifacts/scripts/ana_lab_hub.py
?? ANA_MAX/dev_artifacts/scripts/ana_mcp.ps1
?? ANA_MAX/dev_artifacts/scripts/ana_mcp_call.ps1
?? ANA_MAX/dev_artifacts/scripts/ana_mcp_call.py
?? ANA_MAX/dev_artifacts/scripts/ana_mirror_watch.py
?? ANA_MAX/dev_artifacts/scripts/ana_nucleus_smoke.py
?? ANA_MAX/dev_artifacts/scripts/ana_under_hood.py
?? ANA_MAX/docs/SESSION_CHECKPOINT_2026-05-28T165952Z0000.md
?? ANA_MAX/docs/SESSION_CHECKPOINT_2026-05-29T045820Z0000.md
?? ANA_MAX/docs/SESSION_CHECKPOINT_2026-05-29T050430Z0000.md
?? ANA_MAX/docs/SESSION_CHECKPOINT_2026-05-29T051020Z0000.md
?? ANA_MAX/docs/SESSION_CHECKPOINT_2026-05-29T051203Z0000.md
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
?? docs/DOCS_INDEX.md
?? docs/LAB_WORKSPACE_STRUCTURE.md
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
