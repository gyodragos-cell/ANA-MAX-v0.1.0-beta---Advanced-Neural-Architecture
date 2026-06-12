# Session Checkpoint - 2026-05-31T22:09:29+00:00

## Docs indexes updated for Autonomy dirty-tree evidence

## Summary

Updated ANA examples/docs indexes so Autonomy Runner contract and Patch Advisor entries mention local Dirty Tree evidence. Governance check passed 116/116 after the index update.

## Current Goal

Keep ANA MAX docs discoverable and aligned with current self-healing/autonomy behavior.

## Next Steps

- Operator restart ANA MCP when ready, then run Live Behavior, Reload Consistency, Post-Reload Verify, and Autonomy Pass.

## Files Changed

- docs/ANA_EXAMPLES_INDEX.md
- docs/DOCS_INDEX.md
- docs/AGENT_MEMORY.md

## Validation

```text
python -m pytest tests/runtime/test_ana_autonomy_runner.py tests/runtime/test_ana_patch_advisor.py -q => 22 passed; ana_governance_check.py => PASS 116/116, report governance_check_20260531_220910.json
```

## Risks

- Docs/index-only change. Live behavior WARN remains expected until ANA MCP restart.

## Lab/Release Sync Status

mother-lab only; public/repo pending
