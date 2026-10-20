# OS29 local memory retrieval

OS29 uses SQLite FTS5 with BM25 ranking for persistent cross-session retrieval. This is a lexical retrieval baseline, not semantic/vector embeddings and not an LLM answer-generation loop.

## Sources

The index refreshes from the OS29 SQLite store:
- Trace-event summaries, using a field allowlist.
- Incidents, with unverified causes labeled as hypotheses.
- Mission capsules, limited to mission-relevant summary fields.
- Experiences, with candidate records excluded by default and rejected records always excluded.
- Capability/world-model labels and statuses.
- Explicit local text sources listed in config/memory_sources.json: the master blueprint, OS28 journal/handoff files, GPT-only project state, OS29 README and OS29 Markdown documentation.

File intake is restricted to configured paths and extensions .md, .txt and .rst. It does not fetch from the network or crawl the home directory. Limits are 512 KiB per file, 8 MiB combined source bytes and 200 files. Text is chunked and redacted before it is stored. HTTP request/response bodies are not indexed.

## Commands

Run from the OS29 project root:

```powershell
python -m os29.cli memory-index
python -m os29.cli memory-search "Frida MITM" --limit 10
python -m os29.cli memory-search "mission capsule" --source-type capsule
python -m os29.cli memory-search "ReadTimeout" --source-type event --source-type incident
python -m os29.cli memory-search "retry timeout" --source-type experience --include-candidates
python scripts\verify_mcp_memory_live.py
```

The same search is exposed in MCP as os29_memory_search. Each query refreshes the index by default. Results include source type/reference, trust status, excerpt, metadata and BM25 relevance score.

## Security and trust semantics

- Query terms are quoted before FTS search so input is not interpreted as FTS query syntax.
- Candidate experiences stay labeled as candidates and do not count as validated skills. Rejected experiences are always filtered.
- No remote services, optional OS28 services or local inference models are started.
- SQLite files are not encrypted at rest. Redaction is defense in depth, not a complete secret detector.
- Only lexical ranking is available today. Embeddings, semantic similarity, reranking and model-mediated reasoning remain future work.

## Recorded local verification snapshot — 2026-10-19

The figures below are historical evidence from the local workstation, not live counters from this public repository.

- SQLite FTS5 was available in the active Python runtime.
- Full suite: 37 passed in 2.94 seconds; compilation and Frida JavaScript syntax checks passed.
- Tests cover cross-source search, candidate filtering, secret omission, explicit-file allowlisting, incremental update, stale-document deletion and input validation.
- Live local index: 351 documents — 327 capabilities, 8 events, 2 capsules, 1 experience, 1 incident and 12 local-document chunks.
- Live MCP STDIO child process: initialize PASS, 14 tools, memory-search request PASS with three document results; stderr empty.
- CLI search for Frida/MITM returned relevant OS29 integration and handoff documents. A second refresh reported all indexed documents unchanged.
