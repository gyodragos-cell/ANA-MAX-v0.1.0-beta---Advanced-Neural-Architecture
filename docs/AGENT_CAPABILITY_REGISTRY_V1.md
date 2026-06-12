# Agent Capability Registry v1

`agent_capability_registry.py` is the first OS-21 kernel scaffold. It records
agent roles, declared capabilities, tool references, and sandbox policy as
metadata only.

## What it includes

- Agent records
- Capability records
- Tool references
- Capability index
- Tool index
- Sandbox policy metadata
- Reasoning graph hints

## Current behavior

- Local only
- Metadata only
- ASCII-safe and JSON-friendly
- No agent execution
- No tool execution
- No file writes
- No OS-20.1 runtime changes

## Usage

```powershell
python -m ANA_MAX.kernel.agent_capability_registry --summary
python -m ANA_MAX.kernel.agent_capability_registry --validate
python -m ANA_MAX.kernel.agent_capability_registry --capability web_scraper.read_only
python -m ANA_MAX.kernel.agent_capability_registry --agent web_recon_agent_v1
```

## OS-21 alignment

- Multi-agent kernel: agents now have a central capability registration layer.
- Tool virtualization: capabilities reference tools by contract, not execution.
- Reasoning graph: registry output can become graph nodes and edges.
- Local autonomy sandbox: all registered agents default to `execution_allowed=false`.
