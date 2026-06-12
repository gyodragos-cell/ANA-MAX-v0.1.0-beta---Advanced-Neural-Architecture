# Web Recon Orchestrator v1

`web_recon_orchestrator.py` is a planning-only OS-21 slice. It does not run
browser actions. Instead, it consumes `BrowserReconAgent` metadata and turns it
into a structured recon pipeline for future orchestration layers.

## What it produces

- A deterministic pipeline plan
- Passive and optional active recon phases
- Capability contracts for browser and scraper tools
- Reasoning-graph hints for future graph builders
- Capsule hints for future recon artifact storage
- A stable handoff target for `web_recon_agent.py`

## How it fits OS-21

- Multi-agent kernel: the orchestrator sits above the agent and coordinates its plan
- Reasoning graph: it exposes node and edge hints for future graph construction
- Knowledge capsules: it emits capsule hints so recon artifacts can be stored later

## Current behavior

- Local only
- Metadata only
- ASCII-safe and JSON-friendly
- No browser execution
- No OS-20.1 runtime changes
