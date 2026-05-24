# PATCH_START v19_phase4
# Release Notes

## v19 - Self-Aware Runtime Diagnostics

- Added `ana_runtime_inspector`, a read-only runtime snapshot and environment
  comparison diagnostic.
- Added `tool_contract_validator`, a read-only contract checker with safe
  allowlisted probes.
- Added `schema_diff`, a read-only schema/response diff helper.
- Integrated the diagnostics as manual runtime tools.
- Updated the public baseline to `80 loaded tools`.

The v19 diagnostics do not auto-run and do not modify files, bridge behavior,
core runtime behavior, or existing tools.
# PATCH_END v19_phase4
