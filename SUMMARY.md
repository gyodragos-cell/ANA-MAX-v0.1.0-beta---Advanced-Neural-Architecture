# PATCH_START v20_phase3
# ANA MAX v20.0.0-alpha Summary

ANA MAX v20.0.0-alpha adds the Autonomous Runtime Foundation and integrates it
as controlled, manual-call diagnostics.

## Included v20 Tools

- `ana_health_check`
- `baseline_update_suggester`
- `docs_generator`
- `ana_patch_suggester`
- `runtime_guard`
<!-- # PATCH_START v20_phase5 -->
- `autonomy_dashboard`
<!-- # PATCH_END v20_phase5 -->

## Release Baseline

```text
80 loaded tools
7 AI Core adapters
4 premium-gated tool families
```

## Release Position

v20 keeps existing runtime behavior intact. The autonomy layer is additive,
manual, read-only by design, and does not auto-run.

<!-- # PATCH_START v20_phase5 -->
Phase 5 adds a read-only autonomy dashboard renderer. It displays v20 tool
outputs as HTML and does not write files or modify runtime state.
<!-- # PATCH_END v20_phase5 -->

## Recommended Tag

```text
v20.0.0-alpha
```
# PATCH_END v20_phase3

# PATCH_START v19_phase5
# ANA MAX v19.0.0 Summary

ANA MAX v19.0.0 packages the Self-Aware Runtime release.

The release adds a read-only diagnostics layer that helps maintainers answer
three common runtime questions:

- Which runtime and bridge are actually active?
- Do tool responses match the contract expected by callers?
- Where do schemas and actual responses differ?

## Included v19 Tools

- `ana_runtime_inspector`
- `tool_contract_validator`
- `schema_diff`

## Release Baseline

```text
80 loaded tools
7 AI Core adapters
4 premium-gated tool families
```

## Release Position

v19 keeps the existing ANA MAX runtime behavior intact. The diagnostics layer is
additive, explicit, manual, and side-effect free.

## Recommended Commit

```text
ANA MAX v19 - Self-Aware Runtime (Phase 1-5 complete)
```

## Recommended Tag

```text
v19.0.0
```
# PATCH_END v19_phase5
