# PATCH_START v20_phase3
# ANA MAX v20 Overview

ANA MAX v20.0.0-alpha adds the Autonomous Runtime Foundation.

<!-- # PATCH_START v20_final -->
Final v20 alpha status: complete, manually integrated, documented, tested, and
ready for commit, tag, and push after maintainer review.
<!-- # PATCH_END v20_final -->

The release adds a controlled, manual-call layer that helps maintainers inspect
runtime health, compare baselines, generate documentation previews, suggest
patches, and verify consistency without changing runtime behavior.

## Public Baseline

```text
80 loaded tools
7 AI Core adapters
4 premium-gated tool families
```

## v20 Components

- `ana_health_check`
- `baseline_update_suggester`
- `docs_generator`
- `ana_patch_suggester`
- `runtime_guard`
<!-- # PATCH_START v20_phase5 -->
- `autonomy_dashboard`
<!-- # PATCH_END v20_phase5 -->

## Guarantees

- No auto-run.
- No behavior changes.
- No writes from v20 tools.
- No patch application.
- Manual invocation through the registry/MCP only.
# PATCH_END v20_phase3
