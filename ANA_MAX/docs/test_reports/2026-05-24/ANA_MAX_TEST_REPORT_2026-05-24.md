# ANA MAX Test Report - 2026-05-24

## Environment

Workspace:

```text
C:\Users\billy\Desktop\ana_dev\ANA_MAX
```

Mode:

```text
mother lab
```

## Required Lab Checks

### Compile

Command:

```powershell
python -m compileall -q main.py core tools
```

Result:

```text
PASS
```

### Quick Test

Command:

```powershell
$env:VSCODE_AGENT='1'; python main.py --test
```

Important output:

```text
ANA MAX: 74 tools loaded
[PASS] file_operations
[PASS] system_control
Rezultat: 2 PASS / 0 FAIL
```

Result:

```text
PASS
```

### Tool List

Command:

```powershell
$env:VSCODE_AGENT='1'; python main.py --list-tools
```

Important output:

```text
ANA MAX: 74 tools loaded
Tool-uri ANA MAX (74 disponibile)
```

Result:

```text
PASS
```

## Spot Checks

### project_navigator

Command:

```powershell
python -c "from tools.project_navigator_tool import ProjectNavigatorTool; r=ProjectNavigatorTool().execute(operation='find', path='tools', pattern='error_*', limit=5); print(r.status.value, r.message, r.data)"
```

Result:

```text
success 1 matches
```

### file_patch

Command:

```powershell
python -c "from tools.file_patch_tool import FilePatchTool; r=FilePatchTool().execute(path='tools/file_patch_tool.py', old_text='Compact file patch tool for exact read -> patch -> write edits.', new_text='Compact file patch tool for exact read -> patch -> write edits.', preview_only=True); print(r.status.value, r.message, r.data['changed'], r.data['matches'])"
```

Result:

```text
success Patch preview generated False 1
```

### error_radar

Command:

```powershell
python -c "from tools.error_radar_tool import ErrorRadarTool; r=ErrorRadarTool().execute(scope='quick', limit=5); print(r.status.value, r.message); print(r.data)"
```

Result:

```text
success 1 findings
finding: large dirty tree
recommendation: Separate old dirty work from today's change before editing or committing.
```

### uia_click confirmation gate

Command:

```powershell
python -c "from tools.base import registry; from tools.uia_click_tool import UiaClickTool; registry.reset(); registry.register(UiaClickTool()); r=registry.execute('uia_click', window_title='x', element_title='y'); print(r.status.value, r.message or r.error)"
```

Result:

```text
requires_confirmation Tool requires confirmation: call uia_click with confirm=True
```

### window_manager

Command:

```powershell
python -c "from tools.window_manager import WindowManagerTool; r=WindowManagerTool().execute(action='list'); print(r.status.value, r.message, r.data.get('count') if r.data else None)"
```

Result:

```text
success Window action complete
```

### ocr_tool

Command:

```powershell
python -c "from tools.ocr_tool import OcrTool; r=OcrTool().execute(action='check'); print(r.status.value, r.message or r.error, r.data)"
```

Result:

```text
success OCR engine available: paddle
```

### tool_healthcheck safe

Command:

```powershell
python -c "from main import _register_all_tools; from tools.base import registry; registry.reset(); _register_all_tools(); r=registry.execute('tool_healthcheck', scope='safe'); print(r.status.value, r.message); print(r.data)"
```

Result:

```text
success Healthcheck finalizat: 6 OK / 0 FAIL
```

## Not Run

The following were not fully exercised during this pass:

- live UIA clicking/typing with `confirm=True`;
- live region screenshot capture;
- OpenCV template matching against a real template;
- full offline_lab healthcheck;
- MCP HTTP `/mcp tools/call` integration tests.

## Overall Result

```text
PASS for compile, quick test, list-tools, and non-mutating spot checks.
needs-more-testing for live desktop and public release sync.
```
