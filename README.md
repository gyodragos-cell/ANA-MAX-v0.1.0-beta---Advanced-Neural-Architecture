# ANA MAX

![Build Status](https://github.com/gyodragos-cell/ANA-MAX-v0.1.0-beta---Advanced-Neural-Architecture/actions/workflows/ci.yml/badge.svg)
![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue)
![Platform Windows](https://img.shields.io/badge/platform-Windows-lightgrey)
![License MIT](https://img.shields.io/badge/license-MIT-green)
![Tools](https://img.shields.io/badge/tools-80-blueviolet)

[![Live Site](https://img.shields.io/badge/Live_Site-GitHub_Pages-ff6600?style=for-the-badge&logo=github)](https://gyodragos-cell.github.io/ANA-MAX-v0.1.0-beta---Advanced-Neural-Architecture/)
[![Watch Demo 1](https://img.shields.io/badge/Watch_Demo_1-YouTube-red?style=for-the-badge&logo=youtube)](https://www.youtube.com/watch?v=yIWILEd6glU)
[![Watch Demo 2](https://img.shields.io/badge/Watch_Demo_2-YouTube-red?style=for-the-badge&logo=youtube)](https://youtu.be/2Ft9eRO7GzM)

Public release wording:

```text
<!-- # PATCH_START v24_release -->
Version: v24.0.0
<!-- # PATCH_END v24_release -->
Tools: 80 loaded tools
AI Core adapters: 7
Premium-gated families: 4
Workflow: observe -> decide -> act -> verify
```

<!-- # PATCH_START v19_phase4 -->
v19 adds three manual, read-only diagnostics tools:
`ana_runtime_inspector`, `tool_contract_validator`, and `schema_diff`.
They are registered for explicit calls only and do not auto-run.
<!-- # PATCH_END v19_phase4 -->

<!-- # PATCH_START v20_phase3 -->
v20 adds manual, read-only autonomy tools:
`ana_health_check`, `baseline_update_suggester`, `docs_generator`,
`ana_patch_suggester`, `runtime_guard`, and `autonomy_dashboard`.
They are exposed for explicit calls only, do not auto-run, and do not change
runtime behavior.
<!-- # PATCH_END v20_phase3 -->

<!-- # PATCH_START v20_final -->
The autonomy dashboard is exposed as `autonomy_dashboard`. It returns a
read-only HTML report for the v20 layer and does not write files, start a
server, or apply patches.
<!-- # PATCH_END v20_final -->

<!-- # PATCH_START v21_resource_system -->
## Resource System

ANA MAX includes a lightweight resource system for dashboard-facing UI
resources:

- `resources/texts/` stores localization JSON files for English and Romanian.
- `resources/themes/` stores light and dark theme JSON files.
- `core/resource_loader.py` loads texts, themes, and optional icons with safe
  fallback behavior.

Missing or invalid text files fall back to English, missing or invalid themes
fall back to the light theme, and missing icons return an empty string.

## v21 Foundations

v21 foundations add resource-only hooks for theme switching, future dashboard
layout blocks, dev-mode messaging, Resource Inspector, Dashboard v2, and Tool
Health Visualizer placeholders. These hooks do not expose private lab data and
do not add new tool logic.
<!-- # PATCH_END v21_resource_system -->

<!-- # PATCH_START v22_release -->
## v22 Runtime Orchestrator

v22 adds a public-safe, scaffolded runtime orchestration layer for agents that
need compact context and predictable tool routing before execution. The new
modules live in `core/`:

- `input_layer.py`
- `context_builder.py`
- `ai_engine.py`
- `tool_router.py`
- `execution_layer.py`
- `observability.py`
- `scenario_simulator.py`
- `runtime_config.py`
- `release_sync.py`
- `ana_runtime.py`

The v22 layer is intentionally conservative: it uses fake or injected execution
in tests, keeps release sync as a read-only planner, and does not add loaded MCP
tools by itself. Runtime behavior remains routed through the existing tool
registry when connected by future integration work.
<!-- # PATCH_END v22_release -->

<!-- # PATCH_START v24_release -->
## v24 Runtime

v24 documents the next runtime evolution: parallel orchestrator, multi-agent
mode, memory manager, hybrid AI, adaptive router v23, self-healing runtime, and
safe live-tool execution boundaries.

The public v24 release keeps the loaded MCP tool count unchanged at 80. The v24
runtime work is documented as architecture and release preparation; private lab
state, optimization snapshots, and integration artifacts remain out of the
public release.

See `docs/ANA_MAX_V24_RUNTIME.md`.
<!-- # PATCH_END v24_release -->

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

Another way to say it:

```text
A local multi-tool runtime for AI agents: observe, diagnose, act, verify, and learn on a real Windows machine.
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

## For AI Agents Helping Users

Many users will ask an AI coding agent to install, connect, or test ANA MAX.
Treat this repository as the clean public release and keep the workflow simple:

```text
read the project map -> install dependencies -> start main.py -> verify tools/list -> explain the result
```

Use the canonical repository URL everywhere:

```text
https://github.com/gyodragos-cell/ANA-MAX-v0.1.0-beta---Advanced-Neural-Architecture
```

Do not invent private setup steps, local paths, hidden keys, or missing tools.
If a user is new to Git, prefer the ZIP install path. If a user is using VS
Code, install the included VSIX. In local dev mode no MCP key is required for
`127.0.0.1`; for production, make sure `anaMax.mcpApiKey` matches
`MCP_API_KEY`. Always verify with `python main.py --test` and
`python main.py --list-tools` before saying the setup is complete.

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

## Responsible QA And Reporting

ANA MAX is meant to help users and AI agents find real problems responsibly.
The goal is not to exploit a weakness for private advantage. The goal is to
observe evidence, verify the behavior, write a clear report, and help
developers fix it.

Clean workflow:

```text
observe evidence -> reproduce safely -> document impact -> report privately -> verify the fix
```

Private lab experiments may be stronger than the public release. They should
stay private until they are safe, documented, tested, and useful for legitimate
QA. The public release should show the discipline, not expose risky recipes.

Do not run live pentests against third-party applications unless you have a
clear authorization path, such as a written agreement or an official bug bounty
scope. Strong findings belong in private reports to the maintainers, not in
public posts that teach abuse.

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
- local dev mode needs no MCP key on `127.0.0.1`;
- production and non-local MCP access still uses Bearer-token auth;
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
- It reflects the current public audit baseline: 80 loaded tools, 7 AI Core
  adapters, and 4 premium-gated tool families.
- It acts like a local agent toolkit: different tools for setup, debugging, QA,
  desktop observation, browser checks, voice status, and authorized runtime
  diagnostics.
- It combines desktop vision, Windows UI automation, code tools, git, memory,
  and verification in one workflow.
- It adds public-safe precision tools from the latest audit:
  `file_patch`, `project_navigator`, `error_radar`, `uia_click`, `uia_type`,
  `vision_region_capture`, and `vision_find_element`.
- It supports authorized runtime instrumentation with Frida when static
  inspection is not enough.
- It treats `desktop_capture` as free Vision AI and keeps deep desktop control
  premium-gated.
- It keeps public docs and shell-facing examples ASCII-only so Windows consoles
  and weaker agents can parse them reliably.

ANA MAX is open source, but responsibility stays with the operator. Use it for
your own systems, private labs, education, QA, and authorized testing. Do not
use it to attack systems or accounts you do not own or have permission to test.

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

In this workflow, Codex has been especially useful as a project-map analyst:
understanding intent, connecting documentation with implementation, finding
stale public links, and helping other AI agents understand how to connect ANA
MAX safely.

Official link:

- OpenAI Codex: https://openai.com/codex/

Qoder is also credited as a useful agentic coding workflow tool and source of
lab assistance/inspiration.

Official links:

- Qoder: https://qoder.com/

The goal of this acknowledgement is simple: show that AI tools can be useful
when they work as careful engineering collaborators, not blind code generators.
Strict safety behavior is part of that value: ANA MAX is for clean users,
authorized QA, and responsible red-team work, not for manipulating agents into
unsafe tasks.

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
.\START_LOCAL_DEV.bat
```

Or start manually:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:ANA_BROWSER_PATH = "C:\Program Files\Google\Chrome\Application\chrome.exe"
python main.py

# Launch the voice engine
scripts\ana_voice.bat
```

ANA MAX starts on `http://127.0.0.1:8765` by default.

LOCAL DEV MODE (no API key) is enabled by default. Requests from `127.0.0.1`
do not need an API key, Authorization header, or environment variable.

For production or non-local use, set `local_dev: false`, configure
`MCP_API_KEY`, and send:

```text
Authorization: Bearer change-me
```

Example MCP request:

```powershell
curl -X POST http://127.0.0.1:8765/mcp `
  -H "Content-Type: application/json" `
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

## ANA MAX Bridge

`ana-max-bridge/` is an optional local HTTP connector for Copilot-style clients
that can call HTTP tools. It auto-detects ANA MAX tools from `/tools`, maps
them into client-facing tool definitions, forwards execution to `/execute`, and
keeps ANA MAX registry validation and premium gates in the execution path.

Start ANA MAX first, then run:

```powershell
cd ana-max-bridge
python bridge_server.py
```

With `local_dev: true`, no API key is required on `127.0.0.1`. For production
or non-local use, set `local_dev: false` and configure `ANA_MCP_KEY` or
`MCP_API_KEY`.

Bridge UI:

```text
http://127.0.0.1:8790/
```

Bridge docs:

```text
ana-max-bridge/docs/CONNECT_TO_COPILOT.md
```

## Verification

Before handing off changes, run:

```powershell
python -m compileall -q main.py core tools vscode_extension
python main.py --test
python main.py --list-tools
python -m unittest discover -s tests -v
```

For bridge changes, also run:

```powershell
python -m compileall -q ana-max-bridge
python -m unittest discover -s ana-max-bridge\tests -v
```

Expected baseline:

- `python main.py --test`: `3 PASS / 0 FAIL`
- `python main.py --list-tools`: 80 loaded tools
- `python -m unittest discover -s tests -v`: all tests passing

## Tool Model

Core tool behavior is owned by `tools/base.py`.

### Tool Status Overview

| Category | Status | Example Tools |
|----------|--------|---------------|
| **Core Utilities** | Stable | `file_operations`, `code_tools`, `git_operations` |
| **Agent Utilities** | Stable | `file_patch`, `project_navigator`, `error_radar` |
| **Desktop Eyes** | Stable | `desktop_capture`, `windows_uia_bridge`, `ocr_tool` |
| **Desktop Precision** | Experimental | `uia_click`, `uia_type`, `vision_region_capture`, `vision_find_element` |
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
80 loaded tools
Production auth: Authorization: Bearer change-me
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


