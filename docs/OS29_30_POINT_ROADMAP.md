# OS29 blueprint-to-implementation roadmap — 30 numbered modules

| # | Master plan module | OS29 status | Evidence / gap |
|---:|---|---|---|
| 1 | Memory of Failure / REM | Partial | Recurring failure signatures; synthetic data excluded. Long-term consolidation and measured memory reuse remain open. |
| 2 | Agent Evolution | Guarded foundation | Suggestions can be produced; no unattended self-change. |
| 3 | Skill Distillation | Partial | Uses repeated validated experiences only; no real validated lesson yet. |
| 4 | Self-Building System | Guarded foundation | Suggestions only; no automatic source/policy mutation. |
| 5 | Agent Reputation / Agent DNA | Partial | Explicit agent labels and minimum evidence thresholds; no identities/scores inferred without telemetry. |
| 6 | Future Simulator | Partial | Temporal Branching proposes falsifiable experiments; no execution engine or validated simulator. |
| 7 | Regret Engine | Partial | Recurrent unvalidated failures become review candidates; regret score stays null without cost/avoidability evidence. |
| 8 | Discovery Engine | Partial | Lists offline/degraded components, graph orphans and binding risks with read-only recommendations. |
| 9 | Digital Immune System | Partial | Detects sanitized scope denials, recurrent failures and wildcard bindings; no automated containment/repair. |
| 10 | Temporal Branching | Partial | Proposed experiment/falsifier records, explicitly not executed. |
| 11 | Resource-Aware Cognition / Cognitive Resource Manager | Observation only | CPU/RAM/disk pressure is read-only; no automatic scheduling, GPU measurement or service starts. |
| 12 | Agent Gateway | Present | Narrow MCP stdio and optional authenticated loopback HTTP API; HTTP API not running by default. |
| 13 | Mission Capsule Engine | Present | SQLite persistence and file/database round-trip; capsule stores next steps and open issues. |
| 14 | Memory Cortex | Partial — lexical retrieval present | SQLite FTS5/BM25 searches trace summaries, incidents, capsules, experiences, capability labels and explicitly approved local text sources. No vector embeddings yet. |
| 15 | Experience Engine | Partial | Candidate and validated states with linked test evidence plus interactive operator confirmation; no real validated retest yet. |
| 16 | Context System | Partial | Mission capsule and retrieval state persist locally; context injection into all external agents is not connected. |
| 17 | RAG System | Lexical baseline present | Local indexed retrieval works through CLI and MCP. Semantic embeddings, reranking and model-mediated answer generation remain pending. |
| 18 | NetLab | Foundation present | Scope policy plus metadata-only MITM trace. Broader network DNA/TLS/API coverage and long-running isolated proxy remain pending. |
| 19 | Network DNA | Pending | No trained/validated network behavior profile. |
| 20 | Frida Fusion | Foundation present | Exact device/process allowlists and metadata-only hook script; no test target attached, so no live app attach. |
| 21 | Capability Graph | Present | 327 nodes/645 edges, including profile/tool-instance/process/port/service relationships. |
| 22 | World Model | Foundation present | Read-only loopback snapshot and capability state; not a comprehensive environment simulator. |
| 23 | Error Radar | Partial | Unified report groups observed failure signatures; no continuous watcher/service. |
| 24 | Root Cause Cortex | Foundation present | Parent lineage plus incident evidence; causal claims remain unverified without independent reproduction. |
| 25 | Causal Trace Engine | Present baseline | os29.trace.v1, trace ID/event ID/parent IDs and persisted lineage; no automatic cross-process propagation except shared test trace ID. |
| 26 | Live Error Graph | Partial | Graph structures and text report; no live interactive dashboard/streaming UI. |
| 27 | Knowledge Compression | Partial | Summary reports and bounded evidence; no periodic large-log compression/retention pipeline. |
| 28 | Operator Layer | Foundation present | Separate project/capsule and interactive validation; broader operator preference profile is not implemented. |
| 29 | Security Principle / fail closed | Present baseline | Loopback defaults, strict host/port scope, empty Frida allowlists, auth API, redaction and size limits; not a Windows OS sandbox. |
| 30 | Absolute Priority: first ten components as one brain | Partial | Capability graph, capsule, trace, diagnosis, experience, world model, agent evidence, REM, Regret, Discovery and lexical retrieval share one store/report. Real Frida-to-HTTP-to-fix/retest-to-validated-memory remains the acceptance gate. |

## Latest evidence checkpoint

- Full suite: 37 passed; compilation and Frida JavaScript syntax checks passed.
- OS29 stdio MCP: 14 tools; live memory-search request returned three relevant indexed documents.
- Local index: 351 documents (327 capability nodes, 8 events, 2 capsules, 1 experience, 1 incident and 12 document chunks).
- Search backend is SQLite FTS5/BM25; semantic/vector RAG is explicitly not marked complete.

## Next acceptance gate

One authorized test app/device must run a harmless metadata-only Frida hook whose method trace shares a test trace ID with one local MITM request/response; create a controlled failure, apply a fix, then explicitly validate and retrieve the experience in a later session. Until this is measured, the vertical slice works but OS29's full cross-agent "one brain" goal is not yet proven.
