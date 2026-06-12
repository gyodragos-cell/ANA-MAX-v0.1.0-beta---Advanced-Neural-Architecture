# Web Agents v1

Web Agents v1 adds metadata-only agents for scraper and web recon planning.
They do not execute browser actions, network requests, or file writes.

## Components

- `web_scraper_agent.py`: plans safe use of `web_scraper` operations.
- `web_recon_agent.py`: composes browser recon, scraper planning, and the web recon orchestrator.

## Web scraper agent

The scraper agent builds a JSON-friendly plan with:

- target scope
- fetch metadata plan
- HTML parsing plan
- link extraction plan
- text extraction plan
- asset and form extraction plans
- future capsule hints

Active mode only adds review-only follow-up metadata for multi-page expansion
and download review.

## Web recon agent

The web recon agent combines:

- `BrowserReconAgent`
- `WebScraperAgent`
- `WebReconOrchestrator`

It emits graph hints, capsule hints, and handoff metadata for capsule storage,
reasoning graph updates, and distributed pipeline planning.

## Current behavior

- Local only
- Metadata only
- ASCII-safe and JSON-friendly
- No tool execution
- No transport activity
- No OS-20.1 runtime changes

## Usage

```powershell
python -m ANA_MAX.agents.web_scraper_agent --target https://example.com --cycle
python -m ANA_MAX.agents.web_recon_agent --target https://example.com --cycle
```

## OS-21 alignment

- Multi-agent kernel: adds explicit scraper and web recon agent roles.
- Tool virtualization: uses capability contracts instead of direct tool calls.
- Knowledge capsules: emits capsule hints for future recon artifacts.
- Reasoning graph: emits graph nodes and edges for later graph building.
- Kernel registry: agents can now be registered through `agent_capability_registry.py`.
