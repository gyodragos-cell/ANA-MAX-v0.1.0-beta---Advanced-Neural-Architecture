# ANA MAX Tool Status - Mother Lab

Date: 2026-05-27

Baseline:

```text
86 loaded tools in mother lab after MCP restart
session_lifecycle visible through HTTP /mcp tools/list and /execute
```

Legend:

- OK: registered and either verified directly or considered stable from current
  baseline.
- In progress: registered but needs more live or MCP-level testing.
- Broken: confirmed failing in this audit.
- Premium/internal: expected to require confirmation, license, or controlled lab
  use.

## Summary

```text
OK: core compile, quick test, list-tools, safe healthcheck, lifecycle wake/rest smoke
Broken: none confirmed in this pass
In progress: live desktop, UI mutation, template matching, broader MCP tests
```

## Tool Table

| Tool | Status | Notes |
| --- | --- | --- |
| `adal_integration` | Retired | Removed from active tool registration; historical only. |
| `adb_operations` | In progress | Registered; device-dependent. |
| `advanced_scanner` | In progress | Registered; authorized security use only. |
| `agent_coach` | OK | Present; safe healthcheck path uses it in offline profile. |
| `ana_identity` | OK | Registered. |
| `ana_memory` | In progress | Registered; private memory tool, not exercised to avoid touching memory stores. |
| `ana_orchestrator` | In progress | Registered AI Core adapter; not exercised. |
| `apk_analyzer` | In progress | Registered; APK/toolchain-dependent. |
| `autonomous_engine` | In progress | Registered; needs controlled scenarios. |
| `bash_exec` | In progress | Registered; powerful shell tool, needs policy controls. |
| `browser_control` | In progress | Registered; browser persistence needs more testing. |
| `clipboard_manager` | In progress | Registered adapter; not exercised. |
| `code_search` | OK | Registered. |
| `code_tools` | OK | Registered. |
| `codebase_understanding` | In progress | Registered; semantic paths can be heavier. |
| `context_bridge` | In progress | Registered adapter; persistence-sensitive. |
| `context_engine` | In progress | Registered adapter; not exercised. |
| `conversation_learning` | In progress | Registered; not exercised to avoid extra memory writes. |
| `debugger` | OK | Registered. |
| `desktop_capture` | In progress | Registered; needs native/safer window capture pass. |
| `desktop_control` | In progress / Premium | Registered; needs stricter validation and confirmation boundaries. |
| `edge_tts_voice` | In progress | Registered; voice dependencies vary by machine. |
| `edit` | OK | Registered; existing exact edit tool. |
| `error_radar` | OK | Added and spot-checked; reports dirty tree correctly. |
| `event_stream` | In progress | Registered; not exercised. |
| `file_operations` | OK | Quick test PASS. |
| `file_patch` | OK | Added and spot-checked with preview-only patch. |
| `foreground_ui_snapshot` | In progress | Registered; live UI quality depends on active window. |
| `frida_instrument` | In progress / Premium-internal | Registered; requires explicit confirmation and authorized runtime use. |
| `git_operations` | OK | Registered. |
| `glob_search` | OK | Registered. |
| `grep_content` | OK | Registered. |
| `grep_file` | OK | Registered. |
| `hardware_scanner` | In progress | Registered; authorized hardware/security use only. |
| `live_desktop_viewer` | In progress / Premium | Registered; live streaming needs controlled test. |
| `live_tool_healer` | In progress | Registered; needs real failure scenarios. |
| `memory_cortex` | In progress | Registered adapter; memory-sensitive. |
| `mitm_analyzer` | In progress | Registered; authorized traffic analysis only. |
| `network_diag` | OK | Registered. |
| `network_pentest` | In progress | Registered; authorized targets only. |
| `ocr_tool` | OK | Direct Tool class added; `check` spot-check PASS. |
| `privacy_shield` | OK | Registered. |
| `proactive_interrupt` | In progress | Registered adapter; not exercised. |
| `project_navigator` | OK | Added and spot-checked. |
| `qa_testing` | OK | Registered. |
| `remote_control` | In progress | Registered; remote targets not tested. |
| `science_research` | In progress | Registered; not exercised. |
| `security_audit` | OK | Registered. |
| `self_evolving_tool` | In progress | Registered adapter; high-risk auto-change behavior needs controls. |
| `session_checkpoint` | OK | Registered; existing handoff tool. |
| `session_lifecycle` | OK | v1.0.12 lifecycle coordinator; MCP-visible after restart; `wake` and `rest consolidate=false` smoke PASS. |
| `session_log_miner` | In progress | Registered; private logs not mined in this pass. |
| `session_rem_sleep` | OK | Between-session retrospective tool; preview/save flow used by lifecycle rest. |
| `smart_search` | OK | Used in safe healthcheck. |
| `swarm_orchestrator` | In progress | Registered; not exercised. |
| `system_control` | OK | Quick test PASS. |
| `system_optimization` | In progress | Registered; mutating system actions need confirmation. |
| `task` | In progress | Registered; needs controlled multi-step tests. |
| `terminal` | In progress | Registered; powerful shell tool needs stricter destructive-command policy. |
| `todowrite` | OK | Registered. |
| `tool_healthcheck` | OK | Safe healthcheck PASS: 6 OK / 0 FAIL. |
| `tool_router` | OK | Added as read-only MCP recommendation router; direct smoke tested; included in auto-guidance for failed tool results. |
| `uia_click` | In progress | Added; confirmation gate spot-check PASS; live click not run. |
| `uia_type` | In progress | Added; confirmation-gated; live typing not run. |
| `vector_memory` | In progress | Registered; memory/vector dependencies not exercised. |
| `vision_fallback` | In progress | Registered; not exercised. |
| `vision_find_element` | In progress | Added; compile/register OK; needs real template scenario. |
| `vision_region_capture` | In progress | Added; compile/register OK; needs live capture scenario. |
| `web_ai_bridge` | In progress | Registered; provider-key dependent. |
| `web_fetch` | In progress | Registered; network dependent. |
| `web_scraper` | In progress | Registered; network dependent. |
| `web_search` | In progress | Registered; network dependent. |
| `window_manager` | OK | Direct Tool class added; list spot-check PASS. |
| `windows_deep_sight` | In progress / Premium | Registered; premium/internal diagnostics. |
| `windows_insight` | In progress / Premium | Registered; needs controlled diagnostic test. |
| `windows_uia_bridge` | In progress | Registered; core structural eyes; needs output limiting and selector hardening. |
| `workspace_situational_awareness` | OK | Safe healthcheck PASS; compact dirty-tree output retained. |

## Confirmed Broken

None confirmed during this pass.

## Highest Priority Next Fixes

1. Stabilize `desktop_capture` window capture and reduce PowerShell/clipboard
   dependency.
2. Harden `desktop_control` validation and confirmation behavior.
3. Add output limits and selector escaping to `windows_uia_bridge`.
4. Add MCP-level tests for all new tools.
5. Add unit tests for `file_patch`, `project_navigator`, `error_radar`, and
   registry validation.
