# ANA MAX Internal Agent Rules

This is the full development workspace for ANA MAX, not the clean public
GitHub release.

## Workspace Roles

- `C:\Users\billy\Desktop\ana_dev\ANA_MAX` is the mother workspace: full tools,
  local memory, logs, experiments, launcher state, databases, and private config.
- `C:\Users\billy\Desktop\ANA_MAX_GitHub_Release` is the clean public release:
  no private memory, no logs, no `.env`, no internal-only data.

Do not copy private runtime data from this workspace into the public release.

## Required First Step

Before changing code or starting tasks, read these documents:

- `../docu/ANA_MAX_Mother_Lab_Stability_Report_v2.md` (Active development roadmap, text-injection status, and what works/doesn't work)
- `docs/PROJECT_MAP_AI_GUIDE.md`
- `docs/ANA_WORKGRAPH_ARCHITECTURE.md`
- `docs/PLAN_VIITOR_OCHI_ANA_MAX.md` when touching UIA/Vision/desktop eyes

The project map explains current architecture and release hygiene. WorkGraph is
the forward-looking direction: operational awareness, structural eyes, error
radar, workflow learning, and self QA.

## Launch Path

The desktop launcher is:

- `C:\Users\billy\Desktop\ANA_MAX.bat`

It enters this workspace, starts `launcher.py` with the local venv, then opens:

- `opencode://`
- `http://127.0.0.1:8765/mcp/stream`
- `http://127.0.0.1:8765/events`

`launcher.py` starts `main.py` on port `8765`, checks required files, checks the
port, and performs MCP health checks.

## Development Priorities

- Optimize for usefulness, not perfection.
- The main goal is helping the agent complete real tasks faster by seeing the
  computer state, detecting errors, acting carefully, and verifying results.
- Structural eyes come first: UIA foreground snapshots, compact workspace state,
  visible errors, and next-step recommendations.
- WorkGraph MVP should produce compact JSON, not huge UI dumps.

## Full Workspace Notes

- This workspace may include premium/internal tools such as `windows_deep_sight`,
  live desktop viewing, desktop control, local logs, event databases, and memory.
- These are allowed here, but must be filtered before public release.
- `desktop_capture` is a free Vision AI feature in v0.2.0.
- Public release docs use `64 loaded tools, 4 premium-gated tools, 9 AI Core
  adapters` as the clean release count.
- Local full workspace counts may differ because internal tools are enabled.

## Safety Rules

- Do not commit or copy `.env`, `.license`, `apikey.txt`, memory databases,
  `data/events.db`, logs, screenshots with private content, or local keys.
- Do not delete memory/log/data folders unless explicitly asked.
- Move note-only patch snippets into `docs/*.md`; do not leave patch text as
  `.py` files because `compileall` will try to compile them.
- Use native Python/Windows APIs where reasonable. Avoid spawning PowerShell for
  simple file/process/UI inspection if a native API exists.
- Any automation that clicks, types, changes files, kills processes, or pushes
  Git should support confirmation or `dry_run` unless explicitly requested.

## Lab-To-Release Sync Discipline

Any code, tool, config, runtime behavior, launch behavior, auth, environment
variable, premium gate, tool count, or public messaging change in the mother
workspace must get an explicit sync decision before handoff:

```text
ship-safe -> sync the safe part into ANA_MAX_GitHub_Release
lab-only -> document as private/internal and do not copy
```

For ship-safe changes, update the public release surfaces in the same work
cycle:

- `docs/PROJECT_MAP_AI_GUIDE.md`
- `README.md`
- `SETUP_AND_RUN.md`
- `CHANGELOG.md`
- `.env.example` when env vars, auth, ports, provider keys, or launch settings
  change
- tests that protect the behavior or release hygiene
- VS Code extension docs/config when extension behavior changes

Do not let GitHub release docs drift behind the mother lab. Do not copy private
runtime data while syncing.

## Checks Before Handoff

Run the relevant checks for the workspace you touched:

```powershell
python -m compileall -q main.py core tools
python main.py --test
python main.py --list-tools
```

For the clean GitHub release, also run:

```powershell
python -m unittest discover -s tests -v
```

If a check cannot run because a dependency or local service is missing, report
the reason clearly.

## Current Direction

Next high-value implementation target:

- `workspace_situational_awareness.py`

It should return a compact JSON state containing active app/window, UIA quality,
visible error signals, repo/git state, relevant open files if detectable, and a
recommended next step.

For daily polish and bug-hunt sessions, use:

```text
docs/MINT_CONDITION_DAILY_LOOP.md
```
