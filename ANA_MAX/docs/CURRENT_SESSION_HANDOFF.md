# Current Session Handoff

Latest checkpoint: `SESSION_CHECKPOINT_2026-06-06T130800Z0000.md`
Timestamp: 2026-06-06T13:08:00+00:00
Memory topic: `session_checkpoint_2026_06_06T130800Z0000`

Open the checkpoint file for the full handoff.

## Standard Reload Flow

Use:

```text
docs/ANA_OPERATOR_RELOAD_RUNBOOK.md
```

It covers:

```text
dry-run VSIX install helper
apply VSIX install when ready
Developer: Reload Window
restart ANA MCP
Post-Reload Verify
Autonomy Pass after marker=True, tool_surface=PASS, and behavior=PASS
```

## Checkpoint Preservation Fix

Local code preserves manual notes in this file when `session_checkpoint_tool.py`
updates the latest pointer. After the clean MCP reload, local and live
checkpoint lanes should both preserve these notes.

Evidence:

```text
docs/examples/SESSION_CHECKPOINT_PRESERVES_NOTES_EXAMPLE.md
tests/runtime/test_session_checkpoint_tool.py
```

For deterministic handoff work, the local source checkpoint remains the
preferred lane:

```powershell
python ANA_MAX/dev_artifacts/scripts/ana_local_checkpoint.py --title "..." --summary "..."
```

## Extension v1.0.71

VSIX v1.0.71 links more Activity Bar commands to both voice and ANA-first
preflight. Command triggers are announced through `onDidExecuteCommand`, action
start/success/fail are spoken through `runInCockpit`, and normal status /
diagnostic / audit commands now route through `runWithGoldenRule` before
executing. Bootstrap controls such as Live Console, Start MCP Server, Codex
Guard, and Live Conversation Audit remain loop-safe exceptions but still speak
their cues.

v1.0.71 includes Activity Bar `Voice Operator Smoke`, backed by
`ana_voice_operator_smoke.py`, so Billy can test the voice queue -> chat bridge
-> conversation audit path from the stable left-side control surface. The real
smoke phrase `ANA voice operator smoke v1.0.71-final...` was audited as
`voice_queue`, proving the local operator voice path is alive; human hearing
still needs Billy's confirmation after reload.

v1.0.71 keeps Activity Bar `Codex Companion`, backed by
`ana_codex_companion.py`, so ANA can observe, route, coach, context-pack, and
challenge Codex before scoped lab work. It keeps `Refresh Context Maps`,
`Review Batch Plan`, `Reload Readiness`, `Reload Consistency`, `Live Behavior`,
`Operator Status`, and keeps `Checkpoint` routed through
`ana_local_checkpoint.py`, so checkpoint saves do not depend on stale live MCP
`session_checkpoint` behavior.

v1.0.71 also includes the bug bounty voice polish: Windows user paths are
redacted case-insensitively before spoken Live Console text enters the queue,
conversation audit redacts Windows user paths even when text enters outside the
extension sanitizer, and noisy Golden Rule / Live Behavior / reload / audit
lines are summarized before speech.

v1.0.71 also starts the private-lab Voice Inbox daemon when the Live Console
opens. The daemon listens in short local System.Speech windows, copies safe
recognized speech to `ANA_MAX/memory/voice_inbox_latest.txt`, and can auto-paste
only prefix-guarded speech (`codex ...` or `ana ...`) into allowed focused
windows. For hands-free Codex prompts, focus the chat input, speak the prefix,
and let the daemon paste and press Enter.

## Reload Consistency Guard

`Operator Status`, `Lab State`, `Post-Reload Verify`, and `Autonomy Pass` now
agree on stale live MCP state. Marker alone is not enough. Before action work,
the live server should show:

```text
marker=True
tool_surface=PASS
behavior=PASS
```

Current clean state after MCP reload:

```text
marker=True
tool_surface=PASS
behavior=PASS(checks=9/9)
```

Reload diagnostics agree now: Live Behavior, Reload Consistency, Post-Reload
Verify, and Operator Status report PASS. Continue with Autonomy Pass or one
scoped lab action. If tool-surface or live-behavior drift returns, `Autonomy
Pass` should prioritize MCP restart over coach-driven action recommendations.

Latest Autonomy Pass after clean reload:

```text
ANA Autonomy: PASS (19 pass / 0 warn / 0 fail) trust=100% trace=19/19 aligned=True
report=ANA_MAX/dev_artifacts/reports/autonomy_runner_20260602_065346.json
```

This pass includes the dry-run `review_batch_plan` step after Patch Advisor.
It plans active review batches without executing the commands from Autonomy.

`ana_live_behavior_check.py` is strict by default and returns non-zero while it
prints `WARN`. Use `--allow-warn` only when collecting diagnostics through a
wrapper; it does not mean the reload passed.

Packaged artifacts:

```text
ANA_MAX/ana-max-codex-cockpit-1.0.71.vsix
vscode_extension/ana-codex-cockpit-1.0.71.vsix
```

Latest v1.0.71 evidence:

```text
focused pytest: 54 passed
full runtime pytest: review batch test PASS
no_reload_quality_gate_20260602_100724.json: PASS 8/8
ANA Nucleus: PASS 10/10
ANA Voice Operator Smoke: PASS audit_seen=True
ANA Operator Status: PASS with review batches 6/6 fresh
git diff --check: no whitespace errors, CRLF warnings only
```
