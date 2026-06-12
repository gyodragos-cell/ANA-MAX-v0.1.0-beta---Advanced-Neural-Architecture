# OS-22 Launch Readiness

## Purpose

This document describes the final local launch gate for ANA_MAX OS-22.
The gate checks Python, the local LLM environment, requirements, models,
startup scripts, OS-22 boot, OS-22 doctor, and focused tests.

## Launch Audit

Run:

```text
python scripts\os22\os22_launch_audit.py --write-report
```

Optional focused tests:

```text
python scripts\os22\os22_launch_audit.py --write-report --run-tests
```

The report is written to:

```text
ANA_MAX\memory\os22_launch_audit_report.json
```

## Checked Items

- Main Python is 3.12.x.
- Local LLM Python is 3.11.x.
- `requirements.txt` and `requirements_local_llm.txt` exist.
- Required local LLM modules are importable in `local_llm_env`.
- `.env.local_llm` points to the `llama_cpp` backend.
- The configured GGUF model exists.
- OS-22 doctor reports `READY`.
- OS-22 boot reports `READY`.
- Focused tests pass when `--run-tests` is used.

## Required Install Status

If the launch audit reports missing required modules, run:

```text
.\local_llm_env\Scripts\python.exe -m pip install -r requirements_local_llm.txt
```

Optional modules:

- `beautifulsoup4`: only needed for legacy `WebScraperTool` parse/extract operations.
- `ollm`: only needed if switching back from `llama_cpp` to the old `ollm` backend.

## Launch

Start the OS-22 interactive agent:

```text
scripts\os22\start_os22_agent.bat
```

The default interactive chat uses the `ana_chat` profile. It is the natural
conversation profile for talking with the local agent while keeping RAG and
ToolBridge available in the background.

Strict deterministic runtime mode remains available:

```text
scripts\os22\start_os22_core_agent.bat
```

Start the full lab runtime with OS/tools and a separate chat window:

```text
scripts\os22\start_os22_lab_chat.bat
```

Default behavior starts OS/tools readiness checks and a separate Phi-3 chat
window plus an OS-22 live log window. It does not start the old Ollama-backed legacy server. If that legacy
server is explicitly needed, use:

```text
scripts\os22\start_os22_lab_chat.bat --legacy-server
```

The live log follows:

```text
ANA_MAX\logs\os22_chat.log
ANA_MAX\local\tool_telemetry.log
```

Strict model smoke:

```text
.\local_llm_env\Scripts\python.exe .\scripts\local_llm\start_local_llm.py --smoke --profile os22_core --backend llama_cpp --model-path .\local_models\phi3-mini-q5_k_m.gguf --prompt "Return exactly: READY" --max-tokens 16 --temperature 0
```

## Policy

- Local-only.
- No cloud.
- No external APIs.
- No automatic installs.
- No OS-20.1 runtime behavior changes.
