# ANA_MAX OS-22 Agent Boot Banner

This is the operator-facing banner shown when the interactive OS-22 agent starts.

```text
============================================================
ANA_MAX OS-22 AGENT - BOOT SEQUENCE
Model: Phi-3 Mini - GGUF - Q5_K_M
Backend: llama_cpp
Mode: Deterministic Runtime
Profile: os22_core
============================================================
Initializing RAGBridge... OK
Initializing ToolBridge... OK
Initializing VectorMemoryCortex... OK
Initializing Reasoning Graph... OK
Initializing Telemetry Stream... OK
Initializing Agent Foundation... OK
Initializing LocalBrainAgent... OK

Agent status: READY
Welcome to ANA_MAX OS-22.
```

## Rules

- The banner is informational and local-only.
- The launcher may print `WARN` if a component is unavailable.
- The banner must stay ASCII-only.
- The banner must not load cloud services or remote endpoints.
