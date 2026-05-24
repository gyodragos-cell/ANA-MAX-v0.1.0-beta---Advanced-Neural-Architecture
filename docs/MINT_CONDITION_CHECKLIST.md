# ANA MAX Mint Condition Checklist

Use this checklist before ending a release-polish session. The goal is simple:
leave the public repo cleaner than it was found.

## Golden Rule

```text
clean today -> verified today -> documented today -> tomorrow starts with bug hunt, not old cleanup
```

## Public Release Checks

- [ ] `git status --short` is clean, or every remaining change is intentional.
- [ ] No `.env`, `.license`, API keys, logs, databases, memory stores, private
      screenshots, local shortcuts, or private lab paths are staged.
- [ ] Tool counts match the release map:
      `80 loaded tools, 4 premium-gated tool families, 7 AI Core adapters`.
- [ ] Public links use the canonical repository URL:

```text
https://github.com/gyodragos-cell/ANA-MAX-v0.1.0-beta---Advanced-Neural-Architecture
```

- [ ] Docs are ASCII-only and free of mojibake.
- [ ] README, setup guide, changelog, project map, VS Code extension metadata,
      and tests are aligned when behavior changes.
- [ ] Private lab power stays private until it is safe, documented, tested, and
      useful for authorized QA.

## Required Verification

```powershell
python -m compileall -q main.py core tools vscode_extension
python main.py --test
python main.py --list-tools
python -m unittest discover -s tests -v
```

Expected:

```text
3 PASS / 0 FAIL
80 loaded tools
all tests passing
```

## Agent Handoff

Tell the next agent:

```text
Read docs/PROJECT_MAP_AI_GUIDE.md first.
Observe before editing.
Keep changes scoped.
Run the checks.
Report failures plainly.
Do not copy private lab data into this repo.
```

## Daily Polish Loop

1. Inspect `git status --short`.
2. Search for stale counts, placeholder links, mojibake, and private paths.
3. Fix only real public noise.
4. Run the required checks.
5. Commit small, named changes.
6. Push only when the release is public-safe.

