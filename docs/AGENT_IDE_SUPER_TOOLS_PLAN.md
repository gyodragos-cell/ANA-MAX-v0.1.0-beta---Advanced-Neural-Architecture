# Agent IDE Super Tools Plan

ANA MAX should be presented as a local-first tool orchestration layer for AI
coding agents, not as a general chatbot and not as a claim about being the most
powerful AI.

Short positioning:

```text
ANA MAX is a Windows-first MCP runtime that gives agent IDEs local super tools:
desktop awareness, runtime diagnostics, workflow orchestration, observability,
and verification.
```

Even shorter:

```text
Super tools for local AI coding agents.
```

Expanded:

```text
A local multi-tool runtime for AI agents: observe, diagnose, act, verify, and learn on a real Windows machine.
```

## Target Users

The strongest users are:

- AI coding agents that need real Windows context before editing;
- local/offline agent IDE workflows;
- QA labs and private workstations;
- security and runtime analysis labs with authorized targets;
- developers who need desktop, terminal, git, logs, tests, and runtime signals
  in one MCP-accessible layer.

## What To Prove First

Do not lead with raw tool count alone. Lead with three workflows that work end to end.

### Workflow 1: Desktop Reasoning

Goal:

```text
The agent sees the real Windows desktop or app state before acting.
```

Minimum demo:

- start ANA MAX;
- run `workspace_situational_awareness`;
- capture the desktop with `desktop_capture`;
- inspect structure with `foreground_ui_snapshot` or `windows_uia_bridge`;
- make one small safe action or recommendation;
- verify the visible result.

Success signal:

```text
The agent explains what it can see, what it cannot see, and the next safe step.
```

### Workflow 2: Runtime Diagnostics

Goal:

```text
The agent diagnoses a live failure with local evidence instead of guessing.
```

Minimum demo:

- show a small failing app, script, or test;
- collect repo and terminal state;
- read logs or test output;
- use `frida_instrument` only if runtime instrumentation is needed and
  authorized;
- patch a small issue;
- run verification.

Success signal:

```text
The agent identifies the failure source, applies a targeted fix, and proves it.
```

### Workflow 3: Adaptive Agent IDE Flow

Goal:

```text
The agent uses ANA MAX as a tool layer while working inside an IDE workflow.
```

Minimum demo:

- connect through MCP or the VS Code extension;
- list available tools;
- ask the agent to inspect workspace state;
- perform a small code or docs change;
- run tests;
- report the result with exact command output.

Success signal:

```text
The IDE agent uses observe -> decide -> act -> verify instead of blind edits.
```

## Product Priorities

### 1. Reliability Before Tool Count

The public story should be:

```text
Three reliable workflows matter more than a long tool list.
```

Each flagship workflow needs:

- a known entry command;
- expected output;
- visible failure behavior;
- a verification command;
- a short demo script.

### 2. Observability

Agent IDE users need to trust what happened. Add or expose compact runtime
records for:

- tool timeline;
- tool name, input summary, status, and duration;
- error summaries;
- verification commands;
- blocked premium tools;
- safety decisions and blind spots.

The first useful version can be a local event stream plus a plain text or JSON
summary. It does not need a complex dashboard.

### 3. Security Perception

Desktop control, shell access, network tools, and Frida can look risky if they
are not framed clearly.

Public messaging must emphasize:

- local-first operation;
- explicit MCP authentication;
- premium gates for deep desktop control;
- authorized targets only;
- auditability;
- no private logs, memory, screenshots, tokens, or license files in public git;
- Frida only when normal inspection cannot answer the question.

### 4. IDE Integration Shape

ANA MAX should remain useful as a local MCP runtime. Agent IDEs can integrate
by:

- connecting to `http://127.0.0.1:8765/mcp`;
- sending the configured bearer token;
- calling `tools/list`;
- using observation tools before write tools;
- using verification tools before handoff.

The VS Code extension should be treated as the reference adapter, not the only
adapter. Other agent IDEs can use the same MCP surface.

## Demo Package

Create three public-safe demos:

```text
demo_desktop_reasoning
demo_runtime_diagnostics
demo_agent_ide_flow
```

Each demo should include:

- one clean task;
- no private files;
- no local machine paths in the public script;
- exact commands;
- expected results;
- a short failure note explaining what to do if dependencies are missing.

## Outreach Message

Use a simple technical sentence:

```text
I am exploring local-first runtime orchestration and adaptive desktop tooling
for agent IDE workflows on Windows.
```

Avoid:

```text
I built the most powerful AI ever.
```

Lead with proof:

- three short demos;
- architecture clarity;
- reliability notes;
- security posture;
- MCP integration instructions.

## Near-Term Checklist

- Stabilize the three flagship workflows.
- Keep docs aligned with the release map.
- Make tool timeline and event stream easy to inspect.
- Keep MCP auth enabled by default.
- Keep public docs ASCII-only.
- Keep large videos, logs, memory stores, tokens, and private screenshots out
  of git.
- Prefer smaller, verified tools over new tool count.
