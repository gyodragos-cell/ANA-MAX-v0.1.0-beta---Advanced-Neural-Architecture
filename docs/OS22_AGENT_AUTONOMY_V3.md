# ANA_MAX OS-22 Agent Autonomy V3

Level: Controlled Professional Autonomy
Purpose: bounded goal tracking, confidence scoring, and recovery-aware execution without changing OS-22 architecture.

## 1. Definition

Autonomy V3 adds controlled local initiative.
The agent may manage a small task goal, score confidence, and choose a safe next step.

It must not create tools, edit architecture, leave the workspace, access internet, or ignore OS-22 rules.

## 2. Goal Tracking

The agent may track:

- current objective
- known inputs
- missing inputs
- completed steps
- next safe step

## 2.1 Micro-Planning

For complex local tasks, the agent can form a compact multi-turn plan:

1. inspect RAG
2. choose one tool if needed
3. reason over the result
4. choose the next safe tool if still needed
5. summarize progress
6. optimize context for the next turn

The plan is advisory metadata. It must not bypass the one-tool-per-turn rule.

## 3. Confidence Scoring

The agent may classify confidence:

- `high`: enough context and tool evidence
- `medium`: partial context but safe direct answer
- `low`: missing input or conflicting evidence

Low confidence should trigger clarification or minimal answer.

## 4. Recovery-Aware Execution

Before responding, the agent checks:

1. Is RAG relevant?
2. Is a tool more precise?
3. Did a tool fail?
4. Is a fallback answer safe?
5. Is clarification required?

## 4.1 Tool Orchestration

The agent can classify tools before use:

- required: needed for correctness
- useful: improves precision
- redundant: duplicates another tool
- risky: needs operator intent
- avoid: outside the manifest or workspace boundary

Only one `TOOL_CALL` may be emitted per turn.

## 5. Proactive Suggestions

The agent may suggest one next step when useful.

Allowed examples:

```text
Next: run /rag <query>.
Next: use /tools to inspect available tools.
Next: provide the workspace file path.
```

## 6. Memory Discipline

The agent may suggest storing stable facts in memory, but must not store noisy data automatically unless routed through an explicit tool call or operator action.

Memory shaping rules:

- keep stable facts
- reject noisy snippets
- compress repeated context
- prefer recent local evidence
- suggest storage only when it improves future turns

## 6.1 Context Awareness

The agent should track:

- the current user goal
- completed steps
- pending blockers
- intent changes
- the next safe action

If intent changes, the agent should adapt the next step instead of continuing an obsolete plan.

## 7. Tool Discipline

The agent may plan multi-tool chains, but must emit only one tool call per turn.

## 8. Safety Boundary

Autonomy V3 remains:

- local-only
- manifest-only
- workspace-bounded
- profile-stable
- deterministic

## 9. Goal

Autonomy V3 brings the local agent closer to a senior runtime operator while preserving predictable OS-22 execution.

## 10. V3 Loop

Autonomy V3 follows this bounded loop:

1. understand request
2. inspect RAG
3. create compact plan
4. choose one tool or answer directly
5. execute one tool call if needed
6. reason briefly over result
7. update progress metadata
8. compress context
9. self-audit with Self-Healing V2
10. provide a final answer or next safe step
