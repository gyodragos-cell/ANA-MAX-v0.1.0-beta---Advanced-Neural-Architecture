# ANA MAX Documentation

This folder contains the public-safe documentation for the clean ANA MAX
release.

Start here:

- `PROJECT_MAP_AI_GUIDE.md` - source-of-truth project map for agents.
- `LOCAL_QA_LAB_VISION.md` - local/offline QA lab and private workstation
  vision.
- `AGENT_IDE_SUPER_TOOLS_PLAN.md` - positioning and flagship workflow plan for
  agent IDE integrations.
- `ANA_WORKGRAPH_ARCHITECTURE.md` - observation-first architecture notes.
- `ANA_MAX_WOW_DEMO.md` - 90-second public demo blueprint.
- `LICENSING.md` - Free/Pro licensing overview.

Current public baseline:

```text
64 loaded tools
4 premium-gated tool families in the public message
9 AI Core adapters
```

Required verification:

```powershell
python -m compileall -q main.py core tools vscode_extension
python main.py --test
python main.py --list-tools
python -m unittest discover -s tests -v
```

Documentation rules:

- Keep public docs ASCII-only.
- Do not include private paths, tokens, memory stores, logs, local shortcuts, or
  screenshots with private content.
- Do not document tools that are not present and executable in this clean
  release.
- Prefer exact workflow proof over broad claims.
