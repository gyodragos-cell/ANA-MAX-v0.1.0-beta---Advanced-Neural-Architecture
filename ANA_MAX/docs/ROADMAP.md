# ANA MAX Mother Lab Roadmap

**Status:** Active private lab
**Last Updated:** 2026-05-25
**Current Lab Baseline:** 74 loaded tools, 2 PASS / 0 FAIL
**Public Release Rule:** Safe lab changes must be synced to GitHub release
surfaces before handoff.

## Project Vision

ANA MAX is a Windows-first local agent runtime for private workstations, QA
labs, offline model workflows, and agent IDEs that need real computer context.

The core loop is:

```text
observe -> decide -> act -> verify -> learn
```

The mother lab is the creative and testing space. The GitHub release is the
clean public export.

## Two-Workspace Discipline

This project has two active surfaces:

- `C:\Users\billy\Desktop\ana_dev\ANA_MAX`
  Private mother lab. It can contain logs, memory, local config, screenshots,
  experiments, launch state, and private runtime evidence.

- `C:\Users\billy\Desktop\ANA_MAX_GitHub_Release`
  Public release. It must stay clean, reproducible, and public-safe.

Agents must not treat these as unrelated projects. A real behavior change in
the mother lab needs an explicit decision:

```text
ship-safe -> sync to public release
lab-only -> document as private/internal and do not copy
```

## Release Sync Rule

When code, tools, config, runtime behavior, launch behavior, API behavior,
premium gates, environment variables, or public messaging changes in
`ana_dev\ANA_MAX`, update the matching public surfaces in the same work cycle
when the change is intended to ship.

Required public surfaces:

- `docs/PROJECT_MAP_AI_GUIDE.md`
- `README.md`
- `SETUP_AND_RUN.md`
- `CHANGELOG.md`
- `.env.example` when environment variables, auth, ports, provider keys, or
  launch settings change
- tests that protect the behavior or release hygiene
- VS Code extension docs/config when extension behavior changes
- website/docs pages when public positioning or counts change

Do not leave the public release behind with stale commands, stale tool counts,
stale premium gates, stale setup steps, or missing environment variables.

## Lab-Only Rule

Some changes are intentionally private. Examples:

- `.env`
- `.license`
- API keys or tokens
- memory databases
- event databases
- logs
- screenshots with private content
- local videos
- local shortcuts
- private model/provider experiments
- private IDE-specific notes

These may stay in the mother lab, but they must not be copied to the public
release. If a lab-only feature affects architecture, document it as private or
experimental instead of pretending it is public release behavior.

### v21 Planning

- [x] Resource system foundation added (localization + themes + loader).

## Documentation Contract

Every meaningful change should answer these questions before handoff:

1. Did code behavior change?
2. Did a command change?
3. Did an environment variable change?
4. Did auth, premium gates, ports, models, or launch behavior change?
5. Did tool count or tool availability change?
6. Does README/setup/changelog/project map still match reality?
7. Is this safe to sync to GitHub release, or lab-only?

If the answer touches public users, update docs and tests in the same pass.

## Current Priorities

### 2026-05-24 Tool Audit Pass

Repaired:

- Strengthened `Tool.safe_execute()` and `ToolRegistry.execute()` with stricter
  validation, compact errors, normalized `ToolResult` handling, and quiet
  default execution.
- Converted `ocr_tool` and `window_manager` into direct Tool-contract classes.
- Made `ocr_tool action=check` lightweight and quiet.
- Fixed `window_manager` false-success results for target-window actions.
- Tightened `error_radar` matching to avoid timestamp false positives.

Optimized:

- Reduced noisy registry output for agent IDE workflows.
- Added safe/offline healthcheck coverage for the new tools.
- Kept new observation tools compact and JSON-oriented.

Added:

- `file_patch`
- `project_navigator`
- `uia_click`
- `uia_type`
- `vision_region_capture`
- `vision_find_element`
- `error_radar`
- `CHANGELOG.md`
- `TOOL_STATUS.md`
- `docs/logs/ANA_MAX_AUDIT_2026-05-24.md`
- `docs/test_reports/2026-05-24/ANA_MAX_TEST_REPORT_2026-05-24.md`

Recommendations:

- Run MCP-level tests for all new tools.
- Add unit tests for `file_patch`, `project_navigator`, `error_radar`, and
  registry validation.
- Stabilize `desktop_capture`, `desktop_control`, and `windows_uia_bridge`
  before public sync.
- Keep this pass marked `needs-more-testing` until live desktop behavior is
  verified.

### Phase 1: Keep The Lab Clean And Current

- [x] Replace stale/mojibake project map with a clean current map.
- [x] Add mother lab manager rules.
- [x] Add Qoder/OpenAI Codex credit wording.
- [x] Add public AI collaboration guidance that credits Codex as main
  analyst/coder and Qoder as a useful agentic workflow tool.
- [x] Add VS Code 1.121 `VSCODE_AGENT` compact output behavior.
- [x] Add `session_checkpoint` so important sessions can be saved before chat
  credit or agent context ends.
- [x] Fix first bug-hunt pass: compact situational Git output, offline safe
  healthcheck, current launcher tool count.
- [ ] Keep roadmap, project map, README, setup, changelog, `.env.example`, and
  tests aligned whenever behavior changes.
- [ ] Add a small sync checklist or script that compares lab-vs-release public
  surfaces before handoff.

### Phase 2: Observation First

- [x] Keep `workspace_situational_awareness` as the first observation tool.
- [x] Keep `workspace_situational_awareness` compact on dirty worktrees.
- [x] Add first-pass `error_radar` for logs, git state, and visible error windows.
- [ ] Expand visible error detection from terminal output, foreground UI,
  logs, and test failures.
- [ ] Keep output compact JSON for agent IDEs.

### Phase 3: Agent Reliability

- [ ] Stabilize `agent_coach` as concise guidance, not noisy commentary.
- [ ] Stabilize `live_tool_healer` for real failures and clear summaries.
- [x] Add missing agent utility tools: `file_patch`, `project_navigator`,
  `uia_click`, `uia_type`, `vision_region_capture`, and `vision_find_element`.
- [ ] Add repeatable self-QA checks for compile, quick tests, list-tools, and
  public release hygiene.

### Phase 4: Public Release Hygiene

- [ ] Sync safe improvements into `ANA_MAX_GitHub_Release`.
- [ ] Keep public docs ASCII-only and exact.
- [ ] Keep public release free of private logs, memory, screenshots, keys, and
  local paths.
- [ ] Keep tool counts and premium gates accurate in every public surface.

## Verification

Mother lab checks:

```powershell
python -m compileall -q main.py core tools
python main.py --test
python main.py --list-tools
```

Public release checks:

```powershell
python -m compileall -q main.py core tools vscode_extension
python main.py --test
python main.py --list-tools
python -m unittest discover -s tests -v
```

## Management Principle

The lab can move fast, but it must not become memory soup. The public release
can be conservative, but it must not fall behind reality. Every agent must keep
both worlds connected with a clear sync decision.

- [x] v21 foundations added for theme switching, UI modernization hooks, dev-mode messaging, and next feature placeholders.
