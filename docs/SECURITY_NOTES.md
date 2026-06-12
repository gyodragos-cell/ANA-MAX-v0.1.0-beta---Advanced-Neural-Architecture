# Security Notes

## 2026-06-10

- Direct bridge defaults to local-only operation.
- Risky tools require explicit `--confirm` or `--dry-run`.
- Sensitive payload keys are redacted in bridge audit logs.
- Maintenance cleanup is dry-run by default; deletion requires explicit `-Apply`.
- Log archival requires both `-ArchiveLogs` and `-Apply`; dry-run reports candidates only.
- Size-based log rotation requires both `-RotateLargeLogs` and `-Apply`; dry-run reports candidates only.
- Scheduled task installation is dry-run by default and requires explicit `-Apply`.
- Archive compression requires both `-CompressArchive` and `-Apply`; dry-run reports candidates only.
- Incremental log compression is dry-run by default; zip retention cleanup requires explicit `-Apply`.
- Filesystem cleanup archives `.tmp/.bak/.old` candidates under `ANA_MAX/sandbox/fs_cleanup_archive/`; no direct deletion.
- Placeholder quarantine removes local modules that shadow external packages such as `requests`, `pytest`, `psutil`, `numpy`, and `yaml`.
- Restored tools came from local duplicate archive only; no network or remote source was used.
- Archive contents remain read-only by convention unless an explicit repair/restore action is requested.

## 2026-06-10 - OS-10 Layer Check

- The OS-10 security engine remains report-only unless an explicit apply flow is introduced.
- Risky tool markers are scanned locally from filenames only; no execution or auto-registration occurs.
- Dry-run orchestration continues to emit RAW-tagged JSON and does not enable dangerous tools.

## 2026-06-10 - Memory Layer Security Note

- The new memory context layer reads and writes only local workspace files under `ANA_MAX/memory/`.
- No network calls, remote storage, secret handling, or tool auto-registration were introduced by the memory layer.
- Memory fallbacks return `module_missing` or `failed_to_load` instead of mutating state blindly.
