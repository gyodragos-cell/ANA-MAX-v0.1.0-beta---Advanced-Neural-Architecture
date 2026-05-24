# ANA MAX Installation Guide

This legacy guide is kept as a short pointer for users and AI agents. The
source of truth for setup is `SETUP_AND_RUN.md`.

## Requirements

- Windows 10 or Windows 11
- Python 3.10 or newer
- VS Code, if you want to use the included extension
- Git, optional; ZIP download is fine for beginners

Optional tools:

- Android platform tools for ADB workflows
- Frida only for authorized runtime instrumentation
- Chrome for visible browser workflows

## Simple Install

If you are new to Git:

1. Open the public repository.
2. Click `Code`.
3. Click `Download ZIP`.
4. Extract the ZIP.
5. Open the extracted folder in VS Code or PowerShell.

Public repository:

```text
https://github.com/gyodragos-cell/ANA-MAX-v0.1.0-beta---Advanced-Neural-Architecture
```

Install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Start

MCP authentication is enabled by default:

```powershell
$env:MCP_API_KEY = "change-me"
python main.py
```

Expected:

```text
MCP server: http://127.0.0.1:8765
80 loaded tools
```

## Verify

Run these from the repository root:

```powershell
python -m compileall -q main.py core tools vscode_extension
python main.py --test
python main.py --list-tools
python -m unittest discover -s tests -v
```

Expected:

```text
3 PASS / 0 FAIL
80 loaded tools
all tests passing
```

## VS Code Extension

Install the included VSIX:

```powershell
code --install-extension .\vscode_extension\advanced-neural-architecture-0.2.0.vsix
```

Then use:

```text
ANA MAX: Start MCP Server
ANA MAX: Call Tool
```

Make sure the VS Code setting `anaMax.mcpApiKey` matches `MCP_API_KEY`.

## Help

- Main setup guide: `SETUP_AND_RUN.md`
- Beginner extension guide: `docs/USER_EXTENSION_INSTALL_AND_ETHICS.md`
- Public repo: `https://github.com/gyodragos-cell/ANA-MAX-v0.1.0-beta---Advanced-Neural-Architecture`
- Issues: `https://github.com/gyodragos-cell/ANA-MAX-v0.1.0-beta---Advanced-Neural-Architecture/issues`

