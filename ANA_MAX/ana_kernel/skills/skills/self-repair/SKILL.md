# Skill: self-repair

## Version
1.0.0

type: system
status: stable

## Capability
self.repair

## Context
Skill declarativ care descrie modul in care ANA MAX OS v2 detecteaza si remediaza problemele
runtime prin ajustari de configurare, fallback si reguli declarative.

## Scop
Permite OS v2 sa recunoasca degradari, sa aplice patch-uri sigure si sa invete din
executii anterioare pentru a evita aceleasi erori.

## Structura directoare
- Diagnostics: evenimente si erori colectate
- Repair plan: propuneri de patch-uri
- Learned rules: actualizari persistente
- Execution: aplicarea si verificarea patch-urilor

## Componente OS v2
1. EventBus - colectare de erori si telemetrie
2. CooperationEngine - orchestrare self-repair
3. Registry - verificare tool-uri si capabilitati
4. Fallback - reutilizare de canale de backup
5. ConfigLoader - aplicare patch-uri

## Discipline OS v2
- Determinism: patch-urile trebuie sa fie sigure si reproductibile
- Observability: trebuie sa fie jurnalizate toate deciziile
- Single source of truth: learned_rules.yaml este sursa adevarului pentru reguli
- Strict boundaries: nu se modifica date externe direct
- Fail fast: daca reparatia e imposibila, se opreste si raporteaza
- Zero guessing: nu se face ghicire fara date certe

## Taskuri pentru implementare
### A. Colecteaza diagnostice
### B. Analizeaza tiparele de eroare
### C. Identifica reguli si skill-uri relevante
### D. Propune patch-uri declarative
### E. Aplica patch-urile sigure
### F. Verifica efectul modificarilor
### G. Scrie learnings in learned_rules.yaml
### H. Raporteaza status
### I. Trigger self-repair daca este necesar
### J. Documenteaza deciziile
### K. Inchide procesul

## Reguli pentru Codex
- Output trebuie sa fie clar, structurat si corect pentru diagnostice
- Nu se pot aplica modificari fara un plan validat
- Trebuie sa includa steps, status si learnings

## Output asteptat
```json
{
  "status": "patched",
  "details": "Applied self-repair patch based on diagnostic analysis.",
  "learnings": [
    {
      "rule": "llm.complete.retry=2",
      "reason": "recoverable failure pattern"
    }
  ]
}
```

## Summary
Skill declarativ care descrie modul in care ANA MAX OS v2 detecteaza probleme,
analizeaza cauze, aplica patch-uri, actualizeaza configurari si invata din
executiile anterioare folosind CooperationEngine si SelfRepairEngine.

## Intent
Acest skill este folosit automat de CooperationEngine atunci cand:
- apare o eroare repetitiva
- fallback-urile sunt declansate prea des
- un tool sau un serviciu devine inconsistent
- configurarea nu mai reflecta realitatea runtime
- lipsesc skill-uri declarative sau reguli declarative

## Preconditions
- CooperationEngine este activ
- SelfRepairEngine este disponibil in cooperation.py
- learned_rules.yaml este accesibil pentru citire/scriere
- fallback engine este functional
- event bus publica evenimentele de tip error/failure

## Steps
1. **Collect Diagnostics**
   - citeste evenimentele recente din EventBus
   - extrage erorile din ErrorPacket
   - identifica pattern-uri (repetitii, degradari, timeouts)

2. **Analyze**
   - clasifica problemele: recoverable / non-recoverable / transient / structural
   - verifica daca exista reguli declarative pentru aceste cazuri
   - verifica daca exista skill-uri declarative relevante
   - verifica daca fallback-urile sunt configurate corect

3. **Generate Patch**
   - propune ajustari pentru:
     - fallback rules
     - skills.yaml
     - discipline enforcement
     - config (services active, limits, boundaries)
   - genereaza patch-uri in format declarativ

4. **Apply Patch**
   - scrie patch-urile in learned_rules.yaml
   - notifica CooperationEngine ca patch-ul a fost aplicat
   - actualizeaza runtime-ul daca patch-ul este safe

5. **Verify**
   - ruleaza un health-check intern
   - verifica daca problema a disparut
   - daca nu, marcheaza patch-ul ca "ineficient"

## Fallbacks
- daca SelfRepairEngine nu poate aplica patch-ul  returneaza status=deferred
- daca learned_rules.yaml nu poate fi scris  returneaza status=blocked
- daca analiza nu gaseste nimic  returneaza status=noop

## Output
- status: ok | noop | patched | deferred | blocked
- details: descrierea actiunilor efectuate
- learnings: lista regulilor noi salvate

## Example Output
status: patched
details: "Updated fallback rules for llm.complete after repeated recoverable failures."
learnings:
  - rule: "llm.complete.retry=2"
    reason: "pattern: recoverable failure x3"
