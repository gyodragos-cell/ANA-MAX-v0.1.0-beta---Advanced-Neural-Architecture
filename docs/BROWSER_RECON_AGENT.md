# Browser Recon Agent v1

Browser Recon Agent v1 is a metadata-only OS-21 slice. It does not execute
browser actions. Instead, it plans passive and active recon work on top of the
browser pack manifest.

## What it does

- Consumes `browser_pack` metadata
- Builds passive and active recon plans
- Separates read-only work from confirm-required follow-up
- Exposes reasoning-graph hints for future orchestration

## Passive phases

- scope_target
- passive_scrape
- dom_snapshot
- headers_tls_review
- forms_inventory
- js_endpoint_mapping
- risk_classification

## Active follow-up phases

- interactive_probe
- network_intercept_review

These phases are planning only. They are not executed by this module.

## OS-21 alignment

- Tool virtualization: uses the browser pack contract instead of guessing tool behavior
- Multi-agent kernel: creates an explicit agent slice with a stable role and plan shape
- Reasoning graph: exports agent, tool, context, and memory hints for future graph builders
- Orchestration handoff: `web_recon_orchestrator.py` can consume the plan and build a multi-phase pipeline
- Knowledge capsules: the recon plan now lines up with `ana.os21.recon_capsule.v1` for later artifact storage
- Graph builder handoff: the recon plan now feeds `reasoning_graph_builder.py` and the distributed pipeline skeleton
- Web agent handoff: `web_recon_agent.py` now composes this agent with `web_scraper_agent.py` and the web recon orchestrator

## Usage

The module supports a small CLI for planning and validation:

- plan
- validate
- summary
- cycle

The outputs are JSON only and remain local-safe.

The agent is still planning-only. No browser actions are executed here.
