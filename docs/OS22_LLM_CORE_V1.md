# OS-22 LLM Core v1

## Overview

OS-22 LLM Core is the local, ASCII-safe, manifest-driven layer that turns
`LocalLLMBackend` and `LocalBrainAgent` into a small agent stack:

1. profile layer
2. prompt engine
3. RAG bridge
4. tool bridge
5. local LLM backend
6. local brain agent

The implementation stays local-only, optional, and compatible with the current
OS-21.5 baseline.

## Layers

### Profile Layer

`ANA_MAX/local/prompt_profiles.py`

- `default`
- `lab`
- `phi3_lab`
- `codex`
- `lab_pentest`
- `pentest_lab`

Profiles define tone and work style only. Tool awareness comes from the tool
manifest, not from the profile text.

### Prompt Engine

`ANA_MAX/local/prompt_engine.py`

- Combines a profile prompt with manifest-backed tool specs.
- Injects RAG context when present.
- Emits the `TOOL_CALL: <tool_name> <json_arguments>` instruction block.

### RAG Bridge

`ANA_MAX/local/rag_bridge.py`

- Read-only retrieval helper.
- Builds context from the local semantic memory store.
- Does not execute tools or mutate runtime state.

### Tool Bridge

`ANA_MAX/tools/tool_manifest.json`
`ANA_MAX/tools/tool_manifest_loader.py`
`ANA_MAX/local/tool_dispatcher.py`
`ANA_MAX/local/tool_telemetry.py`

- Manifest is the source of truth for tool names, schemas, and categories.
- Dispatcher parses `TOOL_CALL` and executes local tools.
- Telemetry is append-only JSONL and never blocks inference.
- Web Learning tools are manifest-driven:
  - `web_scrape` fetches http/https pages and extracts bounded clean text.
  - `rag_store_text` stores source-tagged chunks through `RAGBridge`.

### Local LLM Backend

`ANA_MAX/local/local_llm_backend.py`

- Loads optional local backends only on demand.
- Keeps `infer()` and `infer_with_rag()` deterministic and local-only.
- Injects manifest tool specs when the caller does not provide an override.

### Local Brain Agent

`ANA_MAX/agents/local_brain_agent.py`

- Builds reasoning capsules and optional plans.
- Detects `TOOL_CALL` responses and sends a bounded follow-up prompt.
- Preserves metadata-only fallback behavior when inference is unavailable.
- The interactive launcher exposes `/time`, `/tool`, `/open`, and `/rag` for
  deterministic ToolBridge and RAG checks without relying on model behavior.

### Boot Sequence

`ANA_MAX/local/os22_boot.py`
`ANA_MAX/local/agent_boot_banner.py`
`ANA_MAX/local/agent_foundation.py`
`ANA_MAX/local/agent_self_healing.py`

- Builds a deterministic boot and health report for the local brain stack.
- Checks backend metadata, prompt engine availability, RAG readiness, tool
  bridge readiness, and agent metadata.
- Can write `ANA_MAX/memory/os22_boot_report.json` without loading the model.
- Provides the interactive ASCII boot banner used by the local agent launcher.
- Reports the unified agent foundation readiness status.
- Reports metadata-only self-healing diagnostic readiness.

### Doctor

`ANA_MAX/local/os22_doctor.py`

- Runs launch readiness checks without loading the model.
- Verifies boot, foundation, self-healing, Web Learning tools, diagnostics,
  RAG conflict handling, stabilizer behavior, and preflight metadata.
- The interactive launcher exposes `/doctor`.

### Agent Operating Pack

The agent onboarding and runtime education pack lives in:

```text
docs/OS22_AGENT_OPERATING_PACK.md
```

The unified foundation document lives in:

```text
docs/OS22_AGENT_FOUNDATION.md
```

## Flow

```text
User prompt
  -> LocalBrainAgent.run_turn()
  -> LocalLLMBackend.infer_with_rag()
  -> PromptEngine(profile + manifest + RAG)
  -> LLM
  -> TOOL_CALL?
       -> yes: ToolDispatcher + Telemetry + bounded follow-up
       -> no: final answer
```

## Web Learning Flow

```text
User approved URL
  -> web_scrape
  -> rag_store_text
  -> RAGBridge / VectorMemoryCortex
  -> future retrieval through infer_with_rag
```

## Validation

- `python -m compileall -q ANA_MAX`
- `python -m pytest tests/test_os22_boot_sequence.py -q`
- `python -m pytest tests/test_tool_manifest_loader.py tests/test_prompt_engine.py tests/test_tool_dispatcher.py tests/test_local_brain_agent_tool_bridge.py -q`
- `python -m pytest tests/test_local_llm_backend.py tests/test_local_llm_integration.py tests/test_local_llm_rag_integration.py -q`

## Notes

- No cloud calls.
- No model load during import.
- No OS-21.5 baseline drift.
- Tool awareness stays additive and manifest-driven.
