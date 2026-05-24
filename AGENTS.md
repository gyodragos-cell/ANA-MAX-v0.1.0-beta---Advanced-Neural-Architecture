# ANA MAX Agent Rules

This repository is the clean public release of ANA MAX. The full development
workspace may contain private memory, databases, logs, keys, and experiments;
do not copy private runtime data into this repository.

## Required First Step

Before making code or documentation changes, read:

- `docs/PROJECT_MAP_AI_GUIDE.md`

Use it as the project map for architecture, file ownership, release boundaries,
and verification commands.

## Release Hygiene

- Keep this repository clean, public-safe, and limited to release-ready files.
- Do not add `.env`, `.license`, API keys, database files, memory stores, logs,
  screenshots with private content, or local machine paths.
- Treat `desktop_capture` as a free Vision AI feature in v0.2.0.
- Treat only these tools as premium-gated unless the map changes:
  `live_desktop_viewer`, `desktop_control`, `desktop_control_tool`,
  `windows_insight`, `windows_insight_tool`, `windows_deep_sight`.
- Keep documentation counts aligned with the release map:
  `71 loaded tools, 4 premium-gated tool families, 7 AI Core adapters`.
- Use the current public wording when a page needs a version label:
  `18.0-MAX-lab.audit.2026-05-24`.

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
