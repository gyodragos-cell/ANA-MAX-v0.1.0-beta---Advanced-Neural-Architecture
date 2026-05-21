# ANA Tool TODO

Scop: ANA MAX nu trebuie sa aiba 1000 de tooluri. Trebuie sa aiba putine
capabilitati clare, bune, testate, care ajuta agentul sa vada, sa verifice si
sa nu lucreze orbeste.

## Nota Curenta

Nota: 9/10.

De ce:
- S-au adaugat CI/CD pentru validarea toolurilor, README curatat cu badges si tabele de status
- Fisierul `atentie.txt` a fost curatat din release-ul public
- `ROADMAP.md` a fost curatat de emoji-uri pentru a respecta regula ASCII-only
- Tool registry incarca 64 tooluri si testele trec.
- Premium gate este acum la runtime.
- MCP auth este activ by default.
- `window_manager`, `clipboard_manager` si `edge_tts_voice` nu mai sunt
  fantome.
- Exista regula si test pentru docs ASCII-only, ca PowerShell si agentii slabi
  sa nu se impiedice in mojibake.

Ce scade nota:
- Sunt prea multe tooluri optionale incarcate simultan.
- Unele tooluri au output cu descrieri vechi sau mix romana/engleza.
- Healthcheck-ul inca nu testeaza fiecare tool listat cu un scenariu real.
- Unele module AI Core au comentarii/docstring-uri vechi si private-style.
- Dependentele Python pot afisa warning `requests/urllib3/chardet` in unele
  medii locale.

## Prioritate 1 - Sa Nu Mai Lucreze Orbeste

- [ ] Fa un `vision_check` standard: capture -> OCR/UIA -> rezumat scurt.
- [ ] Fa un `verify_after_action` standard: dupa orice edit/control, agentul
      trebuie sa verifice cu tool potrivit.
- [ ] Fa `tool_healthcheck` real: fiecare tool listat trebuie sa aiba un smoke
      test minim sau sa fie marcat explicit manual/premium.
- [ ] Adauga test: niciun tool din `main.py --list-tools` nu are voie sa pice
      la import sau la `status/check/list` daca are asa ceva.

## Prioritate 2 - Tooluri Mai Putine, Mai Bune

- [ ] Grupeaza toolurile in categorii clare:
      `core`, `desktop_eyes`, `desktop_hands`, `memory`, `security`,
      `developer`, `premium`.
- [ ] Ascunde din default toolurile experimentale sau grele care nu ajuta zilnic.
- [ ] Pastreaza public doar tooluri cu:
      cod real, test minim, docs scurte, comportament stabil.
- [ ] Scoate sau marcheaza experimental orice tool care porneste subprocesse
      grele fara nevoie.

## Prioritate 3 - Reguli Pentru Agenti

- [ ] Orice agent citeste `docs/PROJECT_MAP_AI_GUIDE.md` inainte de editari.
- [ ] Orice agent ruleaza `rg` inainte sa inventeze unde e codul.
- [ ] Orice agent modifica doar fisierele necesare.
- [ ] Orice agent nu adauga docs pentru tooluri inexistente.
- [ ] Orice agent nu adauga path-uri private, tokenuri, screenshots, logs sau DB.
- [ ] Orice agent lasa docs si shell output ASCII-only.
- [ ] Orice agent raporteaza clar ce a rulat si ce a picat.

## Prioritate 4 - Desktop Eyes

- [ ] Standardizeaza `desktop_capture` ca free vision input.
- [ ] Standardizeaza `windows_uia_bridge` ca prima alegere pentru UI structural.
- [ ] Standardizeaza `foreground_ui_snapshot` pentru context rapid.
- [ ] OCR ramane fallback, nu prima alegere.
- [ ] `windows_deep_sight` ramane premium si doar pentru inspectie sub capota.

## Prioritate 5 - Curatenie Release

- [ ] Rezolva warning-ul `requests` dependency mismatch.
- [ ] Verifica periodic ca extensia VS Code ramane aliniata cu release-ul.
- [ ] Ruleaza scan periodic pentru mojibake/private paths in docs principale.
- [ ] Nu creste numarul de tooluri pana nu exista healthcheck real.

## Comenzi De Verificare

```powershell
python -m compileall -q main.py core tools vscode_extension
python main.py --test
python main.py --list-tools
python -m unittest discover -s tests -v
```

## Directie

Mai bine 30 tooluri impecabile decat 100 tooluri care mint. ANA trebuie sa fie
un agent cu ochi, memorie si verificare, nu o lista lunga de butoane.
