# User Guide: Extension Install And Ethical Use

This guide is for users who are not used to Git, MCP, or local AI tooling yet.

ANA MAX is not a black-hat hacking kit. It is a local MCP runtime for
observation, QA, debugging, repair, learning, and authorized security work.

Use ANA MAX for:

- your own computer, lab, app, website, repository, or test device;
- school labs, private QA labs, and engineering workflows with permission;
- red-team or security research only when the target owner has authorized it;
- debugging UI, logs, tests, browser behavior, and local runtime problems;
- helping an AI coding agent observe first, act carefully, and verify results.

Do not use ANA MAX for:

- systems you do not own or do not have permission to test;
- live third-party applications outside a written agreement or official bug
  bounty scope;
- stealing data, bypassing access controls, spying, persistence, or malware;
- harassment, credential theft, account abuse, or destructive automation;
- pretending a demo is authorized security work when it is not.

The rule is simple:

```text
own it or have written permission before you test it
```

## Install Without Git

Use this path if Git feels confusing.

1. Open the GitHub repository page in your browser.
2. Click `Code`.
3. Click `Download ZIP`.
4. Extract the ZIP to a normal folder, for example:

```text
C:\Users\YourName\Desktop\ANA_MAX
```

5. Open that folder in VS Code.
6. Install Python dependencies from the VS Code terminal:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

7. Install the VS Code extension from the included VSIX:

```powershell
code --install-extension .\vscode_extension\advanced-neural-architecture-0.2.0.vsix
```

Alternative VS Code method:

1. Open Extensions.
2. Click the `...` menu.
3. Choose `Install from VSIX`.
4. Select `vscode_extension\advanced-neural-architecture-0.2.0.vsix`.

## If An AI Agent Helps You

It is normal to ask Codex, Windsurf, Cursor, Qoder, or another coding agent to
help with installation and connection. Give the agent this rule:

```text
Use the public repo, set the MCP key, start main.py, list tools, run tests, and report only verified facts.
```

The correct public repository is:

```text
https://github.com/gyodragos-cell/ANA-MAX-v0.1.0-beta---Advanced-Neural-Architecture
```

The agent should not use private lab paths, old repository aliases, local
shortcuts, hidden tokens, or forum guesses. If something fails, it should show
the command, the error, and the next safe fix.

## Install With Git

Use this path if you already know Git.

```powershell
git clone https://github.com/gyodragos-cell/ANA-MAX-v0.1.0-beta---Advanced-Neural-Architecture.git
cd ANA-MAX-v0.1.0-beta---Advanced-Neural-Architecture
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
code --install-extension .\vscode_extension\advanced-neural-architecture-0.2.0.vsix
```

## Start ANA MAX

MCP authentication is enabled by default.

```powershell
$env:MCP_API_KEY = "change-me"
python main.py
```

The local MCP server starts at:

```text
http://127.0.0.1:8765/mcp
```

Required header for MCP clients:

```text
Authorization: Bearer change-me
```

In VS Code, open the command palette and run:

```text
ANA MAX: Start MCP Server
ANA MAX: Call Tool
```

## What Users Should Expect

ANA MAX is useful when it is used as a workflow:

```text
observe -> decide -> act -> verify -> learn
```

Good examples:

- inspect the current desktop before clicking;
- read repository files before editing;
- run tests before saying a fix is complete;
- use browser tools to check a local app;
- use Frida only for authorized runtime diagnostics.

Bad examples:

- clicking blindly;
- running powerful tools without knowing the target;
- testing machines or accounts without permission;
- treating security tools as entertainment.

ANA MAX is built for people who repair, verify, teach, test, and build.
