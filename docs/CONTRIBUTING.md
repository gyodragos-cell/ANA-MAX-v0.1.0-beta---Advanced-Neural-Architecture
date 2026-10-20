# Contributing to OS29

## Change policy

1. Prefer small, reversible changes tied to an observable defect or defined acceptance gate.
2. Add a regression test for behavior changes and state exactly what the test does not prove.
3. Keep runtime evidence separate from plans, synthetic fixtures and historical reports.
4. Never commit local databases, raw logs, browser profiles, credentials, machine-specific paths or target identifiers.
5. Keep the HTTP gateway loopback-only by default; do not add arbitrary shell or raw file-write operations to the MCP surface.
6. For Frida/MITM work, use explicitly authorized targets and metadata-only collection unless a reviewed test requires otherwise.
7. Do not mark a candidate experience validated without linked evidence, a measured retest and explicit local operator confirmation.

## Local checks

```powershell
python -m pip install -e ".[test]"
python -m pytest -q
node --check .\integrations\frida\os29_trace.js
npm ci
npm run test:e2e
```

Reports are generated locally and ignored by Git unless a sanitized summary is intentionally written to documentation.
