# ANA MAX Documentation

This folder contains the public-safe documentation for the clean ANA MAX
release.

Start here:

- `../README.md` - plain overview, ethics, quick start, and verification.
- `../SETUP_AND_RUN.md` - first install path for ZIP users, Git users, VS Code,
  and MCP clients.
- `PROJECT_MAP_AI_GUIDE.md` - source-of-truth project map for agents.
- `AI_COLLABORATION_AND_TOOLS.md` - credits and practical guidance for Codex,
  Qoder, and agent-assisted development.
- `LOCAL_QA_LAB_VISION.md` - local/offline QA lab and private workstation
  vision.
- `AGENT_IDE_SUPER_TOOLS_PLAN.md` - positioning and flagship workflow plan for
  agent IDE integrations.
- `USER_EXTENSION_INSTALL_AND_ETHICS.md` - beginner-friendly VS Code extension
  install guide and ethical-use rules.
- `ANA_WORKGRAPH_ARCHITECTURE.md` - observation-first architecture notes.
- `ANA_MAX_WOW_DEMO.md` - 90-second public demo blueprint.
- `MINT_CONDITION_CHECKLIST.md` - final release-polish checklist for keeping
  GitHub clean.
- `LICENSING.md` - Free/Pro licensing overview.

Current public baseline:

```text
80 loaded tools
4 premium-gated tool families in the public message
7 AI Core adapters
```

<!-- # PATCH_START v20_phase3 -->
v20 autonomy tools included in the 80-tool baseline:
`ana_health_check`, `baseline_update_suggester`, `docs_generator`,
`ana_patch_suggester`, `runtime_guard`, and `autonomy_dashboard`.
<!-- # PATCH_END v20_phase3 -->

<!-- # PATCH_START v20_final -->
v20.0.0-alpha is the current public release. Start with `v20_OVERVIEW.md` and
`v20_AUTONOMY_LAYER.md` for the autonomy foundation and dashboard.
<!-- # PATCH_END v20_final -->

<!-- # PATCH_START v19_phase4 -->
v19 diagnostics remain included in the current baseline:
`ana_runtime_inspector`, `tool_contract_validator`, and `schema_diff`.
<!-- # PATCH_END v19_phase4 -->

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

Reader order:

```text
new user -> README.md -> SETUP_AND_RUN.md -> USER_EXTENSION_INSTALL_AND_ETHICS.md
developer -> README.md -> PROJECT_MAP_AI_GUIDE.md -> verification commands
AI agent -> PROJECT_MAP_AI_GUIDE.md -> inspect files -> edit -> verify
```

