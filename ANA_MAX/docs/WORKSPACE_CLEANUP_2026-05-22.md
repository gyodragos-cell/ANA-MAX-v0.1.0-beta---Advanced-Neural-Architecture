# Workspace Cleanup - 2026-05-22

Scop: radacina `C:\Users\billy\Desktop\ana_dev\ANA_MAX` era aglomerata cu
teste, demo-uri, rapoarte, capturi si documentatie temporara. Acestea faceau
proiectul greu de citit si riscau sa incurce agentii.

## Ce a ramas in root

Au ramas fisiere operationale sau conventionale:

- `main.py`
- `launcher.py`
- `mcp_stdio.py`
- `mcp_server.py`
- `chat_voice_bridge.py`
- `voice_toggle.py`
- `requirements.txt`
- `README.md`
- `AGENTS.md`
- `.env.example`
- `Start_ANA_MCP_Server.bat`
- `Start_ANA_MCP_Server.ps1`

Nota: `README.md` si `AGENTS.md` raman in root intentionat. Sunt fisiere
conventionale pe care agentii si oamenii le cauta acolo.

## Unde s-au mutat fisierele

### Teste

Mutate in:

```text
dev_artifacts\tests
```

Include `test_*.py`, `quick_test.py`, `quick_smoke_test.py`,
`smoke_test_comprehensive.py` si `test_input.txt`.

### Demo-uri

Mutate in:

```text
dev_artifacts\demos
```

Include demo-uri Frida, WOW, calculator, real demo, mouse/icon demos.

### Diagnostic / helper scripts

Mutate in:

```text
dev_artifacts\diagnostics
```

Include scripturi manuale pentru procese, Frida, voice, vision, benchmark,
health check si validari.

### Manual scripts

Mutate in:

```text
dev_artifacts\scripts
```

Include scripturi vechi de start, push, BOM fix si alte helper-e manuale care
nu sunt entrypoint-uri principale.

### Voice alternatives

Mutate in:

```text
dev_artifacts\voice
```

Root pastreaza doar `chat_voice_bridge.py` si `voice_toggle.py`.

### Media

Mutate in:

```text
dev_artifacts\media
```

Include capturi `.png` generate in demo-uri.

### Documentatie voice

Mutata in:

```text
docs\voice
```

### Rapoarte si snapshot-uri text

Mutate in:

```text
docs\reports
```

Include rapoarte `.txt` si `requirements_current.txt`.

## Ce nu s-a sters

Nu s-au sters testele si demo-urile. Au fost mutate ca istoric recuperabil.
Daca dupa cateva sesiuni nu mai sunt necesare, se pot sterge din
`dev_artifacts/` cu confirmare explicita.

## Regula pe viitor

- Documentatie noua: `docs/`.
- Rapoarte temporare: `docs/reports/`.
- Teste manuale si experimente: `dev_artifacts/tests/`.
- Demo-uri: `dev_artifacts/demos/`.
- Scripturi de diagnostic manual: `dev_artifacts/diagnostics/`.
- Capturi media locale: `dev_artifacts/media/`.
- Root ramane pentru runtime real, config, entrypoints si fisiere conventionale.
