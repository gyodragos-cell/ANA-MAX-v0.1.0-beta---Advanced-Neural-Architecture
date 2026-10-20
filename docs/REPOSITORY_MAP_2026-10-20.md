# Repository map and safe reorganization plan

**Snapshot date:** 20 October 2026  
**Scope:** documentation-led inventory; no source files or runtime paths were moved in this pass.

## 1. Current public entry points

- **index.html** — professional portfolio overview for the OS-28 foundation and OS-29 direction.
- **live.html** — browser-native, privacy-first Live Profile demo.
- **cv.html** — printable CV page and copy-ready LinkedIn summary.
- **README.md** — current repository entry point.
- **docs/PORTFOLIO_STATUS_2026-10-20.md** — dated test evidence and explicit project boundaries.

OS-29 is a separate local companion project at the time of this snapshot. This repository does not yet contain its source tree.

## 2. Root-level directory groups

| Group | Locations | Intended role / interpretation |
|---|---|---|
| Application implementation | ANA_MAX/ | Main ANA MAX application modules and related source |
| Protocol adapters | mcp/ | MCP-facing entry points and integration adapters |
| Local launch workflows | launchers/ | Windows launch and operator workflow helpers |
| Helper and verification scripts | scripts/ | Maintenance, development and verification scripts |
| Project documentation | docs/ | Architecture, setup, historical iterations, reports and handoffs |
| Public website | index.html, live.html, cv.html, site/ | Portfolio pages and related web assets |
| Browser/network utilities | duck_proxy/ | Separate helper area; current production role must be checked before changes |
| Experiment / legacy areas | sandbox/, scratch_test_dir/, urgent/, .cache/, .agents/, .cursor/, .devin/, .duck_profile/, .zcode/ | Preserve until tracked status, references and purpose have been checked |
| Additional web templates | socialbooksi web siteuri facute de ai template/ | Historical or independent website material; not assumed to be part of ANA MAX runtime |
| Editor and agent instruction files | .cursorrules, .windsurfrules, CLAUDE.md, DEVIN.md, GEMINI.MD and related files | Tool-specific instructions; not all are guaranteed to be consumed by every editor or agent |
| Historical top-level reports | ANA_MAX_TOOLS_REPAIR_REPORT.md, *_SMOKE_TEST.md, *_REPORT.md, ENGINEERING_JOURNAL.md and similar | Evidence/reference material with varying dates; prefer a dated report that matches the component and build being discussed |

Folder names alone do not establish whether a component is active, imported, launched or tested.

## 3. Public-facing scope

The portfolio focuses on:

1. **OS-28:** local tool integration, launcher reliability, bounded operation/path policy and test evidence.
2. **OS-29:** local operational-intelligence companion, trace lineage, redaction, explicit scope and lexical evidence retrieval.
3. **Live Profile:** a static browser demonstration that does not upload visitor-selected names or browser properties.

The portfolio deliberately does not market experimental low-level or legacy material as a finished commercial capability.

## 4. What remains unclassified

The repository has many historical docs and editor-specific files, plus experimental directories and a Git history with previously reported deletions. This pass has not determined which old folders can be removed, merged or moved without affecting consumers.

No mass restore, mass delete or source-tree move was performed.

## 5. Recommended target structure

Use this as a destination map only after reference checks:

- Keep the GitHub Pages entry files at repository root while the Pages workflow uploads the root tree.
- Keep the actual runtime packages in stable locations until imports, launcher paths and client configs have been scanned.
- Group dated repair/test reports under a predictable documentation convention, retaining the date and original evidence.
- Move retired design notes into a clearly named history/archive area only after inbound links and local references have been checked.
- Put experimental assets in a documented experiment group once current users and workflows have been identified.
- Choose one canonical contributor/agent guide and make tool-specific files point back to it rather than keeping contradictory copies.

## 6. Safe sequence for a future physical cleanup

1. Snapshot the current branch, working-tree status and important file hashes.
2. Search imports, launch scripts, client configuration and documentation links for each candidate path.
3. Classify each candidate as active, historical, duplicate, generated or unknown.
4. Move only one small, understood batch; keep a rollback copy and review the exact diff.
5. Run the relevant unit suite, syntax checks and launcher status checks.
6. Check the resulting Pages deployment and public links before proceeding to the next batch.

**Principle:** a cleaner tree is useful only if it is still runnable, its history is preserved and its status claims remain evidence-based.
