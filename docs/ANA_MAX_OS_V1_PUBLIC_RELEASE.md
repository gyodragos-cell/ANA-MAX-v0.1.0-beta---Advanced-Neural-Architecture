# ANA MAX OS v1 Public Release

ANA MAX OS v1 is the first public-safe package of the simulated ANA MAX AI
Kernel runtime. It is published as `ana_os_v1/` so it does not overwrite the
existing ANA MAX MCP tool runtime in `core/`.

## What Is Included

- Cluster membership, health, routing, and summaries.
- Distributed memory, filesystem sync, event bus, locks, tasks, services,
  metrics, and recovery helpers.
- Model registry, placement, routing, loader, and simulated inference.
- Agent registry, lifecycle, messaging, memory, filesystem, and task hooks.
- Vector memory, cognitive runtime, pipeline manager, DevTools, federation, and
  packaging helpers.

## Release Boundary

- No real network transport.
- No real ML inference.
- No threads or async runtime loops.
- No tests or fake transport scaffolding are included in the package.
- The existing public MCP tool count remains 80.

## Import Example

```python
from ana_os_v1.cluster_manager import ClusterManager
from ana_os_v1.model_registry import ModelRegistry

cluster = ClusterManager()
registry = ModelRegistry()
```

## Verification

```powershell
python -m compileall -q ana_os_v1
python -m unittest tests.test_ana_os_v1_public -v
```
