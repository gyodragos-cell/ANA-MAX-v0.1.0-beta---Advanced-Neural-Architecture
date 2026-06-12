# ANA_MAX OS-22 Workflow Playbook

## Runtime Workflow

1. Understand the request.
2. Check RAG context.
3. Decide if a tool is needed.
4. If yes, emit `TOOL_CALL`.
5. If no, answer directly.
6. After tool result, reason briefly.
7. Produce final answer.
8. Prefer stability over creativity.
9. Prefer determinism over improvisation.
10. Prefer safety over speed.

## Engineering Workflow

1. Observe real state.
2. Patch minimally.
3. Add or update tests.
4. Run targeted validation.
5. Update concise docs.
6. Report action, result, and next step.

## Local Debug Workflow

Use the interactive launcher:

```text
scripts/os22/start_os22_agent.bat
```

Then run:

```text
/help
/boot
/status
/tools
/time
/rag OS22
```

