# ANA_MAX OS-22 Agent Operating Pack

This pack collects the durable OS-22 agent onboarding and runtime documents.

## Included Documents

1. `docs/OS22_AGENT_SELF_INIT.md`
2. `docs/OS22_AGENT_BOOT_BANNER.md`
3. `docs/OS22_AGENT_CONTRACT.md`
4. `docs/OS22_AGENT_TRAINING_LESSONS.md`
5. `docs/OS22_AGENT_ADVANCED_TRAINING.md`
6. `docs/OS22_AGENT_SANDBOX_SCENARIOS.md`
7. `docs/OS22_AGENT_MASTER_CLASS.md`
8. `docs/OS22_AGENT_AUTONOMY_V1.md`
9. `docs/OS22_AGENT_AUTONOMY_V2.md`
10. `docs/OS22_AGENT_AUTONOMY_V3.md`
11. `docs/OS22_AGENT_SELF_HEALING_V1.md`
12. `docs/OS22_AGENT_SELF_HEALING_V2.md`
13. `docs/OS22_AGENT_MEMORY_PRIMER.md`
14. `docs/OS22_TOOL_AWARENESS_PACK.md`
15. `docs/OS22_REASONING_GRAPH_PRIMER.md`
16. `docs/OS22_WORKFLOW_PLAYBOOK.md`
17. `docs/OS22_AGENT_FOUNDATION.md`

## Unified Foundation

`docs/OS22_AGENT_FOUNDATION.md` is the single unified foundation document.
It combines identity, environment, architecture, boot behavior, contract,
training lessons, memory, tools, reasoning graph, workflow, limitations, and
final goals.

## Operational Mastery Layer

- `docs/OS22_AGENT_SANDBOX_SCENARIOS.md`: 20 advanced scenario checks.
- `docs/OS22_AGENT_MASTER_CLASS.md`: 12 expert self-audit and optimization modules.
- `docs/OS22_AGENT_AUTONOMY_V1.md`: bounded autonomy rules and limits.
- `docs/OS22_AGENT_AUTONOMY_V2.md`: multi-turn planning, tool orchestration, and memory shaping.
- `docs/OS22_AGENT_AUTONOMY_V3.md`: controlled goal tracking, confidence scoring, and recovery-aware execution.
- `docs/OS22_AGENT_SELF_HEALING_V1.md`: runtime problem detection and basic recovery.
- `docs/OS22_AGENT_SELF_HEALING_V2.md`: tool auto-diagnostic and RAG conflict resolver.

## Runtime Profiles

- `codex`: engineering profile.
- `os22_core`: deterministic runtime profile.

## Validation

Run:

```text
python -m compileall -q ANA_MAX scripts
python -m pytest tests/test_agent_foundation.py tests/test_agent_boot_banner.py tests/test_start_local_llm_agent.py tests/test_prompt_profiles.py -q
```
