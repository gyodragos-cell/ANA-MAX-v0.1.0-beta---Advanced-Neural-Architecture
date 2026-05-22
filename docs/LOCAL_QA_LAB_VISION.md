# Local QA Lab Vision

ANA MAX is built for agents that must work on a real Windows machine without
guessing and without sending private work outside the environment.

The main use case is not a public cloud chatbot. The main use case is a local
QA lab, security lab, private workstation, or offline LLM setup where the model
needs practical senses:

- eyes: desktop capture, UI Automation, OCR, foreground UI snapshots;
- hands: file edits, terminal commands, controlled desktop actions;
- ears: logs, test output, runtime errors, health checks;
- memory: local lessons, repeated error patterns, self-healing notes;
- instrumentation: Frida only when static inspection and normal logs are not
  enough.

## Why Tools Matter Offline

A local model such as Ollama with Mistral, CodeLlama, Qwen, or another private
model can reason, but it cannot automatically see the desktop, read a terminal,
inspect a Windows window tree, check a port, or remember that it already clicked
the same button ten times.

ANA MAX provides that missing layer through MCP tools.

The target workflow is:

```text
observe -> decide -> act -> verify -> learn
```

This is useful when:

- internet access is blocked;
- source code, client data, malware samples, QA evidence, or logs must stay on
  the machine;
- an AI coding agent needs local facts before editing code;
- a tester needs repeatable desktop observations and smoke checks;
- a lab operator wants voice feedback while watching live failures.

## Tool Groups

Core offline tools:

- `file_operations`
- `terminal`
- `system_control`
- `git_operations`
- `tool_healthcheck`
- `workspace_situational_awareness`

Eyes:

- `desktop_capture`
- `foreground_ui_snapshot`
- `windows_uia_bridge`
- `ocr_tool`

QA and debug:

- `qa_testing`
- `debugger`
- `browser_control`
- `frida_instrument`
- `security_audit`
- `network_diag`

Memory and learning:

- `memory_cortex`
- `context_bridge`
- `context_engine`
- `proactive_interrupt`
- `self_evolving_tool`

Voice:

- `edge_tts_voice`

## What ANA MAX Is Not

ANA MAX is not meant to be a pile of tools for screenshots and hype. Tool
quality matters more than tool count.

The agent should use the smallest useful tool:

- inspect the UI before clicking;
- read logs before changing code;
- run tests before claiming a fix;
- use Frida only for authorized runtime instrumentation;
- verify the result after each important action.

## Public Demo Rule

Do not store large videos in git. Use YouTube, GitHub Releases, or another
external video host, then link from the README or website.

The repository should contain source code, docs, tests, and small public-safe
assets only. It must not contain private memory, logs, tokens, local shortcuts,
databases, or screenshots with private content.
