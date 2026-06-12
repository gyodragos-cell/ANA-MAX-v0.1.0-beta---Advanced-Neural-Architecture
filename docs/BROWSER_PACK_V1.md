# Browser Pack v1

Browser Pack v1 is the first OS-21 tool-layer slice. It does not change OS-20.1
runtime behavior. It adds a metadata contract for browser and web tools so
future agents can reason about safe operations, risky operations, and tool
load policy.

## What it covers

- `browser_control` as a hybrid-optional browser tool
- `web_scraper` as a local web parsing and fetch tool
- Explicit read-only, stateful, and confirm-required operation groups
- A simple manifest that future orchestrators can consume

## Why it matters

- Tool virtualization: the pack describes contracts before behavior changes
- Multi-agent planning: agents can inspect the manifest instead of guessing
- Reasoning graph: tool metadata can become graph nodes later

## Current policy

- Local only
- Additive only
- OS-20.1 safe by default
- `browser_control` stays hybrid-optional
- Risky browser actions still require explicit confirmation

## Suggested follow-up

- Add an OS-21 browser agent that consumes the manifest
- Add a web recon orchestrator that uses the browser and scraper contracts
- Add capsule storage for browser recon results
