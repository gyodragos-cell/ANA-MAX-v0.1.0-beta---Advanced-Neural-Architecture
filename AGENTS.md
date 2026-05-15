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
  `43 Free + 4 Premium + 9 AI Core`.

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
