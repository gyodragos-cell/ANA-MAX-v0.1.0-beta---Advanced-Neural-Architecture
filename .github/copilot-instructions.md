# ANA MAX Coding Instructions

Before changing this repository, read `docs/PROJECT_MAP_AI_GUIDE.md`.

This is the clean public GitHub release. Do not add private runtime data such as
`.env`, `.license`, logs, memory databases, local user paths, API keys, or
internal-only workspace artifacts.

Before handoff, run the release checks when relevant:

```powershell
python -m compileall -q main.py core tools vscode_extension
python main.py --test
python main.py --list-tools
python -m unittest discover -s tests -v
```

Current release facts:

- `desktop_capture` is FREE in v0.2.0.
- Premium tools are `live_desktop_viewer`, `desktop_control`,
  `desktop_control_tool`, `windows_insight`, `windows_insight_tool`, and
  `windows_deep_sight`.
- Documentation should stay aligned with `43 Free + 4 Premium + 9 AI Core`.
