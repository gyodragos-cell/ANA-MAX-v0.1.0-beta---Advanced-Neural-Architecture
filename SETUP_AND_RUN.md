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
3 PASS / 0 FAIL
64 loaded tools
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

## Local QA Lab Mode

ANA MAX can be used with local/offline models when project data cannot leave
the machine. Configure a local backend such as Ollama in `config/settings.yaml`
and keep cloud API keys unset in private labs.

Typical local workflow:

```text
observe -> decide -> act -> verify -> learn
```

Use the smallest useful tool: inspect UI before clicking, read logs before
editing code, run tests before claiming a fix, and use Frida only for
authorized runtime instrumentation.

See `docs/LOCAL_QA_LAB_VISION.md`.

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
