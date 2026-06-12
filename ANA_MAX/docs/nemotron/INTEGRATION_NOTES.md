# Integration Notes

## Principiu

Integrarea a fost facuta separat, nu peste fluxul standard `ANA_MAX + OpenCode`.

Motiv:
- sa nu stricam setup-ul principal
- sa putem testa Nemotron in siguranta
- sa tinem codul modular

## Ce a fost adaugat

### 1. Backend nou

Fisier:
- `core/backends/nemotron_openrouter_backend.py`

Rol:
- initializeaza backend-ul Nemotron via OpenRouter
- citeste cheile din mediu
- face fallback intre chei
- trimite mesaje catre model

### 2. Integrare in router

Fisier:
- `core/backends/router.py`

Rol:
- permite ca backend-ul `nemotron_openrouter` sa fie recunoscut de infrastructura ANA

### 3. Integrare in ANAAgent

Fisier:
- `core/agent.py`

Rol:
- initializeaza backend-ul nou
- poate trimite mesaje prin backend-ul Nemotron
- suporta si backend-urile care existau deja in config

### 4. Entry point separat

Fisier:
- `main_nemotron.py`

Rol:
- forteaza `ai.primary_backend = nemotron_openrouter`
- dezactiveaza routing-ul global standard pentru acest mod separat

## De ce a fost nevoie de dezactivarea routing-ului global

Configul general `ANA_MAX` avea rute active pentru:
- `opencode_zen`
- `gemini`
- `kimi`
- `ollama`

Fara izolare, modul Nemotron ar fi fost imediat inlocuit de rutele globale.

De aceea `main_nemotron.py`:
- seteaza backend-ul principal pe `nemotron_openrouter`
- dezactiveaza `ai.routing.enabled`
- goleste `ai.routing.backends`

## Stare actuala

Integrarea este buna pentru:
- reasoning backend separat
- testare
- extindere viitoare

Pasul urmator pentru agent complet:
- bucla de tool calling
- executie de tool-uri pe baza raspunsurilor Nemotron
- observatie iterativa rezultat -> urmatorul tool
