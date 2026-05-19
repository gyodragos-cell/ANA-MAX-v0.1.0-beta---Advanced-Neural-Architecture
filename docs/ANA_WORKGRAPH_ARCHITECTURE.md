# ANA WorkGraph Architecture

ANA WorkGraph is the observation and reasoning layer for ANA MAX. Its goal is
not to add hundreds of tools. Its goal is to make every agent see enough context
to choose the right tool and avoid working blind.

## North Star

A useful agent should reduce real task time, detect errors early, verify before
handoff, and explain what it can and cannot see.

For this project, quality beats tool count:
- Prefer 10 reliable tools that compose well over 100 noisy tools.
- Every tool must answer a clear job: observe, diagnose, act, verify, or learn.
- Do not add a tool only because it is possible to add one.
- If a task can be solved with an existing tool plus better output, improve the
  existing tool.

## Observation First

Before editing files, clicking UI, running destructive commands, or claiming a
task is done, an agent should collect a compact workspace state.

Minimum state:
- active app and window title
- repo path, branch, and git status
- open files when visible
- last terminal command status when available
- visible UI errors or dialogs
- relevant logs or test failures
- confidence score and blind spots

The state must be compact JSON, not a huge UI dump. A good target is under 8 KB.

Example:

```json
{
  "schema": "ana.workgraph.workspace_state.v1",
  "active_window": {
    "app": "Code.exe",
    "title": "ANA_MAX_GitHub_Release - Visual Studio Code",
    "visibility_quality": "good"
  },
  "workspace": {
    "repo": "ANA_MAX_GitHub_Release",
    "branch": "main",
    "git_clean": true,
    "modified_files": []
  },
  "signals": {
    "errors": [],
    "warnings": [],
    "important_text": ["63 loaded tools", "63 tests OK"]
  },
  "recommended_next_step": "No blocking errors detected. Safe to continue.",
  "confidence": 0.86,
  "blind_spots": []
}
```

## Tool Selection Rule

Agents must choose tools by task, not by habit.

- Use `git_operations` or direct git commands for repository state.
- Use `windows_uia_bridge` or `foreground_ui_snapshot` for visible Windows UI.
- Use `desktop_capture` and OCR only when structural UI is incomplete.
- Use `frida_instrument` only for dynamic runtime instrumentation, mobile app
  analysis, process hooks, or cases where static inspection cannot answer the
  question.
- Use `network_diag`, `network_pentest`, or `mitm_analyzer` only for network
  tasks with an authorized target.
- Use `security_audit` before release when secrets or public hygiene matter.
- Use tests and compile checks before saying a code change is complete.

Frida is powerful, but it should not become the default hammer. The right order
is: inspect files, inspect runtime state, choose the smallest useful tool, then
verify.

## WorkGraph Layers

### 1. Structural Eyes

Purpose: observe the current workspace and visible UI.

Inputs:
- UI Automation tree for the active window
- foreground screenshot when needed
- OCR fallback when UIA is partial
- git status
- terminal/test output
- open files and repo metadata

Output:
- compact JSON
- confidence score
- explicit blind spots
- suggested next step

Rules:
- Observe only. Do not mutate state.
- Return relevant elements, not entire trees.
- Mark `visibility_quality` as `good`, `partial`, or `unknown`.
- Prefer native Windows/Python APIs where practical.

### 2. Error Radar

Purpose: detect likely blockers before the user has to notice them.

Sources:
- terminal exit codes and stderr
- Python tracebacks
- test failures
- VS Code Problems panel when visible
- browser console or network failures when available
- Windows error dialogs
- release logs, excluding private runtime logs from public commits

Output:
- prioritized errors
- suspected root cause
- suggested verification command
- whether the agent can fix safely

### 3. Self QA

Purpose: verify before handoff.

Release checks:

```powershell
python -m compileall -q main.py core tools vscode_extension
python main.py --test
python main.py --list-tools
python -m unittest discover -s tests -v
```

Self QA must also check:
- no private files in the public repo
- docs match current behavior
- `.env.example` matches required public config
- shell-facing docs are ASCII-only
- git status is understood before commit or push

### 4. Workflow Learning

Purpose: learn repeatable user workflows without turning them into blind
automation.

Stored workflow fields:
- name
- intent
- preconditions
- steps
- expected signals
- verification commands
- error handlers
- rollback or stop conditions

Workflow replay must start with observation and end with verification.

### 5. Autonomous Recovery

Purpose: recover from common failures safely.

Recovery loop:
1. Read the error.
2. Diagnose root cause.
3. Search memory or known fixes.
4. Apply only small safe fixes automatically.
5. Verify.
6. Store the lesson.

Large, destructive, or ambiguous fixes require user confirmation.

## Anti-Chaos Rules

- Do not chase tool count.
- Do not register phantom tools.
- Do not add docs for private or missing modules.
- Do not expose raw private logs, memory databases, API keys, or screenshots.
- Do not let a tool return massive unfiltered output to an AI agent.
- Do not use Frida, desktop control, network tools, or write actions unless the
  task actually requires them.
- Always report uncertainty and blind spots.

## Implementation Priority

1. `workspace_situational_awareness`: compact state JSON.
2. `error_radar`: multi-source blocker detection.
3. `self_qa_agent`: release and handoff verification.
4. `workflow_learner`: capture repeatable workflows.
5. `autonomous_recovery`: safe recovery loops.

The first valuable version is not full autonomy. It is an agent that can see the
workspace, find obvious errors, choose the right tool, and verify its own work.
