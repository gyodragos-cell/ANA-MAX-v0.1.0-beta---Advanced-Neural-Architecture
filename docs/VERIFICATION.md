# OS29 verification and evidence

## Recorded local baseline

The operator's local checkpoint dated **19 October 2026** recorded:

| Check | Recorded result | Interpretation |
|---|---|---|
| OS29 pytest suite | 37 passed | Historical local run; CI reruns the suite against the published source. |
| MCP STDIO | 14 tools; initialize/list and memory-search smoke passed | Validates the recorded companion interface, not every tool against every target. |
| Lexical index | 375 documents | SQLite FTS5/BM25 local index size at the recorded checkpoint, not a public live counter. |
| Persisted trace E2E | 3 linked events; validation and triage records retrieved | Demonstrates a bounded evidence round-trip for the recorded scenario. |
| Validated experiences | 0 | Candidate records do not count as verified/validated lessons. |

## How CI verifies the public source

- Installs the package in an isolated Python 3.12 environment with test dependencies.
- Runs the pytest suite.
- Compiles the OS29 and integration modules.
- Checks the Frida JavaScript syntax with Node.js.
- Runs a separate Playwright suite against the static portfolio at multiple viewport widths.

CI results apply to the checked-out commit only. A successful browser test is not proof that the local OS29 runtime, external target or every cataloged tool is operational.

## Reproducibility

From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[test]"
python -m pytest -q
node --check .\integrations\frida\os29_trace.js
```

Do not include the local SQLite store, logs, credentials or approved target identifiers in a public test report.
