# ANA MAX Mother Lab - AI Agent Project Map

This is the working map for the private mother lab:

```text
C:\Users\billy\Desktop\ana_dev\ANA_MAX
```

The mother lab has priority over the public GitHub release. It is where ANA MAX
is tested, evolved, observed, and repaired. The GitHub release is the clean
export for users and engineers who need a public-safe package.

## Current Baseline

Last verified from the mother lab on 2026-05-22:

```powershell
python main.py --list-tools
python main.py --test
```

Observed result:

```text
74 loaded tools
2 PASS / 0 FAIL
```

The public release may have a different count. Do not copy private lab counts
or private runtime data into the public repository unless the release is being
intentionally synchronized.

## Workspace Roles

- `ana_dev\ANA_MAX`: private mother lab, full runtime, memory, logs,
  experiments, launch state, private config, screenshots, and local databases.
- `ANA_MAX_GitHub_Release`: clean public release, no `.env`, no `.license`, no
  logs, no memory stores, no private screenshots, no local machine secrets.
- `ana_dev`: control room for launchers, demos, videos, notes, and external
  agent IDE experiments.

## Required First Step

Before changing code in this lab, read:

- `AGENTS.md`
- `LAB_MANAGER.md`
- `docs/ANA_WORKGRAPH_ARCHITECTURE.md`
- `docs/PLAN_VIITOR_OCHI_ANA_MAX.md` when touching UIA, OCR, screenshots, or
  desktop tools

Use this project map as the current operational source of truth.

## North Star

ANA MAX is a Windows-first local agent runtime. It should help an AI agent
observe the real computer state, choose the smallest useful tool, act safely,
verify the result, and learn from the session.

Core loop:

```text
observe -> decide -> act -> verify -> learn
```

Quality beats tool count. Improve noisy tools before adding new ones.

## Current Architecture

`main.py` is the runtime entry point. It:

- loads `.env` and `config/settings.yaml`;
- registers all tools into `tools.base.registry`;
- starts the Flask MCP server;
- exposes `/health`, `/tools`, `/execute`, `/mcp`, `/events`, `/mcp/stream`, and `/chat`;
- supports quick verification with `--test` and `--list-tools`.

`tools/base.py` owns the standard tool contract:

- `Tool`
- `ToolDefinition`
- `ToolParameter`
- `ToolResult`
- `ToolRegistry`

All public and internal tool calls should route through `ToolRegistry.execute()`
so validation, permission manifest checks, observability logs, and premium
gates stay in one path.

`core/license_manager.py` owns Free/Pro licensing.

Current premium-gated tools:

- `live_desktop_viewer`
- `desktop_control`
- `desktop_control_tool`
- `windows_insight`
- `windows_insight_tool`
- `windows_deep_sight`

`desktop_capture` is free Vision AI.

## Resource System

The lightweight resource system lives in `core/resource_loader.py` and
`resources/`. It provides optional localized texts, themes, and icon loading
for UI surfaces. Missing files must fall back to English text, the light theme,
or an empty icon string without crashing.

## Agent-Aware Runtime

VS Code 1.121+ sets `VSCODE_AGENT` for terminal commands launched by an agent.
ANA MAX detects this environment variable and should keep terminal output
compact for agent workflows.

Current intended behavior:

- normal human terminal: full banner and tool loading details;
- `VSCODE_AGENT=1`: compact startup lines and no rich per-tool terminal panels;
- `/health`: reports `vscode_agent` and `output_profile`.

This keeps the lab aligned with modern agent IDE behavior and reduces token
noise during long sessions.

## Bug Hunt Notes

Confirmed fixes from 2026-05-22:

- `workspace_situational_awareness` accepts real booleans as well as string
  booleans from MCP callers.
- `workspace_situational_awareness` returns a compact Git preview instead of a
  full dirty worktree dump.
- `tool_healthcheck` safe scope stays offline and avoids semantic search model
  loading.
- `tool_healthcheck` registry fallback includes `session_checkpoint`,
  `workspace_situational_awareness`, and `agent_coach`.
- `launcher.py` reports the live MCP tool count instead of the old `46+`
  message.

Operational note: when tool registration changes, restart the running MCP
server. An already-running server keeps its old in-memory tool registry.

## Tool Groups

Core utilities:

- `ana_identity`
- `file_operations`
- `code_tools`
- `web_search`
- `system_control`
- `tool_healthcheck`
- `git_operations`
- `terminal`
- `file_patch`
- `project_navigator`
- `todowrite`
- `edit`
- `system_optimization`

Workspace and learning:

- `conversation_learning`
- `session_log_miner`
- `session_checkpoint`
- `ana_memory`
- `privacy_shield`
- `workspace_situational_awareness`

Coding and diagnostics:

- `debugger`
- `codebase_understanding`
- `code_search`
- `smart_search`
- `qa_testing`
- `browser_control`
- `web_scraper`
- `error_radar`

Security, network, and mobile:

- `security_audit`
- `network_diag`
- `network_pentest`
- `mitm_analyzer`
- `hardware_scanner`
- `advanced_scanner`
- `adb_operations`
- `frida_instrument`
- `apk_analyzer`

Desktop, UI, vision, and voice:

- `desktop_capture`
- `windows_uia_bridge`
- `uia_click`
- `uia_type`
- `foreground_ui_snapshot`
- `ocr_tool`
- `window_manager`
- `vision_region_capture`
- `vision_find_element`
- `clipboard_manager`
- `edge_tts_voice`
- premium: `live_desktop_viewer`, `desktop_control`, `windows_insight`,
  `windows_deep_sight`

Intelligent supervision:

- `live_tool_healer`
- `agent_coach`

Memory and orchestration:

- `vector_memory`
- `swarm_orchestrator`
- `vision_fallback`
- `remote_control`
- `event_stream`

AI Core adapters:

- `context_engine`
- `proactive_interrupt`
- `self_evolving_tool`
- `memory_cortex`
- `ana_orchestrator`
- `context_bridge`
- `clipboard_manager`

## File Ownership

`core/`:

- shared runtime, config, licensing, memory, event systems, model backends, and
  orchestration helpers.
- Do not put new user-facing tools here unless they are shared infrastructure.

`tools/`:

- user-facing capabilities.
- New tools must inherit from `tools.base.Tool`, implement `get_definition()`
  and `execute()`, and be registered from `main.py`.

`docs/`:

- current architecture, lab plans, offline profile, support notes, and release
  preparation notes.
- Keep docs exact and current. Do not leave old patch snippets as `.py` files.

`logs/`, `memory/`, `data/`, `screenshots/`, `browser_snapshots/`,
`voice_temp/`:

- private runtime evidence and local lab state.
- These are allowed in the mother lab and forbidden in the public release.

`dev_artifacts/`, `archives/`, `backups/`:

- experiments, old versions, and temporary analysis.
- Ignore these for normal source-of-truth code reads unless the task asks for
  history recovery.

## Clean Lab Rules

- Keep root files intentional.
- Move loose experiments into `dev_artifacts/` or `archives/`.
- Do not delete memory, logs, screenshots, databases, or private config unless
  the operator explicitly asks.
- Do not copy `.env`, `.license`, API keys, memory databases, logs, or private
  screenshots into `ANA_MAX_GitHub_Release`.
- Do not add docs for tools that are not present and executable.
- Prefer compact JSON and short summaries over huge dumps.
- Use native Python and Windows APIs where practical.
- Frida is for authorized runtime instrumentation, mobile/process hooks, or
  cases where normal inspection cannot answer the question.

## Public Release Sync Rule

Every meaningful lab change needs an explicit sync decision:

```text
ship-safe -> sync the safe part into the public release
lab-only -> document as private/internal and do not copy
```

When behavior should ship publicly, sync only the safe parts into:

```text
C:\Users\billy\Desktop\ANA_MAX_GitHub_Release
```

For ship-safe changes, update these public surfaces in the same work cycle:

- `docs/PROJECT_MAP_AI_GUIDE.md`
- `README.md`
- `SETUP_AND_RUN.md`
- `CHANGELOG.md`
- `.env.example` when environment variables, auth behavior, provider keys,
  ports, or launch settings change
- tests that protect the behavior or release hygiene
- VS Code extension docs/config when extension behavior changes
- website/docs pages when public positioning or counts change

Do not leave users behind with stale commands, stale tool counts, stale premium
gates, missing environment variables, or docs that no longer match the real
runtime.

Before public sync, filter out:

- `.env`
- `.license`
- API keys and tokens
- databases
- logs
- memory stores
- local screenshots
- private videos
- local machine shortcuts
- private-only integration notes

The public release should stay boring, repeatable, and exact.

## Qoder And AI Tooling Credit

Official links:

- Qoder: https://qoder.com/
- Qoder docs: https://docs.qoder.com/

Safe wording unless there is a formal sponsorship agreement:

```text
ANA MAX is developed in a private local lab with assistance from modern
agentic coding workflows, including Qoder and OpenAI Codex.
```

Use "sponsored by" only after written sponsor approval.

## Verification Before Handoff

For mother lab changes:

```powershell
python -m compileall -q main.py core tools
python main.py --test
python main.py --list-tools
```

For public release sync:

```powershell
python -m compileall -q main.py core tools vscode_extension
python main.py --test
python main.py --list-tools
python -m unittest discover -s tests -v
```

If a check cannot run because a local dependency, service, or device is
missing, say that plainly.

## Current Priorities

1. Keep `workspace_situational_awareness` compact, reliable, and useful.
2. Use `session_checkpoint` before ending important work so the next agent can
   continue from a saved handoff.
3. Restart MCP after registry changes so `/tools` and `tools/list` expose the
   current tool set.
4. Stabilize `error_radar` from terminal output, visible UI errors, logs, and tests.
5. Keep `agent_coach` and `live_tool_healer` focused on concise guidance, not
   noisy commentary.
6. Keep `VSCODE_AGENT` output compact for modern agent IDEs.
7. Keep the mother lab creative and fast, while keeping the public release
   clean and safe.

v21 foundations add resource-only hooks for:
- theme switching through `ANA_THEME` with a light-theme fallback;
- dev-mode messaging through `ANA_DEV_MODE` without exposing private data;
- future Resource Inspector, Dashboard v2, and Tool Health Visualizer dashboard
  placeholders.
