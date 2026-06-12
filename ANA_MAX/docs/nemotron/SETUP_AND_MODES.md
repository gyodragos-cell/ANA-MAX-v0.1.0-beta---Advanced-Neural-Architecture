# Setup Si Moduri De Pornire

## Variabile folosite

Din `.env`:

- `OPENROUTER_API_KEY`
- `OPENROUTER_API_KEYS`
- `OPENROUTER_BASE_URL`
- `OPENROUTER_MODEL`
- `OPENROUTER_SITE_URL`
- `OPENROUTER_APP_NAME`
- `OPENROUTER_PROMPT`

## Mod 1: runner simplu

Pornire:

```cmd
cd C:\Users\billy\Desktop\ana_dev\ANA_MAX
START_NEMOTRON.bat
```

Util pentru:
- smoke test
- verificare chei
- verificare model

## Mod 2: chat web local

Pornire:

```cmd
cd C:\Users\billy\Desktop\ana_dev\ANA_MAX
START_NEMOTRON_CHAT.bat
```

Deschide:

`http://127.0.0.1:8787`

Util pentru:
- discutii normale
- idei
- cod
- test rapid in browser

## Mod 3: ANA MAX cu backend Nemotron

Pornire:

```cmd
cd C:\Users\billy\Desktop\ana_dev\ANA_MAX
START_ANA_NEMOTRON_AGENT.bat
```

Util pentru:
- a rula infrastructura ANA cu backend Nemotron
- a testa incarcarea tool-urilor cu Nemotron ca model principal

## Mod 4: chat web pentru ANA + Nemotron

Pornire:

```cmd
cd C:\Users\billy\Desktop\ana_dev\ANA_MAX
START_ANA_NEMOTRON_AGENT_CHAT.bat
```

Deschide:

`http://127.0.0.1:8797`

Util pentru:
- a vorbi cu ANA in browser
- a folosi backend-ul Nemotron peste infrastructura Anei
- a avea chat si mod agent in acelasi flux vizual

## Observatie importanta

Acest mod este separat de:
- `START_ANA_MAX.bat`
- `START_DEV_ANA_OPENCODE.bat`

Deci nu strica legatura standard cu OpenCode.
