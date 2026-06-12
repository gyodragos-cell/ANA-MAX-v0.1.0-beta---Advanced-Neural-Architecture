# Agent Zero Research Notes

## Scope

- Source reviewed: `ANA_MAX/sandbox/research/agent-zero`
- Upstream commit reviewed: `f9d8167`
- Purpose: identify safe, local-first patterns that can improve ANA MAX OS-20 without replacing the stable OS-20 runtime.

## Current ANA Baseline

- OS-20 baseline lock: `PASS`, `31/31` checks.
- Direct bridge: `14/14` local core tools.
- Stable direct tools do not currently include `browser_control`.
- `ANA_MAX/tools/browser_control.py` is present, but direct import fails because `core.browser_runtime` is missing.

## Useful Agent Zero Patterns

1. Browser DOM refs and action batching
   - Agent Zero browser supports structured actions such as `content`, `detail`, `screenshot`, `click`, `type`, and `multi`.
   - Its DOM helper extracts interactive roles, ARIA state, selectors, shadow DOM content, and bounded page content.
   - Best ANA use: add a small local `browser_runtime` plus DOM snapshot/ref extraction instead of replacing ANA tools.

2. Time Travel snapshots
   - Agent Zero uses shadow snapshot history for diff, travel, revert, and conflict protection.
   - Tests exclude secrets, `.env`, `node_modules`, `__pycache__`, nested git projects, and plugin internals.
   - Best ANA use: add safe pre-mutation workspace snapshots before patch/apply/healing operations.

3. Plugin manifest and toggle model
   - Agent Zero uses `plugin.yaml`, `default_config.yaml`, `.toggle-0`, and `.toggle-1`.
   - Best ANA use: add report-only plugin manifests and explicit enable gates; do not auto-enable community plugins.

4. Skill frontmatter and discovery
   - Agent Zero skills are `SKILL.md` files with metadata, trigger patterns, tags, and tool constraints.
   - Best ANA use: upgrade `self_skills_engine` discovery metadata while keeping current OS schemas intact.

5. Tool lifecycle hooks
   - Agent Zero wraps tool execution with consistent response objects and before/after execution hooks.
   - Best ANA use: add direct bridge telemetry hooks for latency, audit events, and rollback hints.

## Recommendation

- Do not replace ANA MAX OS-20 with Agent Zero.
- Do not import Agent Zero as a runtime dependency.
- Port three patterns additively:
  1. `browser_runtime` repair + DOM refs for ANA browser tooling.
  2. shadow snapshot/time-travel safety before mutations.
  3. plugin/skill manifests with explicit local enable toggles.

## Proposed Next Patch

1. Add `core/browser_runtime.py` or adjust `browser_control.py` to use an existing ANA runtime path.
2. Add a read-only `browser_snapshot`/`dom_refs` operation.
3. Keep `browser_control` outside the safe direct bridge until smoke tests pass.
4. Re-run `scripts/OS20_BASELINE_LOCK.ps1 -RunRuntimeChecks`.

## Implemented OS-20.1 Hybrid Layer

- Added `ANA_MAX/core/browser_runtime.py` as an optional local browser runtime.
- Repaired `ANA_MAX/tools/browser_control.py` import path by providing `core.browser_runtime`.
- Added `dom_refs` and `page_snapshot` operations to `browser_control`.
- Kept `browser_control` outside the 14/14 direct bridge baseline until explicit promotion.
- Added `scripts/ana_encoding_normalize.py` and `scripts/ana_encoding_normalize.ps1` for ASCII/BOM normalization.
- Added `direct_bridge.py --enable-hybrid-tools` so local agents can opt into `browser_control` without changing the OS-20 default 14-tool baseline.
