# AI Collaboration And Tools

ANA MAX is a human-led project created, tested, and directed by Dragos.

The project has also benefited from AI coding tools used as engineering
collaborators. These tools do not replace judgment, testing, or responsibility,
but they can help developers understand a codebase, plan safer changes, write
patches, review risks, and keep documentation aligned.

## Main AI Coding Collaborator

OpenAI Codex has been the main AI coding collaborator for this release.

How Codex helped:

- codebase analysis and project-map thinking;
- intent-aware analysis: reading the project as a connected map instead of a
  pile of files;
- focused code edits and release hygiene;
- verification planning and test execution;
- documentation cleanup and public-safe wording;
- keeping the mother lab and public release connected through sync rules.

In this project workflow, Codex has been especially useful as a project-map
analyst. It helps connect intent, documentation, implementation, tests, and
release boundaries so the public repo stays understandable for users and for
other AI agents that may help them install or connect ANA MAX.

Official link:

- OpenAI Codex: https://openai.com/codex/

Recommended use:

```text
Use Codex as a careful analyst and coding partner. Ask it to inspect first,
make small changes, run checks, and explain what changed.
```

Codex is also strict about safety. That is useful for ANA MAX: the project is
intended to attract clean users, QA testers, red-teamers with permission, and
developers who want reliable local tools. It should not be optimized for users
trying to manipulate agents into unsafe work.

## Additional Agentic Coding Tool

Qoder is also credited as a useful agentic coding workflow tool and source of
lab assistance/inspiration.

Official links:

- Qoder: https://qoder.com/

Recommended use:

```text
Use Qoder for agentic coding workflows, codebase exploration, and delegated
development tasks where its workspace model fits the job.
```

## Honest Guidance For New Developers

AI agents are powerful, but they work best with discipline:

- give them a project map;
- ask them to inspect before editing;
- keep changes small;
- require tests before handoff;
- keep secrets and private runtime data out of public git;
- update README, setup docs, changelog, `.env.example`, and tests when behavior
  changes.

ANA MAX tries to be useful to any capable AI agent by giving it local Windows
context through MCP tools: desktop state, files, terminal output, git status,
logs, OCR, UI Automation, and verification.

## Responsible QA Mindset

ANA MAX tools are meant to make AI agents more careful, not more reckless. A
good agent should use tools to observe real evidence, reproduce issues safely,
separate facts from guesses, and help developers fix problems.

Good use:

```text
find a weakness -> verify it safely -> report it privately -> help confirm the fix
```

Bad use:

```text
find a weakness -> exploit it silently -> publish risky steps -> hide the evidence
```

The private lab can test stronger workflows than the public release. Keep those
experiments private until they are safe, documented, tested, and useful for
authorized QA. Public docs should teach discipline and verification, not expose
abuse recipes.

Safe public wording:

```text
ANA MAX is developed in a private local lab with assistance from modern
agentic coding workflows, including OpenAI Codex and Qoder.
```

Use "sponsored by" only after a formal sponsorship agreement exists.
