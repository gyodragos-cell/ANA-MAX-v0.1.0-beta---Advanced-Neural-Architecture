# Nemotron Overview

## Ce este

Nemotron este integrat in `ANA_MAX` in trei forme separate, ca sa nu stricam fluxul principal cu OpenCode:

1. runner simplu in terminal
2. chat web local in browser
3. backend integrat in `ANAAgent`
4. chat web pentru `ANAAgent` cu Nemotron

## Fisiere importante

- `nemotron_runner.py`
- `START_NEMOTRON.bat`
- `nemotron_chat.py`
- `START_NEMOTRON_CHAT.bat`
- `core/backends/nemotron_openrouter_backend.py`
- `main_nemotron.py`
- `START_ANA_NEMOTRON_AGENT.bat`

## Ce face acum

- foloseste OpenRouter cu modelul `nvidia/nemotron-3-super-120b-a12b:free`
- citeste cheile din `.env`
- suporta fallback intre mai multe chei
- poate fi folosit ca runner simplu
- poate fi folosit ca chat web local
- poate fi folosit ca backend pentru `ANAAgent`

## Ce nu face inca

Integrarea actuala nu inseamna inca un agent complet de tipul celui folosit aici in sesiunea curenta.

Adica:
- Nemotron este backend de reasoning
- ANA are tool-urile
- dar bucla completa de tool-calling autonom nu este inca implementata special pentru Nemotron

Acesta este pasul urmator daca vrem comportament de tip agent complet.
