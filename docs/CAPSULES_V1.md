# Capsules v1

Capsules v1 defines a metadata-only recon capsule shape and a simple in-memory
store. It is the first OS-21 knowledge-layer slice and is designed to stay
local-only and compatible with OS-20.1.

## Capsule schema

`ReconCapsuleSchema` captures:

- `capsule_id`
- `url`
- `mode`
- `timestamp`
- `passive_phases`
- `active_phases`
- `artifacts`
- `capability_contracts`
- `reasoning_graph_hints`
- `version`
- `lineage`

## Capsule store

`CapsuleStore` provides:

- `save_capsule()`
- `load_capsule()`
- `list_capsules()`
- `diff_capsules()`
- `merge_capsules()`

`CapsuleMergeEngine` provides:

- `detect_conflicts()`
- `merge()`

`CapsuleSyncEngine` provides:

- `build_sync_plan()`
- `apply_plan_preview()`

The store is in-memory and deterministic. It does not execute browser actions
or mutate OS-20.1 runtime behavior.

Sync and merge remain metadata-only. Conflict handling reports divergent scalar
changes instead of guessing a final value.

## OS-21 alignment

- Knowledge capsules: versioned recon units for later sync and composition
- Reasoning graph: capsules become graph nodes and edges later
- Distributed runtime: capsules can be copied, merged, and compared before transport exists
- OS-21.5 sync: capsules now support deterministic merge planning and conflict reporting
