# Changelog

## 2026-10-20 — OS29-only public source tree

- Published the isolated OS29 core, integrations, tests and selected technical documentation.
- Reorganized the premium portfolio under `site/portfolio/`; GitHub Pages stages only the three approved HTML pages.
- Added separate OS29 pytest/compile/Frida-JS CI and browser Playwright E2E workflows.
- Excluded runtime SQLite databases, logs, artifacts, browser profiles, caches, local target IDs, private memory sources and machine-specific MCP configuration.
- Preserved a recoverable branch of the prior mixed repository: `archive/pre-os29-clean-rebuild-2026-10-20`.
