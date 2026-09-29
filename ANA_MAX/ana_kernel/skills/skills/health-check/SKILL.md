# Skill: health-check

## Version
1.0.0

## Context
Skill declarativ care verifica starea serviciilor active, a tool-urilor inregistrate,
a fallback-urilor declarative si a disciplinei OS v2.

## Scop
Verifica disponibilitatea si stabilitatea infrastructurii OS v2.

## Structura directoare
- Registry: tool-uri active
- Services: config active
- Event Bus: intrari in journal
- Sandbox: politici active

## Componente OS v2
1. Registry - tool storage
2. EventBus - event streaming
3. Sandbox - execution policy
4. Fallback - recovery mechanism

## Discipline OS v2
- Determinism: verifica ca responses sunt deterministe
- Observability: verifica ca event-uri sunt publicate
- Single source of truth: verifica ca registry e consistent
- Strict boundaries: verifica ca sandbox policy e activ
- Fail fast: verifica ca fallbacks sunt registered
- Zero guessing: verifica ca nu avem missing tools

## Taskuri pentru implementare
### A. Verifica registry
### B. Verifica services
### C. Verifica fallbacks
### D. Verifica event bus
### E. Verifica sandbox
### F. Colecteaza stats
### G. Evalueaza health
### H. Returneaza report
### I. Logeaza diagnostics
### J. Actualizeaza timestamp
### K. Finalizeaza

## Reguli pentru Codex
- Report trebuie sa includa: ok | degraded | failed
- Details trebuie sa listeze fiecare component
- Errors trebuie sa fie specifice si actionable

## Output asteptat
```json
{
  "status": "ok",
  "details": {
    "registry": "active",
    "services": ["http", "shell", "llm"],
    "fallbacks": 3,
    "event_bus": "active",
    "sandbox": "active",
    "timestamp": "2026-06-05T..."
  }
}
```
