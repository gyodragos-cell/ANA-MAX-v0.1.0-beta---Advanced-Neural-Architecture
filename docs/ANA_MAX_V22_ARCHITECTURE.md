# ANA MAX v22 Architecture Plan

Status: Phase 1 architecture only
Scope: dev workspace first; no public release changes yet
Goal: make ANA MAX a token-saving universal orchestrator that observes, routes, executes, and verifies with compact context.

## Design Principles

- Observe before acting.
- Prefer compact structured context over raw dumps.
- Route every action through a scored tool decision.
- Keep risky or mutating actions gated by policy and confirmation.
- Measure latency, output size, and approximate token cost for every tool call.
- Ship only public-safe, tested pieces after the dev version stabilizes.

## Modules

### 1. Input Layer

Responsibilities:
- Accept user tasks from Codex, MCP clients, VS Code, CLI, dashboard, or future agents.
- Normalize requests into one task envelope.
- Attach caller identity, workspace root, permissions, urgency, and requested mode.
- Reject malformed, unauthenticated, or out-of-scope requests early.

Minimal task envelope:

```json
{
  "task": "audit the repo and summarize risks",
  "source": "codex",
  "workspace": "C:/Users/billy/Desktop/ana_dev/ANA_MAX",
  "mode": "observe_only",
  "constraints": ["no_public_release_changes"]
}
```

### 2. Context Builder

Responsibilities:
- Build the smallest useful context for the next decision.
- Merge workspace state, git status, visible UI state, recent tool results, errors, docs, and memory.
- Prefer `workspace_situational_awareness`, `error_radar`, `project_navigator`, and focused file reads over broad scans.
- Cache recent context with freshness timestamps.
- Return explicit blind spots and confidence.

Output shape:

```json
{
  "summary": "Repo dirty; docs available; no tests run yet.",
  "facts": ["80 public tools visible", "dev tree has lab artifacts"],
  "blind_spots": ["active UI not inspected"],
  "confidence": 0.82
}
```

### 3. AI Engine Abstraction

Responsibilities:
- Provide a common interface for Codex and future engines.
- Separate reasoning from tool execution.
- Support model-specific limits, context windows, cost profiles, and streaming behavior.
- Allow fallback engines without changing orchestration logic.

Engines:
- Codex: primary coding and repo-work engine.
- Local LLMs: offline reasoning when available.
- Cloud/provider adapters: optional, policy-controlled.

Interface concept:

```text
plan(task, context) -> candidate_steps
critique(plan, safety_context) -> approved_plan_or_revision
summarize(tool_result, budget) -> compact_result
```

### 4. Tool Router

Responsibilities:
- Select the best tool or no-tool action for each step.
- Score candidates by relevance, risk, cost, context need, latency, reliability, and expected output size.
- Prefer read-only observation tools before mutating tools.
- Enforce tool allowlists, premium gates, workspace boundaries, and confirmation rules.
- Return a route decision with rationale short enough for agent logs.

Scoring inputs:

```json
{
  "tool": "file_operations",
  "relevance": 0.95,
  "risk": 0.15,
  "cost": 0.05,
  "context_fit": 0.9,
  "expected_tokens": 500,
  "requires_confirmation": false
}
```

### 5. Execution Layer

Responsibilities:
- Execute approved tool calls through `ToolRegistry.execute()` or the MCP bridge.
- Normalize results into a stable compact schema.
- Apply output limits, redaction, truncation, and summaries.
- Preserve audit trails without exposing private runtime data.
- Stop immediately on policy failures, tool errors, or unsafe ambiguity.

Normalized result:

```json
{
  "tool": "grep_file",
  "success": true,
  "latency_ms": 43,
  "output_bytes": 812,
  "summary": "Found 6 matching files.",
  "next_hint": "Read the top 2 owners."
}
```

### 6. Observability Layer

Responsibilities:
- Track tool latency, failure rate, output bytes, estimated token savings, and safety decisions.
- Record compact event logs for debugging and learning.
- Expose health endpoints and dashboard summaries.
- Detect noisy tools and route around them when cheaper tools can answer.

Metrics:
- `tool_latency_ms`
- `tool_success_rate`
- `result_output_bytes`
- `estimated_tokens_saved`
- `confirmation_required_count`
- `policy_block_count`

### 7. Scenario Simulator (Optional)

Responsibilities:
- Replay common workflows without touching real user data.
- Test router decisions, token budgets, safety gates, and fallback paths.
- Provide fake tool results for deterministic unit tests.
- Compare reasoning-only vs tool-assisted plans.

Example scenarios:
- Dirty git tree audit.
- Failed test diagnosis.
- UI error detection.
- Public release hygiene check.
- Tool timeout and fallback.

## Data Flow

```text
Input Layer
  -> Context Builder
  -> AI Engine abstraction
  -> Tool Router
  -> Execution Layer
  -> Observability Layer
  -> Context Builder cache
  -> AI Engine final response
```

Feedback loops:
- Execution results refresh context.
- Observability updates tool scores.
- Safety blocks return to the AI engine for a safer plan.
- Simulator runs validate router behavior before real execution.

## Token-Saving Strategy

- Use tools for factual observation instead of reasoning from memory.
- Read only owner files and line ranges, not entire repositories.
- Prefer structured JSON summaries under fixed byte budgets.
- Cache workspace state and reuse it while fresh.
- Summarize large tool outputs before sending them to the AI engine.
- Route by expected token cost, not just capability.
- Track estimated savings: reasoning-only prompt size minus compact tool-assisted context size.

Example:

```text
Reasoning-only: ask model to infer architecture from broad pasted files.
Tool-assisted: grep owners -> read 3 focused ranges -> summarize facts.
Result: fewer tokens, fresher facts, lower hallucination risk.
```

## Safety Model

- Read-only tools are preferred for discovery.
- Mutating file, shell, desktop, network, and Git actions require policy checks.
- Destructive or ambiguous actions require user confirmation.
- Workspace boundaries are enforced before file writes.
- Public release sync requires explicit ship-safe/lab-only classification.
- Private data classes are blocked from public docs and release exports.
- Premium/internal tools remain gated by license and runtime policy.

Safety decision shape:

```json
{
  "allowed": false,
  "reason": "write path escapes workspace root",
  "required_action": "choose allowed workspace or request confirmation"
}
```

## v22 Minimal Viable Slice

1. Add a compact task envelope.
2. Add context budget rules and cached workspace state.
3. Add router scoring for relevance, risk, cost, context, and latency.
4. Normalize tool result summaries.
5. Track latency, output bytes, and estimated token savings.
6. Add simulator tests for router and safety decisions.

## Non-Goals For Phase 1

- No new tools yet.
- No public release edits yet.
- No autonomous write loops.
- No private memory or logs in public outputs.
- No long raw UI dumps as model context.