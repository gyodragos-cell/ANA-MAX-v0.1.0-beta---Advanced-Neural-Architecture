# Local LLM Setup v1

## Overview

ANA MAX uses Python 3.12 as the main OS-21.5 development interpreter. The local
LLM backend can optionally use a separate Python 3.11 environment for OLLM,
Phi-3 Medium, Phi-3 Mini, and future local RAG or LoRA helpers.

The local LLM setup is explicit and user-controlled. Nothing installs, downloads,
or enables inference unless you run the matching script with `--apply`.

The current default runtime backend is `llama_cpp` with the local Phi-3 Mini
GGUF file. `ollm` remains optional for alternate local backends, but it is no
longer required for the default starter flow.

## Layout

```text
local_llm_env/
local_models/
.env.local_llm
requirements_local_llm.txt
scripts/local_llm/
```

The local requirements file now includes `pytest` so the dedicated
`local_llm_env` can run the local LLM test suite directly.

## Install Python 3.11

Install Python 3.11 for Windows from your preferred local installer source.
Do not replace `python.exe` for the main ANA MAX runtime. Keep Python 3.12 as the
main interpreter and expose Python 3.11 as one of:

```text
python311.exe
python3.11.exe
py -3.11
```

## Create local_llm_env

Dry-run inspection:

```text
python scripts/local_llm/create_local_llm_env.py
```

Create the environment:

```text
python scripts/local_llm/create_local_llm_env.py --apply
```

Use an explicit Python 3.11 executable:

```text
python scripts/local_llm/create_local_llm_env.py --python311 C:\Path\To\python311.exe --apply
```

## Activate and deactivate

PowerShell:

```text
.\scripts\local_llm\activate_local_llm_env.ps1
.\scripts\local_llm\deactivate_local_llm_env.ps1
```

CMD:

```text
scripts\local_llm\activate_local_llm_env.bat
scripts\local_llm\deactivate_local_llm_env.bat
```

Activation loads `.env.local_llm` into the current process and activates
`local_llm_env` if it exists.

## Install OLLM

Dry-run:

```text
python scripts/local_llm/install_ollm_backend.py
```

Install from `requirements_local_llm.txt` inside `local_llm_env`:

```text
python scripts/local_llm/install_ollm_backend.py --apply
```

This is the only script in this setup that calls `pip`, and it only does so with
`--apply`. On Windows it uses a CPU-safe strategy:

```text
pip install --no-deps ollm
pip install -r requirements_local_llm.txt
```

This avoids auto-building optional flash-attention packages that are not needed
for the default safe backend check.

## Install models

The model helper accepts a user-provided local file path or URL. No model URL is
hardcoded in the repository.

Dry-run:

```text
python scripts/local_llm/install_models.py --model phi3-medium
```

Copy a local model file:

```text
python scripts/local_llm/install_models.py --model phi3-medium --source C:\Models\phi3-medium-q5_k_m.gguf --apply
```

Download from a user-provided URL:

```text
python scripts/local_llm/install_models.py --model phi3-mini --source https://example.invalid/model.gguf --apply
```

If the URL is gated or returns `401 Unauthorized`, provide a Hugging Face token
through `--token`, `HUGGINGFACE_HUB_TOKEN`, or `HF_TOKEN`:

```text
python scripts/local_llm/install_models.py --model phi3-medium --source https://huggingface.co/.../model.gguf --token hf_xxx --apply
```

Expected model filenames:

```text
local_models/phi3-medium-q5_k_m.gguf
local_models/phi3-mini-q5_k_m.gguf
```

## Test backend

Metadata-only test:

```text
local_llm_env\Scripts\python.exe scripts/local_llm/test_local_brain.py
```

Try a tiny inference only if OLLM is available:

```text
local_llm_env\Scripts\python.exe scripts/local_llm/test_local_brain.py --infer
```

## Start model

Double-click or run this to open the local chat loop:

```text
scripts\local_llm\start_local_llm.bat
```

For a more direct lab-oriented prompt style on Windows, use:

```text
scripts\local_llm\start_local_llm_lab.bat
```

or pass the profile directly:

```text
local_llm_env\Scripts\python.exe scripts\local_llm\start_local_llm.py --profile lab --interactive
```

Interactive OS-22 debug commands:

```text
/help
/status
/boot
/foundation
/heal
/heal read_file {"path": "docs/OS22_AGENT_FOUNDATION.md"}
/ragheal OS22
/tools
/time
/tool current_time
/tool system_info
/open file:///C:/Users/billy/Desktop/ana_dev/ANA_MAX/sandbox/os22_browser_smoke.html
/rag OS22 smoke marker
```

The interactive launcher prints the OS-22 boot banner by default. Use
`--no-banner` only when you need cleaner machine-readable console output.

If you want a full local rebuild and smoke pass, use:

```text
scripts\local_llm\rebuild_local_llm_stack.bat
```

## Validate setup

```text
python scripts/local_llm/validate_local_llm_setup.py
```

or from Python 3.11:

```text
local_llm_env\Scripts\python.exe scripts/local_llm/validate_local_llm_setup.py
```

The validator reports:

- main Python version
- local Python 3.11 env presence
- OLLM availability
- `.env.local_llm` values
- configured model file presence
- overall readiness

When the default backend is `llama_cpp`, the validator also checks that
`llama_cpp` is installed in `local_llm_env` and that the configured GGUF file is
present.

## Enable local brain

Default:

```text
ANA_LOCAL_LLM_ENABLED=0
```

To enable after setup, edit `.env.local_llm`:

```text
ANA_LOCAL_LLM_ENABLED=1
```

ANA MAX still runs safely when the flag is `0`, when OLLM is missing, or when
model files are absent.
