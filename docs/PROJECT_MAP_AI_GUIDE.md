# ANA MAX - AI Agent Project Map

This is the source-of-truth map for the clean public release. Every AI agent
must read this file before making code or documentation changes.

## Release Boundary

This repository is public-safe. Do not copy private workspace data here.

Canonical public repository URL:
`https://github.com/gyodragos-cell/ANA-MAX-v0.1.0-beta---Advanced-Neural-Architecture`

Do not shorten it to `https://github.com/gyodragos-cell/ANA-MAX`; that path is
not the public release repository and can leave documentation or extension
links pointing at an empty location.

Allowed:
- Release-ready source code: `main.py`, `core/`, `tools/`, `plugins/`,
  `vscode_extension/`, `tests/`, `docs/`.
- Public documentation that matches the code currently present in this repo.
- Template configuration such as `.env.example`.
- Small public-safe assets for the website.

Not allowed:
- `.env`, `.license`, API keys, local databases, memory stores, logs,
  screenshots with private content, local shortcuts, private MCP configs.
- Large local video files. Host demos on YouTube, GitHub Releases, or another
  external video host and link them from README/site pages.
- Private workspace paths, private IDE setup, or local machine-specific
  instructions.
- Documentation for tools that are not present and executable in this release.

## Current Architecture

`main.py` is the public entry point. It loads config, registers tools, runs
quick checks, lists tools, and starts the Flask MCP server.

`tools/base.py` owns the standard tool interface and global registry:
- `Tool`
- `ToolDefinition`
- `ToolParameter`
- `ToolResult`
- `ToolRegistry`

All public MCP entry points must route tool calls through
`ToolRegistry.execute()`. Do not call a tool instance directly from MCP bridge
code, because that can skip parameter validation, logging, and premium gates.

`core/license_manager.py` owns Free/Pro licensing. Runtime access is enforced
inside `ToolRegistry.execute()`, so premium tools are blocked even if called
through HTTP/MCP.

`config/settings.yaml` controls local runtime behavior. MCP auth is enabled for
the public release. Set `ANA_MCP_KEY` or `MCP_API_KEY` before using `/execute`,
`/tools`, `/mcp`, `/events`, or `/mcp/stream`.

The VS Code extension must pass the same token when it starts the server or
calls tools. Its public settings are `anaMax.mcpApiKey`, `anaMax.mcpHost`, and
`anaMax.mcpPort`.

VS Code 1.121+ sets `VSCODE_AGENT` for terminal commands launched by an agent.
When ANA MAX sees this environment variable, `main.py` keeps startup output
compact for agent readability while preserving normal output for human-run
terminals, and `ToolRegistry.execute()` suppresses rich terminal panels during
agent-run tool calls. The `/health` endpoint reports `vscode_agent` and
`output_profile` so IDE integrations can verify the runtime mode.

## Tool Ownership

New user-facing capabilities belong in `tools/`, not in `core/`.

Every registry tool must:
- Inherit from `tools.base.Tool`.
- Implement `get_definition()` and `execute()`.
- Be registered from `main.py`.
- Be importable from the clean repo without private files.
- Be listed in `tools/__init__.py` when it is a direct tool class.

Adapters in `tools/tool_adapters.py` may wrap helper modules, but they must not
register phantom tools. If a backing module is missing, the adapter must be
skipped or the module must be added.

Tool quality beats tool count:
- Prefer a small set of reliable, composable tools over many noisy tools.
- Every tool must have a clear job: observe, diagnose, act, verify, or learn.
- Before adding a new tool, check whether an existing tool can be improved.
- Agents must observe the workspace before acting. Use structural UI, git
  status, terminal/test output, logs, OCR, or Frida according to the task.
- Use Frida only for dynamic runtime instrumentation, mobile/process hooks, or
  cases where static and structural inspection cannot answer the question.
- Do not use powerful tools by habit. Choose the smallest useful tool and verify
  the result.
- `tool_healthcheck` safe scope must stay offline and avoid semantic search
  model or network loading. Use `scope=all` only when heavier optional checks
  are intended.

## Local QA Lab Vision

ANA MAX is designed for local QA labs, private workstations, offline LLM
setups, and AI coding agents that need real Windows context without exposing
private work. The core value is giving a local model practical senses:

- eyes: `desktop_capture`, `foreground_ui_snapshot`, `windows_uia_bridge`,
  `ocr_tool`;
- hands: file, terminal, git, edit, and controlled desktop tools;
- ears: logs, terminal output, tests, health checks, and runtime errors;
- memory: AI Core context and local lessons;
- instrumentation: `frida_instrument` only for authorized runtime work when
  normal inspection is not enough.

The public message should stay factual:

```text
observe -> decide -> act -> verify -> learn
```

See `docs/LOCAL_QA_LAB_VISION.md`.

Browser workflow note: Chrome is the preferred visible external browser target
on Windows. `browser_control` operation `open_external` launches a normal
Chrome window that can stay open after a one-shot tool call exits.
Playwright-backed operation `open` is for automation sessions, may use bundled
Chromium first, and remains persistent while the ANA MAX server process is
running.

For agent IDE positioning, demos, and outreach language, see
`docs/AGENT_IDE_SUPER_TOOLS_PLAN.md`. The public story should focus on three
flagship workflows before tool count:

- desktop reasoning;
- runtime diagnostics;
- adaptive agent IDE flow.

## Premium Gates

`desktop_capture` is free Vision AI.

Only these tools are premium-gated unless this file and tests are updated:
- `live_desktop_viewer`
- `desktop_control`
- `desktop_control_tool`
- `windows_insight`
- `windows_insight_tool`
- `windows_deep_sight`

Premium checks must happen at runtime through `ToolRegistry.execute()`, not only
in isolated `LicenseManager` tests.

## Public Tool Groups

Core utilities:
- `ana_identity`, `file_operations`, `code_tools`, `web_search`,
  `system_control`, `tool_healthcheck`, `workspace_situational_awareness`,
  `git_operations`, `terminal`, `todowrite`, `edit`, `task`,
  `autonomous_engine`.

Security, network, and analysis:
- `security_audit`, `network_diag`, `network_pentest`, `mitm_analyzer`,
  `hardware_scanner`, `advanced_scanner`, `apk_analyzer`, `frida_instrument`,
  `adb_operations`.

Desktop, vision, and voice:
- `desktop_capture`, `windows_uia_bridge`, `foreground_ui_snapshot`,
  `ocr_tool`, `window_manager`, `clipboard_manager`, `edge_tts_voice`.
- Premium: `live_desktop_viewer`, `desktop_control`, `windows_insight`,
  `windows_deep_sight`.

AI Core:
- `context_engine`, `proactive_interrupt`, `self_evolving_tool`,
  `memory_cortex`, `ana_orchestrator`, `context_bridge`,
  `window_manager`, `clipboard_manager`, `ocr_tool`.

Advanced memory and orchestration:
- `vector_memory`, `swarm_orchestrator`, `vision_fallback`,
  `remote_control`, `event_stream`.

## Removed Noise

Old private integrations and private setup guides are not part of this clean
public release. Do not add them back unless their source code, tests, public
docs, and release hygiene are all present in this repo.

## Release Sync Rule

When code, tools, config, or runtime behavior changes, update every public
surface in the same change:
- `docs/PROJECT_MAP_AI_GUIDE.md`
- `README.md`
- `SETUP_AND_RUN.md`
- `CHANGELOG.md`
- `.env.example` when environment variables or auth behavior change
- tests that protect the behavior or release hygiene

Do not leave users behind with stale commands, stale tool counts, stale premium
gates, or missing environment variables.

## Agent Discipline

Agents must work from facts:
- Inspect owning files before editing.
- Keep changes scoped.
- Do not invent tool counts or publish stale architecture claims.
- Do not register a tool unless it imports and executes.
- Do not write docs for private experiments.
- Prefer native Python/Windows APIs over shell subprocesses for common system
  operations.
- Keep CLI output UTF-8 tolerant on Windows.
- Keep public docs and shell-facing text ASCII-only. Commands, expected
  PowerShell output, log examples, and MCP examples must not contain Romanian
  diacritics, smart quotes, emoji, or mojibake. This is a release rule, not a
  style preference.

Before handoff, run the relevant verification commands and report failures:

```powershell
python -m compileall -q main.py core tools vscode_extension
python main.py --test
python main.py --list-tools
python -m unittest discover -s tests -v
```

## Current Verification Baseline

The expected public baseline is:
- `python main.py --test`: `3 PASS / 0 FAIL`
- `python main.py --list-tools`: 64 loaded tools
- `python -m unittest discover -s tests -v`: all tests passing

If the numbers change, update this file, `AGENTS.md`, README/docs, and tests in
the same change.

Operational note: after changing tool registration or startup behavior, restart
the running MCP server before trusting `/tools` or MCP `tools/list`; an existing
process keeps its old in-memory registry.
