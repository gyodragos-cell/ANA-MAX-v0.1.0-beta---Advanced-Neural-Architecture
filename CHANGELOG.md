# Changelog

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
- Updated public release counts to `71 loaded tools`, `4 premium-gated tool
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
  public message around 71 loaded tools, MCP auth, local-first orchestration,
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
- Tool list: 71 loaded tools
- Unit tests: all tests passing

