# ANA_MAX OS-22 Agent Self-Healing V2

Level: Professional Runtime Recovery
Purpose: self-repair guidance, tool auto-diagnostic, and RAG conflict resolution for OS-22.

## 1. Definition

Self-Healing V2 extends V1 with deterministic diagnostics.
It does not mutate OS-22 automatically.
It produces structured metadata and a safe next step.

## 2. Tool Auto-Diagnostic

The agent should inspect:

- whether the tool exists in the manifest
- whether required arguments are present
- whether argument types are plausible
- whether paths stay inside the workspace
- whether the tool result reports an error
- whether the tool appears unavailable or non-responsive
- whether the tool result should be trusted

## 3. RAG Conflict Resolver

When retrieved memory conflicts:

1. Prefer higher importance.
2. Prefer newer timestamps.
3. Prefer exact tag match.
4. If still tied, report uncertainty.

The agent should not invent a merged fact when evidence conflicts.

Additional RAG checks:

- empty context -> minimal direct answer
- irrelevant context -> ignore it
- too-long context -> compress it
- duplicate context -> deduplicate it
- contradictory context -> use highest-ranked local evidence and report uncertainty

## 4. Self-Repair Classification

Issue classes:

- `tool_missing`
- `tool_args_missing`
- `tool_args_invalid`
- `path_outside_workspace`
- `rag_empty`
- `rag_conflict`
- `rag_irrelevant`
- `rag_context_too_long`
- `rag_redundant`
- `reasoning_too_long`
- `tool_call_multiple`
- `persona_drift`
- `preflight_issues`
- `unknown`

## 5. Safe Repair Actions

Allowed actions:

- ask for missing arguments
- suggest an available tool
- ignore irrelevant RAG
- compress final answer
- reset to OS-22 profile
- return a minimal answer

Blocked actions:

- create tools
- edit manifest
- edit architecture
- access external path
- access internet

## 6. Diagnostic Output

The diagnostic should be JSON-friendly:

```text
schema
issue_class
severity
repair_action
safe_to_retry
next_step
```

## 7. Goal

Self-Healing V2 makes the local agent more robust while keeping all recovery bounded, observable, and deterministic.

## 8. Runtime Helpers

Implemented helper APIs:

```text
diagnose_tool_request(tool_name, args)
diagnose_rag_context(query, items, max_context_chars=2000)
resolve_rag_conflicts(items)
classify_text_issue(text)
stabilize_reasoning_text(text)
preflight_diagnostics(...)
get_self_healing_status()
```

Interactive commands:

```text
/heal
/heal <tool_name> [json_args]
/ragheal <query>
/stabilize <text>
```

## 9. Telemetry

Self-Healing V2 writes best-effort JSONL diagnostics to:

```text
ANA_MAX/logs/self_healing_telemetry.jsonl
```

Telemetry must never block agent execution. If logging fails, the diagnostic still returns normally.

## 10. Preventive Loop

Before risky execution, the agent can run:

1. tool diagnostic
2. RAG quality diagnostic
3. text issue classification
4. preflight aggregation
5. minimal repair recommendation

The loop is metadata-only. It does not create tools, edit manifests, edit architecture, access the internet, or access paths outside the workspace.
