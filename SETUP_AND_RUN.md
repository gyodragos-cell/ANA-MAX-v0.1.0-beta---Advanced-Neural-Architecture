# Setup And Run

This file is intentionally ASCII-only. PowerShell examples and expected output
must not contain diacritics, smart quotes, emoji, or mojibake.

## Install

If you are new to Git, use the simple path:

1. Open the GitHub page.
2. Click `Code`.
3. Click `Download ZIP`.
4. Extract the ZIP.
5. Open the extracted folder in VS Code or PowerShell.

Then run these commands from the extracted folder:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

If you already know Git, clone the repository and run the same commands from
the repo root.

## What Success Looks Like

These are the important signs:

```text
python main.py --test        -> 3 PASS / 0 FAIL
python main.py --list-tools  -> 71 loaded tools
server URL                   -> http://127.0.0.1:8765
```

If your result is different, do not guess. Read the error message, then run the
verification commands below.

## Install The VS Code Extension

If you downloaded the project as a ZIP from GitHub, extract it first and open
the extracted folder in VS Code.

Install the included VSIX:

```powershell
code --install-extension .\vscode_extension\advanced-neural-architecture-0.2.0.vsix
```

Or use the VS Code UI:

```text
Extensions -> ... -> Install from VSIX
```

After installing, use the command palette:

```text
ANA MAX: Start MCP Server
ANA MAX: Call Tool
```

The extension reads these VS Code settings:

```json
{
  "anaMax.mcpApiKey": "change-me",
  "anaMax.mcpHost": "127.0.0.1",
  "anaMax.mcpPort": 8765
}
```

When the server is started from VS Code, `anaMax.mcpApiKey` is passed as
`MCP_API_KEY`. Tool calls from the extension send the matching Bearer token.

VS Code 1.121+ sets `VSCODE_AGENT` for terminal commands launched by an agent.
ANA MAX detects it automatically and uses compact startup output for agent
sessions. Human-launched terminals keep normal output. The `/health` endpoint
reports `vscode_agent` and `output_profile`.

Beginner guide:

```text
docs/USER_EXTENSION_INSTALL_AND_ETHICS.md
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
71 loaded tools
all tests passing
```

## Run

MCP authentication is enabled by default.

```powershell
$env:MCP_API_KEY = "change-me"
$env:ANA_BROWSER_PATH = "C:\Program Files\Google\Chrome\Application\chrome.exe"
python main.py
```

Keep this terminal open while you use the VS Code extension or another MCP
client. If you change tool registration or update the code, stop and restart
the server so the tool list is fresh.

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

## Ethical Use

ANA MAX is for white-hat, authorized red-team, QA, education, debugging, and
repair workflows. Do not use it against systems, accounts, networks, or devices
that you do not own or do not have permission to test.

Simple rule:

```text
own it or have written permission before you test it
```

## Agent IDE Connection

ANA MAX exposes the same local MCP runtime to the VS Code extension and to any
agent IDE that can call MCP over HTTP.

Default endpoint:

```text
http://127.0.0.1:8765/mcp
```

Required header:

```text
Authorization: Bearer change-me
```

Recommended agent flow:

```text
tools/list -> observe workspace -> choose smallest useful tool -> act -> verify
```

If you are an AI agent helping a user connect ANA MAX, keep these facts fixed:

- public repo: `https://github.com/gyodragos-cell/ANA-MAX-v0.1.0-beta---Advanced-Neural-Architecture`
- expected tool list: `71 loaded tools`
- default server: `http://127.0.0.1:8765/mcp`
- required auth header: `Authorization: Bearer change-me`
- VS Code setting: `anaMax.mcpApiKey` must match `MCP_API_KEY`

Do not use private lab paths, old repository aliases, or hidden local setup
notes. Read `docs/PROJECT_MAP_AI_GUIDE.md` before changing files.

For the three flagship workflows, see
`docs/AGENT_IDE_SUPER_TOOLS_PLAN.md`.

## Browser Workflows

Chrome is recommended for visible local browser workflows on Windows:

```powershell
$env:ANA_BROWSER_PATH = "C:\Program Files\Google\Chrome\Application\chrome.exe"
```

Use `browser_control` operation `open_external` when a normal visible Chrome
window should stay open after a one-shot tool call exits. Use operation `open`
for Playwright automation sessions; those sessions may use bundled Chromium
first and stay alive while the ANA MAX server process is running.

## Troubleshooting

If Python cannot import project modules, run commands from the repo root.

If the VS Code extension cannot call tools, check that:

- `python main.py` is still running.
- `MCP_API_KEY` matches `anaMax.mcpApiKey`.
- The server URL is `http://127.0.0.1:8765`.
- The request includes `Authorization: Bearer change-me`.

If `tools/list` shows an old tool count after an update, restart `python
main.py`. A running MCP server keeps its in-memory registry until it restarts.

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
