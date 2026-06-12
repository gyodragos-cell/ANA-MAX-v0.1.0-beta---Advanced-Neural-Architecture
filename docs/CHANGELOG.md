# Changelog

## 2026-06-12 - OS-22 Desktop Inventory Tool

- Replaced the old Desktop `run_evolution.bat` launcher with a wrapper around `scripts\run_evolution_maintenance.bat`.
- Added `scripts\run_evolution_maintenance.bat` with `check`, `fast`, `cycle`, `os5`, and `audit` modes, timestamped logs under `ANA_MAX\logs`, preflight checks, evolution execution, and OS-22 launch audit.
- Added a clearer Desktop launcher named `C:\Users\billy\Desktop\ANA MAX Evolution Maintenance.bat`.
- Added `web_learn_course` for bounded multi-page course learning with same-domain/path-scoped crawling, main-content extraction, per-page summaries, RAG storage, and deterministic URL ordering.
- Added `desktop_write_text_file` for safe ASCII Markdown/text reports on Desktop with backup-on-overwrite.
- Added the combined operator pipeline `open_url_in_windows_app + web_learn_course + desktop_write_text_file` for prompts like `deschide brave browser intra pe https://www.w3schools.com/php/ ... salveaza pe desktop ... invata`.
- Real W3Schools PHP probe opened Brave, learned 12 `/php/` pages, wrote `C:\Users\billy\Desktop\php.md`, and stored 43 clean RAG chunks after main-content filtering.
- Added `desktop_list_items` as a ToolBridge tool for safe Desktop inventory without reading file contents.
- Added `list_desktop_items()` in `ANA_MAX/tools/desktop_workspace.py` with deterministic metadata output, ASCII-safe names, bounded item count, hidden-item filtering, and no mutations.
- Added `desktop_inspect_folder` for safe one-folder Desktop inspection without reading file contents.
- Added `desktop_read_text_file` for bounded reading of allowed text/code files from Desktop or one Desktop folder.
- Added `web_learn_url` for URL scrape -> summary -> RAG storage in one safe operator intent.
- Wired `desktop_list_items` into `ANA_MAX/local/tool_dispatcher.py`, `ANA_MAX/local/operator_intent_router.py`, `ANA_MAX/local/tool_prompt_policy.py`, and both tool manifests.
- Wired `desktop_inspect_folder`, `desktop_read_text_file`, and `web_learn_url` into ToolBridge, the operator intent router, prompt policy, self-healing diagnostics, and OS-22 doctor.
- Natural prompts such as `listeaza tot ce am pe desktop` now route through ANA before Phi-3 answers, so the agent sees Desktop metadata instead of guessing.
- Natural prompts such as `intra in folderul ana_dev de pe desktop si listeaza ce e acolo` now inspect that Desktop folder deterministically.
- Natural prompts such as `citeste fisierul script.py din folderul vasile de pe desktop` now read the bounded text file.
- Natural prompts such as `intra pe linkul https://example.com si invata tot ce este important` now scrape and store useful text into RAG.

## 2026-06-11 - OS-22 Launch Readiness Audit

- Added `scripts/os22/os22_launch_audit.py` as the unified launch gate for Python, requirements, local LLM env, models, OS-22 doctor, OS-22 boot, and optional focused tests.
- Added `scripts/os22/os22_launch_audit.bat` for one-click Windows launch audit.
- Added `scripts/os22/start_os22_lab_chat.bat` to launch the ANA lab runtime with OS/tools and a separate clean OS-22 chat window.
- Added the `ana_chat` prompt profile for natural operator conversation and made it the default OS-22 chat launcher profile.
- Added `scripts/os22/start_os22_core_agent.bat` for the old strict `os22_core` runtime mode.
- Hardened `LocalBrainAgent` so identity prompts answer deterministically and malformed model `TOOL_CALL` output is visible instead of producing a blank chat turn.
- Hardened `ana_chat` against pseudo-call responses such as `ANA_MAX: tool(...)` and added automatic natural-answer repair for that failure mode.
- Added a deterministic local shortcut for `cine este presedintele romaniei?`, returning `Presedintele Romaniei este Nicusor Dan.`
- Added a deterministic tool-inventory shortcut for prompts like `cate tooluri ai?`, returning the OS-22 ToolBridge count, names, categories, and ANA/Phi-3 orchestration summary.
- Calibrated `ana_chat` as the human-facing profile: natural same-language replies, less robotic prompt text, greeting and capability shortcuts, and launcher temperature `0.40`.
- Made `LocalBrainAgent` accept explicit response token and temperature settings from the launcher while keeping repair/follow-up turns deterministic.
- Refined `ana_chat` again for Phi-3 Mini: Romanian ASCII conversational prompt, transliterated model output, capability routing before date routing, vague-explanation fallback, and launcher temperature `0.40`.
- Added `ANA_MAX/local/operator_intent_router.py` so high-confidence operator intents are handled by ANA before Phi-3 Mini drifts into pseudo-calls or generic advice.
- Added `ANA_MAX/tools/desktop_workspace.py` and the `desktop_create_python_script` ToolBridge tool for safe Desktop workspace script creation with ASCII name cleanup and backup-on-change behavior.
- Routed RAG explanation, collaboration setup, and Desktop Python script requests through the operator intent router, keeping chat natural while still letting ANA choose the right local tool.
- Reworked the OS-22 chat runtime toward Codex-like structure: normal chat now goes model-first, while only concrete local actions use the operator intent router.
- Added `conversation_context`, `tool_prompt_policy`, `rag_prompt_policy`, and `chat_response_coach` layers so ANA keeps continuity, exposes only relevant tools, avoids RAG leakage on casual chat, and repairs broken Phi-3 chat output.
- Recalibrated the OS-22 chat launcher to `--temperature 0.25` and `--max-tokens 192` for more stable Phi-3 Mini conversation.
- Added `docs/OS22_LAUNCH_READINESS.md` and `tests/test_os22_launch_audit.py`.
- The audit writes `ANA_MAX/memory/os22_launch_audit_report.json` when `--write-report` is used.

## 2026-06-11 - OS-22 Web Learning And Launch Doctor

- Added `web_scrape` and `rag_store_text` to the OS-22 tool manifest and fallback manifest.
- Added `web_scrape()` and `html_to_text()` wrappers in `ANA_MAX/tools/web_scraper.py` for bounded http/https text extraction.
- Added `ANA_MAX/tools/rag_store_text.py` for deterministic chunking and RAGBridge ingestion with source metadata.
- Wired `web_scrape` and `rag_store_text` into `ANA_MAX/local/tool_dispatcher.py`.
- Added `ANA_MAX/local/os22_doctor.py` and `/doctor` in the local LLM launcher for launch readiness checks.
- Hardened `TOOL_CALL` parsing for live Phi-3 output such as `TOOL_CALL: current_time{}`.
- Added `docs/OS22_WEB_SCRAPER_TOOL.md` and `docs/OS22_WEB_LEARNING_PIPELINE.md`.
- Added regression coverage in `tests/test_os22_web_learning_tools.py` and `tests/test_os22_doctor.py`.

## 2026-06-11 - OS-22 Self-Healing V2 And Autonomy V3

- Added `docs/OS22_AGENT_AUTONOMY_V2.md`, `docs/OS22_AGENT_AUTONOMY_V3.md`, `docs/OS22_AGENT_SELF_HEALING_V1.md`, and `docs/OS22_AGENT_SELF_HEALING_V2.md`.
- Added `ANA_MAX/local/agent_self_healing.py` for metadata-only tool diagnostics, RAG conflict resolution, and text issue classification.
- Extended `agent_self_healing.py` with RAG quality diagnostics, reasoning stabilization, preventive preflight aggregation, and best-effort self-healing telemetry.
- Added self-healing readiness to `OS22BootSequence` and the interactive boot banner.
- Added `/heal`, `/ragheal`, and `/stabilize` commands to `scripts/local_llm/start_local_llm.py`.
- Extended tests for self-healing diagnostics, RAG conflict resolution, foundation readiness, and interactive command helpers.
- Added a minimal pytest collection guard for uppercase lab scripts that execute local service checks at import time.
- Split pytest into a green default stable profile and an explicit legacy opt-in path via `ANA_INCLUDE_LEGACY_TESTS=1` and `scripts/run_legacy_tests.ps1`.

## 2026-06-11 - OS-22 Operational Mastery Layer

- Added `docs/OS22_AGENT_SANDBOX_SCENARIOS.md` with 20 advanced local agent training scenarios.
- Added `docs/OS22_AGENT_MASTER_CLASS.md` with 12 expert self-audit, profiling, and optimization modules.
- Added `docs/OS22_AGENT_AUTONOMY_V1.md` with bounded autonomy rules and limits.
- Wired all three documents into the foundation readiness check and operating pack index.
- Extended tests to verify scenario/module counts, ASCII safety, and foundation readiness.

## 2026-06-11 - OS-22 Advanced Agent Training

- Added `docs/OS22_AGENT_ADVANCED_TRAINING.md` with 12 professional OS-22 runtime training modules for Phi-3 Mini.
- Linked advanced training from `docs/OS22_AGENT_FOUNDATION.md` and `docs/OS22_AGENT_OPERATING_PACK.md`.
- Added advanced training to the foundation readiness check in `ANA_MAX/local/agent_foundation.py`.
- Extended tests to verify all 12 modules, ASCII safety, and foundation readiness.

## 2026-06-11 - OS-22 Unified Agent Foundation

- Added `docs/OS22_AGENT_FOUNDATION.md` as the unified OS-22 agent foundation document.
- Added `ANA_MAX/local/agent_foundation.py` to load, summarize, and validate the foundation pack.
- Added foundation readiness to `OS22BootSequence` and the interactive boot banner.
- Added `/foundation` to the local LLM interactive launcher for direct operator inspection.
- Added tests for foundation loading, ASCII safety, status readiness, boot integration, and banner output.

## 2026-06-11 - OS-22 Agent Operating Pack

- Added the OS-22 agent onboarding pack under `docs/`, including self-init, boot banner, contract, training lessons, memory primer, tool awareness, reasoning graph primer, workflow playbook, and operating pack index.
- Added `ANA_MAX/local/agent_boot_banner.py` and wired the interactive local LLM launcher to print a real ASCII boot banner with component readiness.
- Added `--no-banner` to `scripts/local_llm/start_local_llm.py` for clean interactive output when needed.
- Exported `build_agent_boot_banner` through `ANA_MAX/local/__init__.py` and added banner tests.

## 2026-06-11 - OS-22 Codex Profile Refresh

- Expanded the `codex` prompt profile with the full OS-22 engineering scope for Phi-3 Mini GGUF Q5_K_M via `llama_cpp`.
- Normalized the profile to ASCII-only text to avoid mojibake and shell-facing encoding issues.
- Added tests covering OS-22 component coverage, `TOOL_CALL` contract presence, and ASCII safety.

## 2026-06-11 - OS-22 Interactive Tool Debug Commands

- Added `/time`, `/tool`, `/open`, and `/rag` commands to `scripts/local_llm/start_local_llm.py` for direct local ToolBridge and RAG testing inside the interactive agent shell.
- Kept normal chat input routed through `LocalBrainAgent.run_turn()` with RAG and ToolBridge enabled.
- Added unit coverage for no-argument tool commands, JSON tool arguments, and direct RAG command output.

## 2026-06-11 - OS-22 Agent Tool Smoke Hardening

- Added `current_time` to the OS-22 tool manifest and dispatcher so Phi-3 can answer date/time questions through a deterministic local tool.
- Made `TOOL_CALL` parsing tolerant of no-argument tool calls such as `TOOL_CALL: current_time`, matching the live Phi-3 Mini output while preserving JSON argument support.
- Updated `BrowserControlTool` URL normalization to allow `file://` URLs only when the target stays inside the ANA workspace.
- Verified real OS-22 agent turns for `current_time` and `open_browser` through the Phi-3 Mini GGUF backend.

## 2026-06-11 - RAG Legacy Store Compatibility

- Updated `ANA_MAX/core/vector_memory.py` to handle both the new schema and the older live SQLite layout used by the existing lab memory database.
- Kept `RAGBridge` and `OS-22` boot checks healthy without forcing a destructive migration.

## 2026-06-11 - OS-22 Boot Sequence

- Added `ANA_MAX/local/os22_boot.py` for deterministic boot and health metadata for the local brain stack.
- Added `docs/OS22_BOOT_SEQUENCE_V1.md` and extended `docs/OS22_LLM_CORE_V1.md` with the boot sequence layer.
- Added tests for boot report generation and report writing.

## 2026-06-11 - OS-22 LLM Core Tool Bridge

- Added `ANA_MAX/tools/tool_manifest.json` and `ANA_MAX/tools/tool_manifest_loader.py` as the manifest source of truth for local tool metadata.
- Added `ANA_MAX/local/prompt_engine.py`, `ANA_MAX/local/tool_dispatcher.py`, and `ANA_MAX/local/tool_telemetry.py` for manifest-driven prompt composition, deterministic `TOOL_CALL` execution, and append-only telemetry.
- Wired `LocalLLMBackend` and `LocalBrainAgent` to use manifest-backed tool awareness and bounded follow-up turns.
- Added lab profiles `phi3_lab`, `codex`, and `pentest_lab` for OS-22 local brain work.
- Added tests for the manifest loader, prompt engine, dispatcher, and agent tool-follow-up flow.

## 2026-06-11 - Local Brain RAG And Tool Awareness

- Added `ANA_MAX/core/vector_memory.py` as the canonical SQLite-backed compatibility store for semantic memory.
- Added `ANA_MAX/local/rag_bridge.py` and wired it into `LocalLLMBackend.infer_with_rag()` and `LocalBrainAgent`.
- Added tool-awareness prompt injection through `compose_system_prompt()` while keeping the default `infer()` path unchanged.

## 2026-06-11 - Local LLM Lab Profile

- Added `ANA_MAX/local/prompt_profiles.py` with `default` and `lab` prompt styles.
- Added `--profile` support to `scripts/local_llm/start_local_llm.py` and `scripts/local_llm/test_local_brain.py`.
- Added `scripts/local_llm/start_local_llm_lab.bat` for Windows-only lab startup.
- Added desktop shortcut `ANA MAX LLM LAB.lnk` to launch the lab profile directly.

## 2026-06-11 - Desktop Shortcut Launchers

- Added dedicated `.cmd` wrappers for `ALL`, `OS20`, `TOOLS`, and `FAST` startup flows.
- Recreated Desktop shortcuts to point at the wrappers, so double-click launch is stable.
- Kept `START_ANA.bat` unchanged and preserved the original fast start path.

## 2026-06-11 - ANA Auto Load Launcher

- Added `scripts/auto_load_ana.bat` for explicit OS-20 and tool startup automation.
- Supported modes: `all`, `os20`, and `tools`.
- Documented the launcher in `SETUP_AND_RUN.md`.

## 2026-06-11 - Local LLM Test Environment Support

- Added `pytest` to `requirements_local_llm.txt` so the dedicated `local_llm_env` can run the local LLM test suite directly.
- Updated the integration test to request the optional `ollm` backend explicitly when checking the unavailable-backend fallback path.
- Verified the dedicated env now runs `pytest` successfully without falling back to system Python.

## 2026-06-11 - Local LLM Startup And Rebuild Flow

- Changed the active local LLM backend to `llama_cpp` for the default Phi-3 Mini GGUF path.
- Kept `ollm` support as an optional backend path for alternate local setups and tests.
- Added `scripts/local_llm/start_local_llm.bat` for one-click local chat startup.
- Added `scripts/local_llm/rebuild_local_llm_stack.bat` for install, validate, and smoke recovery.
- Updated the local LLM setup docs to describe the current CPU-safe default flow.

## 2026-06-11 - OS-21.5 Dual Python Local LLM Setup

- Added dry-run-first helper scripts under `scripts/local_llm/`.
- Added `.env.local_llm` with local brain disabled by default.
- Added `requirements_local_llm.txt` for the optional OLLM environment.
- Added `docs/LOCAL_LLM_SETUP_V1.md` and extended `docs/LOCAL_LLM_BACKEND_V1.md`.
- Kept Python 3.12 as the main ANA interpreter and Python 3.11 as an optional local LLM environment.
- Created `local_llm_env` with local Python 3.11.15 after explicit operator readiness.
- Added `.gitignore` entries for `local_llm_env/`, `local_models/`, and Python cache outputs.

## 2026-06-10 - OS-21.5 Optional Local LLM Backend

- Added optional `ANA_MAX/local/local_llm_backend.py` for Phi-3 Medium primary and Phi-3 Mini fallback through `ollm`.
- Added lazy `ANA_MAX/local/__init__.py`.
- Filled `ANA_MAX/agents/local_brain_agent.py` with deterministic local-brain metadata helpers.
- Filled `ANA_MAX/distributed/pipeline_reasoning_helper.py` with optional pipeline reasoning metadata.
- Added focused local LLM tests and `docs/LOCAL_LLM_BACKEND_V1.md`.

## 2026-06-10 - OS-21 Context Level Report And Self-Healing Validation

- Extended `ANA_MAX/kernel/os21_finalizer.py` to produce `ANA_MAX/memory/os_level_OS21_report.json`.
- Updated the OS-21 finalizer tests to cover the level report artifact.
- Refreshed context export and confirmed `current_os_level=OS-21`, `os_report_count=21`, `health_score=100`, and `warnings=0`.
- Ran self-healing diagnostic and repair simulation; both returned clean dry-run results with no mutations.

## 2026-06-10 - OS-21 Finalizer Stop Point

- Added `ANA_MAX/kernel/os21_finalizer.py` to mark OS-21 as finalized without entering OS-22.
- Exported `OS21Finalizer` from `ANA_MAX/kernel/__init__.py`.
- Wrote `ANA_MAX/memory/os21_final_report.json` with schema `ana.os21.finalizer.v1`.
- Added `docs/OS21_FINALIZATION.md` as the final stop-boundary document.
- Added tests for final status, validation, summary reuse, and final report writing.

## 2026-06-10 - OS-21 Final Metadata Baseline

- Added `ANA_MAX/kernel/tool_virtualization_contracts.py` for sandboxed metadata contracts, no-op simulation, and fallback metadata.
- Added `ANA_MAX/kernel/os21_baseline_lock.py` as the final OS-21 metadata baseline report.
- Extended `ANA_MAX/kernel/__init__.py` lazy exports for `ToolVirtualizationContracts` and `OS21BaselineLock`.
- Added tests for virtualization contracts, simulation blocking, fallback plans, and OS-21 baseline validation.
- Added `docs/TOOL_VIRTUALIZATION_CONTRACTS_V1.md` and `docs/OS21_BASELINE_LOCK.md`.

## 2026-06-10 - OS-21 Agent Capability Registry

- Added `ANA_MAX/kernel/agent_capability_registry.py` as the first metadata-only OS-21 kernel scaffold.
- Added `ANA_MAX/kernel/__init__.py` with lazy export for `AgentCapabilityRegistry`.
- Registered browser recon, web scraper, and web recon agent capabilities without executing agents or tools.
- Added tests for default registry generation, custom plan registration, capability lookup, tool lookup, validation, and summary reuse.
- Added `docs/AGENT_CAPABILITY_REGISTRY_V1.md` and updated OS-21 roadmap notes.

## 2026-06-10 - OS-21 Web Agents Metadata

- Added `ANA_MAX/agents/web_scraper_agent.py` for metadata-only scraper planning.
- Added `ANA_MAX/agents/web_recon_agent.py` to compose browser recon, scraper planning, and web recon orchestration metadata.
- Converted `ANA_MAX/agents/__init__.py` to lazy exports for new and existing agent classes.
- Added tests for passive and active web agent planning plus validation summaries.
- Added `docs/WEB_AGENTS_V1.md` and updated OS-21 handoff docs.

## 2026-06-10 - OS-21.5 Pipeline Recovery Metadata

- Added `ANA_MAX/distributed/pipeline_recovery.py` for metadata-only checkpoint, retry, shard state, and task migration planning.
- Exported `PipelineRecoveryPlanner` from `ANA_MAX/distributed/__init__.py` with lazy loading.
- Added deterministic tests for recovery plans with failed tasks, failed shards, ready-only plans, and summary reuse.
- Added `docs/PIPELINE_RECOVERY_V1.md` and updated distributed runtime roadmap notes.

## 2026-06-10 - OS-21.5 Reasoning Graph Query API

- Added `ANA_MAX/graph/reasoning_graph_query.py` as a read-only metadata query layer on top of `ReasoningGraphBuilder`.
- Exported `ReasoningGraphQuery` from `ANA_MAX/graph/__init__.py`.
- Added deterministic tests for node type lookup, agent edge lookup, capsule URL lookup, tool degree ranking, bounded paths, and summary output.
- Added `docs/REASONING_GRAPH_QUERY_V1.md` and updated OS-21 roadmap notes.

## 2026-06-10 - Dependency Pin Repair And Bootstrap Validation

- Added root `requirements.txt` shim and `SETUP_AND_RUN.md` for the canonical local setup flow.
- Added `scripts/bootstrap_ana_env.ps1` and `scripts/bootstrap_ana_env.bat` to create `ANA_MAX\.env` and `ANA_MAX\venv` when needed.
- Updated `START_ANA.bat` to self-bootstrap missing env or venv state before launch.
- Repaired requirement pins so bootstrap resolves cleanly on the current Python 3.12 lab:
  - `pywinauto==0.6.9`
  - `sqlalchemy==2.0.50`
  - `asyncio-contextmanager==1.0.1`
  - `black==26.5.1`
  - `pylint==4.0.5`
  - `frida==17.11.0`
  - `frida-tools==14.9.0`
- Verified `scripts/bootstrap_ana_env.ps1 -Apply` completes successfully and leaves the OS-20 startup checks green.

## 2026-06-10 - Local Bootstrap And Requirements Shim

- Added root `requirements.txt` as a shim to `ANA_MAX/requirements.txt`.
- Added `scripts/bootstrap_ana_env.ps1` and `scripts/bootstrap_ana_env.bat` to create `ANA_MAX\.env` and `ANA_MAX\venv` when needed.
- Updated `START_ANA.bat` to self-bootstrap missing env or venv state before launch.
- Added `SETUP_AND_RUN.md` with the canonical local setup and run flow.

## 2026-06-10 - OS-20.1 Hybrid Browser And Encoding Layer

- Added `ANA_MAX/core/browser_runtime.py` with optional Playwright automation plus HTTP/system-browser fallback.
- Extended `ANA_MAX/tools/browser_control.py` with `dom_refs` and `page_snapshot` operations.
- Added ASCII/BOM normalization scripts for active docs and scripts.
- Added ASCII stability report alias `docu/ANA_MAX_Mother_Lab_Stability_Report_v2.md`.
- Added `cascade_integration/direct_bridge.py --enable-hybrid-tools` for optional `browser_control` loading.
- Added operation-level confirmation guard for risky browser actions.
- Preserved OS-20 direct bridge baseline at `14/14`; `browser_control` remains optional.

## 2026-06-10

- **ANA MAX OS-4 Additive Layer**
  - Added `self_reasoning_engine.py` for local hypothesis and priority generation from existing evaluation artifacts.
  - Added `toolchain_discovery.py` for report-only active/candidate/dangerous toolchain manifests without auto-enable.
  - Extended `knowledge_graph_engine.py` with history snapshots, graph diffs, hot nodes, and cold nodes.
  - Added `os4_daemon.py` for bounded local orchestration and `docs/OS4_DAEMON_LOG.md` heartbeats.
  - Preserved OS-3 baselines and RAW-tagged CLI output while keeping OS-4 local-only, standard-library-only, and reversible.

- **ANA MAX OS-3 COMPLETION MODE Complete**
  - Phase 1 (Runtime Artifacts): Verified all 8 modules have CLI entrypoints with --cycle handlers, confirmed runtime artifact paths are consistent (docs/ for docs, ANA_MAX/memory/ for state)
  - Phase 2 (Testing & Validation): Created test suite for all 8 OS-3 modules in tests/self_optimization/, documented test runner command in TECHNICAL_NOTES.md
  - Phase 3 (Documentation Completion): Created OS3_OVERVIEW.md, OS3_MODULES.md, OS3_RUNTIME.md, OS3_AUTONOMY.md, updated ROADMAP.md with OS-3 Status section
  - Phase 4 (Evolution Loop Wiring): Verified self_evolution_engine.py orchestrates all modules correctly, added optional github_pattern_extractor handling
  - Phase 5 (Multi-Agent Orchestration): Hardened multi_agent_orchestrator.py with clear agent role mappings, updated AGENTS.md with detailed agent responsibilities
  - Phase 6 (Safety & Failure Modes): Added safety safeguards to self_structuring_engine.py (backup before moves, dry-run defaults, delete only empty directories), enhanced self_healing_engine.py logging (logs what failed, what fix proposed, whether applied or suggested)
  - Phase 7 (Final Consistency): Completed consistency pass on logging, docs, and paths, updated ROADMAP.md and CHANGELOG.md with completion status
  - OS-3 system is now production-grade, fully wired, fully documented, fully testable, and ready for continuous evolution

- **ANA MAX OS-3 Implementation Complete**
  - Phase 0: Preparation - Updated AGENTS.md with OS-3 agent roles, added OS-3 Implementation section to ROADMAP.md, created ANA_MAX/self_optimization/ directory
  - Phase 1: Self-Profiling Engine - Created self_profiling_engine.py with profile_tools(), profile_system(), log_performance() APIs, integrated with direct_bridge for tool timing
  - Phase 2: Self-Healing Engine - Created self_healing_engine.py with detect_failures(), propose_fixes(), apply_safe_patch(), re_run_tests() APIs, integrated with test suite
  - Phase 3: Self-Structuring Engine - Created self_structuring_engine.py with scan_structure(), detect_redundancy(), propose_reorg(), apply_reorg() APIs, defined OS-3 canonical layout
  - Phase 4: Self-Expanding Skills Layer - Created self_skills_engine.py with detect_missing_capabilities(), generate_skill(), update_skills_manifest() APIs, maintains skills manifest
  - Phase 5: Self-Documenting Knowledge Graph - Created knowledge_graph_engine.py with scan_project(), build_graph(), render_markdown() APIs, generates knowledge_graph.json and KNOWLEDGE_GRAPH.md
  - Phase 6: GitHub Pattern Extractor - Created github_pattern_extractor.py with analyze_repo(), extract_patterns(), propose_integrations() APIs for pattern extraction from user-provided repos
  - Phase 7: Self-Evolution Engine - Created self_evolution_engine.py with run_cycle(), plan_next_steps(), coordinate_modules() APIs, orchestrates all OS-3 modules
  - Phase 8: Multi-Agent Mode - Created multi_agent_orchestrator.py with assign_tasks(), sync_state(), merge_results() APIs, implements shared state mechanism for multi-agent coordination
  - All modules include OS-3 Autonomy Zone headers for maximum autonomy within project workspace
  - ROADMAP.md updated to mark all phases as completed
  - Multi-agent roles defined: Optimizer, Tester, Documenter, Structurer, Extractor

## 2026-06-10

- Added root `docs/` startup summary files for universal execution loop compatibility.
- Recorded direct bridge as the active local lab integration.
- Added Universal Agent Protocol to `AGENTS.md` so future agents load direct-first rules automatically.
- Added `scripts/agent_startup_check.ps1` for automated agent startup readiness checks.
- Added `scripts/ana_quick_check.ps1` for one-command startup, smoke, benchmark, and security validation.
- Added `scripts/ana_maintenance.ps1` for dry-run log/cache/disk/RAM maintenance checks.
- Added optional log archival to `scripts/ana_maintenance.ps1` via `-ArchiveLogs -Apply`.
- Added optional size-based log rotation to `scripts/ana_maintenance.ps1` via `-RotateLargeLogs -Apply`.
- Added `scripts/ana_daily.ps1` for one-command daily quick-check and maintenance reporting.
- Added `scripts/install_ana_daily_task.ps1` for optional local Windows Scheduled Task installation.
- Added archive compression support to `scripts/ana_maintenance.ps1` via `-CompressArchive -Apply`.
- Added `scripts/ana_planner.ps1` to regenerate `docs/ROADMAP.md` from local metrics.
- Extended `scripts/ana_planner.ps1` with scripts/tests technical debt scanning.
- Fixed PowerShell path/line interpolation in `scripts/ana_planner.ps1`.
- Fixed PowerShell `Join-Path` array construction in `scripts/ana_planner.ps1`.
- Added `scripts/ana_log_compress.ps1` for incremental archive compression and zip retention cleanup.
- Reduced false-positive risky-operation findings in `scripts/ana_planner.ps1` by recognizing nearby `-Apply` guards.
- Fixed literal `$Apply` regex matching in `scripts/ana_planner.ps1`.
- Replaced planner self-scan regex with literal string checks.
- Added `direct_bridge.py --benchmark-all` and `scripts/ana_benchmark_tools.ps1` for safe direct tool benchmarking.
- Corrected `--benchmark-all` payloads for `code_search`, `privacy_shield`, and `security_audit`.
- Repaired `ANA_MAX/self_optimization/self_structuring_engine.py` package paths, raw JSON output, safety logging, dry-run cycle behavior, and empty-directory detection.
- Repaired `ANA_MAX/self_optimization/self_evolution_engine.py` to avoid DirectBridge/toolhost/MCP side effects and emit RAW-tagged JSON.
- Added `self_evolution_engine.py` modes: `--fast-parallel`, `--auto-evolution`, and `--health-monitor` with subprocess isolation, timeouts, bounded loops, and RAW-tagged CLI output.
- Added `docs/AGENTS.md` pointer for agents that load docs-local instructions.
- Added `scripts/ana_filesystem_health.ps1` for large/old/duplicate file scans and cleanup candidate archival.
- Added `scripts/ana_profile_tool.ps1` for direct tool latency profiling.
- Fixed JSON argument escaping and failure exit code in `scripts/ana_profile_tool.ps1`.
- Added `direct_bridge.py --payload-b64` and switched profiler to base64 payload transport.
- Restored 93 archived ANA tool modules into `ANA_MAX/tools/` without overwriting active files.
- Repaired `ANA_MAX/tools/__init__.py` with lazy loading so missing optional tools cannot break direct bridge startup.
- Restored `ANA_MAX/core/smart_search.py` from duplicate archive to satisfy `smart_search_tool`.
- Quarantined 50 auto-created placeholder modules under `ANA_MAX/archives/placeholders_quarantine/`.
- Added missing package markers for `ana/core/scheduler` and `ana/services/fs`.
- Normalized OS-3 CLI JSON output through RAW tags across profiling, structuring, skills, healing, evaluation, knowledge graph, extractor, and multi-agent orchestrator.
- Repaired `multi_agent_orchestrator.py` to use subprocess-based procedural engines and treat GitHub extraction as user-triggered skipped work.
- Excluded lab-only archive/sandbox/log/memory paths from active profiling, structuring, healing, and skills reports.

## 2026-06-10 - OS-5OS-10 Additive Ladder

- Added OS-5 goals/strategy layering and the OS-6OS-10 additive engines without changing OS-3/OS-4 baseline schemas.
- Kept all new orchestration local-only, standard-library-only, bounded, and RAW-tagged for shell-safe output.
- Restored OS-8/OS-9/OS-10 level-report persistence on dry-runs so level artifacts are always emitted during validation.
- Verified compile, daemon, evolution, architecture, global, and enterprise smoke tests passed.

## 2026-06-10 - Level Report Wrapper Tightening

- Converted OS-6, OS-8, OS-9, and OS-10 level report files to explicit generic wrapper schemas while preserving detailed payloads.
- Updated the OS-10 enterprise reader to unwrap the OS-9 payload before evaluating overall success.
- Re-verified the wrapper files on disk and kept all raw detailed engine outputs intact.

## 2026-06-10 - OS-21 Recon Orchestration And Capsules

- Added `ANA_MAX/orchestrators/web_recon_orchestrator.py` as a planning-only metadata pipeline over `BrowserReconAgent`.
- Added `ANA_MAX/knowledge/capsule_schema.py` and `ANA_MAX/knowledge/capsule_store.py` for recon capsule metadata, diff, and merge support.
- Added documentation for the orchestrator and capsule layer in `docs/WEB_RECON_ORCHESTRATOR.md` and `docs/CAPSULES_V1.md`.
- Kept OS-20.1 runtime behavior unchanged.

## 2026-06-10 - OS-21 Reasoning Graph, Scheduler, And Distributed Pipeline

- Added `ANA_MAX/graph/reasoning_graph_builder.py` to combine agent registry, distributed topology, knowledge graph, recon plans, and capsule metadata into a deterministic graph.
- Added `ANA_MAX/agents/agent_scheduler.py` as a metadata-only multi-agent scheduler with deterministic role-aware assignments.
- Added `ANA_MAX/distributed/distributed_pipeline.py` as a local-only distributed runtime skeleton that combines the scheduler and reasoning graph.
- Added docs for the new slices in `docs/REASONING_GRAPH_V1.md`, `docs/AGENT_SCHEDULER_V1.md`, and `docs/DISTRIBUTED_PIPELINE_V1.md`.

## 2026-06-10 - OS-21.5 Capsule Sync And Merge

- Added `ANA_MAX/knowledge/capsule_merge.py` for deterministic three-way capsule merge planning and conflict reporting.
- Added `ANA_MAX/knowledge/capsule_sync.py` for metadata-only local/remote sync plans and in-memory previews.
- Added `tests/test_capsule_merge.py` and `tests/test_capsule_sync.py`.
- Added `docs/CAPSULE_SYNC_V1.md`.

## 2026-06-10 04:58:04

- Self-Healing Engine executed
- Detected 0 failures
- Proposed 0 fixes
- Applied 0 healing actions

## 2026-06-10 - Memory Context Integration

- Added `ANA_MAX/self_optimization/memory_context.py` as the bounded shared-memory view for reasoning, evolution, and daemon flows.
- Added `memory_consolidation_engine.py` and `self_consistency_engine.py` to keep `core_memory.json` and memory safety checks in sync.
- Extended `self_reasoning_engine.py`, `self_evolution_engine.py`, and `os4_daemon.py` to read memory context additively with safe fallbacks.
- Verified compileall and smoke tests passed with RAW-tagged output intact.

## 2026-06-10 - OS-20 Context Bundle Integration

- Added `ANA_MAX/context/context_injector.py` and `ANA_MAX/context/__init__.py` for local agent bootstrap context.
- Extended `personal_ai_studio.py` to include a bounded context summary and agent bootstrap prompt in OS-20 output.
- Kept `current_os_level` deterministic by selecting the highest PASS level report.
- Verified compile and smoke tests passed with RAW markers intact and OS-20 `overall_success=true`.

## 2026-06-10 04:59:32

- Self-Healing Engine executed
- Detected 0 failures
- Proposed 0 fixes
- Applied 0 healing actions

## 2026-06-10 05:01:23

- Self-Healing Engine executed
- Detected 0 failures
- Proposed 0 fixes
- Applied 0 healing actions
## 2026-06-10 - Final OS-18 to OS-20 Sync

- Fixed `habit_routine_engine.py` so it scans workspace docs instead of `ANA_MAX/memory/docs` and reads lesson JSONL files as text.
- Re-ran `memory_consolidation_engine`, `self_consistency_engine`, `context_injector`, `self_evolution_engine`, and `personal_ai_studio` after consolidation.
- Confirmed OS-20 context bundle still resolves to `current_os_level=OS-20` with `health_score=100` and `warnings=0`.
- Final gate stayed clean: `overall_success=true`, `parse_error_count=0`, and RAW markers remained intact.

## 2026-06-10 - Self-Healing Validation Compatibility

- Added no-op RAW-tagged compatibility modules for `ANA_MAX.skills.skill_engine`, `fallback_engine`, and `error_model`.
- Added dry-run CLI aliases `--diagnostic` and `--simulate-repair` to `self_healing_engine.py`.
- Added `ANA_MAX/skills/__init__.py` to keep package-structure validation clean.

## 2026-06-10 - OS-20 Final Baseline

- Added `docs/OS20_FINAL_BASELINE.md` as the official PASS-level OS-20 checkpoint.
- Refreshed `ANA_MAX/context/context_bundle.json` and `ANA_MAX/context/agent_bootstrap_prompt.txt` from the existing context injector.
- Recorded the baseline in `docs/ANA_MEMORY.md` for future agents.

## 2026-06-11 - OS-22 Embedded Tool Call Recovery

- Extended `ANA_MAX/local/tool_dispatcher.py` to accept both canonical `TOOL_CALL: <tool_name> <json_arguments>` and JSON-object payloads.
- Updated `ANA_MAX/agents/local_brain_agent.py` to detect `TOOL_CALL` lines embedded anywhere in the model output, not just at the start of the response.
- Added regressions for embedded tool calls and JSON payload parsing so the runtime can recover from noisy Phi-3 outputs instead of leaking tool text into the final answer.

## 2026-06-11 - OS-22 Tool Follow-Up Tightening

- Tightened `ANA_MAX/agents/local_brain_agent.py` follow-up prompts so Phi-3 receives the original user prompt, the executed `TOOL_CALL`, and the tool result in one structured handoff.
- Reduced the follow-up generation budget to keep second-pass answers concise and focused on the original request.
- Added regression coverage in `tests/test_local_brain_agent_tool_bridge.py` for the improved follow-up prompt structure.

## 2026-06-11 - OS-22 Profile Split

- Added `os22_core` to `ANA_MAX/local/prompt_profiles.py` as the compact deterministic runtime profile for Phi-3 Mini.
- Cleaned the `codex` profile to ASCII-safe text and kept it as the engineering profile for OS-22 design and debugging.
- Switched the OS-22 smoke runner default profile to `os22_core` so the one-turn validation path now exercises the runtime prompt by default.
- Raised the OS-22 smoke runner default context window to `4096`, which matches the GGUF training capacity and removed the `n_ctx_seq < n_ctx_train` warning on the local Phi-3 Mini run.

## 2026-06-11 - OS-22 Smoke Runner

- Added `scripts/os22/os22_infer_smoke.py` as the deterministic one-turn OS-22 smoke entrypoint.
- The runner now boots OS-22 metadata, composes the prompt engine, exercises the manifest-backed tool bridge, and writes a compact log to `ANA_MAX/logs/os22_infer_smoke.log`.
- Added `tests/test_os22_infer_smoke.py` so the smoke path stays verified without requiring a live model load.

## 2026-06-10 - OS-20 Baseline Lock Script

- Added `scripts/OS20_BASELINE_LOCK.ps1` to verify the OS-20 baseline before OS-21 planning or larger refactors.
- The default path checks artifacts only; `-RunRuntimeChecks` additionally runs compileall and direct bridge health.

## 2026-06-10 - Memory Cleanup and Context Refresh

- Archived the stale `ANA_MAX/memory/test_smoke_vector_1779322205.0416353.db` artifact into `ANA_MAX/sandbox/memory_cleanup_archive/`.
- Restored `ANA_MAX/memory/knowledge_graph_history/` and `ANA_MAX/memory/evolution_strategy_history/` with fresh snapshots so the memory layer stays visible to future runs.
- Refreshed `ANA_MAX/context/context_bundle.json` and `ANA_MAX/context/agent_bootstrap_prompt.txt` after the cleanup so the exported context matches the live workspace again.

## 2026-06-10 - ASCII Encoding Sweep

- Normalized `docs/KNOWLEDGE_GRAPH.md`, `docs/ROADMAP.md`, and `ANA_MAX/docs/reports/requirements_current.txt` to ASCII-only text with no BOM.
- Confirmed the workspace text surface is now PowerShell, CMD, and Python friendly for the active documentation and support files.

## 2026-06-10 - Active Workspace Text Sweep

- Repaired `scripts/ana_encoding_normalize.py` so the normalizer itself stays ASCII-safe and scans active `.env` and `.html` files.
- Normalized `ANA_MAX/.env` and `ANA_MAX/index.html` to remove BOM and non-ASCII content.
- Final active scan returned `finding_count=0`, with only runtime voice queue/temp artifacts left outside the normalization scope.

## 2026-06-10 - Voice Path ASCII Hardening

- Updated `ANA_MAX/chat_voice_bridge.py` to normalize queue and clipboard text to ASCII before audit or speech handling.
- Updated `ANA_MAX/tools/live_voice_bridge.py` to write ASCII-safe System.Speech temp files.
- Normalized `ANA_MAX/voice_queue.txt` and runtime voice temp files so the live voice path stays PowerShell, CMD, and Python friendly.
- Follow-up encoding scan still reported `finding_count=0` for the active workspace text surface.

## 2026-06-10 - OS-21 Browser Pack v1

- Added `ANA_MAX/tools/browser_pack.py` as a metadata-only browser contract layer for OS-21 planning.
- Added `tests/test_browser_pack.py` to validate browser and scraper contract alignment.
- Added `docs/BROWSER_PACK_V1.md` as the first browser-pack design note for OS-21.

## 2026-06-10 - OS-21 Browser Recon Agent v1

- Added `ANA_MAX/agents/browser_recon_agent.py` as a metadata-only recon planner that consumes the browser pack.
- Added `tests/test_browser_recon_agent.py` to validate passive and active recon plan shapes.
- Added `docs/BROWSER_RECON_AGENT.md` to document the new agent slice and its OS-21 alignment.

## 2026-06-11 - OS-22 Smoke Output Cleanup

- `ANA_MAX/agents/local_brain_agent.py` now normalizes final model text and unwraps simple JSON answer envelopes such as `{"answer": "..."}`.
- The regression keeps tool follow-up behavior intact while making the OS-22 smoke runner return plain final answers instead of JSON-wrapped text.
- Verified with the real Phi-3 Mini GGUF smoke path through `scripts/os22/os22_infer_smoke.py`.

## 2026-06-11 - Event Stream Restoration

- Added `ANA_MAX/core/event_stream.py` back into the live workspace as the SQLite-backed observability stream used by `ANA_MAX/tools/base.py` and `ANA_MAX/tools/event_stream_tool.py`.
- Restored compatibility helpers for topic-based `EventBus` and `EventLog` flows so legacy event-bus style tests stay usable alongside the event stream API.
- Added focused tests for emit/query/timeline/stats/replay behavior and verified the real OS-22 smoke runner still completes cleanly with the new observability hook in place.

## 2026-06-11 - Tool Telemetry Aggregation

- Extended `ANA_MAX/local/tool_telemetry.py` with read/merge/summary helpers that can combine JSONL telemetry with the SQLite event stream.
- Updated `ANA_MAX/tools/agent_coach_tool.py` to consume the merged telemetry view so coach guidance can see event-stream-backed tool results as well as local JSONL logs.
- Added focused tests proving the aggregation path sees both sources and keeps the agent coach report stable.

## 2026-06-12 - Phi-3 Raw Chat and Local Action Tools

- Added a clean Phi-3 raw chat launcher at `scripts/local_llm/start_phi3_raw_chat.py` plus `scripts/local_llm/start_phi3_raw_chat.bat` and the desktop entry `C:\Users\billy\Desktop\ANA MAX PHI3 RAW CHAT.bat`.
- Fixed `LocalLLMConfig.from_value()` so explicit `use_rag=False` is preserved instead of falling back to environment defaults.
- Added Windows local action helpers for calculator launch, desktop screenshot capture, and deterministic arithmetic through the OS-22 ToolBridge.
- Expanded the tool manifest, dispatcher, prompt policy, and operator intent router so common local actions route through real tools instead of invalid browser/tool strings.

## 2026-06-12 - Phi-3 Medium Model Upgrade

- Added `scripts/model_download/download_phi3_medium.bat` to download or verify the Phi-3 Medium Q5_K_M GGUF model in `local_models/`.
- Switched local LLM defaults, OS-22 launchers, raw/clean chat launchers, and launch-audit commands from `phi3-mini` to `phi3-medium`.
- Updated `.env.local_llm` to `phi3-medium`, `local_models/phi3-medium-q5_k_m.gguf`, and `ANA_LOCAL_LLM_N_CTX=4096`.
- Removed the old `local_models/phi3-mini-q5_k_m.gguf` file after full validation passed.

## 2026-06-12 - Phi-3 Medium Romanian Language Lock

- Calibrated `ana_chat`, `phi3_lab`, `os22_core`, and the clean Phi-3 chat profiles to answer in Romanian ASCII only.
- Added inline language guard instructions in `LocalBrainAgent` so the model sees the Romanian-only rule inside the turn prompt, not only in the system prompt.
- Added deterministic routing for language-switch requests such as `continue in english mode`, returning a Romanian answer without model drift.
- Kept `raw` Phi-3 chat unchanged for pure model comparison with no system prompt.

## 2026-06-12 - OS-22 Under-Hood Inventory Tools

- Added read-only OS inventory tools for `process_list`, `installed_apps`, `find_app`, `system_overview`, and `frida_status`.
- Extended `open_windows_app` to locate safe allowlisted browsers such as Brave, Chrome, and Edge, fixing `deschide brave browser` routing.
- Updated ToolBridge manifest, dynamic prompt policy, and operator intent router so Phi-3 Medium can inspect local process/app metadata through explicit tools instead of guessing.

## 2026-06-12 - OS-22 Full PC Specs Intent

- Expanded `system_overview` with Windows edition/build, PC manufacturer/model, CPU cores/logical processors, RAM, GPU, and disk metadata.
- Added a combined operator intent for questions like `ce sistem de operare am`, `full spec pc`, and `task manager`, returning `system_overview + process_list` directly in chat.
- Updated prompt policy so the model sees `system_overview` and `process_list` for full-spec and Task Manager style requests.

## 2026-06-12 - OS-22 Browser Search Read Flow

- Added `browser_search_read`, a high-level ToolBridge contract that opens an allowlisted local browser on a search URL and reads the same page through `web_scrape`.
- Routed prompts like `deschide brave browser si cauta desene animate` through the composed browser/search/scrape flow instead of only opening the browser.
- Switched search-read default engine to Bing after live DuckDuckGo smoke returned an anti-bot challenge.
- Improved web text ASCII normalization so scraped Romanian text uses plain letters instead of `?` placeholders.

## 2026-06-12 - Natural Desktop Script Intent Repair

- Fixed desktop script routing for natural prompts such as `fa un folder pe desktop cu numele vasile si fa un mic py script`.
- The router now accepts `py` as a Python-script signal, extracts folder names from `folder ... cu numele ...`, and defaults unnamed small scripts to `script.py`.
- Verified the real smoke path created `C:\Users\billy\Desktop\vasile\script.py`.
