# Session Checkpoint - 2026-06-02T00:14:46+00:00

## Extension 1.0.52 Refresh Context Maps

## Summary

Activity Bar refresh now runs ana_refresh_context_maps.py --json, refreshing Code Map and Graph Map together and surfacing freshness in Live Console. Packaged lab VSIX 1.0.52 without install/reload.

## Current Goal

Keep ANA MAX mother-lab Activity Bar reliable and context-aware.

## Next Steps

- Operator may install vscode_extension/ana-codex-cockpit-1.0.52.vsix when ready, reload VS Code, restart ANA MCP, then run Post-Reload Verify and Operator Status.

## Files Changed

- vscode_extension/package.json
- vscode_extension/extension.js
- vscode_extension/README.md
- vscode_extension/MARKETPLACE.md
- vscode_extension/CHANGELOG.md
- tests/runtime/test_vscode_extension.py
- docs active version/context files

## Validation

```text
json.tool PASS; node --check PASS; pytest test_vscode_extension PASS 33; ana_vsix_version_check PASS; package_cockpit_vsix built 1.0.52; ana_refresh_context_maps PASS; no_reload_quality_gate PASS 8/8; review batches test/extension/doc PASS; nucleus PASS 10/10; operator status PASS.
```

## Risks

- Active IDE still needs manual VSIX install/reload before the new Activity Bar label appears. Existing command id anaMax.refreshCodeMap is intentionally kept as a compatibility alias.

## Lab/Release Sync Status

Mother lab only; no public/GitHub sync.
