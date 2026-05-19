# ANA MAX - AI Agent Project Map

This is the source-of-truth map for the clean public release. Every AI agent
must read this file before making code or documentation changes.

## Release Boundary

This repository is public-safe. Do not copy private workspace data here.

Allowed:
- Release-ready source code: `main.py`, `core/`, `tools/`, `plugins/`,
  `vscode_extension/`, `tests/`, `docs/`.
- Public documentation that matches the code currently present in this repo.
- Template configuration such as `.env.example`.

Not allowed:
- `.env`, `.license`, API keys, local databases, memory stores, logs,
  screenshots with private content, local shortcuts, private MCP configs.
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

`core/license_manager.py` owns Free/Pro licensing. Runtime access is enforced
inside `ToolRegistry.execute()`, so premium tools are blocked even if called
through HTTP/MCP.

`config/settings.yaml` controls local runtime behavior. MCP auth is enabled for
the public release. Set `ANA_MCP_KEY` or `MCP_API_KEY` before using `/execute`,
`/tools`, `/mcp`, `/events`, or `/mcp/stream`.

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
  `system_control`, `tool_healthcheck`, `git_operations`, `terminal`,
  `todowrite`, `edit`, `task`, `autonomous_engine`.

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
- `python main.py --test`: `2 PASS / 0 FAIL`
- `python main.py --list-tools`: 63 loaded tools
- `python -m unittest discover -s tests -v`: all tests passing

If the numbers change, update this file, `AGENTS.md`, README/docs, and tests in
the same change.
