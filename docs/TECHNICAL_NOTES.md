# Technical Notes

## OS-22 Desktop Inventory Tool

- `scripts\run_evolution_maintenance.bat` is the maintained local evolution launcher. Modes: `check` validates wiring only, `fast` runs fast-parallel evolution plus OS-22 audit, `cycle` runs the old sequential cycle, `os5` enables the OS-5 layer, and `audit` runs only the OS-22 launch audit.
- Desktop `C:\Users\billy\Desktop\run_evolution.bat` and `C:\Users\billy\Desktop\ANA MAX Evolution Maintenance.bat` are thin wrappers that call `scripts\run_evolution_maintenance.bat fast` and pause for review.
- Evolution maintenance is not the chat launcher; interactive ANA/Phi-3 chat still starts through the OS-22 chat launcher.
- `web_learn_course()` exposes schema `ana.os22.web_learn_course.v1` and performs bounded breadth-first learning over same-domain pages while staying under the start URL path prefix, such as `/php` for `https://www.w3schools.com/php/`.
- Course learning preserves tutorial link priority: home/default and `php_*` lesson pages are preferred over reference/function pages, preventing early drift into API reference noise.
- Course text extraction prefers the page `id=main` content and strips W3Schools-style HTML comment noise before summary and RAG storage.
- `write_desktop_text_file()` exposes schema `ana.os22.desktop_write_text_file.v1`, writes ASCII-safe `.md` text on Desktop, and creates timestamped `.bak` files on overwrite.
- The combined router intent handles browser-open + course learning + Desktop notes + RAG storage in one deterministic pipeline for prompts that mention a URL, web scrape/extract/learn, Desktop save, and file name.
- `ANA_MAX/tools/desktop_workspace.py` exposes `list_desktop_items()` with schema `ana.os22.desktop_inventory.v1`.
- The tool is metadata-only: it returns names, paths, item type, extension, file size, child count, and UTC modified time, but never reads file contents.
- The default router call uses `max_items=80` and `include_hidden=false` for safe chat output.
- `inspect_desktop_folder()` exposes schema `ana.os22.desktop_folder_inspection.v1` for one Desktop folder at a time.
- `read_desktop_text_file()` exposes schema `ana.os22.desktop_text_file.v1` and reads only allowed text/code extensions with bounded output.
- `ANA_MAX/tools/web_learning.py` exposes `web_learn_url()` with schema `ana.os22.web_learn_url.v1`; it calls `web_scrape()`, summarizes the page text, and stores chunks through `rag_store_text()`.
- `desktop_list_items`, `desktop_inspect_folder`, `desktop_read_text_file`, `desktop_write_text_file`, `web_learn_url`, and `web_learn_course` are available through ToolBridge, the tool manifest, dynamic prompt policy, and the operator intent router.
- `desktop_list_items` declares `required_args=[]`, while `desktop_inspect_folder` declares `required_args=["folder_name"]`; self-healing uses those fields to avoid false missing-argument warnings.
- `desktop_read_text_file` declares `required_args=["file_name"]`; `desktop_write_text_file` declares `required_args=["file_name", "content"]`; `web_learn_url` declares `required_args=["url"]`; `web_learn_course` declares `required_args=["start_url"]`.
- Prompts like `ce am pe desktop`, `listeaza tot ce am pe desktop`, and `ce fisiere am pe desktop` are handled deterministically before model inference.
- Prompts like `intra in folderul ana_dev de pe desktop si listeaza ce e acolo` are routed to `desktop_inspect_folder`.
- Prompts like `citeste fisierul script.py din folderul vasile de pe desktop` are routed to `desktop_read_text_file`.
- Prompts like `intra pe linkul https://example.com si invata tot ce este important` are routed to `web_learn_url`.
- `OS22Doctor` now checks `desktop_visibility_tools` and `content_learning_tools`, confirming all visibility and learning tools exist and self-healing diagnostics accept their valid argument shapes.
- This keeps Phi-3 Medium as the local reasoning brain while ANA provides real local filesystem visibility under the hood.

## OS-22 Launch Readiness Audit

- `scripts/os22/os22_launch_audit.py` is metadata-only and does not load the LLM model.
- The launch audit checks the main Python 3.12 runtime, `local_llm_env` Python 3.11 runtime, required local LLM imports, `.env.local_llm`, GGUF model presence, launch scripts, OS-22 doctor, OS-22 boot, and optional focused tests.
- Optional items such as `bs4` and `ANA_LOCAL_LLM_ENABLED=0` are reported as notes, not warnings, because they do not block launch.
- `bs4` is treated as optional because the active OS-22 `web_scrape` wrapper uses standard-library HTML extraction; `beautifulsoup4` is only needed for legacy `WebScraperTool` parse/extract operations.
- `ANA_LOCAL_LLM_ENABLED=0` is allowed because explicit CLI launch scripts pass backend/model configuration and keep the default OS-20.1 runtime unchanged.
- `scripts/os22/start_os22_lab_chat.bat` starts OS/tools readiness checks in one window and `scripts/os22/start_os22_agent.bat` in a separate chat-only window.
- The OS-22 launcher also opens `ANA MAX OS22 LIVE LOG`, tailing `ANA_MAX/logs/os22_chat.log` and `ANA_MAX/local/tool_telemetry.log`.
- `scripts/os22/start_os22_agent.bat` now uses the `ana_chat` profile for natural operator conversation. Strict deterministic mode remains available through `scripts/os22/start_os22_core_agent.bat`.
- The old Ollama-backed HTTP server is no longer started by default from the OS-22 launcher; it remains available with `--legacy-server`.
- `LocalBrainAgent.run_turn()` now short-circuits identity prompts before model inference. This keeps the chat responsive when Phi-3 Mini over-applies the strict `TOOL_CALL` contract to greetings.
- Malformed model `TOOL_CALL` output is surfaced as an explicit `Invalid tool call` message instead of raising through the interactive loop and printing a blank turn.
- Romanian date/time prompts such as `ce zi este azi` are routed directly to the local `current_time` tool, reducing Phi-3 uncertainty and latency.
- `ana_chat` now instructs Phi-3 Mini to avoid pseudo-calls like `ANA_MAX: tool(...)`; if such output still appears, `LocalBrainAgent` runs one deterministic natural-answer repair prompt before showing a fallback error.
- Romanian current-fact prompt `cine este presedintele romaniei?` is handled as a local deterministic shortcut so the chat answers directly instead of storing the question in RAG.
- Tool-inventory prompts such as `cate tooluri ai?` are handled directly from `ANA_MAX/tools/tool_manifest.json`, avoiding invalid model-generated `TOOL_CALL` fragments and making the ANA/Phi-3 split clear to the operator.
- `ana_chat` is now the conversational layer, not the strict runtime layer. It keeps the same ToolBridge contract but uses a shorter natural-language system prompt and same-language replies.
- `scripts/os22/start_os22_agent.bat` launches `ana_chat` with `--temperature 0.40`; `LocalBrainAgent` now forwards launcher `max_tokens` and `temperature` into initial chat turns while repair/tool follow-up turns stay deterministic.
- Simple greetings and capability prompts are handled by the local router before model inference, reducing latency and avoiding small-model drift on common chat turns.
- Final `ana_chat` calibration uses a Romanian ASCII system prompt and launcher temperature `0.40`; live smoke showed `0.55` increased drift for vague Romanian prompts.
- `_ascii_text()` now transliterates Unicode to ASCII instead of replacing characters with `?`, keeping terminal output readable when Phi-3 emits Romanian diacritics.
- Capability prompts run before date/time prompts so `ce poti face pentru mine azi?` is not misrouted to `current_time`.
- Vague explanation prompts such as `explica-mi ceva simplu` ask for a subject instead of letting the small model hallucinate a long mixed-language answer.
- `ANA_MAX/local/operator_intent_router.py` now runs before shortcut routing and model inference for high-confidence operator intents. It is intentionally narrow: it handles collaboration setup, clean RAG explanations, and explicit Desktop Python script creation requests.
- The operator intent router is the practical ANA orchestration layer for small-model reliability: Phi-3 remains the local reasoning brain, while ANA selects deterministic tools when the user asks for concrete local actions.
- `desktop_create_python_script` is a ToolBridge tool backed by `ANA_MAX/tools/desktop_workspace.py`. It writes only under the Desktop root, sanitizes folder/script names to ASCII-safe values, creates `.py` suffixes deterministically, and backs up changed existing files before overwrite.
- Tool inventory now reports 11 OS-22 ToolBridge tools after adding `desktop_create_python_script`; historical logs may still show 10 tools from the earlier launch stage.
- `ana_chat` is now model-first for normal conversation. The operator intent router is restricted to concrete local actions such as explicit Desktop Python script creation, not general explanation or collaboration prompts.
- `ANA_MAX/local/conversation_context.py` provides compact in-process conversation memory. Interactive chat passes the last turns into `LocalBrainAgent.run_turn()` so Phi-3 has continuity similar to a real chat session.
- `ANA_MAX/local/tool_prompt_policy.py` exposes only relevant ToolBridge contracts for the current prompt. Normal chat such as `ce este RAG` receives no tool list, preventing accidental `vector_store` or `current_time` calls.
- `ANA_MAX/local/rag_prompt_policy.py` prevents RAG retrieval from casual greetings or teamwork prompts while still allowing RAG for project, code, memory, log, test, and ToolBridge questions.
- `ANA_MAX/local/chat_response_coach.py` validates visible `ana_chat` output and repairs known small-model failure modes: mojibake-style question marks, translation drift, irrelevant date/time leakage, and unknown-tool leakage.
- `scripts/os22/start_os22_agent.bat` now launches `ana_chat` at `--temperature 0.25` and `--max-tokens 192`; live smoke showed this is more stable than the previous chat setting.

## OS-22 Web Learning And Launch Doctor

- `web_scrape` is an explicit OS-22 wrapper over web text extraction. It accepts only `http` and `https`, strips HTML/script/style content, and returns schema `ana.os22.web_scrape.v1`.
- `rag_store_text` stores text through `RAGBridge.ingest_text()` with source metadata and deterministic chunking.
- `ToolDispatcher` returns JSON for both Web Learning tools, keeping `TOOL_CALL` follow-up prompts machine-readable.
- `parse_tool_call()` accepts the live Phi-3 compact form `TOOL_CALL: current_time{}` in addition to the canonical spaced JSON form.
- `OS22Doctor` is metadata-only and does not load the LLM model. It verifies boot, foundation, self-healing, Web Learning tool visibility, diagnostic behavior, RAG conflict handling, stabilizer behavior, and preflight metadata.
- `/doctor` is available in `scripts/local_llm/start_local_llm.py` for quick launch readiness checks before talking to the local agent.

## OS-22 Self-Healing V2 And Autonomy V3

- `ANA_MAX/local/agent_self_healing.py` is metadata-only and never executes tools or mutates files.
- `diagnose_tool_request()` checks manifest membership, required arguments, and workspace path safety.
- `resolve_rag_conflicts()` ranks RAG candidates by importance, score, timestamp, and content, then reports conflicts without inventing merged facts.
- `diagnose_rag_context()` adds empty, irrelevant, too-long, duplicate, and conflicting context checks before an answer uses retrieved memory.
- `classify_text_issue()` detects overlong answers and multiple tool calls.
- `stabilize_reasoning_text()` compresses unstable or overlong output into a compact OS-22-safe answer.
- `preflight_diagnostics()` aggregates tool, RAG, and text diagnostics before execution.
- Self-healing events are best-effort JSONL telemetry under `ANA_MAX/logs/self_healing_telemetry.jsonl`; telemetry failures never block runtime execution.
- The interactive launcher exposes `/heal`, `/heal <tool> [json_args]`, `/ragheal <query>`, and `/stabilize <text>` for local diagnostics.
- Autonomy V3 remains bounded: no tool creation, no manifest edits, no architecture mutation, no internet, no external paths, and no persona switching.
- `pytest.ini` now limits default collection to `tests/`, while `tests/conftest.py` quarantines legacy/service tests unless `ANA_INCLUDE_LEGACY_TESTS=1` is set.
- `scripts/run_legacy_tests.ps1` provides the explicit opt-in path for old tests that require legacy `core.*` modules, public release artifacts, local MCP/Ollama services, VSCode files, or import-time side effects.

## OS-22 Operational Mastery Layer

- The operational mastery layer is documentation and test-design material, not default prompt payload.
- `OS22_AGENT_SANDBOX_SCENARIOS.md` provides 20 deterministic training scenarios for tool calls, RAG conflicts, safety, boot, foundation, and stress behavior.
- `OS22_AGENT_MASTER_CLASS.md` provides self-diagnostic, self-profiling, ToolBridge audit, RAG quality, recovery, and Phi-3 Mini optimization guidance.
- `OS22_AGENT_AUTONOMY_V1.md` defines bounded autonomy without allowing tool creation, manifest mutation, architecture mutation, internet access, external file access, or persona switching.

## OS-22 Advanced Agent Training

- `docs/OS22_AGENT_ADVANCED_TRAINING.md` is documentation-only and is not injected into every prompt, preserving Phi-3 Mini context budget.
- `ANA_MAX/local/agent_foundation.py` treats the advanced training document as part of the required foundation pack.
- The advanced modules define deterministic reasoning, self-correction, tool chaining, RAG interpretation, failure recovery, telemetry awareness, safety discipline, precision answering, context compression, ToolBridge optimization, reasoning graph mastery, and professional workflow.

## OS-22 Unified Agent Foundation

- `docs/OS22_AGENT_FOUNDATION.md` is the unified durable training document for local OS-22 agents.
- `ANA_MAX/local/agent_foundation.py` exposes metadata-only helpers: `load_agent_foundation()`, `summarize_agent_foundation()`, and `get_agent_foundation_status()`.
- `OS22BootSequence` includes `agent_foundation` readiness and validation now reports `agent_foundation_unavailable` if the pack is incomplete.
- The interactive launcher exposes `/foundation` for fast inspection without loading the whole document into the runtime prompt.

## OS-22 Agent Operating Pack

- `docs/OS22_AGENT_OPERATING_PACK.md` is the index for the OS-22 agent onboarding and runtime education docs.
- `ANA_MAX/local/agent_boot_banner.py` builds the startup banner from backend metadata and the OS-22 boot report.
- `scripts/local_llm/start_local_llm.py` prints the banner in interactive mode unless `--no-banner` is supplied.
- The banner is ASCII-only and reports RAGBridge, ToolBridge, VectorMemoryCortex, Reasoning Graph, Telemetry Stream, and LocalBrainAgent status.

## OS-22 Codex Profile Refresh

- `ANA_MAX/local/prompt_profiles.py` keeps `codex` as the long engineering profile and `os22_core` as the compact deterministic runtime profile.
- The refreshed `codex` profile explicitly covers Phi-3 Mini GGUF Q5_K_M, `llama_cpp`, RAGBridge, VectorMemoryCortex, ToolBridge, LocalBrainAgent, reasoning graph, and boot sequence work.
- The prompt is ASCII-only and avoids mojibake sequences from pasted rich text.

## OS-22 Interactive Tool Debug Commands

- `scripts/local_llm/start_local_llm.py` now supports slash commands for deterministic local diagnostics:
  `/time`, `/tool <name> [json_args]`, `/open <url>`, and `/rag <query>`.
- These commands execute through the same `ToolDispatcher` and `RAGBridge` modules used by the agent loop, but bypass model inference for faster debugging.
- Normal non-command input still flows through `LocalBrainAgent.run_turn()` with RAG and ToolBridge follow-up enabled.

## OS-22 Live Tool Smoke Notes

- `current_time` is a no-argument system tool exposed through `ANA_MAX/tools/tool_manifest.json` and handled by `ANA_MAX/local/tool_dispatcher.py`.
- `parse_tool_call()` accepts both canonical JSON calls and no-argument calls emitted as `TOOL_CALL: tool_name`; this prevents live model output from failing when a tool has an empty argument schema.
- `BrowserControlTool._normalize_url()` accepts workspace-local `file://` URLs and rejects file URLs outside the workspace boundary.
- The real Phi-3 Mini smoke path now confirms `current_time` and `open_browser` through `LocalBrainAgent.run_turn()`, not only direct dispatcher calls.

## OS-22 Embedded Tool Call Recovery

- `ANA_MAX/local/tool_dispatcher.py` now parses both the canonical tool-call contract and the JSON-object form that the live Phi-3 Mini occasionally emits.
- `ANA_MAX/agents/local_brain_agent.py` scans each model response for the first `TOOL_CALL` line anywhere in the text, so embedded tool calls are recovered instead of leaked into the final answer.
- The follow-up path still keeps the original user prompt and tool result together, but now the runtime can recover from multi-line or partially noisy model outputs.

## OS-22 Tool Follow-Up Tightening

- `ANA_MAX/agents/local_brain_agent.py` now builds a structured follow-up prompt that includes the original user request, the executed tool call, and the tool result before the second inference pass.
- The follow-up pass uses a smaller token budget and tells Phi-3 to return a final answer only, which reduces the chance of plan-like or tool-like noise after a tool result.
- The regression test now checks that the second prompt contains the original request and the tool result together.

## OS-22 Profile Split

- `ANA_MAX/local/prompt_profiles.py` now carries a compact `os22_core` profile for Phi-3 Mini runtime execution and a longer `codex` profile for engineering work.
- The OS-22 smoke runner now defaults to `os22_core`, which keeps the deterministic runtime path short while preserving `codex` for architecture and debugging sessions.
- The profile split keeps the `TOOL_CALL` contract and RAG expectations intact while reducing prompt size for runtime inference.
- The smoke runner default `n_ctx` was raised to `4096` after the live GGUF run proved stable at the model's training context and removed the llama.cpp capacity warning.

## OS-22 Boot and Health Check

- `ANA_MAX/local/os22_boot.py` builds a deterministic, metadata-only boot
  report for the local LLM core.
- The boot sequence checks prompt engine, RAG bridge, tool bridge, backend
  metadata, and agent metadata without loading a model at import time.
- The default boot report can be written to
  `ANA_MAX/memory/os22_boot_report.json`.
- `health_score` is a metadata score, not a runtime benchmark, and is safe to
  compute when the optional backend is unavailable.

## RAG Legacy Store Compatibility

- `ANA_MAX/core/vector_memory.py` now supports both the current `tags_json` /
  `metadata_json` layout and the older `tags` / `metadata` SQLite layout found
  in the live lab database.
- The compatibility layer keeps `RAGBridge.get_status()` and `VectorMemory`
  queries working against the existing local DB without forcing a destructive
  migration.

## OS-22 LLM Core and Tool Bridge

- `ANA_MAX/local/prompt_engine.py` is the canonical prompt composer for OS-22.
- `ANA_MAX/tools/tool_manifest.json` is the source of truth for tool metadata.
- `ANA_MAX/local/tool_dispatcher.py` parses `TOOL_CALL`, executes local tools,
  and logs telemetry in JSONL form.
- `ANA_MAX/local/tool_telemetry.py` is append-only and never blocks inference.
- `LocalLLMBackend.infer_with_rag()` now injects manifest-driven tool specs when
  the caller does not override them.
- `LocalBrainAgent.run_turn()` handles bounded tool follow-up and keeps the
  metadata-only fallback path intact when inference is unavailable.

## OS-21.5 Dual Python Local LLM Setup

- Python 3.12 remains the main ANA MAX interpreter.
- Python 3.11 is optional and isolated in `local_llm_env/` for OLLM and local model work.
- `scripts/local_llm/create_local_llm_env.py` detects Python 3.11 and creates the env only with `--apply`.
- Python 3.11 detection checks `python311`, `python3.11`, `py -3.11`, `py -0p`, and `uv python find 3.11`.
- `scripts/local_llm/install_ollm_backend.py` calls pip only with `--apply` and uses `ollm --no-deps` plus CPU-safe dependencies to avoid Windows `flash-attn` build failures.
- `scripts/local_llm/install_models.py` uses only user-provided source paths or URLs and never hardcodes model URLs.
- `.env.local_llm` defaults to `ANA_LOCAL_LLM_ENABLED=0`.

## OS-21.5 Local Brain Backend

- `ANA_MAX/local/local_llm_backend.py` is an optional adapter for `ollm`; importing ANA MAX does not import or load `ollm`.
- Default model metadata is `phi3-medium` with `phi3-mini` fallback and `cpu` device.
- `LocalLLMBackend.is_available()` checks only optional backend importability.
- `LocalLLMBackend.infer_with_rag()` composes retrieved local context and tool-awareness metadata without changing the default `infer()` path.
- `LocalBrainAgent` and `PipelineReasoningHelper` default to deterministic metadata when inference is disabled or unavailable, but can now forward RAG context and tool prompts through the optional local brain path.
- No OS-20.1 or OS-21 baseline runtime behavior is changed by the local brain hook.

## OS-21 Finalizer Stop Point

- `ANA_MAX/kernel/os21_finalizer.py` aggregates the OS-21 baseline lock, agent registry summary, and tool virtualization summary.
- `OS21Finalizer.write_final_report()` writes `ANA_MAX/memory/os21_final_report.json` only when explicitly called.
- `OS21Finalizer.write_level_report()` writes `ANA_MAX/memory/os_level_OS21_report.json` so context export resolves the highest PASS level as `OS-21`.
- The finalizer sets `status=FINALIZED`, `os_level=OS-21`, `os22_started=false`, and `ready_for_os22=false`.
- The only allowed next phase before explicit operator instruction is `promotion_review_only`.

## OS-21 Final Metadata Baseline

- `ANA_MAX/kernel/tool_virtualization_contracts.py` derives sandboxed tool contracts from the agent capability registry.
- Tool simulation is a metadata response only; `executed=false` for every simulation.
- Unknown operations return `blocked_unknown_operation`.
- `ANA_MAX/kernel/os21_baseline_lock.py` validates all OS-21 metadata slices by schema and reports `PASS` only when every slice is healthy.
- The OS-21 baseline lock does not execute tools, run transports, write memory, or modify OS-20.1 runtime behavior.

## OS-21 Agent Capability Registry

- `ANA_MAX/kernel/agent_capability_registry.py` is the first metadata-only OS-21 kernel scaffold.
- `AgentCapabilityRegistry` builds a registry from agent plans and indexes agents by capability and tool.
- Registered agents keep `execution_allowed=false` in the top-level and per-agent sandbox policies.
- Capability lookup accepts capability IDs such as `web_scraper.read_only`.
- Tool lookup accepts plain or prefixed agent IDs, such as `web_recon_agent_v1` or `agent:web_recon_agent_v1`.

## OS-21 Web Agents Metadata

- `ANA_MAX/agents/web_scraper_agent.py` plans web scraper usage without calling `web_scraper`.
- `ANA_MAX/agents/web_recon_agent.py` composes `BrowserReconAgent`, `WebScraperAgent`, and `WebReconOrchestrator` into one metadata handoff.
- Active mode stays review-only and sets `execution_allowed=false`.
- Both agents emit capsule hints and reasoning graph hints for future OS-21 layers.
- `ANA_MAX/agents/__init__.py` uses lazy exports to keep module CLI execution warning-free.

## OS-21.5 Pipeline Recovery Metadata

- `ANA_MAX/distributed/pipeline_recovery.py` is local-only, simulated, and metadata-only.
- `PipelineRecoveryPlanner` builds phase checkpoints, shard checkpoints, retry queues, shard states, and migration candidates from a distributed pipeline dict.
- Failed shard IDs generate retry metadata for all tasks on that shard; failed task IDs generate task-level retry and migration metadata.
- Migration candidates are deterministic and choose the next healthy shard by sorted shard ID.
- The CLI is lab ergonomics only; it does not execute tasks, move data, or write artifacts.

## OS-21.5 Reasoning Graph Query API

- `ANA_MAX/graph/reasoning_graph_query.py` is read-only and metadata-only.
- `ReasoningGraphQuery` accepts an existing graph dict or builds one through `ReasoningGraphBuilder`.
- Node, edge, capsule, tool-degree, and path queries return schema `ana.os21.reasoning_graph_query.v1`.
- Path search is bounded, iterative, deterministic, and avoids recursion.
- The CLI is lab ergonomics only; it does not execute tools or write graph artifacts.

## Dependency Pin Repair And Bootstrap Validation

- The root `requirements.txt` now forwards to `ANA_MAX/requirements.txt`, so local installs can use a single canonical entry point.
- `ANA_MAX/requirements.txt` was aligned to versions available on the current index:
  - `pywinauto==0.6.9`
  - `sqlalchemy==2.0.50`
  - `asyncio-contextmanager==1.0.1`
  - `black==26.5.1`
  - `pylint==4.0.5`
  - `frida==17.11.0`
  - `frida-tools==14.9.0`
- `scripts/bootstrap_ana_env.ps1` now checks native exit codes from `venv` creation and `pip install` so dependency failures are surfaced correctly.
- Bootstrap validation completed successfully with `scripts/bootstrap_ana_env.ps1 -Apply`; `agent_startup_check.ps1` and `ana_quick_check.ps1` still pass afterward.

## Local Bootstrap And Dependency Routing

- Root `requirements.txt` now forwards to `ANA_MAX/requirements.txt` so `pip install -r requirements.txt` works from the workspace root.
- `scripts/bootstrap_ana_env.ps1` creates `ANA_MAX\.env` from `ANA_MAX\.env.example` when missing, and can also create `ANA_MAX\venv` plus install dependencies with `-Apply`.
- `START_ANA.bat` now self-heals missing env or venv state before starting the server.
- `SETUP_AND_RUN.md` documents the canonical local setup path for the current lab.

## OS-20.1 Hybrid Browser Runtime

- `ANA_MAX/core/browser_runtime.py` is additive and optional.
- Playwright enables live browser automation when browser binaries are available.
- HTTP inspection fallback keeps `browser_control inspect` usable for local agents without browser automation.
- DOM refs are bounded and returned only through explicit `dom_refs` or `page_snapshot` calls.
- `browser_control` is not loaded by default in `cascade_integration/direct_bridge.py` because OS-20 baseline checks require `14/14` core tools.
- Use `python cascade_integration/direct_bridge.py --enable-hybrid-tools --execute browser_control --payload-b64 <payload>` to enable it for local agents.
- Risky browser actions require `--confirm` or `--dry-run`; read-only actions such as `status`, `inspect`, `dom_refs`, and `page_snapshot` do not.

## Encoding Normalization

- `scripts/ana_encoding_normalize.py` normalizes active `.md`, `.ps1`, `.bat`, `.cmd`, and `.txt` files to UTF-8 without BOM and ASCII-safe content.
- `scripts/ana_encoding_normalize.ps1` is an ASCII wrapper for PowerShell usage.
- Generated history, memory, logs, archives, sandbox, and voice temp files are excluded by default.

## 2026-06-10

- `cascade_integration/direct_bridge.py` loads a focused local ANA MAX tool set in-process.
- Direct health check reports 14 loaded/registered tools.
- Audit output is written to `ANA_MAX/logs/direct_bridge_audit.jsonl`.
- `self_reasoning_engine.py` reads evaluation, evolution, skills, graph, and performance artifacts, then writes `ANA_MAX/memory/self_reasoning_report.json`.
- `toolchain_discovery.py` scans active tools and archived metadata without importing or auto-registering anything; dangerous tools remain report-only.
- `knowledge_graph_engine.py` now stores snapshots in `ANA_MAX/memory/knowledge_graph_history/` and emits hot/cold node diff metadata into `docs/KNOWLEDGE_GRAPH.md`.
- `os4_daemon.py` runs bounded subprocess cycles for profiling, skills, structuring, healing, evaluation, reasoning, graph, and toolchain discovery, then appends `docs/OS4_DAEMON_LOG.md`.
- Workspace-level `AGENTS.md` now defines direct-first, patch-only, verified execution for all agents.
- `scripts/agent_startup_check.ps1` verifies required startup docs and direct bridge local health.
- `scripts/ana_quick_check.ps1` composes startup, smoke, benchmark, and security diagnostics.
- `scripts/ana_daily.ps1` appends daily quick-check and maintenance metrics to `docs/PERFORMANCE_LOG.md`.
- `scripts/install_ana_daily_task.ps1` installs or updates `ANA_DEV_Daily_Check` only when run with `-Apply`.
- `scripts/ana_planner.ps1` scans scripts/tests/cascade integration for TODO/FIXME, risky operations, and broad exception handlers.
- `scripts/ana_planner.ps1` treats mutation lines near `$Apply` checks as guarded to reduce false positives.
- `scripts/ana_filesystem_health.ps1` excludes venv/cache/log archives and archives `.tmp/.bak/.old` candidates instead of deleting them.
- `scripts/ana_profile_tool.ps1` records process-level and tool-level latency samples for configured safe direct tools.
- `direct_bridge.py --payload-b64` avoids Windows JSON argument quoting failures.
- `self_structuring_engine.py` now emits RAW-tagged JSON, writes `self_structuring_report.json`, logs actions to JSONL, defaults to dry-run, backs up before move/archive, and deletes only truly empty directories.
- `self_evolution_engine.py` now imports without DirectBridge initialization, coordinates safe OS-3 modules only, writes `evolution_report.json`, and wraps CLI output in OS3 RAW tags.
- `self_evolution_engine.py --fast-parallel` runs independent OS-3 engines through isolated subprocesses, keeps structuring/healing in dry-run, then runs one evaluation pass.
- `self_evolution_engine.py --auto-evolution` is bounded by `--max-cycles` by default; use `--max-cycles 0` only for explicit continuous local lab mode.
- `self_evolution_engine.py --health-monitor` performs read-only package/disk/report checks plus dry-run evaluation for low-risk monitoring.
- `ANA_MAX/tools/__init__.py` now exports tool classes via `__getattr__` lazy loading and keeps `tools.base` import-safe.
- `scripts/restore_tools_from_archive.ps1 -Apply` restores missing tools from `ANA_MAX/archives/duplicates/20260610T043542Z/tools/` without overwrites.
- `scripts/quarantine_placeholders.ps1 -Apply` moves exact auto-created placeholders to `ANA_MAX/archives/placeholders_quarantine/<stamp>/`.
- OS-3 active scanners now ignore lab-only archive/sandbox/log/memory paths to avoid false health warnings.
- `multi_agent_orchestrator.py` now invokes procedural engines via `python -m ...` and parses RAW-tagged JSON.
- `web_recon_orchestrator.py` is planning-only and consumes `BrowserReconAgent` metadata to build passive and optional active recon pipelines.
- `knowledge/capsule_schema.py` and `knowledge/capsule_store.py` define the first OS-21 recon capsule layer using deterministic, JSON-friendly in-memory storage.
- `graph/reasoning_graph_builder.py` now folds local agent registry, distributed topology, knowledge graph summaries, recon pipelines, and recon capsules into one deterministic metadata graph.
- `agents/agent_scheduler.py` deterministically assigns tasks by agent role and marks explicit-enable work as gated metadata.
- `distributed/distributed_pipeline.py` combines the scheduler and graph builder into a simulated local-first distributed plan with shard metadata.
- `knowledge/capsule_merge.py` performs deterministic three-way capsule merges, unions list fields, preserves lineage, and reports scalar conflicts.
- `knowledge/capsule_sync.py` produces in-memory sync plans with `noop`, `create_local`, `create_remote`, `update_local`, `update_remote`, and `merge_required` actions.

## OS-3 Testing

Run OS-3 module tests:
```powershell
# Run all OS-3 tests
python tests/self_optimization/test_self_profiling_engine.py
python tests/self_optimization/test_self_healing_engine.py
python tests/self_optimization/test_self_structuring_engine.py
python tests/self_optimization/test_self_skills_engine.py
python tests/self_optimization/test_knowledge_graph_engine.py
python tests/self_optimization/test_github_pattern_extractor.py
python tests/self_optimization/test_self_evolution_engine.py
python tests/self_optimization/test_multi_agent_orchestrator.py

# Or run individual test files directly
python tests/self_optimization/test_self_profiling_engine.py
```

Each test file includes:
- Smoke test (module imports, basic instantiation)
- Logic test (core functionality with fake data)
- No external dependencies, no network, no destructive operations

## 2026-06-10 04:58:27

- Self-Structuring Engine executed
- Scanned 3152 files
- Found 169 duplicate groups
- Found 16 empty directories
- Found 5 large files
- Proposed 220 reorganizations

## 2026-06-10 05:05:58

- Self-Structuring Engine executed.
- Files scanned: 3303.
- Duplicate groups: 299.
- Similar-name groups: 298.
- Empty directories: 13.
- Large files: 5.
- Proposals: 13.
- Actions logged: 13.

## 2026-06-10 05:06:40

- Self-Structuring Engine executed.
- Files scanned: 3305.
- Duplicate groups: 299.
- Similar-name groups: 298.
- Empty directories: 13.
- Large files: 5.
- Proposals: 13.
- Actions logged: 13.

## 2026-06-10 05:07:46

- Self-Structuring Engine executed.
- Files scanned: 3305.
- Duplicate groups: 299.
- Similar-name groups: 298.
- Empty directories: 3.
- Large files: 5.
- Proposals: 3.
- Actions logged: 3.

## 2026-06-10 05:08:58

- Self-Structuring Engine executed.
- Files scanned: 3305.
- Duplicate groups: 299.
- Similar-name groups: 298.
- Empty directories: 3.
- Large files: 5.
- Proposals: 3.
- Actions logged: 3.

## 2026-06-10 05:11:09

- GitHub Pattern Extractor executed
- Extracted 0 patterns
- Proposed 0 integrations


## 2026-06-10 05:12:06

- GitHub Pattern Extractor executed
- Extracted 163 patterns
- Proposed 163 integrations

### Extracted Patterns

- **architecture**: src_layout
  Uses src/ directory layout for source code
  Source: src/
- **tool**: network_pentest_tool
  Tool with execute/run method: network_pentest_tool
  Source: tests\network_pentest_tool.py
- **tool**: test_tool_router_tool
  Tool with execute/run method: test_tool_router_tool
  Source: tests\test_tool_router_tool.py
- **tool**: setuptools_ext
  Tool with execute/run method: setuptools_ext
  Source: .venv\Lib\site-packages\cffi\setuptools_ext.py
- **tool**: tool_support
  Tool with execute/run method: tool_support
  Source: .venv\Lib\site-packages\sqlalchemy\util\tool_support.py
- **tool**: adal_tool
  Tool with execute/run method: adal_tool
  Source: ANA_MAX\tools\adal_tool.py
- **tool**: adb_tool
  Tool with execute/run method: adb_tool
  Source: ANA_MAX\tools\adb_tool.py
- **tool**: agent_coach_tool
  Tool with execute/run method: agent_coach_tool
  Source: ANA_MAX\tools\agent_coach_tool.py
- **tool**: ana_context_tool
  Tool with execute/run method: ana_context_tool
  Source: ANA_MAX\tools\ana_context_tool.py
- **tool**: autonomous_tool
  Tool with execute/run method: autonomous_tool
  Source: ANA_MAX\tools\autonomous_tool.py

## 2026-06-10 - Memory Context Layer

- `ANA_MAX/self_optimization/memory_context.py` is now the canonical bounded view over `ANA_MAX/memory/core_memory.json`.
- `self_reasoning_engine.py`, `self_evolution_engine.py`, and `os4_daemon.py` load memory context additively and fall back safely with `module_missing` or `failed_to_load`.
- `memory_consolidation_engine.py` writes bounded updates to `core_memory.json`; `self_consistency_engine.py` gates contradictions and regressions before new memory signals are promoted.
- The memory system stays local-only, standard-library-only, and does not change OS-3/OS-4 schemas.

## 2026-06-10 - OS-20 Context Bundle

- `ANA_MAX/context/context_injector.py` exports `ana.context.bundle.v1` and `ana.context.export.v1` for agent bootstrap.
- OS level reports are scanned from `ANA_MAX/memory/os_level_OS*_report.json` and summarized instead of copying nested payloads into the OS-20 stdout view.
- `current_os_level` is computed from the highest numeric PASS report, so OS-20 remains selected even if an earlier level report is WARN.
- `personal_ai_studio.py` persists the full OS-20 report but emits a compact RAW-tagged stdout view for tool-safe consumption.

## 2026-06-10 07:45

- Added the OS-5 goals engine and OS-6OS-10 additive ladder with RAW-tagged CLI output.
- OS-8, OS-9, and OS-10 level reports now persist even on dry-runs so the required `os_level_*` files are always present.
- Proposal and policy payloads still remain gated by explicit apply behavior; dry-run only refreshes reports.
- Local-only orchestration remains intact; no archive edits or remote dependencies were introduced.
- OS-6, OS-8, OS-9, and OS-10 level report files now use explicit `ana.osX.level_report.v1` wrapper schemas with the detailed engine payload nested underneath.
- The OS-10 enterprise orchestrator unwraps the OS-9 level wrapper before evaluating overall success, so the new report shape stays backward-compatible for consumers.

## 2026-06-10 05:12:46

- GitHub Pattern Extractor executed
- Extracted 163 patterns
- Proposed 163 integrations

### Extracted Patterns

- **architecture**: src_layout
  Uses src/ directory layout for source code
  Source: src/
- **tool**: network_pentest_tool
  Tool with execute/run method: network_pentest_tool
  Source: tests\network_pentest_tool.py
- **tool**: test_tool_router_tool
  Tool with execute/run method: test_tool_router_tool
  Source: tests\test_tool_router_tool.py
- **tool**: setuptools_ext
  Tool with execute/run method: setuptools_ext
  Source: .venv\Lib\site-packages\cffi\setuptools_ext.py
- **tool**: tool_support
  Tool with execute/run method: tool_support
  Source: .venv\Lib\site-packages\sqlalchemy\util\tool_support.py
- **tool**: adal_tool
  Tool with execute/run method: adal_tool
  Source: ANA_MAX\tools\adal_tool.py
- **tool**: adb_tool
  Tool with execute/run method: adb_tool
  Source: ANA_MAX\tools\adb_tool.py
- **tool**: agent_coach_tool
  Tool with execute/run method: agent_coach_tool
  Source: ANA_MAX\tools\agent_coach_tool.py
- **tool**: ana_context_tool
  Tool with execute/run method: ana_context_tool
  Source: ANA_MAX\tools\ana_context_tool.py
- **tool**: autonomous_tool
  Tool with execute/run method: autonomous_tool
  Source: ANA_MAX\tools\autonomous_tool.py
## 2026-06-10 - Final Stability Repair

- `habit_routine_engine.py` now resolves project-relative docs from `WORKSPACE_ROOT`, which fixed a false missing-routine condition caused by `ANA_MAX/memory/docs` lookups.
- Lesson inputs stored as `.jsonl` are now read as text instead of parsed as JSON, so routine counts remain stable.
- The OS-20 studio output stays bounded because the full context bundle is stored on disk and only the summary is surfaced in stdout.

## 2026-06-11 - OS-22 Smoke Runner EntryPoint

- `scripts/os22/os22_infer_smoke.py` now adds a repo-root path bootstrap before importing `ANA_MAX`, so `python .\scripts\os22\os22_infer_smoke.py` works from the workspace root.
- The smoke runner uses `OS22BootSequence`, `LocalLLMBackend`, and `LocalBrainAgent` in one deterministic pass and records the turn in `ANA_MAX/logs/os22_infer_smoke.log`.
- A forced first-pass `TOOL_CALL: system_info {}` path keeps the ToolBridge and follow-up reasoning visible even when the backend is unavailable.

## 2026-06-10 - Self-Healing Validation Compatibility

- Added report-only compatibility entrypoints for `skill_engine`, `fallback_engine`, and `error_model` so audit validation commands resolve without changing OS-20 runtime logic.
- Added `--diagnostic` and `--simulate-repair` aliases to `self_healing_engine.py`; both force dry-run behavior and preserve existing `--cycle` / `--repair` semantics.
- Added the `ANA_MAX/skills` package marker so structuring health reports `missing_init_total=0`.

## 2026-06-10 - Encoding Hygiene

- Normalized the active text surface to ASCII-only output where the workspace text scanners found non-ASCII content.
- The cleanup removed BOM and Unicode noise from `docs/KNOWLEDGE_GRAPH.md`, `docs/ROADMAP.md`, and `ANA_MAX/docs/reports/requirements_current.txt` without changing runtime logic.

## 2026-06-10 - Voice Path ASCII Hardening

- `chat_voice_bridge.py` now strips non-ASCII characters from queue and clipboard text before speech or audit logging.
- `live_voice_bridge.py` now writes ASCII-safe temp files for the System.Speech fallback path.
- `ANA_MAX/voice_queue.txt` and the runtime voice temp files were normalized so the active voice path stays readable in PowerShell, CMD, and Python.

## 2026-06-10 - OS-21 Planning Notes

- The OS-20.1 and OS-21 prompt files were normalized to ASCII-safe text and summarized into `docs/OS21_PLAN.md`.
- The new plan keeps browser expansion, web agents, capability contracts, and reasoning graphs as additive layers only.

## 2026-06-10 - OS-21 Browser Pack v1

- `ANA_MAX/tools/browser_pack.py` is a metadata-only contract layer.
- It classifies browser operations into read-only, stateful, and confirm-required groups.
- It mirrors the existing `browser_control` and `web_scraper` tool definitions so future agents can reason about the tool surface safely.

## 2026-06-10 - OS-21 Browser Recon Agent v1

- `ANA_MAX/agents/browser_recon_agent.py` is planning-only and does not execute browser actions.
- It consumes the browser pack manifest and produces passive and active recon phases.
- It exposes reasoning-graph hints so later graph builders can connect agent, tool, and context nodes.

## 2026-06-11 - Vector Memory Compatibility Layer

- `ANA_MAX/core/vector_memory.py` now provides the canonical SQLite-backed semantic memory store for legacy `VectorMemoryTool` and new RAG bridge tests.
- `ANA_MAX/local/rag_bridge.py` wraps the vector store with metadata-only ingest, retrieve, and context assembly helpers.
- The bridge stays local-only and deterministic; it does not change local LLM inference defaults or OS-20.1 runtime behavior.

## 2026-06-11 - OS-22 Final Answer Normalization

- `ANA_MAX/agents/local_brain_agent.py` now unwraps simple JSON answer envelopes from model output before returning the final answer.
- The normalization only applies to pure JSON-like payloads and leaves tool-call recovery, RAG usage, and follow-up inference unchanged.
- `scripts/os22/os22_infer_smoke.py` now produces a clean plain-text final answer with the Phi-3 Mini GGUF backend.

## 2026-06-11 - Event Stream Hook Restoration

- `ANA_MAX/core/event_stream.py` now provides the persisted event stream contract expected by the tool observability hooks in `ANA_MAX/tools/base.py`.
- The implementation keeps the archived SQLite-backed shape, adds safe enum normalization, and preserves the `emit`, `query_events`, `get_timeline`, `get_statistics`, `replay_actions`, and `cleanup_old_events` entry points.
- The live event stream now writes through the same `ANA_MAX/data/events.db` workspace path used by the lab and remains compatible with the OS-22 smoke runner and tool telemetry path.

## 2026-06-11 - Tool Telemetry Aggregation

- `ANA_MAX/local/tool_telemetry.py` now merges the append-only JSONL telemetry log with event-stream-backed tool results before telemetry coaching and summaries are built.
- `ANA_MAX/tools/agent_coach_tool.py` now reads the merged telemetry source rather than only the JSONL file, which keeps the coach aligned with the event stream emitted by `tools.base`.
- The telemetry summary reports source coverage, per-tool counts, and per-status counts without changing the existing tool execution contract.

## 2026-06-12 - Raw Phi-3 Comparison Path

- `scripts/local_llm/start_phi3_raw_chat.py` loads the same Phi-3 Mini GGUF backend but bypasses ANA orchestration: no agent, no RAG call, no ToolBridge, no shortcuts, and empty system prompt.
- The desktop launcher `C:\Users\billy\Desktop\ANA MAX PHI3 RAW CHAT.bat` is intended only for model comparison against the normal OS-22 chat launcher.
- `LocalLLMBackend` now preserves an explicit `use_rag=False`; this keeps raw comparison metadata honest while leaving default ANA chat behavior unchanged.

## 2026-06-12 - OS-22 Local Action Routing

- `ANA_MAX/tools/windows_local_tools.py` provides local-only helpers for `open_windows_app`, `desktop_screenshot`, and `calculate_expression`.
- `ANA_MAX/local/operator_intent_router.py` handles simple arithmetic, calculator launch, and screenshot-plus-calculator requests before sending prompts to the model.
- `ANA_MAX/local/tool_dispatcher.py` now accepts JSON-style and simple function-style TOOL_CALL output for known safe tools, reducing Phi-3 formatting failures.
- Desktop screenshot capture stores files under `ANA_MAX/logs/screenshots/`; it captures the desktop but does not perform visual analysis yet.

## 2026-06-12 - Phi-3 Medium Runtime Notes

- Active local backend remains `llama_cpp`; only model identity/path were changed to Phi-3 Medium Q5_K_M.
- Active model path is `local_models/phi3-medium-q5_k_m.gguf`; file size is `10074190208` bytes.
- SHA256 recorded by `scripts/model_download/download_phi3_medium.bat`: `25874bc0da2469d366bdd3328530008b8de65a9c57d64a3ba0d5b3d9f9c406a4`.
- `ANA_LOCAL_LLM_N_CTX=4096` avoids the llama.cpp warning where `n_ctx_seq` is lower than the model training context.
- The old Mini GGUF was removed to save disk; `scripts/local_llm/install_models.py` still retains a Mini install option for future reinstall if needed.

## 2026-06-12 - Romanian-Only Prompt Calibration

- Phi-3 Medium did not reliably obey language rules when they were only in the system prompt, so the clean chat launcher now injects the Romanian-only rule inline for calibrated profiles.
- `ANA_MAX/agents/local_brain_agent.py` now adds a compact Romanian ASCII language guard to `ana_chat` turn prompts.
- `scripts/local_llm/start_local_llm.py` handles explicit language-switch prompts deterministically through `language_lock`, preserving Romanian output without another model round trip.
- `scripts/local_llm/start_phi3_raw_chat.py --profile raw` remains the untouched baseline: no ANA, no RAG, no ToolBridge, no shortcuts, no prompt calibration.

## 2026-06-12 - OS-22 Local Under-Hood Visibility

- Phi-3 Medium does not see local processes, installed apps, or Frida by itself; ANA exposes those facts through ToolBridge result JSON.
- `ANA_MAX/tools/windows_local_tools.py` now provides read-only local inventory helpers backed by `tasklist`, registry uninstall metadata, safe browser executable discovery, and Frida import status.
- `open_windows_app` remains allowlist-based; it can now launch Brave, Chrome, Edge, calculator, notepad, paint, and explorer without letting the model execute arbitrary programs.
- `frida_status` is status-only and does not attach to, hook, or instrument any process.

## 2026-06-12 - Full PC Specs Routing

- `system_overview` now combines Python/Windows metadata, `GlobalMemoryStatusEx`, local disk usage, and read-only CIM hardware metadata.
- `operator_intent_router` now handles full-spec questions before generic process routing, so prompts that mention `sistem de operare`, `full spec`, `sub capota`, or `task manager` return a deterministic local report.
- The response is intentionally concise in chat while full JSON remains available in the `tool_result` payload for logs and debugging.

## 2026-06-12 - Browser Search Read Routing

- `browser_search_read` bridges browser launch and page reading: it builds a search URL, opens Brave/Chrome/Edge through the allowlisted Windows app path, and calls `web_scrape` on the same URL.
- The default search engine is Bing because live validation showed DuckDuckGo HTML search can return an anti-bot challenge instead of readable search results.
- The browser is used for visible operator feedback; the scraper is the read channel that gives Phi-3/ANA text to reason over.
- `web_scraper._ascii_text()` now transliterates Unicode to ASCII instead of replacing characters with `?`.

## 2026-06-12 - Natural Desktop Action Routing

- `operator_intent_router` now extracts desktop folder names from natural Romanian phrases before falling back to the default `ANA_MAX` folder.
- `py` is treated as a Python-script intent marker alongside `python` and `.py`.
- If the user asks for a small/simple Python script without naming it, the router now chooses `script.py` instead of relying on model prose.
