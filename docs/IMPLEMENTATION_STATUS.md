# OS29 implementation status

**Last recorded local baseline:** 19 October 2026  
**Publication model:** source and tests are versioned; runtime stores and operator-specific target configuration stay local.

## Working foundation

- Canonical `os29.trace.v1` event model with trace/parent lineage and validated fields.
- Redaction before persistence, bounded JSON/text sizes and URL normalization.
- Loopback-first network target policy with default-deny behavior.
- SQLite persistence for events, incidents, mission capsules, capabilities and experiences.
- Evidence-first diagnosis that keeps causal hypotheses separate from verified causes.
- A bounded MCP STDIO interface and an optional authenticated loopback HTTP gateway.
- Local SQLite FTS5/BM25 retrieval over explicitly approved sources; this is lexical retrieval, not semantic/vector RAG.

## Recorded local evidence

- OS29 suite: **37 passed** in the recorded local run on 19 October 2026.
- MCP STDIO companion: **14 tools** in the recorded catalog; initialize/list and memory-search smoke tests passed.
- Local retrieval index: **375 documents** at the recorded checkpoint.
- Validated experiences: **0** at that checkpoint. Candidate evidence is not treated as a verified lesson.
- Python compilation and the Frida JavaScript syntax check were reported as passing.

These figures are baseline evidence, not current live counters. GitHub Actions independently retests the published source.

## Explicitly incomplete

- Semantic/vector embeddings, reranking and a model-mediated reasoning loop.
- A real authorized Frida-to-MITM application trace followed by a measured fix/retest.
- A real experience promoted after linked validation evidence and retrieved in a later session.
- SQLite encryption at rest; redaction is defense in depth, not a perfect secret/PII detector.
- Production completion of all 30 roadmap modules or a comprehensive environment simulator.

## Publication hygiene

The public tree intentionally excludes SQLite databases, log files, caches, browser profiles, local environment files, private MCP client configuration, machine-specific memory-source paths and raw runtime artifacts. Use the example MCP client configuration and opt in local sources deliberately.
