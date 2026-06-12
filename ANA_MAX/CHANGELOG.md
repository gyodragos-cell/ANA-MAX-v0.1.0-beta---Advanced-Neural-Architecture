# ANA MAX Mother Lab Changelog

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
