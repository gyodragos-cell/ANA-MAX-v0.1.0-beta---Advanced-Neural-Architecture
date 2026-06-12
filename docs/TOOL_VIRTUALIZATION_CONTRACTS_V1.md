# Tool Virtualization Contracts v1

`tool_virtualization_contracts.py` converts registered agent capabilities into
sandboxed tool contracts.

## What it includes

- Tool contracts
- Operation contracts
- Tool index
- Operation index
- Simulation metadata
- Fallback plan metadata
- Sandbox policy metadata

## Current behavior

- Local only
- Metadata only
- ASCII-safe and JSON-friendly
- No tool execution
- No network access
- No filesystem writes
- No OS-20.1 runtime changes

## Usage

```powershell
python -m ANA_MAX.kernel.tool_virtualization_contracts --summary
python -m ANA_MAX.kernel.tool_virtualization_contracts --tool web_scraper
python -m ANA_MAX.kernel.tool_virtualization_contracts --simulate --tool web_scraper --operation parse
python -m ANA_MAX.kernel.tool_virtualization_contracts --fallback --tool browser_control
```

## OS-21 alignment

- Tool virtualization: every registered tool operation has a metadata contract.
- Multi-agent kernel: contracts are derived from the agent capability registry.
- Local autonomy sandbox: execution is blocked by default and simulation is metadata-only.
- Self-healing: fallback plans can be used by future planners without invoking real tools.
