# Capsule Sync v1

Capsule Sync v1 adds metadata-only sync and merge planning for OS-21.5 recon
capsules. It does not write files, call transports, execute tools, or change
OS-20.1 runtime behavior.

## Merge engine

`CapsuleMergeEngine` provides:

- `detect_conflicts(base, left, right)`
- `merge(base, left, right)`

Merge rules:

- Dictionaries merge recursively by sorted key.
- Lists merge by deterministic union, preserving first-seen order.
- Scalars use one-sided changes when only one side changed from base.
- Scalar conflicts are reported when both sides changed differently from base.
- Lineage preserves existing lineage plus `capsule_id@version` references from base, left, and right.

## Sync engine

`CapsuleSyncEngine` provides:

- `build_sync_plan(local_capsules, remote_capsules, base_capsules)`
- `apply_plan_preview(plan, local_capsules, remote_capsules)`

Sync actions:

- `noop`
- `create_local`
- `create_remote`
- `update_local`
- `update_remote`
- `merge_required`

The preview method only returns projected in-memory IDs and counts. It never
performs writes.

## OS-21.5 alignment

- Knowledge capsules: supports deterministic sync, merge, and lineage metadata
- Reasoning graph: conflict and sync actions can become graph nodes later
- Distributed runtime: prepares capsule exchange before real transport exists

