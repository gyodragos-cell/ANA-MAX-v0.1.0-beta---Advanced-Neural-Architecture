# Session Checkpoint - 2026-05-27T02:48:18+00:00

## Tool router and automatic guidance integration

## Summary

Added tool_router as a read-only MCP recommendation router, integrated it into main/mcp_stdio/healthcheck/permission manifest/smoke tests, and extended auto-guidance so failed tool results can include tool_router next-tool recommendations alongside memory and agent_coach guidance. Added tests and updated tool/docs/backlog memory.

## Current Goal

Make ANA MAX tools useful through MCP without forcing agents to consider all tools blindly.

## Next Steps

- Restart MCP server so tool_router is discovered
- run MCP smoke test
- consider adding a dedicated recommend action to agent_coach if needed
- review public release sync later.

## Files Changed

- ANA_MAX/tools/tool_router_tool.py
- ANA_MAX/tools/base.py
- ANA_MAX/main.py
- ANA_MAX/mcp_stdio.py
- ANA_MAX/tools/tool_healthcheck.py
- ANA_MAX/config/permission_manifest.json
- ANA_MAX/dev_artifacts/tests/smoke_mcp_all_tools.py
- ANA_MAX/TOOL_STATUS.md
- tests/runtime/test_tool_router_tool.py
- docs/AGENT_MEMORY.md
- docs/AGENT_STEROID_TOOLS.md
- docs/PUBLIC_RELEASE_SYNC_BACKLOG.md
- docs/TOOL_MATRIX.md

## Validation

```text
python -m compileall -q ANA_MAX/tools/base.py ANA_MAX/tools/tool_router_tool.py ANA_MAX/tools/tool_healthcheck.py ANA_MAX/main.py ANA_MAX/mcp_stdio.py tests/runtime/test_tool_router_tool.py -> OK
python -m pytest tests/runtime/test_tool_router_tool.py -q -> 4 passed, 2 deprecation warnings
Direct registry demo -> failed tool result includes auto_guidance.tool_router mode=failure and recommended tools.
```

## Risks

- MCP server must be restarted before new tool is visible to active clients
- public release sync is parked for later review
- datetime.utcnow deprecation warning remains in tools/base.py observability logging.

## Lab/Release Sync Status

Mother lab only for now; public-safe candidates are tracked in docs/PUBLIC_RELEASE_SYNC_BACKLOG.md.

## Git Snapshot

- branch: main
- clean: False

```text
M .vscode/extensions.json
 M AGENT_START_HERE.md
 M ANA_MAX/.launcher_state.json
 D ANA_MAX/ANA
 M ANA_MAX/README.md
 D ANA_MAX/VOICE_QUICK_START.md
 D ANA_MAX/VOICE_SYSTEM_AUDIT_REPORT.md
 D ANA_MAX/VOICE_SYSTEM_FIXES_COMPLETE.md
 D ANA_MAX/ana_nemotron_agent_chat.py
 D ANA_MAX/analyze_bugs.py
 D ANA_MAX/auto_push_release.ps1
 D ANA_MAX/calc_demo_verify.py
 D ANA_MAX/check_git_status.ps1
 M ANA_MAX/config/permission_manifest.json
 M ANA_MAX/config/settings.yaml
 M ANA_MAX/core/browser_runtime.py
 M ANA_MAX/core/jupyter_sandbox.py
 D ANA_MAX/create_launcher.ps1
 D ANA_MAX/demo_frida_real.py
 D ANA_MAX/demo_wow.py
 D ANA_MAX/desktop_vision_diag.py
 M ANA_MAX/docs/MINT_CONDITION_DAILY_LOOP.md
 M ANA_MAX/docs/PLAN_VIITOR_OCHI_ANA_MAX.md
 M ANA_MAX/docs/PROJECT_MAP_AI_GUIDE.md
 M ANA_MAX/docs/ROADMAP.md
 D ANA_MAX/fix_bom.py
 D ANA_MAX/frida_inject_demo.py
 D ANA_MAX/health_check.py
 D ANA_MAX/kiro.bat
 M ANA_MAX/launcher.py
 M ANA_MAX/main.py
 M ANA_MAX/mcp_stdio.py
 D ANA_MAX/move_mouse_live.py
 M ANA_MAX/opencode.json
 D ANA_MAX/prepare_git_push.ps1
 D ANA_MAX/quick_smoke_test.py
 D ANA_MAX/quick_test.py
 D ANA_MAX/real_demo.py
 M ANA_MAX/requirements.txt
 D ANA_MAX/requirements_current.txt
 D ANA_MAX/ruflo_integration_summary.ps1
 D ANA_MAX/run_benchmark.py
 D ANA_MAX/see_and_move_icon.py
 D ANA_MAX/smoke_test_comprehensive.py
 D ANA_MAX/target_process.py
 D ANA_MAX/test_ana_access.py
 D ANA_MAX/test_desktop_vision.py
 D ANA_MAX/test_final_live.py
 D ANA_MAX/test_frida.py
 D ANA_MAX/test_frida_direct.py
 D ANA_MAX/test_frida_tool.py
 D ANA_MAX/test_frida_vision.py
 D ANA_MAX/test_healer_perfect_10.py
 D ANA_MAX/test_healer_real_scenario.py
 D ANA_MAX/test_input.txt
 D ANA_MAX/test_insight_debug.py
 D ANA_MAX/test_kiro_simulation.py
 D ANA_MAX/test_live_mcp_control.py
 D ANA_MAX/test_live_tool_healer.py
 D ANA_MAX/test_mcp_debug.py
 D ANA_MAX/test_mcp_file_call.py
 D ANA_MAX/test_mcp_frida_call.py
 D ANA_MAX/test_mcp_simple.py
 D ANA_MAX/test_mcp_stdio.py
 D ANA_MAX/test_mcp_tools.py
 D ANA_MAX/test_see_and_move.py
 D ANA_MAX/test_see_errors.py
 D ANA_MAX/test_see_live.py
 D ANA_MAX/test_system_insight.py
 D ANA_MAX/test_vision.py
 D ANA_MAX/test_voice_simple.py
 D ANA_MAX/tool_validate.py
 M ANA_MAX/tools/__init__.py
 M ANA_MAX/tools/adal_tool.py
 M ANA_MAX/tools/base.py
 M ANA_MAX/tools/browser_control.py
 M ANA_MAX/tools/context_engine.py
 M ANA_MAX/tools/edge_tts_voice.py
 M ANA_MAX/tools/edit_tool.py
 M ANA_MAX/tools/files.py
 M ANA_MAX/tools/foreground_ui_snapshot.py
 M ANA_MAX/tools/frida_automation.py
 M ANA_MAX/tools/live_voice_bridge.py
 M ANA_MAX/tools/ocr_tool.py
 M ANA_MAX/tools/system.py
 M ANA_MAX/tools/terminal_tool.py
 M ANA_MAX/tools/tool_adapters.py
 M ANA_MAX/tools/tool_healthcheck.py
 M ANA_MAX/tools/verdent_tools.py
 M ANA_MAX/tools/voice_integration.py
 M ANA_MAX/tools/window_manager.py
 M ANA_MAX/tools/windows_insight_tool.py
 M ANA_MAX/tools/windows_uia_bridge.py
 M ANA_MAX/tools/workspace_situational_awareness.py
 M ANA_MAX/voice_toggle.py
 M ANA_MAX_Launcher/launch.bat
 M ANA_MAX_Launcher/mcp.json
 M ana_dev.code-workspace
 D jokerforge_pythonanywhere_demo/.gitignore
 D jokerforge_pythonanywhere_demo/README.md
 D jokerforge_pythonanywhere_demo/app.py
 D jokerforge_pythonanywhere_demo/requirements.txt
 D jokerforge_pythonanywhere_demo/templates/index.html
?? AGENTS.md
?? ANA_MAX/CHANGELOG.md
?? ANA_MAX/HYBRID_MCP_CONFIG.md
?? ANA_MAX/LAB_MANAGER.md
?? ANA_MAX/LOG.md
?? ANA_MAX/TOOL_STATUS.md
?? ANA_MAX/ana-antigravity-hybrid-1.0.3.vsix
?? ANA_MAX/benchmarks/
?? ANA_MAX/compatibility/
?? ANA_MAX/core/resource_loader.py
?? ANA_MAX/dashboard/
?? ANA_MAX/dev_artifacts/
?? ANA_MAX/docs/CURRENT_SESSION_HANDOFF.md
?? ANA_MAX/docs/CURRENT_SESSION_HANDOFF_2026-05-22.md
?? ANA_MAX/docs/OFFLINE_LAB_PROFILE.md
?? ANA_MAX/docs/PROJECT_SUPPORT_AND_CREDITS.md
?? ANA_MAX/docs/SESSION_CHECKPOINT_2026-05-22T160357Z0000.md
?? ANA_MAX/docs/SESSION_CHECKPOINT_2026-05-22T160434Z0000.md
?? ANA_MAX/docs/SESSION_CHECKPOINT_2026-05-22T160934Z0000.md
?? ANA_MAX/docs/SESSION_HISTORY_2026-05-22.md
?? ANA_MAX/docs/WORKSPACE_CLEANUP_2026-05-22.md
?? ANA_MAX/docs/reports/
?? ANA_MAX/docs/test_reports/
?? ANA_MAX/docs/voice/
?? ANA_MAX/extension/
?? ANA_MAX/resources/
?? ANA_MAX/run_all_tests.py
?? ANA_MAX/run_test_suite.py
?? ANA_MAX/security/
?? ANA_MAX/stability/
?? ANA_MAX/test.py
?? ANA_MAX/test_all_tools.py
?? ANA_MAX/tools/agent_coach_tool.py
?? ANA_MAX/tools/ana_runtime_inspector.py
?? ANA_MAX/tools/error_radar_tool.py
?? ANA_MAX/tools/file_patch_tool.py
?? ANA_MAX/tools/live_debug_console.py
?? ANA_MAX/tools/path_safety.py
?? ANA_MAX/tools/project_navigator_tool.py
?? ANA_MAX/tools/schema_diff.py
?? ANA_MAX/tools/session_checkpoint_tool.py
?? ANA_MAX/tools/tool_contract_validator.py
?? ANA_MAX/tools/tool_router_tool.py
?? ANA_MAX/tools/uia_click_tool.py
?? ANA_MAX/tools/uia_type_tool.py
?? ANA_MAX/tools/v20/
?? ANA_MAX/tools/vision_find_element_tool.py
?? ANA_MAX/tools/vision_region_capture_tool.py
?? ANA_MAX/tools/watchdog.py
?? ANA_MAX/visual/
?? ANA_MAX_COMPLETE_HISTORY_AND_ROADMAP.txt
?? ANA_MAX_Launcher/launch_clean.bat
?? ANA_MAX_Launcher/launch_with_frida.bat
?? ANA_MAX_Launcher/live_watchdog.py
?? ANA_MAX_V22_ARCHITECTURE.md
?? core/
?? dashboard/
?? debug.log
?? docs/
?? tests/
?? video/
?? vscode_extension/
```
