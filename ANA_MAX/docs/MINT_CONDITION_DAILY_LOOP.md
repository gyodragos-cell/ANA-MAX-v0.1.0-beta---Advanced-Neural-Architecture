# ANA MAX Mother Lab Mint Condition Loop

This checklist is for the private mother lab. It is not the public release
checklist. The lab can be stronger, messier, and more experimental, but every
session should leave it easier to continue.

## Golden Rule

```text
observe first -> polish real noise -> verify -> record sync decision
```

## Start Of Session

- [ ] Read `AGENTS.md`.
- [ ] Read `docs/PROJECT_MAP_AI_GUIDE.md`.
- [ ] If touching UI, OCR, browser, screenshots, or desktop tools, read
      `docs/PLAN_VIITOR_OCHI_ANA_MAX.md`.
- [ ] Run or inspect `git status --short`.
- [ ] Separate old dirty work from today's intended work.

## Lab Cleanup Rules

- [ ] Keep root files intentional.
- [ ] Move experiments to `dev_artifacts/` or `archives/` when they are worth
      keeping.
- [ ] Keep logs, memory, screenshots, databases, `.env`, and local evidence out
      of the public release.
- [ ] Do not delete memory, logs, screenshots, or data unless Billy explicitly
      asks.
- [ ] Prefer improving noisy tools over adding new tools.
- [ ] Keep tool output compact for agent workflows.

## Bug Hunt Loop

```text
observe -> reproduce -> isolate owner file -> fix smallest behavior -> verify -> document lesson
```

Good targets:

- `workspace_situational_awareness`
- browser session persistence and visible Chrome confirmation
- voice status tied to verified state
- `tool_healthcheck` safe/offline behavior
- UIA foreground snapshots and popup detection
- release sync drift between lab and GitHub

## Sync Decision

Every meaningful lab change needs one label before handoff:

```text
ship-safe -> sync safe part into ANA_MAX_GitHub_Release
lab-only -> keep private and document why
needs-more-testing -> leave in lab, do not sync yet
```

Never copy private payloads, logs, screenshots, memory stores, keys, local
shortcuts, or third-party live-test details into GitHub.

## Verification

Lab checks:

```powershell
python -m compileall -q main.py core tools
python main.py --test
python main.py --list-tools
```

Current expected lab baseline:

```text
74 loaded tools
2 PASS / 0 FAIL
```

Public sync checks, when a ship-safe change is copied:

```powershell
python -m compileall -q main.py core tools vscode_extension
python main.py --test
python main.py --list-tools
python -m unittest discover -s tests -v
```

## End Of Session

- [ ] Record what changed.
- [ ] Record what was verified.
- [ ] Record what remains dirty and why.
- [ ] Save a session checkpoint when the work is important.
- [ ] Commit only intentional files, not broad old lab churn.
