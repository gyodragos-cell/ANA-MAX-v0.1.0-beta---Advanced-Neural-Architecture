# Session Checkpoint - 2026-06-01T23:18:35+00:00

## Code and Graph Map refreshed after noise guard

## Summary

Refreshed ANA Code Map and Graph Map after the generated-memory noise filter work. Code Map now has 956 summaries and Graph Map has 10335 nodes / 27883 edges. Live Behavior remains PASS 9/9 and Operator Status remains PASS with tool surface 90/90.

## Current Goal

Keep ANA context fresh and reliable after recent lab reliability patches.

## Next Steps

- Continue with one scoped lab reliability/autonomy action
- avoid reload unless source/runtime divergence appears.

## Files Changed

- ANA_MAX/memory/code_map
- ANA_MAX/memory/graph_map
- checkpoint only

## Validation

```text
ana_code_map stats PASS; ana_graph_map stats PASS; code_context_pack live query OK; graph_context_pack live query OK; ana_live_behavior_check PASS 9/9; ana_operator_status PASS.
```

## Risks

- Graph top hubs still include common checkpoint/session keywords, but query-time demotion/filtering is active and verified.

## Lab/Release Sync Status

mother-lab only; no public sync
