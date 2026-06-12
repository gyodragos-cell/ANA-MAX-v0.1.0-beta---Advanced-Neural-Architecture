# ANA MAX Offline Lab Profile

Scop: ANA trebuie sa ramana utila cand nu exista internet sau cand datele nu pot
parasi masina. Modelul local poate rationa, dar tool-urile ii dau ochi, maini,
memorie si verificare.

## Principiu

Workflow-ul corect este:

```text
observe -> decide -> act -> verify -> remember
```

Agentul nu trebuie sa ghiceasca. Inainte de actiuni pe desktop sau cod, trebuie
sa observe starea reala si sa verifice rezultatul.

## Core Offline

Tool-uri de baza pentru orice sesiune offline:

- `file_operations`: citeste si modifica fisiere local.
- `terminal_tool` / `system_control`: ruleaza comenzi si verifica procese, CPU,
  RAM, porturi si vitals.
- `tool_healthcheck`: verifica rapid daca setul de tool-uri este sanatos.
- `memory_tool`, `memory_cortex`, `context_bridge`: memorie locala si lectii.
- `agent_coach`: opreste buclele, click-urile repetate si tool calls gresite.

## Eyes

Tool-uri pentru observare:

- `foreground_ui_snapshot`: primul pas pentru UI activ; output scurt pentru agent.
- `windows_uia_bridge`: structura reala a ferestrelor Windows prin UI Automation.
- `desktop_capture`: captura reala de desktop pentru Vision AI si fallback.
- `ocr_tool`: fallback cand UIA nu poate citi textul.

Regula: foloseste `foreground_ui_snapshot` sau `windows_uia_bridge` inainte de
click. Foloseste `desktop_capture` cand trebuie verificat ce vede omul pe ecran.

## QA And Debug

Tool-uri utile in laborator QA:

- `qa_testing`: generare cazuri simple si edge cases.
- `debugger`: analiza tracebacks si erori runtime.
- `browser_control`: testare locala de pagini si aplicatii web.
- `session_log_miner`: extrage lectii din sesiuni si loguri.
- `frida_instrument`: doar pentru instrumentare dinamica, hook-uri de proces,
  mobile sau cazuri unde inspectia statica nu ajunge.

## Voice

Tool-uri pentru feedback verbal local:

- `edge_tts_voice`: interfata de tool pentru voce.
- `live_voice_bridge`: fallback local Windows `System.Speech`.
- `chat_voice_bridge.py`: citeste chat/queue si vorbeste in timp real.

Vocea trebuie sa fie ajutor, nu zgomot. Mesajele repetate sau erorile recurente
trebuie reduse la `DEBUG`.

## Offline Backend

Pentru laborator fara internet:

```yaml
ai:
  primary_backend: ollama
  fallback_backend: none
  ollama:
    api_url: http://localhost:11434/api/generate
    model: mistral:7b
```

Pentru model mare local, schimba doar `ai.ollama.model`, de exemplu:

```yaml
model: mistral:120b
```

Nu activa backend-uri cloud in medii unde datele nu au voie sa iasa din masina.

## Verification

Ruleaza din root:

```powershell
python main.py --test
python main.py --list-tools
python -m compileall -q main.py core tools
```

Pentru profilul de laborator, prin MCP:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "tool_healthcheck",
    "arguments": {
      "scope": "offline_lab"
    }
  }
}
```

Rezultatul bun inseamna ca agentul are minimul practic: fisiere, sistem,
observare UI, captura/lista ferestre, coach si voce.

## Safety Rules

- Nu copia `.env`, token-uri, baze de date private, loguri sau memorie in release.
- Nu pune video-uri mari in git; foloseste link YouTube/GitHub Release.
- Nu folosi Frida pentru lucruri care se pot rezolva prin logs, UIA sau teste.
- Nu lasa agentul sa repete aceeasi actiune fara `agent_coach`.
- Dupa orice actiune importanta, verifica efectul cu un tool de observare.
