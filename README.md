# ANA MAX — Local AI Tooling & Windows Automation

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Protocol: MCP](https://img.shields.io/badge/Integration-MCP%20%2F%20JSON--RPC-5468ff.svg)](https://modelcontextprotocol.io/)
[![Status: Active development](https://img.shields.io/badge/Status-Active%20development-2c8c72.svg)](docs/PORTFOLIO_STATUS_2026-10-20.md)

**ANA MAX** is a local-first engineering project for connecting AI-assisted workflows to Windows development and automation tools through practical integrations, explicit access boundaries, observable behavior and reproducible test evidence.

**Advanced Neural Architecture** is the technical descriptor; ANA MAX is the project name. The portfolio is organized around three principles: make tool access explicit, make system state observable, and make results independently verifiable.

The repository documents the OS-28 foundation. OS-29 is the next engineering line and remains a separate local companion project; its source code is not published in this repository yet. This is an active experimental project, not a claim of production certification.

## Portfolio links

- **Website:** [ANA MAX — OS-28 → OS-29](https://gyodragos-cell.github.io/ANA-MAX-v0.1.0-beta---Advanced-Neural-Architecture/)
- **Live Profile demo:** [Open browser-native profile](https://gyodragos-cell.github.io/ANA-MAX-v0.1.0-beta---Advanced-Neural-Architecture/live.html)
- **Professional CV:** [View or print the CV](https://gyodragos-cell.github.io/ANA-MAX-v0.1.0-beta---Advanced-Neural-Architecture/cv.html)
- **LinkedIn:** [Professional profile](https://www.linkedin.com/in/gyodragos/)
- **Recorded project status:** [Portfolio status and evidence, 20 Oct 2026](docs/PORTFOLIO_STATUS_2026-10-20.md)

## What this project focuses on

- **MCP / JSON-RPC integration:** connect local tools to compatible model and developer workflows.
- **Windows automation:** Python and PowerShell helpers, launchers, diagnostics and bounded local operations.
- **Access boundaries:** keep operator access separate from restricted client profiles; validate operation and path scope rather than relying on names alone.
- **Quality assurance:** regression tests, syntax checks, smoke tests, and reports that distinguish success, failure, skip and unavailable dependencies.
- **Observability and context:** health checks, bounded/redacted logs, persisted diagnostic evidence and clear runtime status.
- **Developer experience:** readable configuration, repeatable startup and documented recovery paths.

This project is under active development. Features can be declared, partially connected, unavailable or unverified; a name in a tool catalog is not proof that the operation works.

## Recorded verification snapshot

The following figures come from local engineering reports dated **19 October 2026**. They are historical evidence, not live counters on this page.

| Area | Recorded evidence | Important limit |
|---|---|---|
| OS-28 maintained test suite | 324 passed; 1 explicitly skipped in the reported run | The skipped integration check depended on an authentication environment value; the report records a successful authenticated rerun. |
| Main MCP catalog | 127 tool names | Catalog presence does not prove every tool is operational or individually tested. |
| Restricted GPT-only profile | 14 exposed tools with operation/path policy v2 | This is a restricted surface, not proof of a complete authorization matrix for every identity and operation. |
| OS-29 local companion | 37 tests passed; 14 MCP STDIO tools; 375 local indexed documents | OS-29 currently lives separately on the development PC and is not included as source code here. |
| OS-29 retrieval | SQLite FTS5/BM25 lexical search and a recorded end-to-end evidence-retrieval check | Vector embeddings, reranking and a full model-mediated reasoning loop are not claimed as complete. |

See [the dated status note](docs/PORTFOLIO_STATUS_2026-10-20.md) for the recorded scope and remaining acceptance gates.

## Repository map

| Path | Purpose |
|---|---|
| ANA_MAX/ | Main application modules and related implementation |
| mcp/ | MCP-facing entry points and adapters |
| launchers/ | Local launch and workflow helpers |
| docs/ | Architecture notes, operational references, repair reports and project history |
| scripts/ | Helper and verification scripts |
| site/ and root HTML files | Website / public portfolio assets |
| sandbox/, scratch_test_dir/ and other legacy template folders | Experimental or historical material; their current runtime role is not implied by their presence |

The repository still contains a substantial legacy history and experimental material. This README is the current high-level entry point; older documents may describe earlier versions and should not override dated test evidence.

## Safe local-use notes

- Review the source and configuration for the version you intend to run.
- Keep local service endpoints bound to loopback unless a separately reviewed deployment design says otherwise.
- Do not expose development MCP or diagnostic ports directly to the public internet.
- Keep credentials out of source files, logs, screenshots and public issue reports.
- Run tests in the intended project environment and record skips or unavailable dependencies explicitly.
- Treat this repository as active development, not a pre-certified production product.

## Development and tests

Python is the primary implementation language, with PowerShell for Windows workflows and JavaScript/HTML/CSS for the portfolio and browser-facing demos.

Use the project-specific setup instructions and the test scope relevant to the component you change. Because this repository contains historical and experimental directories, do not assume that every script, launcher or folder is part of the default runtime.

### Browser tests for the public portfolio

The Playwright suite checks the three static portfolio pages, key section links, mobile layout, Live Profile personalization, and uncaught JavaScript errors. Run it from the repository root:

```bash
npm ci
npx playwright install chromium
npm run test:e2e
```

GitHub Actions runs the suite on pushes and pull requests. The tests serve the checked-out HTML locally on loopback; they do **not** connect to the operator's local MCP endpoint, control the desktop, or certify OS-28/OS-29 runtime behavior. Playwright reports, traces and failure screenshots are retained as workflow artifacts.

A non-destructive inventory of the current root tree and a dependency-aware cleanup plan are documented in [the repository map](docs/REPOSITORY_MAP_2026-10-20.md).

## Engineering principle

**Make the state observable. Make the scope explicit. Make the evidence reproducible.**

The portfolio intentionally separates verified results from plans and prototypes. That standard applies to this README, the site and the implementation.
