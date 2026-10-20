# OS29 architecture v0.1

## Core contracts

- `os29.trace.v1`: normalized immutable observation with explicit trace/event/parent IDs.
- `os29.scope.v1`: explicit approved target/process policy; default deny.
- Mission capsule: required project, objective, current state, known-good/bad evidence, open issues and next steps.
- Experience: candidate or validated, always references persisted source event IDs, with an explicit recorded outcome and verifier for validated records.
- Capability node: distinguishes declared/configured/running/tested/degraded/offline/unknown and stores its evidence timestamp.

## Components

- `models.py`: trace-event contract and validation.
- `redaction.py`: secret-key/string masking and URL normalization.
- `scope.py`: HTTP(S) target allowlist and exact process-name checks.
- `store.py`: local SQLite event/capsule/incident/experience/capability persistence.
- `diagnosis.py`: observed failure summary without causality inflation.
- `runtime_snapshot.py`: fixed loopback-only health probes; no process start/stop.
- `mcp_stdio.py`: narrow, separate MCP stdio interface.
- `gateway.py`: optional bearer-protected loopback HTTP API, default port 8790, not auto-started.
- `integrations/mitmproxy/os29_addon.py`: HTTP metadata sensor.
- `integrations/frida/os29_trace.js` + `frida_bridge.py`: exact-target method telemetry with no argument/return values.

## Invariants

1. Persisted records pass through redaction.
2. A failure event may open an incident, but root cause remains unverified until independent evidence exists.
3. Only source-linked lessons can be stored; default state is candidate.
4. MCP cannot mark a lesson validated.
5. Network target and Frida process actions require exact allowlist matches.
6. OS28 components are observed through adapters first; their shared source/policy is not mutated by OS29 bootstrap.
