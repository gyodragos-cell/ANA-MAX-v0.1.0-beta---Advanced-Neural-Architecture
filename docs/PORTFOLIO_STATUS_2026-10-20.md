# ANA MAX / OS-28 / OS-29 — Portfolio Status

**Snapshot date:** 20 October 2026  
**Purpose:** one concise, evidence-led reference for the public portfolio and repository handoff.

## What is public

- **index.html:** professional overview of the OS-28 foundation and OS-29 direction.
- **live.html:** browser-native profile demo. The display name is chosen by the visitor and is not uploaded. It uses browser-exposed properties only.
- **cv.html:** printable CV page and copy-ready LinkedIn “About” draft.
- Root **README.md:** current entry point. It supersedes the older OS-27-oriented overview.
- **LinkedIn:** [Professional profile](https://www.linkedin.com/in/gyodragos/).


## Hosted demo and runtime prerequisites

The public portfolio is a static GitHub Pages site. Its session panel is a scripted, operator-triggered replay with illustrative events; it does not start commands, connect to the local MCP endpoint, run a test suite or prove that recovery occurred. The replay remains idle until the visitor selects **Play**.

The site now shows local readiness gates explicitly: the intended checkout and Python environment, a reachable loopback MCP service, the selected access profile and approval policy, a permitted diagnostic target, and evidence from a real controlled test. These items are **not checked by the public page**.

The project includes Frida/MITM-oriented diagnostic paths for controlled failure visibility, but an active target hook, proxy interception or end-to-end diagnostic result is not implied by the portfolio. Such work remains dependent on a configured, authorized target and verifiable local evidence.

## OS-28 evidence on record

The final local report from 19 October records:

- Full maintained test suite: 324 passed and one explicitly skipped check.
- The skip depended on an authentication environment value that was unavailable in that invocation; the report records that the authenticated rerun passed.
- Main MCP catalog: 127 tool names.
- Restricted GPT-only profile: 14 tools with operation/path policy v2.

**Interpretation:** a catalog count is not an operational pass for each tool. The restricted profile is not a claim that a complete identity-by-operation authorization matrix is finished.

## OS-29 evidence on record

The local companion status and completion report record:

- 37 tests passed.
- 14 tools exposed through its separate MCP STDIO interface.
- 375 documents in the local SQLite FTS5/BM25 lexical index at the recorded checkpoint.
- A successful OS-28 → OS-29 end-to-end checkpoint with three linked persisted events and a subsequent memory search that retrieved both the validation event and the follow-up triage decision.

**Current boundary:** OS-29 lives in a separate local workspace on the development PC. Its code is not yet published in this GitHub repository. The current memory path is lexical; vector embeddings, reranking and the full 30-module roadmap are not claimed as complete.

## Repository organization — conservative pass

The repository includes the main ANA_MAX tree, mcp/, launchers/, docs/, scripts/, web assets and historical/experimental folders. The source tree has accumulated substantial history and legacy material.

This pass improves the public entry point and adds a status reference. It intentionally does **not** bulk-move, rename or delete implementation files. Before changing paths, classify import relationships, launcher references, tests and historical Git deletions, then move only what can be verified safe.

## Next acceptance gates

1. Finish a per-tool, per-operation authorization matrix and a verifiable approval context before exposing wider write operations.
2. Improve OS-29 retrieval only with measured evaluations, redaction tests and source-linked evidence.
3. Complete a real, scoped issue → fix → retest → human-reviewed validation sequence before promoting a candidate lesson.
4. Publish the OS-29 source only after its boundaries, dependencies, README, tests and public disclosure have been reviewed.
5. Reorganize legacy source and documentation incrementally, with a file map and rollback reference for each batch.
