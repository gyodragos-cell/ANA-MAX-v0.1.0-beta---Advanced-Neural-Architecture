# Local LLM Backend v1

## Overview

`ANA_MAX/local/local_llm_backend.py` adds an optional local brain adapter for
OS-21.5. It targets Phi-3 Medium as the primary local model and Phi-3 Mini as
the fallback model through an optional Python backend named `ollm`.

In the current lab configuration, the default active backend is `llama_cpp`
with Phi-3 Mini on CPU. `ollm` still remains supported as an optional backend
for older or alternate local setups.

The backend is not required for ANA MAX to start, import, or pass tests.

## Design

- Backend schema: `ana.os21.local_llm_backend.v1`
- Primary model: `phi3-medium`
- Fallback model: `phi3-mini`
- Backend module: `llama_cpp` by default, `ollm` still supported
- Default device: `cpu`
- Import behavior: no `ollm` import at package import time
- Load behavior: model loading happens only through `load_model()` or `infer()`

## Integration

- `LocalLLMBackend.infer_with_rag()` can inject retrieved memory context and
  a manifest-driven tool-awareness block into the prompt while leaving
  `infer()` unchanged.
- `LocalBrainAgent` builds reasoning capsule metadata and can optionally call
  `LocalLLMBackend` with RAG context and tool prompts when inference is
  explicitly enabled.
- `PipelineReasoningHelper` attaches local-brain planning and reflection hints
  to pipeline metadata without changing distributed pipeline behavior.
- Both helpers default to deterministic fallback metadata when `ollm` is absent.

## OS-22 Tool Bridge Core

OS-22 adds a manifest-driven local tool bridge without changing the OS-21.5
baseline:

- `ANA_MAX/tools/tool_manifest.json` defines the source of truth for tool names
  and schemas.
- `ANA_MAX/tools/tool_manifest_loader.py` loads the manifest and falls back to
  a safe built-in manifest when needed.
- `ANA_MAX/local/prompt_engine.py` composes the final prompt from profile text,
  tool specs, and retrieved context.
- `ANA_MAX/local/tool_dispatcher.py` parses `TOOL_CALL` and executes local
  tools.
- `ANA_MAX/local/tool_telemetry.py` records append-only JSONL telemetry for
  later review.
- `LocalBrainAgent.run_turn()` performs a bounded tool-follow-up loop when the
  model requests a tool.

## Safety

- No cloud calls.
- No secrets.
- No hardcoded local paths.
- No runtime behavior changes for OS-20.1 or OS-21.
- No model load during import.
- No tool execution or pipeline mutation.

## Dual Python Setup

ANA MAX keeps Python 3.12 as the main OS-21.5 development interpreter. The
optional local brain can use a separate Python 3.11 environment at
`local_llm_env/` for OLLM and local model work.

Setup helpers live under:

```text
scripts/local_llm/
```

The helper scripts are dry-run by default. Use `--apply` only when intentionally
creating the environment, installing OLLM, or copying/downloading a model file.

Current stable local model flow:

- `scripts\local_llm\start_local_llm.bat` opens the interactive chat loop.
- `scripts\local_llm\rebuild_local_llm_stack.bat` reruns install, validate, and
  smoke checks in one pass.
- The default `.env.local_llm` points to `local_models/phi3-mini-q5_k_m.gguf`.

## Prompt Profiles

The local launcher and local brain helper support prompt profiles:

- `default`: concise, practical, deterministic
- `lab`: more direct and adaptable for offline debugging and white-hat testing
- `phi3_lab`: concise Phi-3 lab profile for code-first local work
- `codex`: senior runtime-engineer profile for concrete diffs and architecture
- `lab_pentest`: explicit local lab prompt surface for test and debug flows
- `pentest_lab`: alias profile for local lab pentest-style testing

Use `lab` when you want a less verbose local assistant while keeping the
project's safety boundaries for destructive or harmful actions.

See `docs/LOCAL_LLM_SETUP_V1.md` for the full flow.

## Manual usage

```text
python -m ANA_MAX.local.local_llm_backend --info
python -m ANA_MAX.agents.local_brain_agent --summary
python -m ANA_MAX.distributed.pipeline_reasoning_helper --summary
```

These commands print JSON metadata. If `ollm` is missing, the backend reports
`available=false` and ANA MAX continues normally.
