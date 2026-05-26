# ANA MAX - Public Roadmap And Development Status

<!-- # PATCH_START v20_final -->
**Public release wording:** public v0.1.0-beta / ANA MAX OS v1.0.0 package
<!-- # PATCH_END v20_final -->

<!-- # PATCH_START v20_final -->
**Repository release:** v0.1.0-beta public release / VS Code extension v0.2.0
<!-- # PATCH_END v20_final -->

**Status:** Clean public release with active private lab development

**Last updated:** 2026-05-26

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
80 loaded public tools
7 AI Core adapters
4 premium-gated tool families
3 PASS / 0 FAIL quick test
```

The public count is intentionally smaller than the private lab surface. Lab
runtime phases, distributed cluster simulations, memory sync experiments, and
model-runtime work are promoted only after they are public-safe and tested.

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
- Public vs lab explanation
- Release highlights for the 80-tool audit baseline
- Core capabilities
- Architecture overview
- Tool categories
- Why ANA MAX
- Roadmap highlights
- Credits and AI collaboration
- Footer with GitHub, license, version, and last updated date

## Roadmap Phases

### Public v0.1.0-beta / ANA MAX OS v1.0.0

- [x] Publish the clean public release with 80 loaded public tools.
- [x] Publish `ana_os_v1/` as an isolated public-safe AI Kernel package.
- [x] Keep the existing MCP runtime in `core/` unchanged.
- [x] Explain public vs lab boundaries on the website and README.
- [x] Keep lab-only runtime state, private memory, local paths, and logs out of
  the public repo.

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

### Phase 120: ANA MAX OS Base

Goal: mature kernel-style services in the private lab before public promotion.

- [x] Publish the public-safe OS v1 package surface.
- [x] Keep runtime primitives simulated and isolated from the public MCP tool
  registry.
- [ ] Promote only cleaned, tested, documented pieces into public release docs.

### Phase 131-134: Distributed Memory Real

Goal: harden cluster-aware memory sync and transport-envelope behavior.

- [x] Mention the direction publicly as high-level roadmap context.
- [ ] Keep deterministic fake-transport tests private until release-safe.
- [ ] Avoid publishing private lab logs, local paths, or generated state.

### Phase 140: Full Cluster Integration

Goal: validate cluster, memory, event bus, and FS sync together in lab.

- [x] Reflect the integration direction on the public site.
- [ ] Promote only public-safe scenarios after API stability and hygiene review.
- [ ] Keep real network, private state, and unsafe automation out of public docs.

### Public Gate

Goal: keep public ANA MAX clean, safe, and easy to verify.

- [x] Keep private logs, memory, screenshots, local paths, `.env`, and license
  files out of the repository.
- [x] Keep public docs ASCII-safe.
- [x] Document canonical public repository links.
- [x] Keep public website claims tied to executable tools or clearly marked
  lab roadmap context.
- [ ] Add release checklist automation for docs count drift.

### v21 Planning

- [x] Resource system foundation added (localization + themes + loader).
- [x] v21 foundations added for theme switching, UI modernization hooks,
  dev-mode messaging, and next feature placeholders.

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

