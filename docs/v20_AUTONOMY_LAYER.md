# PATCH_START v20_phase3
# ANA MAX v20 Autonomy Layer

The v20 autonomy layer is a read-only foundation for self-validating,
self-diagnosing, self-documenting, and patch-suggesting runtime workflows.

## Tool Roles

- `ana_health_check` aggregates diagnostic status.
- `baseline_update_suggester` reports count and baseline drift.
- `docs_generator` returns generated documentation text previews.
- `ana_patch_suggester` creates patch suggestions without applying them.
- `runtime_guard` checks runtime consistency and reports WARN or OK.
<!-- # PATCH_START v20_phase5 -->
- `autonomy_dashboard` renders the v20 autonomy outputs as read-only HTML.
<!-- # PATCH_END v20_phase5 -->

## Integration Model

The tools are registered in the runtime for manual calls only. Registration
does not execute diagnostics, modify files, or change existing tool behavior.

## Release Rule

Any future automation must be added behind explicit controls, tests, and public
documentation. v20.0.0-alpha remains manual and reversible.

<!-- # PATCH_START v20_phase5 -->
## Dashboard

The autonomy dashboard is a manual tool. It renders output from the v20
autonomy tools and returns HTML to the caller. It never writes files, starts a
server, changes runtime state, or applies patch suggestions.
<!-- # PATCH_END v20_phase5 -->

<!-- # PATCH_START v20_final -->
## Final v20 Status

v20.0.0-alpha is complete for public release. The autonomy layer is documented,
registered for manual calls, covered by tests, and represented by the
read-only autonomy dashboard.
<!-- # PATCH_END v20_final -->
# PATCH_END v20_phase3
