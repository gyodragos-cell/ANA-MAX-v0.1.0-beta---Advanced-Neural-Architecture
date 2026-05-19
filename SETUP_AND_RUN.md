# Setup And Run

This file is intentionally ASCII-only. PowerShell examples and expected output
must not contain diacritics, smart quotes, emoji, or mojibake.

## Install

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Verify

```powershell
python -m compileall -q main.py core tools vscode_extension
python main.py --test
python main.py --list-tools
python -m unittest discover -s tests -v
```

Expected:

```text
2 PASS / 0 FAIL
63 loaded tools
all tests passing
```

## Run

MCP authentication is enabled by default.

```powershell
$env:MCP_API_KEY = "change-me"
python main.py
```

Server:

```text
http://127.0.0.1:8765
```

Example:

```powershell
curl -X POST http://127.0.0.1:8765/mcp `
  -H "Content-Type: application/json" `
  -H "Authorization: Bearer change-me" `
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
```

## Troubleshooting

If Python cannot import project modules, run commands from the repo root.

If premium tools return a blocked result, activate a valid license. This is
expected behavior for:

- `live_desktop_viewer`
- `desktop_control`
- `desktop_control_tool`
- `windows_insight`
- `windows_insight_tool`
- `windows_deep_sight`

If text looks corrupted in PowerShell, keep the output ASCII and rerun the
verification commands.
