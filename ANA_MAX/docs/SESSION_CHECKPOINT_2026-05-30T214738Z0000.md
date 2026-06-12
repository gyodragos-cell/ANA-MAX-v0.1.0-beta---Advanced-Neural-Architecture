# Session Checkpoint - 2026-05-30T21:47:38+00:00

## Profile status Activity Bar fallback

## Summary

Hardened the Activity Bar-only Profile Status command. It first calls tool_router mode=profile_status, then falls back to the local ana_permission_manifest_coverage.py script if the live MCP server still runs older code. Webview remains untouched and explicitly has no profileStatus button.

## Current Goal

Keep ANA MAX left Activity Bar controls reliable even when MCP has not yet been restarted for latest code.

## Next Steps

- Package/reload extension only when operator is ready
- Keep adding operator-facing controls to Activity Bar instead of webview
- Eventually remove or further de-emphasize fragile cockpit paths.

## Files Changed

- vscode_extension/extension.js
- tests/runtime/test_vscode_extension.py

## Validation

```text
node --check vscode_extension/extension.js passed; pytest test_vscode_extension 24 passed; ana_permission_manifest_coverage PASS runtime=91 manifest=91 missing=0 extra=0; lab_quality_gate PASS report ANA_MAX/dev_artifacts/reports/lab_quality_gate_20260530_214729.json
```

## Risks

- Installed extension still needs package/install/reload before the new command/fallback is available in the current VS Code window.

## Lab/Release Sync Status

Mother lab only; public release pending review.

## Git Snapshot

- branch: main
- clean: False

```text
M .gitignore
 M .vscode/extensions.json
 M ANA_MAX/ana_memory.db
 M ANA_MAX/config/permission_manifest.json
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
?? ANA_MAX/dev_artifacts/scripts/ana_governance_check.py
?? ANA_MAX/dev_artifacts/scripts/ana_graph_map.py
?? ANA_MAX/dev_artifacts/scripts/ana_input_probe_spec.py
?? ANA_MAX/dev_artifacts/scripts/ana_lab_hub.py
?? ANA_MAX/dev_artifacts/scripts/ana_linux_readiness.py
?? ANA_MAX/dev_artifacts/scripts/ana_mcp.ps1
?? ANA_MAX/dev_artifacts/scripts/ana_mcp_call.ps1
?? ANA_MAX/dev_artifacts/scripts/ana_mcp_call.py
?? ANA_MAX/dev_artifacts/scripts/ana_mirror_watch.py
?? ANA_MAX/dev_artifacts/scripts/ana_nucleus_smoke.py
?? ANA_MAX/dev_artifacts/scripts/ana_permission_manifest_coverage.py
?? ANA_MAX/dev_artifacts/scripts/ana_under_hood.py
?? ANA_MAX/dev_artifacts/scripts/lab_quality_gate.py
?? ANA_MAX/dev_artifacts/scripts/linux_bootstrap.sh
?? ANA_MAX/dev_artifacts/scripts/linux_core_gate.sh
?? ANA_MAX/docs/SESSION_CHECKPOINT_2026-05-28T165952Z0000.md
?? ANA_MAX/docs/SESSION_CHECKPOINT_2026-05-29T045820Z0000.md
?? ANA_MAX/docs/SESSION_CHECKPOINT_2026-05-29T050430Z0000.md
?? ANA_MAX/docs/SESSION_CHECKPOINT_2026-05-29T051020Z0000.md
?? ANA_MAX/docs/SESSION_CHECKPOINT_2026-05-29T051203Z0000.md
?? ANA_MAX/docs/SESSION_CHECKPOINT_2026-05-29T051527Z0000.md
?? ANA_MAX/docs/SESSION_CHECKPOINT_2026-05-29T052050Z0000.md
?? ANA_MAX/docs/SESSION_CHECKPOINT_2026-05-29T053330Z0000.md
?? ANA_MAX/docs/SESSION_CHECKPOINT_2026-05-29T054026Z0000.md
?? ANA_MAX/docs/SESSION_CHECKPOINT_2026-05-29T054146Z0000.md
?? ANA_MAX/docs/SESSION_CHECKPOINT_2026-05-29T055802Z0000.md
?? ANA_MAX/docs/SESSION_CHECKPOINT_2026-05-29T060527Z0000.md
?? ANA_MAX/docs/SESSION_CHECKPOINT_2026-05-29T062250Z0000.md
?? ANA_MAX/docs/SESSION_CHECKPOINT_2026-05-29T115002Z0000.md
?? ANA_MAX/docs/SESSION_CHECKPOINT_2026-05-30T212040Z0000.md
?? ANA_MAX/docs/SESSION_CHECKPOINT_2026-05-30T212443Z0000.md
?? ANA_MAX/docs/SESSION_CHECKPOINT_2026-05-30T212853Z0000.md
?? ANA_MAX/docs/SESSION_CHECKPOINT_2026-05-30T213405Z0000.md
?? ANA_MAX/docs/SESSION_CHECKPOINT_2026-05-30T213750Z0000.md
?? ANA_MAX/docs/SESSION_CHECKPOINT_2026-05-30T213913Z0000.md
?? ANA_MAX/docs/SESSION_CHECKPOINT_2026-05-30T214301Z0000.md
?? ANA_MAX/docs/SESSION_CHECKPOINT_2026-05-30T214615Z0000.md
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
?? LINUX_START_HERE.md
?? PRIVATE_FULL_LINUX_MOVE_START.md
?? docs/ANA_EXAMPLES_AND_TESTS_CHECKLIST.md
?? docs/ANA_LAB_MASTER_CONTEXT.md
?? docs/ANA_LAB_PROJECT_HISTORY.md
?? docs/ANA_PROFILE_MANIFEST.md
?? docs/ANA_SERIOUS_PROJECT_RULES.md
?? docs/CODEX_LAB_MANAGER_PROMPT.md
?? docs/DOCS_INDEX.md
?? docs/LAB_README.md
?? docs/LAB_WORKSPACE_STRUCTURE.md
?? docs/LINUX_MATE_MIGRATION_LANE.md
?? docs/SAFETY_BOUNDARIES.md
?? tests/runtime/test_ana_autonomy_runner.py
?? tests/runtime/test_ana_code_map.py
?? tests/runtime/test_ana_governance_check.py
?? tests/runtime/test_ana_graph_map.py
?? tests/runtime/test_ana_input_probe_spec.py
?? tests/runtime/test_ana_linux_readiness.py
?? tests/runtime/test_binary_map_tool.py
?? tests/runtime/test_code_context_pack_tool.py
?? tests/runtime/test_desktop_control_tool.py
?? tests/runtime/test_error_radar_tool.py
?? tests/runtime/test_graph_context_pack_tool.py
?? tests/runtime/test_input_api_probe_tool.py
?? tests/runtime/test_session_audit_tool.py
?? vscode_extension/assets/ana-max-activity.svg
```
