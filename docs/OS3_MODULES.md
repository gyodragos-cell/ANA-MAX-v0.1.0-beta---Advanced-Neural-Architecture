# ANA MAX OS-3 Modules

## Self-Profiling Engine

**File**: `ANA_MAX/self_optimization/self_profiling_engine.py`

**Purpose**: Measures tool latency, I/O performance, CPU/RAM/disk usage, and detects performance degradation.

**Main APIs**:
- `profile_tools(tool_names, iterations)` - Profile tool latency using direct bridge
- `profile_system()` - Profile current system resource usage
- `log_performance()` - Write profiling results to PERFORMANCE_LOG.md and performance_profile.json
- `run_cycle(iterations)` - Run complete profiling cycle

**Inputs**:
- Tool names to profile (optional, defaults to core tools)
- Number of benchmark iterations (default: 10)

**Outputs**:
- `docs/PERFORMANCE_LOG.md` - Human-readable performance log
- `ANA_MAX/memory/performance_profile.json` - Machine-readable profile data

**Artifacts Generated**:
- ToolProfile objects with latency metrics (avg, min, max, p95, success rate)
- SystemProfile objects with resource metrics (CPU, memory, disk)
- Degradation reports for slow tools

---

## Self-Healing Engine

**File**: `ANA_MAX/self_optimization/self_healing_engine.py`

**Purpose**: Detects errors, regressions, inconsistencies, proposes safe fixes, applies patches, and re-runs tests.

**Main APIs**:
- `detect_failures()` - Detect errors, test failures, and regressions
- `propose_fixes()` - Propose safe fixes for detected failures
- `apply_safe_patch(proposal)` - Apply a safe patch if marked as safe
- `re_run_tests()` - Re-run test suite after applying fixes
- `log_healing_actions()` - Log healing actions to TEST_REPORT.md and CHANGELOG.md
- `run_cycle()` - Run complete healing cycle

**Inputs**:
- None (scans system state automatically)

**Outputs**:
- `docs/TEST_REPORT.md` - Test results and healing actions
- `docs/CHANGELOG.md` - Healing actions logged

**Artifacts Generated**:
- Failure objects with type, location, severity, context
- FixProposal objects with fix type, description, safety flag
- HealingAction objects with timestamp, action, result

---

## Self-Structuring Engine

**File**: `ANA_MAX/self_optimization/self_structuring_engine.py`

**Purpose**: Analyzes project structure, identifies redundant/duplicated files, proposes safe reorganizations, defines canonical layout.

**Main APIs**:
- `scan_structure(max_depth)` - Scan project structure and build file node map
- `detect_redundancy()` - Detect redundant files, similar names, empty directories, large files
- `propose_reorg()` - Propose safe reorganizations based on canonical layout
- `apply_reorg(proposal, dry_run)` - Apply a reorganization proposal
- `update_documentation()` - Update TECHNICAL_NOTES.md and OPTIMIZATIONS.md
- `run_cycle(dry_run)` - Run complete structuring cycle

**Inputs**:
- Max scan depth (default: 5)
- Dry run flag (default: True for safety)

**Outputs**:
- `docs/TECHNICAL_NOTES.md` - Restructuring findings
- `docs/OPTIMIZATIONS.md` - Reorganization proposals

**Artifacts Generated**:
- FileNode objects with path, size, hash, last modified
- RedundancyReport with duplicate groups, similar names, empty directories
- ReorganizationProposal with type, source, target, reason, safety flag

---

## Self-Expanding Skills Layer

**File**: `ANA_MAX/self_optimization/self_skills_engine.py`

**Purpose**: Identifies missing capabilities, generates skills, updates skills manifest, documents skills in AGENTS.md and ANA_MEMORY.md.

**Main APIs**:
- `detect_missing_capabilities()` - Identify missing capabilities based on project needs
- `generate_skill(gap)` - Generate a skill from a capability gap
- `update_skills_manifest()` - Update the skills manifest JSON file
- `document_skills()` - Document skills in AGENTS.md and ANA_MEMORY.md
- `run_cycle()` - Run complete skills expansion cycle

**Inputs**:
- None (scans project automatically)

**Outputs**:
- `ANA_MAX/memory/skills_manifest.json` - Skills manifest
- `docs/AGENTS.md` - Skills documentation
- `docs/ANA_MEMORY.md` - Skills documentation

**Artifacts Generated**:
- Skill objects with name, category, description, status, priority
- CapabilityGap objects with name, description, category, priority, solution

---

## Self-Documenting Knowledge Graph

**File**: `ANA_MAX/self_optimization/knowledge_graph_engine.py`

**Purpose**: Maps relationships between tools, modules, and docs; generates diagrams and structured descriptions.

**Main APIs**:
- `scan_project()` - Scan project and build node map
- `build_graph()` - Build the complete knowledge graph with nodes and edges
- `render_markdown()` - Render knowledge graph as markdown documentation
- `save_graph()` - Save knowledge graph to JSON and markdown files
- `run_cycle()` - Run complete knowledge graph cycle

**Inputs**:
- None (scans project automatically)

**Outputs**:
- `ANA_MAX/memory/knowledge_graph.json` - Machine-readable graph data
- `docs/KNOWLEDGE_GRAPH.md` - Human-readable graph documentation

**Artifacts Generated**:
- Node objects with id, type, name, path, description
- Edge objects with source, target, type, weight
- KnowledgeGraph with nodes, edges, metadata

---

## GitHub Pattern Extractor

**File**: `ANA_MAX/self_optimization/github_pattern_extractor.py`

**Purpose**: Analyzes provided repositories, extracts patterns, proposes integrations (user-triggered only).

**Main APIs**:
- `analyze_repo(repo_path_or_snapshot)` - Analyze a repository snapshot or path
- `extract_patterns(analysis)` - Extract useful patterns from repository analysis
- `propose_integrations(patterns)` - Propose integrations for extracted patterns
- `write_patterns_to_docs()` - Write patterns and integrations to TECHNICAL_NOTES.md and OPTIMIZATIONS.md
- `run_cycle(repo_path_or_snapshot)` - Run complete extraction cycle

**Inputs**:
- Repository path or snapshot (required, user-provided)

**Outputs**:
- `docs/TECHNICAL_NOTES.md` - Extracted patterns
- `docs/OPTIMIZATIONS.md` - Integration proposals

**Artifacts Generated**:
- Pattern objects with type, name, description, source, confidence
- IntegrationProposal with pattern name, integration type, target, rationale

---

## Self-Evolution Engine

**File**: `ANA_MAX/self_optimization/self_evolution_engine.py`

**Purpose**: Orchestrates all OS-3 modules for continuous evolution with OBSERVE  ANALYZE  PLAN  ACT  VERIFY  DOCUMENT cycle.

**Main APIs**:
- `run_cycle()` - Run complete evolution cycle (orchestrates all modules)
- `plan_next_steps(horizon_hours)` - Generate plan for next evolution steps
- `coordinate_modules()` - Coordinate between all OS-3 modules
- `update_roadmap(cycle_result)` - Update ROADMAP.md with evolution cycle results

**Inputs**:
- Planning horizon in hours (default: 24)

**Outputs**:
- `docs/ROADMAP.md` - Evolution cycle results and next steps

**Artifacts Generated**:
- EvolutionStep objects with phase, action, result, timestamp, success
- EvolutionPlan with timestamp, horizon, steps, priorities, estimated completion

---

## Multi-Agent Orchestrator

**File**: `ANA_MAX/self_optimization/multi_agent_orchestrator.py`

**Purpose**: Coordinates multiple agents with different roles (Optimizer, Tester, Documenter, Structurer, Extractor) with shared state mechanism.

**Main APIs**:
- `assign_tasks(task_type)` - Assign tasks to agents based on their roles
- `sync_state()` - Synchronize shared state across all agents
- `merge_results()` - Merge results from all agents into unified output
- `execute_agent_task(task)` - Execute a single agent task
- `run_orchestration_cycle()` - Run complete multi-agent orchestration cycle

**Inputs**:
- Task type (full_cycle, optimization, testing)

**Outputs**:
- `ANA_MAX/memory/multi_agent_shared_state.json` - Shared state file

**Artifacts Generated**:
- AgentTask objects with agent, task_type, description, priority, status, result
- SharedState with timestamp, performance, structure, tests, skills, graph, agent_tasks
