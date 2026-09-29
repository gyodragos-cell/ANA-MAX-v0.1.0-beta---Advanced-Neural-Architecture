# Skill: fs-inspect

## Version
1.0.0

## Context
Skill declarativ care inspecteaza un path din filesystem intr-un mod determinist.

## Scop
Inspecteaza si raporteaza metadata despre un filesystem path.

## Structura directoare
- Input: path (string)
- Validation: path trebuie sa existe si sa fie accessible
- Output: type, size, attributes

## Componente OS v2
1. Sandbox - filesystem access control
2. Error handling - deterministic errors
3. Structured output - consistent format

## Discipline OS v2
- Determinism: same path = same result
- Observability: logezi fiecare access
- Single source of truth: fs is source
- Strict boundaries: no escapes outside root
- Fail fast: clear errors on missing paths
- Zero guessing: report exactly what exists

## Taskuri pentru implementare
### A. Citeste input path
### B. Valideaza path format
### C. Verifica existenta
### D. Determina tip (file|dir|missing)
### E. Citeste metadata
### F. Verifica permissions
### G. Formateaza output
### H. Logheaza access
### I. Returneaza result
### J. Handleaza errors
### K. Cleanup

## Reguli pentru Codex
- Path validation trebuie sa fie strict
- Errors trebuie sa indiceze exact ce e gresit
- Output trebuie sa includa: exists, type, details

## Output asteptat
```json
{
  "path": "ana",
  "exists": true,
  "type": "directory",
  "size": null,
  "accessible": true
}
```
