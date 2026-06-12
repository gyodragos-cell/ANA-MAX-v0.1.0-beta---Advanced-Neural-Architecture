# Session Checkpoint - 2026-06-02T01:02:56+00:00

## ANA Codex Golden Rule

## Summary

Codex Companion and ANA-first golden rule were added so Codex does not work blind in the ANA mother lab. ANA now has an explicit companion preflight that observes, routes, coaches, context-packs, checks Error Radar, and challenges Codex before scoped work.

## Current Goal

Use ANA as Codex visibility and challenge layer before meaningful lab action.

## Next Steps

- Install VSIX v1.0.53 when Billy is ready
- run Developer Reload Window
- restart ANA MCP
- run Post-Reload Verify
- use ANA MAX: Codex Companion before scoped work.

## Files Changed

- docs/ANA_CODEX_GOLDEN_RULE.md
- AGENTS.md
- docs/ANA_LAB_LLM_INDEX.md
- docs/LAB_README.md
- docs/DOCS_INDEX.md
- docs/AGENT_MEMORY.md
- ANA_MAX/dev_artifacts/scripts/ana_codex_companion.py
- vscode_extension/extension.js
- vscode_extension/package.json
- tests/runtime/test_ana_codex_companion.py

## Validation

```text
Codex Companion live WARN as designed; tool_healthcheck 7 OK / 0 FAIL; focused pytest 53 passed; VSIX version check PASS expected 1.0.53; context maps PASS; Nucleus PASS 10/10; Operator Status PASS package=PASS v1.0.53.
```

## Risks

- Large dirty tree remains
- ANA Companion warns Codex to separate old dirty work from today change before commit/archive. Activity Bar v1.0.53 requires manual install/reload to appear.

## Lab/Release Sync Status

Mother lab only; public sync pending explicit Billy approval.
