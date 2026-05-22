# ANA MAX

![Build Status](https://github.com/YOUR_USERNAME/ana-max/actions/workflows/ci.yml/badge.svg)
![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue)
![Platform Windows](https://img.shields.io/badge/platform-Windows-lightgrey)
![License MIT](https://img.shields.io/badge/license-MIT-green)
![Tools](https://img.shields.io/badge/tools-64-blueviolet)

[![Vezi Demo Live](https://img.shields.io/badge/%F0%9F%9A%80_Vezi_Demo_Live-GitHub_Pages-ff6600?style=for-the-badge&logo=github)](https://gyodragos-cell.github.io/ANA-MAX-v0.1.0-beta---Advanced-Neural-Architecture/)
[![Watch Demo 1](https://img.shields.io/badge/Watch_Demo_1-YouTube-red?style=for-the-badge&logo=youtube)](https://www.youtube.com/watch?v=yIWILEd6glU)
[![Watch Demo 2](https://img.shields.io/badge/Watch_Demo_2-YouTube-red?style=for-the-badge&logo=youtube)](https://youtu.be/2Ft9eRO7GzM)

ANA MAX is a Windows-first MCP runtime for local QA labs, private workstations,
offline LLMs, and AI coding agents that need real situational awareness before
they act: files, git state, terminal output, desktop vision, Windows UI
automation, memory, runtime instrumentation, voice feedback, and smoke-test
verification.

Plain version:

```text
ANA MAX is a local helper layer for AI agents.
It gives an agent tools to look at your project, inspect the Windows desktop,
run checks, and verify work before it claims the job is done.
```

For agent IDE workflows, the short version is:

```text
Super tools for local AI coding agents.
```

This repository is the clean public release. It must stay public-safe,
repeatable, and boring in the best possible way.

## Start Here If You Are New

You do not need to be a senior engineer to understand the goal.

ANA MAX does three practical things:

1. It observes: files, git status, terminal output, visible windows, screenshots,
   and UI structure.
2. It acts through tools: file operations, tests, browser control, desktop
   helpers, diagnostics, and MCP calls.
3. It verifies: quick checks, tool health, smoke tests, and clear pass/fail
   output.

If you are new to Git, download the ZIP from GitHub instead of cloning. Then
read this file:

```text
SETUP_AND_RUN.md
```

If you use VS Code, start with:

```text
docs/USER_EXTENSION_INSTALL_AND_ETHICS.md
```

If you are an AI agent or coding assistant, read first:

```text
docs/PROJECT_MAP_AI_GUIDE.md
```

## What This Is Not

ANA MAX is not a magic autopilot and it is not a replacement for judgment. It
does not make private data safe to publish. It does not give permission to test
systems you do not own.

Good use:

```text
observe local evidence -> make a focused change -> run checks -> explain result
```

Bad use:

```text
guess -> edit many files -> skip verification -> hide failures
```

## Ethical Use

ANA MAX is for white-hat, red-team with permission, QA, education, debugging,
and local repair work. It is not a black-hat hacking kit.

Use it only on systems you own or are explicitly allowed to test. The purpose
is to help users and agents observe, diagnose, fix, verify, and learn.

## Why It Exists

Most agents lose time because they guess from partial context. ANA MAX is built
to help agents observe the real workspace first, pick the smallest useful tool,
act, verify the result, and remember useful lessons.

The intended workflow is:

```text
observe -> instrument when needed -> act -> verify -> learn
```

This can turn long manual debugging, QA, UI inspection, and local automation
work into a focused agent workflow, especially when the agent can see the
desktop, inspect Windows UI/API state, use git and tests, speak status aloud,
and use Frida for authorized runtime instrumentation.

ANA MAX is privacy-first and hybrid:

- local/offline workflows are the default direction;
- online models can be used when configured by the operator;
- MCP auth is enabled by default;
- private memory, logs, screenshots, tokens, and license files do not belong in
  the public release.

## Local QA Lab Vision

ANA MAX is designed for environments where data should stay on the machine:

- QA labs that need repeatable desktop observations, logs, and smoke checks;
- AI coding agents working with local projects and local evidence;
- offline Ollama-style model setups where tools provide the missing senses;
- security or reverse-engineering labs where Frida is used only with
  authorization and only when runtime instrumentation is really needed;
- private workstations where screenshots, memory, logs, and tokens must not be
  uploaded to a cloud service.

The important idea is simple: a local model can reason, but tools give it eyes,
hands, ears, memory, and verification. See
[`docs/LOCAL_QA_LAB_VISION.md`](docs/LOCAL_QA_LAB_VISION.md).

## What Makes It Different

- It gives agents situational awareness, not just file access.
- It combines desktop vision, Windows UI automation, code tools, git, memory,
  and verification in one workflow.
- It supports authorized runtime instrumentation with Frida when static
  inspection is not enough.
- It treats `desktop_capture` as free Vision AI and keeps deep desktop control
  premium-gated.
- It keeps public docs and shell-facing examples ASCII-only so Windows consoles
  and weaker agents can parse them reliably.

## Agent IDE Super Tools

ANA MAX is meant to act as a local tool layer for agent IDEs and coding agents.
The strongest public story is not the number of tools. It is three reliable
workflows:

- desktop reasoning: observe the real Windows desktop or app state before
  acting;
- runtime diagnostics: use local evidence, logs, tests, and authorized Frida
  instrumentation when static inspection is not enough;
- adaptive IDE flow: connect through MCP, inspect workspace state, make a
  focused change, and verify before handoff.

For visible external browser workflows on Windows, ANA MAX prefers Chrome. The
`browser_control` tool supports `open_external` for launching a normal Chrome
window that stays open after the tool call exits. Operation `open` uses a
Playwright automation session, which may use bundled Chromium first and stays
alive while the ANA server process is running.

Use this positioning when explaining the project:

```text
Local-first runtime orchestration and adaptive desktop tooling for agent IDE
workflows on Windows.
```

See [`docs/AGENT_IDE_SUPER_TOOLS_PLAN.md`](docs/AGENT_IDE_SUPER_TOOLS_PLAN.md)
for the stabilization plan, demo package, observability priorities, and
security posture.

## AI Collaboration Acknowledgement

This project was built and repaired through a human-led engineering workflow.
Dragos owns the vision, direction, testing, and final decisions.

OpenAI Codex has been the main AI coding collaborator for this release:

- helped turn a noisy experimental workspace into a cleaner public release;
- helped repair MCP, voice, desktop diagnostic, and release-hygiene workflows;
- helped separate public-safe demo material from local-only tools;
- helped keep changes testable through repeatable quality checks;
- helped document the project in a way that engineers can verify instead of
  trusting hype.

Official link:

- OpenAI Codex: https://openai.com/codex/

Qoder is also credited as a useful agentic coding workflow tool and source of
lab assistance/inspiration.

Official links:

- Qoder: https://qoder.com/

The goal of this acknowledgement is simple: show that AI tools can be useful
when they work as careful engineering collaborators, not blind code generators.

For more detail, see
[`docs/AI_COLLABORATION_AND_TOOLS.md`](docs/AI_COLLABORATION_AND_TOOLS.md).

## Demo

**[Website - Live Demo](https://gyodragos-cell.github.io/ANA-MAX-v0.1.0-beta---Advanced-Neural-Architecture/)**

Current public videos:

- **[Watch Demo 1 on YouTube](https://www.youtube.com/watch?v=yIWILEd6glU)**
- **[Watch Demo 2 on YouTube](https://youtu.be/2Ft9eRO7GzM)**

Video demos should be hosted outside git, for example on YouTube or GitHub Releases, then linked from this README and the website. Large `.mp4` files do not belong in the repository.

The demo should prove the core workflow quickly: observe the workspace, choose
focused tools, act, run smoke checks, and verify the result. Keep the public
demo short and factual; users should understand the value before reading the
full architecture notes.

For the recommended public recording plan, see
[`docs/ANA_MAX_WOW_DEMO.md`](docs/ANA_MAX_WOW_DEMO.md).

## Quick Start

Run from the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:MCP_API_KEY = "change-me"
$env:ANA_BROWSER_PATH = "C:\Program Files\Google\Chrome\Application\chrome.exe"
python main.py

# Launch the voice engine
scripts\ana_voice.bat
```

ANA MAX starts on `http://127.0.0.1:8765` by default.

MCP auth is enabled by default. Send:

```text
Authorization: Bearer change-me
```

Example MCP request:

```powershell
curl -X POST http://127.0.0.1:8765/mcp `
  -H "Content-Type: application/json" `
  -H "Authorization: Bearer change-me" `
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
```

## VS Code Extension

For users who do not know Git yet, download the repository ZIP from GitHub,
extract it, open the folder in VS Code, then install the included VSIX:

```powershell
code --install-extension .\vscode_extension\advanced-neural-architecture-0.2.0.vsix
```

You can also install it from VS Code:

```text
Extensions -> ... -> Install from VSIX
```

Then run:

```text
ANA MAX: Start MCP Server
ANA MAX: Call Tool
```

The extension uses these VS Code settings:

```json
{
  "anaMax.mcpApiKey": "change-me",
  "anaMax.mcpHost": "127.0.0.1",
  "anaMax.mcpPort": 8765
}
```

`anaMax.mcpApiKey` is passed to the server as `MCP_API_KEY` and sent as the
Bearer token when the extension calls local MCP endpoints.

VS Code 1.121+ marks agent-launched terminal commands with `VSCODE_AGENT`.
ANA MAX detects that signal and switches startup output to a compact
agent-readable profile. Manual terminal runs keep the normal human-readable
output. Check `/health` for `vscode_agent` and `output_profile`.

For a beginner-friendly walkthrough, see
[`docs/USER_EXTENSION_INSTALL_AND_ETHICS.md`](docs/USER_EXTENSION_INSTALL_AND_ETHICS.md).

## Verification

Before handing off changes, run:

```powershell
python -m compileall -q main.py core tools vscode_extension
python main.py --test
python main.py --list-tools
python -m unittest discover -s tests -v
```

Expected baseline:

- `python main.py --test`: `3 PASS / 0 FAIL`
- `python main.py --list-tools`: 64 loaded tools
- `python -m unittest discover -s tests -v`: all tests passing

## Tool Model

Core tool behavior is owned by `tools/base.py`.

### Tool Status Overview

| Category | Status | Example Tools |
|----------|--------|---------------|
| **Core Utilities** | Stable | `file_operations`, `code_tools`, `git_operations` |
| **Desktop Eyes** | Stable | `desktop_capture`, `windows_uia_bridge`, `ocr_tool` |
| **AI Core Modules** | Experimental | `context_engine`, `self_evolving_tool` |
| **Deep Windows API** | Premium / Pro | `desktop_control`, `windows_deep_sight` |

New tools must:

- inherit from `tools.base.Tool`;
- implement `get_definition()` and `execute()`;
- be registered from `main.py`;
- be importable from this clean repo;
- have docs only when the code and tests exist.

## Premium Gate

`desktop_capture` is free Vision AI.

These tools are premium-gated at runtime:

- `live_desktop_viewer`
- `desktop_control`
- `desktop_control_tool`
- `windows_insight`
- `windows_insight_tool`
- `windows_deep_sight`

Premium checks happen in `ToolRegistry.execute()`, so the gate applies through
CLI, HTTP, and MCP.

## Windows And PowerShell Text Rule

All commands, expected terminal output, log examples, and setup snippets in
public docs must be ASCII-only. Do not use Romanian diacritics, smart quotes,
emoji, or mojibake in shell-facing text.

Good:

```text
3 PASS / 0 FAIL
64 loaded tools
Authorization: Bearer change-me
```

Bad:

```text
mojibake text
non-ascii shell output
```

This is deliberate. Cheap agents and Windows consoles often stumble on encoded
text. Public docs should be simple enough that weak agents cannot misread them.

## Public Release Hygiene

Do not add private workspace notes, local IDE setup files, local shortcuts,
private tokens, logs, databases, or screenshots.

If a feature is experimental, keep it private until code, tests, docs, and
release hygiene are all present.

When behavior changes, update code, docs, `.env.example`, tests, and release
counts together. Users should never need private notes to know how the public
release works.

## License

MIT. Use automated desktop control only on machines you own or are allowed to
operate.

