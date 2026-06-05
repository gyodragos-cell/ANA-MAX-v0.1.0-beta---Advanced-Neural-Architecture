# Self-Repair Internals — ANA MAX OS v2

Acest document explică internals pentru skill-ul `self.repair`: scop, input/output, pași, reguli de siguranță, și modul în care scrie în `learned_rules.yaml`.

## Scop

`self.repair` detectează degradări în pipeline (ex: mapping greșit, path-uri incorecte, SKILL.md invalid) și propune/aplică remedieri declarative, persistând schimbările în `ana/learnings/learned_rules.yaml`.

## Contract (Inputs / Outputs)

**Inputs**
- `trace_id` (string) — id-ul execuției
- `context` (object) — diagnostic info (logs, stack traces, registry snapshot)
- `policy` (object, optional) — limite pentru ce poate modifica skill-ul

**Outputs**
- `result` (object) — `{ skill: "self-repair", actions: [...], applied: true|false, details: {...} }`
- `patches` (array) — lista de modificări propuse/aplicate (file path, diff, hash)

## Pași operaționali (determinist)

1. **Collect** — adună diagnostice: registry snapshot, skill root path, last errors, smoke test logs.
2. **Analyze** — rulează set de reguli deterministe (rule engine) pentru a identifica cauze posibile.
3. **Plan** — generează un set de acțiuni (patches) în format declarativ (ex: update `skills.yaml`, corect path în config loader).
4. **Validate** — validează fiecare patch într-un sandbox (dry-run): reîncarcă skill engine în memorie, rulează smoke test local cu modificările simulate.
5. **Apply** — dacă validarea trece și politica permite, aplică patch-urile pe fișierele reale și commit local (sau scrie în `learned_rules.yaml` pentru reguli runtime).
6. **Report** — returnează `result` cu detalii și trace_id.

## Reguli de siguranță

- **Limitare scope**: `self.repair` nu modifică cod executabil (ex: `orchestrator.py`) fără aprobarea explicită a unui maintainer.
- **Dry-run obligatoriu**: niciun patch nu este aplicat fără validare completă în sandbox.
- **Audit trail**: toate modificările sunt înregistrate în `learned_rules.yaml` cu timestamp, autor=`self.repair`, trace_id.
- **Rollback**: păstrează un backup automat (hash + copy) înainte de aplicare.

## Format pentru `learned_rules.yaml`

```yaml
- id: sr-20260605-0001
  timestamp: 2026-06-05T04:00:00Z
  trace_id: trace-repair-0001
  author: self.repair
  actions:
    - type: update_file
      path: ana/config/skills.yaml
      diff: |
        - capability: ana.self_repair
        + capability: self.repair
  validated: true
  applied: true
  notes: "Normalized capability names to match SKILL.md"
```

## Exemple de scenarii

- **Capabilitate inconsistentă**: detectează `skills.yaml` conținând `ana.self_repair` dar `SKILL.md` conține `self.repair`. Plan: normalizează `skills.yaml`.
- **Skill root path greșit**: detectează `_skill_root()` calculând `.../skills/skills` dublu; plan: corectează funcția loader sau config path.
- **Missing Version header**: SKILL.md fără `## Version` → adaugă `## Version: 1.0.0` și validează.

## Observabilitate & Audit

- `self.repair` emite evenimente: `self_repair.detected`, `self_repair.planned`, `self_repair.validated`, `self_repair.applied`.
- Toate intrările în `learned_rules.yaml` sunt semnate cu `author: self.repair` și includ `trace_id`.

## Extensii viitoare (opțional)

- UI pentru revizuire manuală a patch-urilor propuse.
- Mecanism de aprobări (maintainer sign-off) înainte de aplicare automată.
