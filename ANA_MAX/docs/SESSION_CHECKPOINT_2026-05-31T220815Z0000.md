# Session Checkpoint - 2026-05-31T22:08:15+00:00

## Autonomy example documents dirty-tree signal

## Summary

Updated Autonomy Runner pass contract example to show the current 22-test focused result and the compact Patch Advisor dirty-tree signals exposed by Autonomy: dirty_tree_available and dirty_tree_total.

## Current Goal

Keep ANA MAX examples aligned with current autonomy/self-healing behavior.

## Next Steps

- Operator restart ANA MCP when ready, then run Live Behavior, Reload Consistency, Post-Reload Verify, and Autonomy Pass.

## Files Changed

- docs/examples/AUTONOMY_RUNNER_PASS_CONTRACT_EXAMPLE.md

## Validation

```text
python -m pytest tests/runtime/test_ana_autonomy_runner.py tests/runtime/test_ana_patch_advisor.py -q => 22 passed; rg confirmed dirty_tree_available/dirty_tree_total in the Autonomy example
```

## Risks

- Docs-only change. Live behavior WARN remains expected until ANA MCP restart.

## Lab/Release Sync Status

mother-lab only; public/repo pending
