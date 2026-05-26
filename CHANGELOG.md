# Changelog

<!-- # PATCH_START v24_release -->
## v24.0.0 - Runtime Evolution Release Prep

- Added `docs/ANA_MAX_V24_RUNTIME.md` with the public v24 runtime plan:
  live tool execution boundaries, adaptive router behavior, hybrid AI,
  self-healing runtime, VS Code confirmation flows, optimization persistence,
  multi-agent mode, memory manager, and parallel orchestrator.
- Kept public runtime safe: v24 public release updates docs, site, and version
  labels only. Dev-only integration tests, memory stores, optimization
  snapshots, and private lab artifacts are not synced.
- Kept public tool count unchanged: `80 loaded tools`.
<!-- # PATCH_END v24_release -->

<!-- # PATCH_START v22_release -->
## v22.0.0 - Token-Saving Runtime Orchestrator

- Added the v22 runtime orchestration scaffold in `core/`:
  input normalization, compact context building, AI engine abstraction, tool
  routing, execution normalization, observability, scenario simulation,
  runtime configuration, release sync planning, and a runtime coordinator.
- Added pytest scaffold coverage under `tests/runtime/` for runtime,
  router, execution, observability, and scenario flows.
- Added `docs/ANA_MAX_V22_ARCHITECTURE.md` as the public architecture plan.
- Kept v22 release sync safe: `release_sync` is a read-only planner and does
  not copy, delete, deploy, commit, or modify files by itself.
- Kept public tool counts unchanged: v22 adds runtime scaffolding and tests,
  not new registered MCP tools.
<!-- # PATCH_END v22_release -->

<!-- # PATCH_START v20_phase3 -->
## v20.0.0-alpha - Autonomous Runtime Foundation

- Added the v20 autonomy layer with five manual, read-only tools:
  `ana_health_check`, `baseline_update_suggester`, `docs_generator`,
  `ana_patch_suggester`, and `runtime_guard`.
- Integrated controlled registry exposure for manual MCP/tool invocation.
- Updated the public tool count baseline to `80 loaded tools`.
- Kept runtime behavior unchanged: no auto-run, no auto-patching, no bridge,
  adapter, core, or existing-tool behavior changes.
- Kept the integration reversible through isolated v20 patch blocks.
<!-- # PATCH_START v20_phase5 -->
- Added `autonomy_dashboard`, a manual read-only HTML dashboard for v20
  autonomy tool outputs. The public baseline is now `80 loaded tools`.
- Implemented lightweight resource system (texts + themes + loader +
  dashboard integration).
- Added v21 foundations for theme switching, UI modernization hooks, dev-mode
  messaging, Resource Inspector, Dashboard v2, and Tool Health Visualizer
  placeholders.
<!-- # PATCH_END v20_phase5 -->
<!-- # PATCH_END v20_phase3 -->

<!-- # PATCH_START v19_phase5 -->
## 19.0.0 - Self-Aware Runtime

- Completed v19 Phase 1-5 release packaging for the Self-Aware Runtime.
- Added manual read-only diagnostics:
  `ana_runtime_inspector`, `tool_contract_validator`, and `schema_diff`.
- Integrated the diagnostics into the runtime registry as explicit-call tools.
- Updated the public baseline to `80 loaded tools`, `7 AI Core adapters`, and
  `4 premium-gated tool families`.
- Added unit coverage for the diagnostics layer and updated the public tool
  count baseline test.
- Added release metadata: `VERSION`, `SUMMARY.md`, `RELEASE_NOTES_v19.md`,
  `RELEASE_CHECKLIST_v19.md`, `docs/TOOLS_OVERVIEW.md`, and
  `docs/DIAGNOSTICS_LAYER.md`.
- Recommended release tag: `v19.0.0`.
<!-- # PATCH_END v19_phase5 -->

<!-- # PATCH_START v19_phase4 -->
## v19 - Self-Aware Runtime Diagnostics

- Added and integrated three manual, read-only diagnostics:
  `ana_runtime_inspector`, `tool_contract_validator`, and `schema_diff`.
- Updated public release documentation and baseline tests from the prior count
  to `80 loaded tools`.
- Kept diagnostics side-effect free: no auto-run, no auto-patching, and no
  changes to existing tool behavior.
<!-- # PATCH_END v19_phase4 -->

## 18.0-MAX-lab.audit.2026-05-24 - Public Website Upgrade

- Added `ana-max-bridge/`, an optional local HTTP connector for Copilot-style
  clients with dynamic ANA MAX tool detection, `/tools/call` forwarding,
  watchdog validation, a local control panel UI, schemas, docs, and tests.
- Added reversible LOCAL DEV MODE for localhost-only development: `local_dev:
  true` disables MCP Bearer-token requirements only for `127.0.0.1`, while
  production auth logic remains in place for non-local use.
- Added `START_LOCAL_DEV.bat` to launch ANA MAX and the local bridge UI from a
  single Windows command.
- Added `ana-max-bridge/test_all_tools.py`, a safe localhost-only bridge smoke
  tester that exercises the live tool inventory and writes reports to `C:\tmp`.
- Rebuilt `index.html` into a premium public GitHub Pages presentation for ANA
  MAX - Advanced Neural Architecture.
- Added public site sections for release highlights, core capabilities,
  architecture overview, tool categories, Why ANA MAX, roadmap highlights,
  credits, and verification.
- Aligned website and docs with the current public baseline: `80 loaded tools`,
  `7 AI Core adapters`, `4 premium-gated tool families`, and `3 PASS / 0 FAIL`
  quick healthcheck behavior.
- Updated README, project map, roadmap, and agent rules so public-facing
  documentation uses the same release wording and counts.
- Kept the work limited to public documentation and website content.

## v0.1.0-beta - Current Clean Release

- Synced the public-safe tool audit subset from the mother lab: added
  `file_patch`, `project_navigator`, `error_radar`, `uia_click`, `uia_type`,
  `vision_region_capture`, and `vision_find_element`.
- Strengthened `ToolRegistry`/`Tool.safe_execute()` with stricter parameter
  type validation, compact errors, confirmation handling, and quiet default
  tool execution for agent-friendly output.
- Promoted `ocr_tool` and `window_manager` to direct Tool classes, reducing the
  AI Core adapter count to 7 while keeping the same public tool names.
- Updated `tool_healthcheck` safe/offline coverage for the new compact utility
  and observation tools.
- Updated public release counts to `80 loaded tools`, `4 premium-gated tool
  families`, and `7 AI Core adapters`.
- Added regression coverage for the public tool count, new utility tools,
  confirmation gating, `file_patch` preview behavior, and parameter type
  validation.
- Restored a clean public release boundary: private integration setup notes are
  not part of this repository.
- Added runtime premium gating in `ToolRegistry.execute()` so premium tools are
  blocked no matter whether they are called from CLI, HTTP, or MCP.
- Enabled MCP authentication by default in `main.py`; set `ANA_MCP_KEY` or
  `MCP_API_KEY` before calling tool endpoints.
- Added release-safe backing modules for `window_manager` and
  `clipboard_manager` so AI Core adapters are no longer phantom tools.
- Added `edge_tts_voice` as a release-safe voice tool. It registers cleanly and
  reports disabled if local TTS dependencies are unavailable.
- Updated agent rules and project map to require fact-based edits, no private
  workspace paths, and no documentation for missing tools.
- Added a release sync rule so code, docs, `.env.example`, tests, and release
  counts stay aligned when behavior changes.
- Added regression tests for runtime premium blocking and adapter backing
  modules.
- Documented `MCP_API_KEY` in `.env.example`.
- Rewrote the WorkGraph architecture note as ASCII-only guidance focused on
  observation-first agents, tool quality over tool count, and task-based Frida
  usage.
- Added `workspace_situational_awareness`, an observation-only WorkGraph tool
  that returns compact workspace JSON before an agent acts.
- Hardened `workspace_situational_awareness` after bug hunt: file paths now
  resolve to their parent repo, loose AI parameters fall back safely, and local
  absolute repo paths are not exposed in the snapshot.
- Repaired `index.html` for the public website: removed mojibake/emoji, aligned
  tool counts with the release baseline, documented MCP auth, and added it to
  release hygiene tests.
- Added a first-page demo section to `index.html` so users can understand the
  workflow before reading the architecture notes.
- Repositioned the public website and README around ANA MAX as a privacy-first
  hybrid situational-awareness runtime: observe, instrument when needed, act,
  verify, and learn.
- Added `docs/ANA_MAX_WOW_DEMO.md`, a 90-second public demo blueprint that
  explains how to show ANA MAX as a situational-awareness runtime for agents.
- Reframed the public README and website around the local QA lab vision:
  offline agents, private workstations, Ollama-style local models, voice
  feedback, and tool-assisted observe-act-verify work.
- Added `docs/LOCAL_QA_LAB_VISION.md` to explain why ANA tools matter when
  internet access is blocked or data cannot leave the machine.
- Removed large demo videos from git tracking and documented the rule that
  public videos should be hosted externally, then linked from the site.
- Linked the current public YouTube demo from README, the website, and the
  video map.
- Added `docs/AGENT_IDE_SUPER_TOOLS_PLAN.md` to frame ANA MAX as local-first
  super tools for agent IDE workflows: desktop reasoning, runtime diagnostics,
  adaptive IDE flow, observability, and security posture.
- Updated the README, setup guide, and VS Code extension metadata to align the
  public message around 80 loaded tools, MCP auth, local-first orchestration,
  and agent IDE integration.
- Replaced the stale `docs/README.md` with an ASCII-only public documentation
  index that points to the release map, local lab vision, agent IDE plan,
  WorkGraph architecture, demo blueprint, and licensing notes.
- Updated browser workflow behavior so ANA MAX prefers Chrome before Brave on
  Windows and added `browser_control` operation `open_external` for launching a
  normal visible browser window that stays open after one-shot tool calls.
- Documented optional `ANA_BROWSER_PATH` for Chrome-based browser workflows and
  added smoke tests for the browser launch contract.
- Hardened the legacy MCP bridge so registered tools expose real parameter
  schemas and all tool calls route through `ToolRegistry.execute()` for
  validation, logging, and premium-gate enforcement.
- Added beginner-friendly VS Code extension install instructions and
  white-hat/authorized-use guidance for users who are new to Git, MCP, and
  local AI tooling.
- Added homepage install guidance for non-Git users, including ZIP download,
  VSIX install, MCP start commands, and explicit white-hat/authorized-use
  positioning.
- Updated the VS Code extension to honor `anaMax.mcpApiKey`,
  `anaMax.mcpHost`, and `anaMax.mcpPort`, pass the MCP API key to `main.py`,
  and send the matching Bearer token when calling `/execute`.
- Added VS Code 1.121 agent-awareness: when `VSCODE_AGENT` is present,
  `main.py` uses compact startup output and `/health` reports `vscode_agent`
  plus `output_profile` for IDE integrations.
- Added public AI collaboration credits and guidance for OpenAI Codex and
  Qoder, including official links and safe non-sponsorship wording.
- Hardened the first bug-hunt pass: `tool_healthcheck` safe scope now stays
  offline, launcher startup reports the live MCP tool count instead of the old
  `46+` text, and tests protect safe healthcheck behavior.
- Fixed stale public repository links in the VS Code extension documentation
  command, licensing docs, and premium-license message.
- Added agent-facing install guidance so Codex, Windsurf, Cursor, Qoder, and
  other coding agents can connect users to the public repo and MCP runtime
  without private lab paths or stale aliases.
- Replaced stale legacy install/publish docs that still referenced placeholder
  GitHub URLs, old tool counts, and mojibake.
- Cleaned quick MCP, dependency, and VS Code publishing guides so public agent
  handoffs use current auth, tool counts, and canonical links.
- Added responsible QA and white-hat reporting language to the README, AI
  collaboration guide, and roadmap while keeping private lab capabilities out
  of the public release.
- Expanded the AI collaboration acknowledgement to describe Codex as a
  project-map analyst and to explain why strict safety behavior is valuable for
  clean users and authorized QA.
- Clarified that live third-party testing requires explicit authorization and
  that strong server-side findings belong in private responsible-disclosure
  reports, not public abuse recipes.
- Added a public mint-condition checklist for release polish, verification, and
  clean agent handoff.
- Added public positioning for ANA MAX as a local multi-tool runtime for AI
  agents, with clear operator responsibility for lawful and authorized use.
- Added a safe VS Code extension publish helper that packages, verifies, and
  optionally publishes the VSIX without storing marketplace tokens.
- Hardened the publish helper so Marketplace authentication failures stop the
  script instead of looking successful.

## Verification Baseline

```powershell
python -m compileall -q main.py core tools vscode_extension
python main.py --test
python main.py --list-tools
python -m unittest discover -s tests -v
```

Expected:
- Quick test: `3 PASS / 0 FAIL`
- Tool list: 80 loaded tools
- Unit tests: all tests passing


