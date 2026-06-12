# Session Checkpoint - 2026-05-31T21:41:18+00:00

## Autonomy carries Patch Advisor dirty-tree signals

## Summary

Autonomy Runner now includes Patch Advisor's local Dirty Tree signals in compact output: dirty_tree_available and dirty_tree_total. This makes the observe-route-verify loop show that self-healing used local dirty-tree evidence even while live MCP error_radar remains stale before restart.

## Current Goal

Keep ANA MAX autonomy reports evidence-rich and robust to stale live MCP behavior.

## Next Steps

- Operator restart ANA MCP when ready, then run Live Behavior, Reload Consistency, Post-Reload Verify, and Autonomy Pass.

## Files Changed

- ANA_MAX/dev_artifacts/scripts/ana_autonomy_runner.py
- tests/runtime/test_ana_autonomy_runner.py
- docs/examples/AUTONOMY_RUNNER_PASS_CONTRACT_EXAMPLE.md
- docs/AGENT_MEMORY.md

## Validation

```text
python -m pytest tests/runtime/test_ana_autonomy_runner.py tests/runtime/test_ana_patch_advisor.py -q => 22 passed; ana_autonomy_runner.py --no-write --json => WARN 15 pass / 1 warn / 0 fail with patch_advisor dirty_tree_available=true dirty_tree_total=373
```

## Risks

- Autonomy remains read-only in this path. Live behavior WARN remains expected until ANA MCP restart.

## Lab/Release Sync Status

mother-lab only; public/repo pending
