# ANA MAX Mother Lab Manager

This file is for the private mother workspace:

```text
C:\Users\billy\Desktop\ana_dev\ANA_MAX
```

The public GitHub release is only the clean export. The mother lab has higher
priority for creation, testing, memory, local experiments, launchers, logs, and
tool evolution.

## Operating Rule

```text
observe -> decide -> act -> verify -> learn
```

## Workspace Roles

- `ana_dev\ANA_MAX`: private mother lab, full runtime, memory, logs, local
  tools, launch state, experiments, and private config.
- `ANA_MAX_GitHub_Release`: public-safe release, no private data, no logs, no
  local secrets, no internal-only notes.
- `ana_dev`: desktop-level control room for launchers, demos, notes, videos,
  and external agent IDE artifacts.

## Clean Lab Rules

- Keep root files intentional. Root is for launchers, README, agent rules,
  current entry points, and critical operator notes.
- Put experiments in `dev_artifacts/` or `archives/`, not loose in root.
- Put private runtime evidence in `logs/`, `data/`, `memory/`,
  `browser_snapshots/`, `screenshots/`, or `voice_temp/`.
- Never copy `.env`, API keys, license files, databases, logs, memory stores,
  or screenshots into the public release.
- Do not delete logs, memory, screenshots, or data unless the operator asks
  explicitly.
- Keep tool output compact for agent workflows. Use DEBUG for repeated events
  and INFO only for major lifecycle events.

## Manager Priorities

1. Keep the mother lab useful and fast.
2. Keep project maps current before coding.
3. Keep public release clean and boring.
4. Prefer improving existing tools over adding noisy new tools.
5. Verify with compile, quick tests, and tool listing before handoff.

## Lab-To-Release Sync Rule

Every meaningful change in `ana_dev\ANA_MAX` needs a sync decision before
handoff:

```text
ship-safe -> update ANA_MAX_GitHub_Release in the same work cycle
lab-only -> document as private/internal and do not copy
```

When a ship-safe change touches code, tools, config, runtime behavior, launch
behavior, auth, environment variables, ports, premium gates, or public
messaging, update the matching public surfaces too:

- `docs/PROJECT_MAP_AI_GUIDE.md`
- `README.md`
- `SETUP_AND_RUN.md`
- `CHANGELOG.md`
- `.env.example` when environment variables or auth behavior change
- tests that protect the behavior or release hygiene
- VS Code extension docs/config when extension behavior changes

Never leave the public release with stale commands, stale tool counts, stale
premium gates, missing env vars, or docs that no longer match the lab.

## Current Tech Watch

- VS Code 1.121+: `VSCODE_AGENT` marks agent-launched terminal commands.
- ANA MAX should use that signal for compact output and agent-readable status.
- Qoder: https://qoder.com/
- Qoder docs: https://docs.qoder.com/

## Qoder Credit Wording

Use this wording unless there is a formal sponsorship agreement:

```text
ANA MAX is developed in a private local lab with assistance from modern
agentic coding workflows, including Qoder.
```

Avoid claiming formal sponsorship unless a written sponsorship exists.

## Handoff Checklist

Before ending important work or before chat credit runs out, save a checkpoint:

```text
session_checkpoint
```

It writes a compact handoff into `docs/`, `conversation_learning`, and
`ana_memory` so the next agent can continue without reconstructing the whole
chat.

```powershell
python -m compileall -q main.py core tools
python main.py --test
python main.py --list-tools
```

For public release sync, also run:

```powershell
python -m unittest discover -s tests -v
```
