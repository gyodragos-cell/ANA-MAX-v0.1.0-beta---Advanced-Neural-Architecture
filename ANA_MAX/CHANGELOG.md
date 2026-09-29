# ANA MAX Mother Lab Changelog

## 2026-08-07 - MCP Tool Expansion & Mitmproxy Whitehat Testing

### Added
- **MCP Bridges Expansion**: Extended MCP infrastructure from 31 to 56 total tools
  - `ana-max-core`: 16 → 26 tools (+10 new: smart_search, code_context_pack, tool_healthcheck, live_debug_console, procmon_monitor, memory_cortex, context_engine, privacy_shield, session_checkpoint, qa_tool, conversation_audit, graph_context_pack)
  - `ana-max-advanced`: 15 → 30 tools (+15 new: foreground_ui_snapshot, live_desktop_viewer, windows_deep_sight, windows_uia_bridge, frida_automation, network_pentest_tool, mitm_analyzer_tool, adb_tool, apk_analyzer, watchdog, reflex_dispatcher, session_audit_tool, clipboard_manager, workspace_situational_awareness, advanced_scanner)
- **Mitmproxy Integration**: Installed mitmproxy 12.2.3 for whitehat testing
  - Created `ANA_MAX/tools/mitmproxy_live_analyzer.py` with vulnerability scanning
  - Created `START_MITM_LIVE.bat` for quick launch
  - Created `test_mcp_smoke.py` for MCP bridge validation
  - Created `test_mitmproxy.py` for mitmproxy installation verification
- **Security Testing Capabilities**:
  - Real-time vulnerability scanning (XSS, SQLi, Path Traversal, SSRF, Info Disclosure)
  - Sensitive data detection (passwords, API keys, tokens)
  - Reverse proxy mode for ANA MCP traffic interception
  - JSON export for agent analysis

### Modified
- **`.agents/mcp.json`**: Updated MCP configuration to use dual bridges (ana-max-core + ana-max-advanced) instead of single ana-max-lab bridge
- **`requirements.txt`**: Added `mitmproxy>=12.0.0` for whitehat testing capabilities
- **`mcp_ana_bridge_core.py`**: Added 12 new core tools with delegate implementations
- **`mcp_ana_bridge_advanced.py`**: Added 15 new advanced tools with delegate implementations

### Fixed
- **MCP Configuration**: Resolved "ana ma lab appears yellow" issue by updating `.agents/mcp.json` to use correct bridge files
- **Dependency Conflicts**: Resolved typing-extensions compatibility (upgraded to 4.16.0 for pydantic compatibility)

### Technical Notes
- Excluded voice and OCR tools from MCP expansion per user requirements
- All new MCP tools are currently delegates to local ANA implementations
- Mitmproxy chosen over Charles Proxy for superior Python integration and automation capabilities
- Smoke test validates both MCP bridges load correctly with expected tool counts

## 2026-06-06 - Direct Web Chat Interface & Fast Conversation Mode

- Added `/chat` route in `main.py` serving a premium web chat UI.
- Added `ana.chat` JSON-RPC method to bypass the slow multi-agent loop for standard conversational messages, allowing instant responses.

## 2026-05-25 - Lightweight Resource System

- Implemented lightweight resource system (texts + themes + loader + dashboard integration).

## 18.0-MAX-lab.audit.2026-05-24

Status: private mother lab, needs-more-testing before public sync.

### Added

- Added `file_patch` for exact text patching with preview-first behavior,
  protected-path blocking, compact diffs, and before/after hashes.
- Added `project_navigator` for compact list/tree/find/grep/open project
  navigation.
- Added `uia_click` as a confirmation-gated UIA click wrapper.
- Added `uia_type` as a confirmation-gated UIA typing wrapper.
- Added `vision_region_capture` for crop-based screen capture.
- Added `vision_find_element` for OpenCV template matching.
- Added `error_radar` for first-pass blocker detection from logs,
  observability summaries, git state, and visible window titles.
- Added audit report:
  `docs/logs/ANA_MAX_AUDIT_2026-05-24.md`.
- Added test report:
  `docs/test_reports/2026-05-24/ANA_MAX_TEST_REPORT_2026-05-24.md`.

### Changed

- Updated mother lab baseline to `74 loaded tools, 2 PASS / 0 FAIL`.
- Registered new tools in `main.py`.
- Exported new tool classes in `tools/__init__.py`.
- Updated `tool_healthcheck` fallback registration and safe/offline checks.
- Updated lab docs and roadmap with new tool count and stabilization targets.

### Fixed

- Strengthened `Tool.safe_execute()` parameter validation and compact error
  handling.
- Normalized non-`ToolResult` returns into `ToolResult` to reduce registry
  fragility.
- Removed default raw stdout from `ToolRegistry.execute()` unless
  `ANA_TOOL_STDOUT=1` is set.
- Added direct Tool classes for `ocr_tool` and `window_manager`.
- Made `ocr_tool action=check` lightweight and quiet by avoiding PaddleOCR model
  loading.
- Reduced noisy PaddleOCR stdout/stderr during OCR load/execution.
- Fixed `window_manager` false-success behavior when mutating actions cannot
  find a target window.
- Tightened `error_radar` HTTP auth matching to avoid timestamp false positives.

### Verification

```powershell
python -m compileall -q main.py core tools
$env:VSCODE_AGENT='1'; python main.py --test
$env:VSCODE_AGENT='1'; python main.py --list-tools
```

Observed:

```text
compileall: OK
quick test: 2 PASS / 0 FAIL
list-tools: 74 loaded tools
tool_healthcheck safe: 6 OK / 0 FAIL
```

### Sync Decision

```text
needs-more-testing
```

Do not sync this entire change set to `ANA_MAX_GitHub_Release` yet. Select and
test a public-safe subset first.

- Added v21 foundations for theme switching, UI modernization hooks, dev-mode messaging, Resource Inspector, Dashboard v2, and Tool Health Visualizer placeholders.
