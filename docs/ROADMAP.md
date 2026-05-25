# ANA MAX - Public Roadmap And Development Status

<!-- # PATCH_START v20_final -->
**Public release wording:** v20.0.0-alpha
<!-- # PATCH_END v20_final -->

<!-- # PATCH_START v20_final -->
**Repository release:** v20.0.0-alpha / VS Code extension v0.2.0
<!-- # PATCH_END v20_final -->

**Status:** Clean public release with active private lab development

**Last updated:** 2026-05-25

**License:** MIT

---

## Project Vision

ANA MAX is a Windows-first local MCP runtime that gives AI agents practical QA
senses: workspace observation, desktop context, terminal output, git state,
browser workflows, UI automation, logs, voice feedback, and verification.

The public release is intentionally conservative. Private lab experiments may
be stronger than what is published here, but they stay private until they are
safe, documented, tested, and useful for authorized QA.

Public operating loop:

```text
observe -> decide -> act -> verify -> learn
```

## Current Public Baseline

```text
80 loaded tools
7 AI Core adapters
4 premium-gated tool families
3 PASS / 0 FAIL quick test
```

<!-- # PATCH_START v19_phase4 -->
v19 adds manual self-aware runtime diagnostics:
`ana_runtime_inspector`, `tool_contract_validator`, and `schema_diff`.
<!-- # PATCH_END v19_phase4 -->

<!-- # PATCH_START v20_phase3 -->
v20 adds the manual Autonomous Runtime Foundation:
`ana_health_check`, `baseline_update_suggester`, `docs_generator`,
`ana_patch_suggester`, and `runtime_guard`.
The v20 layer does not auto-run, apply patches, or change runtime behavior.
<!-- # PATCH_END v20_phase3 -->

<!-- # PATCH_START v20_final -->
v20 is DONE for the alpha release. Phase 5 adds `autonomy_dashboard`, a manual
read-only HTML dashboard for the v20 autonomy outputs.
<!-- # PATCH_END v20_final -->

Premium-gated families remain:

- `live_desktop_viewer`
- `desktop_control` and `desktop_control_tool`
- `windows_insight` and `windows_insight_tool`
- `windows_deep_sight`

`desktop_capture` is free Vision AI in this release.

## What Was Repaired

- Promoted `ocr_tool` and `window_manager` to direct Tool classes.
- Reduced the AI Core adapter count to 7 by removing adapter coverage for tools
  that now have direct Tool classes.
- Strengthened registry execution behavior with stricter parameter validation,
  compact errors, confirmation handling, and quieter agent-facing output.
- Kept runtime premium checks in `ToolRegistry.execute()` so CLI, HTTP, and MCP
  calls share the same gate.
- Updated the public website to reflect the 2026-05-24 audit baseline.

## What Was Optimized

- `tool_healthcheck` safe scope stays compact, offline, and suitable for quick
  agent checks.
- Observation tools are now framed around factual workspace and desktop state
  before an agent acts.
- Public documentation now uses one current count model: 80 tools, 7 AI Core
  adapters, and 4 premium-gated tool families.
- Public-facing pages stay ASCII-safe for Windows consoles and weaker agents.

## What Was Added

Latest public-safe tools:

- `file_patch`
- `project_navigator`
- `error_radar`
- `uia_click`
- `uia_type`
- `vision_region_capture`
- `vision_find_element`

Latest public website sections:

- WOW hero for ANA MAX - Advanced Neural Architecture
- Release highlights for the 80-tool audit baseline
- Core capabilities
- Architecture overview
- Tool categories
- Why ANA MAX
- Roadmap highlights
- Credits and AI collaboration
- Footer with GitHub, license, version, and last updated date

## Roadmap Phases

<!-- # PATCH_START v20_final -->
### v20.0.0-alpha: DONE

- [x] Phase 1: Autonomous Runtime Foundation.
- [x] Phase 2: Controlled registry integration.
- [x] Phase 3: Public surfaces sync.
- [x] Phase 4: Release hygiene and versioning.
- [x] Phase 5: Autonomy dashboard.
- [x] Final validation baseline: 80 tools, 3 PASS / 0 FAIL quick test, full
  unittest discovery passing.
<!-- # PATCH_END v20_final -->

### Phase 1: Clean And Current

Goal: keep the public release synchronized with the actual code.

- [x] Publish 80-tool baseline.
- [x] Document 7 AI Core adapters.
- [x] Document 4 premium-gated tool families.
- [x] Keep the website and README aligned with public release wording.
- [ ] Continue removing stale counts and old release language when found.

### Phase 2: Observation First

Goal: make agents gather compact facts before they act.

- [x] Keep `workspace_situational_awareness` compact and relevant.
- [x] Keep `tool_healthcheck` safe scope offline.
- [ ] Improve `desktop_capture` window capture reliability.
- [ ] Add output limits and selector hardening to `windows_uia_bridge`.
- [ ] Add more controlled tests for `vision_region_capture` and
  `vision_find_element`.

### Phase 3: Agent Reliability

Goal: reduce blind actions and improve predictable recovery.

- [x] Strengthen registry parameter validation.
- [x] Add confirmation behavior for higher-risk UI tools.
- [ ] Add broader MCP-level regression tests.
- [ ] Add reliability scoring for core tools.
- [ ] Improve error recovery and retry guidance.

### Phase 4: Public Release Hygiene

Goal: keep public ANA MAX clean, safe, and easy to verify.

- [x] Keep private logs, memory, screenshots, local paths, `.env`, and license
  files out of the repository.
- [x] Keep public docs ASCII-safe.
- [x] Document canonical public repository links.
- [ ] Add release checklist automation for docs count drift.
- [ ] Keep public website claims tied to executable tools.

### v21 Planning

- [x] Added lightweight resource system (texts + themes + loader).

## Recommendations

- Prioritize tool quality over new tool count.
- Treat observation tools as the front door for agent workflows.
- Add MCP-level tests for the new utility and UIA/vision tools.
- Keep premium/internal wording clear and avoid publishing lab-only behavior.
- Keep every public claim verifiable from the repository root.

## Verification Baseline

Run from the repository root:

```powershell
python -m compileall -q main.py core tools vscode_extension
python main.py --test
python main.py --list-tools
python -m unittest discover -s tests -v
```

Expected:

- `python main.py --test`: `3 PASS / 0 FAIL`
- `python main.py --list-tools`: 80 loaded tools
- `python -m unittest discover -s tests -v`: all tests passing

## Responsible QA Direction

ANA MAX is not meant to help users exploit weaknesses silently. It is meant to
help users and agents find real problems, verify them safely, report them
responsibly, and confirm that developers fixed them.

Preferred workflow:

```text
observe -> reproduce safely -> document impact -> report privately -> verify fix
```

Use ANA MAX only on systems you own or are explicitly allowed to test.

---

## Resources

- [Project Map](PROJECT_MAP_AI_GUIDE.md)
- [Local QA Lab Vision](LOCAL_QA_LAB_VISION.md)
- [Agent IDE Super Tools Plan](AGENT_IDE_SUPER_TOOLS_PLAN.md)
- [ANA WorkGraph Architecture](ANA_WORKGRAPH_ARCHITECTURE.md)

---

MIT License - See LICENSE file for details.

