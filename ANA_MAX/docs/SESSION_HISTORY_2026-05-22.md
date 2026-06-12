# ANA MAX Session History - 2026-05-22

Acest fisier noteaza ce s-a investigat, ce s-a reparat si ce merge acum.
Scopul este practic: Qoder/ANA/Codex sa poata relua contextul fara sa
redescopere aceleasi probleme.

## Context

Shortcut-ul folosit:

```text
C:\Users\billy\Desktop\launch.bat - Shortcut.lnk
```

Target real al shortcut-ului:

```text
C:\Users\billy\Desktop\ana_dev\ANA_MAX_Launcher\launch.bat
```

Workspace folosit de launcher:

```text
C:\Users\billy\Desktop\ana_dev\ANA_MAX
```

Port MCP folosit pentru Qoder:

```text
http://127.0.0.1:8766/mcp
```

Config Qoder MCP:

```text
C:\Users\billy\AppData\Roaming\Qoder\SharedClientCache\mcp.json
```

## Ce era gresit

1. Launcher-ul vechi pornea mai multe ferestre, dar raporta OK fara verificari reale.
2. Unele comenzi `start cmd /k` aveau quoting fragil si Windows ajungea sa incerce sa ruleze `python.exe` ca script Python.
3. Eroarea vazuta:

```text
SyntaxError: Non-UTF-8 code starting with '\x90' in file ...\venv\Scripts\python.exe
```

4. `tools\watchdog.py` era pornit prin `python -c`, dar pornea thread daemon si procesul iesea imediat. Deci "watchdog started" putea fi fals.
5. Frida exista, dar tool-ul `frida_instrument` cere `confirm=True`.
6. Qoder avea nevoie de un semnal practic de tip "nu mai repeta aceeasi actiune", nu doar de ferestre demo.
7. Vocea `pyttsx3` esua cu:

```text
Class not registered
```

8. `tools\live_voice_bridge.py` era doar test/motor de voce, nu bridge continuu pentru chat.

## Reparatii facute

### Launcher

Fisier modificat:

```text
C:\Users\billy\Desktop\ana_dev\ANA_MAX_Launcher\launch.bat
```

Schimbari:

- Seteaza Qoder MCP pe `http://127.0.0.1:8766/mcp`.
- Nu mai omoara toate procesele `python.exe`.
- Verifica `/health` inainte sa spuna ca MCP este OK.
- Verifica `tools/list`.
- Testeaza `desktop_capture`.
- Testeaza Frida cu `confirm=True`.
- Porneste `DEBUG CONSOLE`.
- Porneste `WATCHDOG FRIDA`.
- Porneste `CHAT VOICE BRIDGE`.
- Foloseste forma robusta:

```bat
pushd "C:\Users\billy\Desktop\ana_dev\ANA_MAX" && venv\Scripts\python.exe ...
```

Aceasta evita eroarea in care `python.exe` era interpretat ca fisier sursa.

### Watchdog real

Fisier adaugat:

```text
C:\Users\billy\Desktop\ana_dev\ANA_MAX_Launcher\live_watchdog.py
```

Ce face:

- Verifica periodic MCP health.
- Verifica tool count.
- Verifica Frida prin MCP.
- Verifica ferestrele vizibile prin `windows_uia_bridge`.
- Cheama `agent_coach`.
- Afiseaza loguri importante din `logs\ana_max.log`.
- Ramane pornit; nu iese imediat ca vechiul watchdog.

### Agent coach pentru Qoder

Fisier adaugat:

```text
C:\Users\billy\Desktop\ana_dev\ANA_MAX\tools\agent_coach_tool.py
```

Fisier modificat:

```text
C:\Users\billy\Desktop\ana_dev\ANA_MAX\main.py
```

Tool nou:

```text
agent_coach
```

Ce face:

- Citeste `logs\observability.jsonl`.
- Detecteaza actiuni repetate.
- Detecteaza erori repetate.
- Detecteaza `confirm=True` lipsa.
- Detecteaza parametri gresiti, de exemplu `operation` vs `action`.
- Returneaza un `prompt_for_qoder`.
- Salveaza lectii in:

```text
memory\agent_coach_lessons.jsonl
```

Regula dorita pentru Qoder:

```text
La inceput de task, dupa o eroare, sau dupa doua incercari esuate,
apeleaza agent_coach action=coach si urmeaza recomandarea.
```

### Voce / chat verbal

Fisier modificat:

```text
C:\Users\billy\Desktop\ana_dev\ANA_MAX\tools\live_voice_bridge.py
```

Problema:

```text
pyttsx3 / SAPI COM: Class not registered
```

Fix:

- Daca `pyttsx3` esueaza, bridge-ul foloseste fallback prin Windows
  `.NET System.Speech`.
- Dupa primul esec pyttsx3, nu mai incearca pyttsx3 in aceeasi sesiune.
- Fallback-ul este fire-and-forget ca sa nu blocheze chat bridge-ul.

Bridge util pentru chat:

```text
C:\Users\billy\Desktop\ana_dev\ANA_MAX\chat_voice_bridge.py
```

Comanda:

```powershell
cd C:\Users\billy\Desktop\ana_dev\ANA_MAX
python.exe chat_voice_bridge.py --poll 0.7
```

Ce face:

- Citeste verbal textul copiat in clipboard.
- Citeste verbal linii adaugate in `voice_queue.txt`.
- Sare peste texte ce contin `token`, `password`, `api key`, `secret`.

Pentru Qoder:

- Poate chema `edge_tts_voice operation=speak`.
- Sau poate scrie raspunsuri in `voice_queue.txt`.
- Sau utilizatorul copiaza textul din chat, iar bridge-ul il spune verbal.

## Stare verificata

La finalul sesiunii:

```text
MCP health: online
MCP port: 8766
MCP version: 18.0-MAX
Tools count: 66
agent_coach: prezent
Frida: 17.9.8
desktop_capture: functional
windows_uia_bridge: functional cu confirm=True
voice bridge: functional cu fallback System.Speech
```

PID-uri vazute in timpul sesiunii:

```text
MCP server: 16476, apoi 21720, apoi 11048, apoi 7000
```

Nota: PID-ul se schimba la restart. Pentru verificare foloseste:

```powershell
netstat -ano | findstr :8766
```

## Comenzi utile de verificare

Health MCP:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8766/health"
```

Lista tool-uri:

```powershell
$body=@{jsonrpc="2.0";id=1;method="tools/list";params=@{}} | ConvertTo-Json -Depth 5
Invoke-RestMethod -Uri "http://127.0.0.1:8766/mcp" -Method Post -Body $body -ContentType "application/json"
```

Agent coach:

```powershell
$body=@{
  jsonrpc="2.0"
  id=2
  method="tools/call"
  params=@{
    name="agent_coach"
    arguments=@{action="coach";limit=80;repeat_threshold=5}
  }
} | ConvertTo-Json -Depth 8
Invoke-RestMethod -Uri "http://127.0.0.1:8766/mcp" -Method Post -Body $body -ContentType "application/json"
```

Frida:

```powershell
$body=@{
  jsonrpc="2.0"
  id=3
  method="tools/call"
  params=@{
    name="frida_instrument"
    arguments=@{operation="version";confirm=$true}
  }
} | ConvertTo-Json -Depth 8
Invoke-RestMethod -Uri "http://127.0.0.1:8766/mcp" -Method Post -Body $body -ContentType "application/json"
```

Voice test:

```powershell
cd C:\Users\billy\Desktop\ana_dev\ANA_MAX
python.exe tools\live_voice_bridge.py
```

Chat voice bridge:

```powershell
cd C:\Users\billy\Desktop\ana_dev\ANA_MAX
python.exe chat_voice_bridge.py --poll 0.7
```

## Ce trebuie tinut minte

- Nu porni Frida fara `confirm=True` prin MCP.
- Nu folosi `operation` cand schema cere `action`.
- Dupa doua incercari esuate, Qoder trebuie sa opreasca repetitia si sa cheme `agent_coach`.
- Pentru UI: observe -> act once -> verify.
- Pentru voce continua: foloseste `chat_voice_bridge.py`, nu doar `tools\live_voice_bridge.py`.
- `tools\live_voice_bridge.py` este motor/test de voce.
- `chat_voice_bridge.py` este bridge-ul practic pentru chat.

## Offline Lab Profile

Adaugat `docs\OFFLINE_LAB_PROFILE.md` ca profil de lucru pentru laborator fara
internet sau medii unde datele nu pot parasi masina. Profilul separa tool-urile
in Core Offline, Eyes, QA/Debug, Self Healing si Voice.

`tool_healthcheck` are acum `scope=offline_lab`. Verifica:

- `file_operations`
- `system_control`
- `smart_search`
- `foreground_ui_snapshot`
- `windows_uia_bridge`
- `desktop_capture`
- `agent_coach`
- `edge_tts_voice`

`windows_uia_bridge action=list_windows` a fost reparat sa foloseasca Win32 nativ
pentru listarea ferestrelor, ca sa nu mai blocheze profilul offline pe UIA greoi.
Inspect/click/type raman pe UIA.

Verificare MCP dupa restart:

```text
health: online
tools_count: 66
tool_healthcheck scope=offline_lab: 8 OK / 0 FAIL
```
