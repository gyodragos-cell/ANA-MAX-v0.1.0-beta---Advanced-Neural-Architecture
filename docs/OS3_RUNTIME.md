# ANA MAX OS-3 Runtime Guide

## Running Single Module Cycles

Each OS-3 module can be run independently via CLI:

### Self-Profiling Engine

```powershell
# Run complete profiling cycle
python ANA_MAX/self_optimization/self_profiling_engine.py --cycle

# Profile specific tools
python ANA_MAX/self_optimization/self_profiling_engine.py --tools agent_coach tool_router

# Profile system resources only
python ANA_MAX/self_optimization/self_profiling_engine.py --system-only

# Custom iterations
python ANA_MAX/self_optimization/self_profiling_engine.py --cycle --iterations 20
```

### Self-Healing Engine

```powershell
# Run complete healing cycle
python ANA_MAX/self_optimization/self_healing_engine.py --cycle

# Detect failures only
python ANA_MAX/self_optimization/self_healing_engine.py --detect-only

# Propose fixes only
python ANA_MAX/self_optimization/self_healing_engine.py --propose-only
```

### Self-Structuring Engine

```powershell
# Run complete structuring cycle (dry run by default)
python ANA_MAX/self_optimization/self_structuring_engine.py --apply

# Scan structure only
python ANA_MAX/self_optimization/self_structuring_engine.py --scan-only

# Detect redundancy only
python ANA_MAX/self_optimization/self_structuring_engine.py --detect-only

# Propose reorganizations only
python ANA_MAX/self_optimization/self_structuring_engine.py --propose-only

# Apply changes (disable dry run)
python ANA_MAX/self_optimization/self_structuring_engine.py --apply --dry-run=false
```

### Self-Expanding Skills Layer

```powershell
# Run complete skills expansion cycle
python ANA_MAX/self_optimization/self_skills_engine.py --cycle

# Detect missing capabilities only
python ANA_MAX/self_optimization/self_skills_engine.py --detect-only

# Generate skills only
python ANA_MAX/self_optimization/self_skills_engine.py --generate-only
```

### Self-Documenting Knowledge Graph

```powershell
# Run complete knowledge graph cycle
python ANA_MAX/self_optimization/knowledge_graph_engine.py --cycle

# Scan project only
python ANA_MAX/self_optimization/knowledge_graph_engine.py --scan-only

# Build graph only
python ANA_MAX/self_optimization/knowledge_graph_engine.py --build-only

# Render markdown only
python ANA_MAX/self_optimization/knowledge_graph_engine.py --render-only
```

### GitHub Pattern Extractor

```powershell
# Run complete extraction cycle (requires repo path)
python ANA_MAX/self_optimization/github_pattern_extractor.py <repo_path> --cycle

# Analyze repository only
python ANA_MAX/self_optimization/github_pattern_extractor.py <repo_path> --analyze-only

# Extract patterns only
python ANA_MAX/self_optimization/github_pattern_extractor.py <repo_path> --extract-only
```

### Self-Evolution Engine

```powershell
# Run complete evolution cycle (orchestrates all modules)
python ANA_MAX/self_optimization/self_evolution_engine.py --cycle

# Generate next steps plan
python ANA_MAX/self_optimization/self_evolution_engine.py --plan

# Coordinate modules
python ANA_MAX/self_optimization/self_evolution_engine.py --coordinate

# Custom planning horizon
python ANA_MAX/self_optimization/self_evolution_engine.py --plan --horizon 48
```

### Multi-Agent Orchestrator

```powershell
# Run complete orchestration cycle
python ANA_MAX/self_optimization/multi_agent_orchestrator.py --cycle

# Assign tasks only
python ANA_MAX/self_optimization/multi_agent_orchestrator.py --assign full_cycle

# Synchronize shared state only
python ANA_MAX/self_optimization/multi_agent_orchestrator.py --sync

# Merge results only
python ANA_MAX/self_optimization/multi_agent_orchestrator.py --merge

# Assign specific task type
python ANA_MAX/self_optimization/multi_agent_orchestrator.py --assign optimization
```

## Running Full Evolution Cycle

The Self-Evolution Engine orchestrates all modules in a single cycle:

```powershell
python ANA_MAX/self_optimization/self_evolution_engine.py --cycle
```

This executes:
1. Profiling (measure performance)
2. Healing (detect and fix issues)
3. Structuring (analyze and propose reorganizations)
4. Skills (expand capabilities)
5. Knowledge Graph (update documentation)
6. ROADMAP update (log next steps)

## Running Multi-Agent Orchestration

The Multi-Agent Orchestrator coordinates specialized agents:

```powershell
python ANA_MAX/self_optimization/multi_agent_orchestrator.py --cycle
```

This executes:
1. Optimizer Agent (profiling + structuring + skills)
2. Tester Agent (healing + tests)
3. Documenter Agent (docs + knowledge graph)
4. Structurer Agent (filesystem / layout)
5. Extractor Agent (github pattern extractor, if input available)

## Runtime Artifacts

OS-3 modules generate the following artifacts:

**Documentation** (in `docs/`):
- `PERFORMANCE_LOG.md` - Performance profiling results
- `TEST_REPORT.md` - Test results and healing actions
- `KNOWLEDGE_GRAPH.md` - Knowledge graph documentation
- `TECHNICAL_NOTES.md` - Technical notes and patterns
- `OPTIMIZATIONS.md` - Optimization proposals
- `ROADMAP.md` - Evolution cycle results and next steps
- `CHANGELOG.md` - Healing actions and changes

**State/Memory** (in `ANA_MAX/memory/`):
- `performance_profile.json` - Machine-readable performance data
- `skills_manifest.json` - Skills and capabilities manifest
- `knowledge_graph.json` - Machine-readable graph data
- `multi_agent_shared_state.json` - Multi-agent shared state

## Safety Considerations

- All modules default to dry-run mode where applicable
- Destructive operations require explicit flags (e.g., `--dry-run=false`)
- GitHub Pattern Extractor only runs on explicit user input
- All actions are logged before execution
- Changes are applied incrementally with verification

## Scheduling Evolution Cycles

For continuous evolution, schedule periodic runs:

```powershell
# Windows Scheduled Task example
# Run daily evolution cycle at 2 AM
python ANA_MAX/self_optimization/self_evolution_engine.py --cycle

# Or use the existing daily script
powershell -ExecutionPolicy Bypass -File scripts/ana_daily.ps1
```
