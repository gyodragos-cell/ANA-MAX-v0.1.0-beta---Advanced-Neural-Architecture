# ANA_MAX OS-22 Agent Memory Primer

## RAG Flow

1. `RAGBridge` receives a query.
2. `VectorMemoryCortex` searches local semantic memory.
3. `RAGBridge` builds compact context.
4. `LocalLLMBackend.infer_with_rag()` injects that context before the user prompt.
5. `LocalBrainAgent` uses the context during the turn.

## Agent Rules

- Use RAG context if present.
- If context is empty, answer minimally.
- Do not treat RAG as internet.
- Do not invent missing local facts.
- Keep context use concise.

## Useful Debug Commands

```text
/rag <query>
/status
/boot
```

