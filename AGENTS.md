# ANA MAX Agent Rules

This repository is the clean public release of ANA MAX. The full development
workspace may contain private memory, databases, logs, keys, and experiments;
do not copy private runtime data into this repository.

## Required First Step

Before making code or documentation changes, read:

- `docs/PROJECT_MAP_AI_GUIDE.md`

Use it as the project map for architecture, file ownership, release boundaries,
and verification commands.

## Full-Project IDE Agent Mode

When working in this repository, act as a full-project IDE agent:

- Maintain project-wide awareness before changing files.
- Search for files and symbols instead of guessing paths.
- Read the files that own the requested behavior before editing.
- Compare related files when the request touches shared behavior or docs.
- Use minimal patch-based edits and preserve existing style.
- Ask for confirmation before destructive changes.
- Show or summarize diffs after modifying files.
- Keep release hygiene and public-safe boundaries in mind at all times.
- Run the relevant verification commands before handoff and report failures
  plainly.

## Release Hygiene

- Keep this repository clean, public-safe, and limited to release-ready files.
- Do not add `.env`, `.license`, API keys, database files, memory stores, logs,
  screenshots with private content, or local machine paths.
- Treat `desktop_capture` as a free Vision AI feature in v0.2.0.
- Treat only these tools as premium-gated unless the map changes:
  `live_desktop_viewer`, `desktop_control`, `desktop_control_tool`,
  `windows_insight`, `windows_insight_tool`, `windows_deep_sight`.
- Keep documentation counts aligned with the release map:
  `80 loaded tools, 4 premium-gated tool families, 7 AI Core adapters`.
<!-- # PATCH_START v20_phase3 -->
- Treat v20 autonomy tools as manual, read-only diagnostics:
  `ana_health_check`, `baseline_update_suggester`, `docs_generator`,
  `ana_patch_suggester`, and `runtime_guard`.
  `autonomy_dashboard` is also manual and read-only.
<!-- # PATCH_END v20_phase3 -->
<!-- # PATCH_START v20_final -->
- Use the current public wording when a page needs a version label:
  `v22.0.0`.
<!-- # PATCH_END v20_final -->
<!-- # PATCH_START v22_release -->
- Treat v22 runtime modules as orchestration scaffolding, not loaded MCP tools:
  `input_layer`, `context_builder`, `ai_engine`, `tool_router`,
  `execution_layer`, `observability`, `scenario_simulator`, `runtime_config`,
  `release_sync`, and `ana_runtime`.
- Keep `release_sync` read-only unless a future release task explicitly
  enables a controlled sync. It must not copy, delete, deploy, or commit by
  default.
<!-- # PATCH_END v22_release -->

## Release Sync Rule

When code, tools, config, or runtime behavior changes, update every public
surface in the same change:

- `docs/PROJECT_MAP_AI_GUIDE.md`
- `README.md`
- `SETUP_AND_RUN.md`
- `CHANGELOG.md`
- `.env.example` when environment variables or auth behavior change
- tests that protect the behavior or release hygiene
- `index.html` when public positioning, release counts, or website sections
  change

Do not leave users behind with stale commands, stale tool counts, stale premium
gates, or missing environment variables.

## Verification Before Handoff

Run the relevant checks before saying the work is done:

```powershell
python -m compileall -q main.py core tools vscode_extension
python main.py --test
python main.py --list-tools
python -m unittest discover -s tests -v
```

For changes under `ana-max-bridge/`, also run:

```powershell
python -m compileall -q ana-max-bridge
python -m unittest discover -s ana-max-bridge\tests -v
```

If a check cannot be run, report that clearly with the reason.

## Coding Rules

- Prefer existing project patterns over new abstractions.
- Keep changes scoped to the requested release behavior.
- Do not rewrite unrelated files or revert user work.
- Use native Python/Windows APIs where possible instead of spawning shell
  subprocesses for common operations.
- Keep CLI output UTF-8 tolerant on Windows.
- Public docs and shell-facing text must be ASCII-only. Commands, expected
  PowerShell output, log examples, and MCP examples must not contain Romanian
  diacritics, smart quotes, emoji, or mojibake. Use simple text that weak
  agents and Windows consoles can parse.
- Tool quality beats tool count. Do not add tools just to increase the number.
  Prefer reliable, composable tools with compact output.
- Observe before acting. Pick tools according to the task: structural UI, git
  state, terminal output, logs, OCR, Frida, or network tooling only when each is
  actually relevant.
- Use Frida only for dynamic runtime instrumentation, mobile/process hooks, or
  cases where static and structural inspection cannot answer the question.

## Agent Discipline Rules

- Work from facts, not assumptions: inspect the files that own the behavior
  before changing them, and verify claims with commands.
- Do not add tool registrations, docs, setup guides, or changelog entries for
  modules that are not present and executable in this clean release.
- Never copy integration notes from private workspaces, private IDE setup,
  local shortcuts, or private tokens into this repository.
- Keep public docs boring and exact: current file names, current tool counts,
  current premium gates, and commands that run from this repo root.
- If a feature is experimental or private-only, leave it out of the public
  release until it has code, tests, docs, and release hygiene.
- Before handoff, run the required verification commands and report failures
  plainly. Passing import/compile is not enough if a listed tool fails when
  executed.

