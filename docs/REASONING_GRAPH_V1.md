# Reasoning Graph v1

`reasoning_graph_builder.py` turns local agent, topology, recon, and capsule
metadata into a deterministic reasoning graph.

## What it includes

- Agent registry nodes and edges
- Distributed topology nodes and edges
- Knowledge graph summary nodes
- Optional browser recon pipeline nodes
- Optional capsule nodes
- Read-only query API through `reasoning_graph_query.py`

## Why it matters

- Multi-agent kernel: agents become explicit graph nodes with predictable roles
- Knowledge capsules: recon artifacts can be attached to graph nodes later
- Distributed runtime: topology and transport metadata can be reasoned about before transport exists

## Current behavior

- Local only
- Metadata only
- ASCII-safe and JSON-friendly
- No execution or transport side effects

## Query layer

`ReasoningGraphQuery` can find nodes by type, edges by agent, capsules by URL,
tool nodes by degree, and bounded paths between graph nodes. It never writes
graph artifacts and returns schema `ana.os21.reasoning_graph_query.v1`.
