# Reasoning Graph Query v1

`reasoning_graph_query.py` adds a read-only query layer for the OS-21
reasoning graph.

## What it queries

- Nodes by type
- Edges connected to an agent
- Capsule nodes by URL
- Tool nodes by graph degree
- Bounded paths between two node IDs

## Current behavior

- Local only
- Metadata only
- ASCII-safe and JSON-friendly
- Deterministic ordering
- No tool execution
- No transport activity
- No graph artifact writes

## Usage

```powershell
python -m ANA_MAX.graph.reasoning_graph_query --summary
python -m ANA_MAX.graph.reasoning_graph_query --node-type agent
python -m ANA_MAX.graph.reasoning_graph_query --agent optimizer
python -m ANA_MAX.graph.reasoning_graph_query --tools-by-degree --min-degree 1
python -m ANA_MAX.graph.reasoning_graph_query --source orchestrator:web_recon_orchestrator_v1 --target pipeline:web_recon_orchestrator_v1
```

## OS-21 alignment

- Multi-agent kernel: agents become searchable graph nodes.
- Knowledge capsules: capsule nodes can be discovered by URL.
- Tool virtualization: tool usefulness can be estimated by graph degree.
- Distributed runtime: paths can trace how agents, tools, pipelines, and
  capsule metadata relate before real transport exists.
