# ANA MAX Public Release Log

## resource_system_sync_2026-05-25

Implemented the lightweight public resource system for texts, themes, and icon
loading.

Files created:
- `core/resource_loader.py`
- `resources/texts/en.json`
- `resources/texts/ro.json`
- `resources/themes/light.json`
- `resources/themes/dark.json`
- `resources/icons/.gitkeep`
- `LOG.md`

Files modified:
- `dashboard/autonomy_dashboard.py`
- `tests/test_v20_phase5/test_autonomy_dashboard.py`
- `docs/PROJECT_MAP_AI_GUIDE.md`
- `docs/ROADMAP.md`
- `CHANGELOG.md`
- `README.md`

Sync status:
The public GitHub repository workspace and Mother Lab workspace both contain
the lightweight resource system. Mother Lab private runtime data was not
copied into the public release.

Test results:
- Public `python -m compileall -q main.py core tools vscode_extension`: OK.
- Public `python main.py --test`: 3 PASS / 0 FAIL.
- Public `python main.py --list-tools`: 80 tools available.
- Public `python -m unittest discover -s tests -v`: 87 tests OK.
- Mother Lab `python -m compileall -q main.py core tools vscode_extension`:
  reported `Can't list 'vscode_extension'` because that folder is absent.
- Mother Lab `python main.py --test`: 2 PASS / 0 FAIL.
- Mother Lab `python main.py --list-tools`: 74 tools available.
- Mother Lab `python -m unittest discover -s tests -v`: not a valid local
  suite run because Mother Lab has no local `tests/` folder; Python discovered
  installed `site-packages` tests from `objection`, which failed on external
  package permission errors.

Audit results:
- Dashboard-facing v20 section labels, status labels, and error strings moved
  into resource text keys.
- Dashboard colors are read from `load_theme(...)`.
- Loader uses Python standard library only and keeps safe fallbacks.

v21 foundations added:
- Theme switching hook with `ANA_THEME`.
- Resource-only dev-mode hook with `ANA_DEV_MODE`.
- Resource Inspector, Dashboard v2, and Tool Health Visualizer placeholders.
