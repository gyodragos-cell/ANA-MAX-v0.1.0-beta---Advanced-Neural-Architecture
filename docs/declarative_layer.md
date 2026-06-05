# Declarative Layer — ANA MAX OS v2

Acest document descrie stratul declarativ al ANA MAX OS v2: cum sunt definite, încărcate și rulate skill-urile, ce rol are `skills.yaml`, `SKILL.md` și `learned_rules.yaml`, și ce așteptări avem pentru output și observabilitate.

## Principii

- **Capability-centric**: unitatea de execuție este `capability`. Orchestratorul primește o cerere pentru o `capability` și o mapează la un tool/skill în Registry.
- **Declarative skills**: skill-urile sunt descrise în directoare sub `ana/skills/skills//SKILL.md` și mapate în `ana/config/skills.yaml`.
- **Determinism pentru testare**: în test suite și smoke test folosim adaptori deterministi (fake HTTP, fake shell, deterministic LLM) pentru a garanta rezultate reproductibile.
- **Self-repair first-class**: skill-ul `self.repair` poate modifica `learned_rules.yaml` pentru a aplica corecții declarative.

## Fișiere cheie

- `ana/config/skills.yaml`
  - Mapare `capability` → `skill` (ex: `self.repair` → `skill.self-repair`).
  - Exemplu minimal:
    ```yaml
    skills:
      self.repair:
        skill: self-repair
        capability: self.repair
        version: 1.0.0
        enabled: true
    ```

- `ana/skills/skills//SKILL.md`
  - Document declarativ al skill-ului: **Capability**, **Version**, **Description**, **Inputs**, **Steps**, **Outputs**, **Fallbacks**, **Examples**.

- `ana/learnings/learned_rules.yaml`
  - Persistență pentru reguli generate de `self.repair` sau alte mecanisme de învățare.

- `ana/smoke_test.py`
  - Verificare end-to-end: skill loading, registry mapping, execuție, fallback presence, sumar final.

## SKILL.md — structură recomandată

Fiecare `SKILL.md` trebuie să conțină, în această ordine:

1. `## Capability` — exact string-ul folosit în `skills.yaml` și în `os.execute(...)`.
2. `## Version` — semantic versioning (ex: `1.0.0`).
3. `## Description` — scopul skill-ului.
4. `## Inputs` — schema așteptată (chei, tipuri, required/optional).
5. `## Steps` — pași clari, numerotați, determinist executabili.
6. `## Outputs` — format JSON așteptat, coduri de stare.
7. `## Fallbacks` — ce fallback-uri sunt aplicabile (dacă există).
8. `## Examples` — input/output concrete.

## Loading & Registration flow

1. La inițializare, **Skill Engine** scanează `ana/skills/skills/` și `ana/config/skills.yaml`.
2. Pentru fiecare skill:
   - Parsează `SKILL.md` și validează prezența `## Capability` și `## Version`.
   - Creează un ToolSpec virtual (ex: `skill.self-repair`) și îl înregistrează în Registry sub `capability`.
3. Registry expune `tools_for(capability)` și `fallbacks_for(capability)`.

## Orchestrator flow (execuție)

1. Client → `ANAMaxOS.execute(capability, payload, trace_id)`.
2. Orchestrator loghează `orchestrator.received`.
3. Registry returnează tool (skill.*) → `orchestrator.routed`.
4. Sandbox validează permisiuni și limite.
5. Tool/skill rulează → `orchestrator.running`.
6. La final: `orchestrator.completed` + output returnat.
7. Dacă lipsește tool sau eșuează: Fallback Engine caută fallback pentru `capability`.

## Observabilitate

- Event bus loghează evenimente standard: `received`, `routed`, `running`, `completed`, `error`.
- Smoke test afișează sumar: skills loaded, exec success, fallback configured, deterministic layer stable.

## Best practices

- **Nume consistente**: `capability` din `skills.yaml` = `## Capability` din `SKILL.md` = string folosit în `os.execute(...)`.
- **Nu modifica `learned_rules.yaml` manual**; preferă `self.repair` pentru update-uri automate.
- **Teste**: fiecare skill are unit/integration tests în `ana/tests/`.
