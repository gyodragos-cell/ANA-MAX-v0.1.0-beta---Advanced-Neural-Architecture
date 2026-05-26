# ANA MAX v24 Runtime

Status: v24 development and public release preparation
Scope: dev-first; public sync only in explicit release phase

## Architecture

```text
Input
  -> Context Builder
  -> Hybrid AI Engine
  -> Adaptive Router
  -> Live Execution Layer
  -> Observability + Health Monitor
  -> Auto-Repair + Self-Optimization
  -> Memory + Multi-Agent + Parallel Orchestrator
```

## Live Tool Execution

v24 supports local callable tools, MCP tools, remote tools, built-in file
operations, subprocess execution, and network calls. Capability flags control
the execution boundary:

- `safe_read`
- `safe_write`
- `network_allowed`
- `subprocess_allowed`

Safe-mode blocks writes, subprocess execution, and network calls by default.

## Adaptive Router

The router keeps the last 50 decisions in memory and scores tools using:

```text
base score
  + reliability boost
  - noise penalty
  - latency penalty
  + scenario fit
  + optimization feedback
```

## Hybrid AI

Hybrid mode tries local generation first and falls back to cloud-compatible
generation on failure. Real local model calls remain opt-in.

## Self-Healing Runtime

Auto-repair turns failures into safe plans:

- retry with adjusted parameters
- switch to backup tool
- suggest code patch text
- log diagnostic hints
- temporarily disable broken tools in memory

No patch is applied automatically.

## VS Code Integration

The dev extension includes:

- runtime status panel
- tool execution command
- router decisions panel
- observability panel
- explicit confirmation dialogs for tool execution, writes, subprocess, and
  network calls

## Optimization Persistence

Optimization snapshots can persist under `ana_dev/.ana_max/optimization`.
Safe-mode rejects public release paths.

## Multi-Agent Mode

The v24 agent manager supports lightweight in-memory agents:

- tool agents
- scenario agents
- fallback agents
- analysis agents

## Memory Manager

Memory is split into:

- semantic memory for tool behavior and patterns
- episodic memory for recent tasks
- context injection for routing and planning

## Parallel Orchestrator

The v24 orchestrator supports:

- task queue
- priority scheduling
- parallel execution
- timeout enforcement

## Roadmap

### v24-alpha

- Stabilize live execution capability flags.
- Keep integration tests dev-only.
- Expand confirmation flows in VS Code.

### v24-beta

- Add lab-only MCP and local model integration markers.
- Add memory-backed routing suggestions.
- Add orchestrator dashboards.

### v24-rc

- Freeze release-safe docs and test matrix.
- Audit public release surfaces.
- Confirm no private logs, screenshots, memory, or secrets are synced.

### v24 Public Release

- Sync only selected ship-safe docs and release surfaces.
- Keep runtime code dev-only until explicitly approved for public sync.
- Tag and push after verification.

## Release Plan

Sync rules:

- Only explicitly listed files move to public release.
- No private state leaves `ana_dev`.
- Public docs must state safe-mode defaults clearly.

Safe-mode rules:

- Read-only by default.
- No subprocess.
- No network.
- No writes.

Write-mode rules:

- Enabled only for explicit release actions.
- Controlled docs/site/version writes only.
- Tag and push after verification.

Extension packaging:

```powershell
node --check vscode_extension\extension.js
```

Test matrix:

```powershell
python -m compileall -q core tests\runtime tests\integration
python -m pytest tests\runtime tests\integration -q
node --check vscode_extension\extension.js
```
