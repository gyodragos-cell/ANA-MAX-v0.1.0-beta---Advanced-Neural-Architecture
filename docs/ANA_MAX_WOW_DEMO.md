# ANA MAX - 90 Second Proof Demo

This is the public demo blueprint. The goal is not to show every tool. The goal
is to make a new user understand one idea in under 90 seconds:

```text
ANA MAX gives AI agents situational awareness before they act.
```

## Core Message

Most agents lose time because they guess from partial context. ANA MAX gives the
agent a workflow:

```text
observe -> instrument when needed -> act -> verify -> learn
```

This is the difference to show:

- a normal agent reads files and guesses;
- ANA MAX observes the workspace, desktop, git state, runtime behavior, and test
  output;
- ANA MAX chooses focused tools instead of using a random toolbox;
- ANA MAX verifies the result with smoke tests.

## 90 Second Storyboard

### 0-8 seconds: Hook

Show: terminal and project folder.

On-screen text:

```text
Most agents guess from files.
ANA MAX observes the live workspace first.
```

Say:

```text
This is ANA MAX, a Windows-first MCP runtime for AI agents that should not work
blind.
```

### 8-20 seconds: Situational Awareness

Show commands:

```powershell
python main.py --list-tools
python main.py --test
```

Show proof:

```text
71 tools loaded
3 PASS / 0 FAIL
```

Say:

```text
The agent can inspect files, git state, desktop context, terminal output, UI
state, and tests before it edits anything.
```

### 20-35 seconds: The Real Task

Show: a small bug, failing behavior, or UI task.

On-screen text:

```text
Task: diagnose, fix, and prove the result.
```

Say:

```text
The point is not the bug. The point is that the agent gathers facts before
acting.
```

### 35-55 seconds: Superpower Moment

Show: ANA MAX choosing the right observation tool.

Examples to show depending on the task:

```text
workspace_situational_awareness
git_operations
desktop_capture
windows_uia_bridge
frida_instrument
windows_insight
```

Use Frida only when it is relevant and authorized:

```text
Frida is used only for authorized runtime instrumentation when static inspection
is not enough.
```

Say:

```text
For normal code work, ANA can inspect files, tests, and git. For live behavior,
it can use desktop vision, Windows UI automation, or authorized runtime
instrumentation.
```

### 55-72 seconds: Fix

Show: small code edit or UI action.

On-screen text:

```text
Act only after observing.
```

Say:

```text
Now the agent has enough context to make a targeted change.
```

### 72-85 seconds: Verify

Show commands:

```powershell
python main.py --test
python -m unittest discover -s tests -v
```

Show proof:

```text
3 PASS / 0 FAIL
81 tests OK
```

Say:

```text
ANA MAX does not stop at a patch. It verifies the result and reports facts.
```

### 85-90 seconds: Close

On-screen text:

```text
ANA MAX
Observe. Instrument. Act. Verify.
Privacy-first hybrid agent runtime.
```

Say:

```text
This is the difference: not more tools, better awareness.
```

## What The Demo Must Prove

The viewer should leave with five beliefs:

1. ANA MAX is not just another chatbot.
2. ANA MAX helps agents avoid blind work.
3. ANA MAX can use desktop vision and Windows inspection.
4. ANA MAX can use Frida for authorized runtime facts when needed.
5. ANA MAX verifies with real checks.

## Contributor Note: Codex

Include one short acknowledgement in the public project page or video
description:

```text
Built by Dragos as a human-led engineering project, with OpenAI Codex used as an
AI coding collaborator for repair work, documentation, release hygiene, and
repeatable verification.
```

Do not make Codex the product story. The product story is still ANA MAX:
observe, instrument, act, verify. The Codex note exists to be transparent about
the workflow and to show engineers that the project was improved through
careful AI-assisted development, not random code generation.

## What To Avoid

Do not make the first demo a long architecture lecture.

Avoid:

- listing every tool;
- showing private logs, memory, tokens, local paths, or screenshots;
- using Frida against third-party targets without permission;
- making claims that are not shown on screen;
- a 10 minute first-contact video.

## Recommended Public Video Set

Make three videos, not one giant video:

```text
90 seconds  - proof demo for README and website
3 minutes   - install and MCP connection
8 minutes   - full technical walkthrough
```

The 90 second video is the main sales asset. The longer videos are for users
who already care.

## Landing Page Copy

Use this short message where space is limited:

```text
ANA MAX gives AI agents situational awareness before they act: desktop vision,
Windows UI automation, git and code tools, memory, authorized runtime
instrumentation, and smoke-test verification in one privacy-first MCP runtime.
```

Use this even shorter version for profile/About:

```text
Windows-first MCP runtime that helps AI agents observe, instrument, act, and
verify instead of guessing.
```

## Demo Checklist

Before recording:

- close private apps and private folders;
- use a clean test project;
- clear terminal history if needed;
- set a public-safe `MCP_API_KEY`;
- run `git status --short`;
- run the smoke checks once before recording;
- keep zoom high enough that text is readable.

After recording:

- cut pauses;
- keep the first public video under 90 seconds;
- show commands and results clearly;
- upload a compressed copy or external link if the file is large;
- keep the original recording out of the public repo if it contains private
  content.
