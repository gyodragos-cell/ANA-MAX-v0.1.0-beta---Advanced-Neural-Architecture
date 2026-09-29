# DUCK PROXY — JURNAL DE LUCRU (2026-07-30)

## Context initial
- **Problema:** `START_DUCK_PROXY.bat` (din `ana_dev\ANA_MAX\duck_proxy\`) pornea proxy-ul, extragea tokenuri cu Playwright, dar apoi `requests.post` replay catre Duck.ai returna `418 ERR_CHALLENGE`.
- **Istoric:** Abordarea veche functiona cand tokenurile erau puse manual din Charles Proxy (fingerprint real). Acum Duck.ai a crescut securitatea.
- **User request:** Repar proxy-ul + mut totul in `ana-manus` (proiect elegant, la un loc).

---

## CE AM FACUT

### 1. Diagnostic sistematic (4 abordari testate)

| # | Abordare | Rezultat | De ce |
|---|---|---|---|
| 1 | `requests.post` replay (cod istoric) | ❌ **418 ERR_CHALLENGE** | TLS/JA3 fingerprint diferit; challenge semnat per-sesiune |
| 2 | `page.evaluate(fetch)` cu headere injectate | ❌ **418 ERR_CHALLENGE** | `x-vqd-hash-1`/`x-fe-signals` se recalculeaza per-request de JS — nu pot fi injectate manual |
| 3 | Chromium bundle Playwright + drive UI | ❌ **CAPTCHA "select all ducks"** | Chromium bundle e fingerprintat ca automatizare/bot |
| 4 | **Chrome REAL (`channel='chrome'`) + profil persistent + intercept retea** | ✅ **200 + SSE curat** | Chrome real trust-uit, profil persistent pastreaza sesiunea, browserul face singur toata criptografia |

**PoC #4 confirmat experimental:** Status 200, stream SSE cu `"message":"Can"`, `"message":" you"`. Chrome-ul trimite cererea, noi doar ascultam raspunsul.

### 2. Cauza reala a 418 (demonstrata)

Analizand pachetul de retea real (furnizat de user):
- `x-vqd-hash-1` contine `challenge_id` + `timestamp` semnate — valide doar pentru sesiunea browser care le-a generat
- `x-fe-signals` e event-tracking live (mouse/tastatura timestamps)
- `durableStream.publicKey` e RSA-OAEP-256 generat proaspat client-side per sesiune
- **Niciuna din aceste componente nu este reutilizabila prin `requests`**

→ Singura solutie: browserul Chrome trust-uit trimite cererea el-insusi. Noi tastam in UI si interceptam raspunsul.

### 3. Implementare noua

**Fisier:** `ANA_MAX/duck_proxy/duck_proxy_server.py` (300+ linii, arhitectura curata)

**Arhitectura:**
- `BrowserWorker` (thread dedicat) — detine tot Playwright + Chrome. Rezolva bug-ul thread-affinity (Playwright sync API nu permite acces de pe thread-uri diferite).
- `FakeOllamaHandler` (HTTP server) — handler-ele trimit task-uri pe coada catre worker si asteapta rezultatul.
- Flux: POST `/api/chat` → traducere mesaje Ollama → tastare in textarea Duck.ai → `page.on("response")` intercepteaza SSE → parse `data: {"message":"..."}` → returneaza obiect Ollama `{model, message, done:true}`.
- Watchdog thread detecteaza daca pagina Chrome moare si pregateste re-lansare la urmatorul request.
- CAPTCHA detection: daca detecteaza "select all ducks", avertizeaza in consola si asteapta rezolvare manuala (o singura data; profilul persistent memoreaza trust-ul).

**Fisier:** `ANA_MAX/duck_proxy/START_DUCK_PROXY.bat` (adaptat ana-manus)
- Foloseste `ana-manus\ANA_MAX\venv\Scripts\python.exe` (totul la un loc)
- Bootstrap automat: `pip install --trusted-host ... playwright requests urllib3` (one-time)
- `taskkill ollama.exe` → elibereaza 11434
- Porneste proxy + ANA + live log + chat/dashboard

### 4. Migrare + cleanup

**Migrat in `ana-manus`:**
- `ANA_MAX/duck_proxy/duck_proxy_server.py` (nou)
- `ANA_MAX/duck_proxy/START_DUCK_PROXY.bat` (nou)
- `ANA_MAX/tests/smoke_duck_proxy.py` (smoke test server complet)
- `ANA_MAX/tests/smoke_worker.py` (smoke test worker thread-safety)

**Sters din root (16 fisiere scratch):**
- `smoke_duck_proxy.py`, `poc_page_fetch.py`, `poc_drive_ui.py`, `poc_real_chrome.py`, `poc_final_ui.py`
- `diag_chrome_state.py`, `diag_response_dom.py`, `diag_intercept_real.py`
- `duck_html.txt`, `duck_screen.png`, `resp_state.png`, `resp_html.html`, `chrome_state.png`
- `inspect_duck.py`, `scratch_duck_playwright.py`, `snap.py`

**Pastrate:** `.duck_profile/` (profil Chrome trust-uit), `run_curl.bat` (util pentru debug manual)
**Neatins:** `ana_dev/` (nu-l mai folosim dar nu-l stergem)

### 5. Dependente instalate

In `ana-manus/ANA_MAX/venv`:
```
playwright  1.61.0
requests    2.32.5
urllib3     1.26.18
```
Nota: `pip install` necesita `--trusted-host pypi.org --trusted-host files.pythonhosted.org --trusted-host pypi.python.org` din cauza unui certificat SSL interceptat in reteaua locala.

---

## CE A MERS ✅

1. **Extragere tokenuri via Playwright** (headless=False) — toate 4 headere + durableStream capturate in 7.9s
2. **Chrome real + profil persistent** — sesiune trust-uita pe duck.ai (fara CAPTCHA cu profil existent)
3. **Interceptare raspuns SSE** — `page.on("response")` a primit status 200 + body SSE complet cu mesaje
4. **Sintaxa + import + structura** — modul compilat, importat, toate metodele prezente, SSE parser functional
5. **Server HTTP** — `/api/tags` raspunde instant cu modelul `duck-ai-model:latest` (confirmat prin urllib)
6. **Bootstrap playwright** — instalare automata via .bat (cu `--trusted-host`)

---

## CE NU A MERS ❌

1. **`requests.post` replay** — HTTP 418 pe noul Duck.ai (fatal — abordare veche, eliminata)
2. **`page.evaluate(fetch)` cu headere injectate** — tot 418 (headerele se recalculeaza de JS per-request)
3. **Prima versiune duck_proxy_server.py** — `SyntaxError: name '_page' is used prior to global declaration` in watchdog. **Rezolvat:** mutat `global` la inceputul functiei.
4. **Prima versiune cu Playwright direct in handler HTTP** — `cannot switch to a different thread (which happens to have exited)`. Playwright sync API e thread-affine; browser-ul creat in thread-ul de initializare nu putea fi accesat din thread-urile handler-ului HTTP. **Rezolvat:** refactor complet cu `BrowserWorker` (thread dedicat cu coada de task-uri).
5. **Smoke test end-to-end cu server complet** — blocat din cauza timeout-urilor lungi (browser + tastare + asteptare SSE). Verificat partial: `/api/tags` raspunde, dar log-ul worker thread nu ajunge la stdout (buffering per-thread). **Nediagnosticat complet inca.**
6. **curl din Git Bash** — returneaza exit 127 / raspuns gol pe anumite comenzi ( posibil alias/path issue). Python urllib functioneaza corect.

---

## CE URMEAZA (NEXT STEPS)

### Prioritate 1: Fix buffering log + validare chat end-to-end
- **Problema:** Worker-ul Chrome ruleaza pe un thread daemon; `print()` din acel thread nu ajunge la stdout-ul serverului (posibil buffered/redirectat).
- **Fix:** Adaugare `sys.stdout.flush()` dupa fiecare `_log()`, sau mai bine: logging cu `logging.StreamHandler` configurat explicit pe `sys.stdout` cu `flush=True`.
- **Validare:** Dupa fix, porneste server, trimite POST PONG prin python urllib (150s timeout), confirma raspuns Duck in format Ollama.

### Prioritate 2: Fix event loop / captura response
- **Problea potentiala:** `page.on("response")` cu `response.text()` e blocking si ar putea da deadlock daca ruleaza in worker thread in timp ce Playwright incearca si alte operatiuni. Trebuie verificat.
- **Fallback:** Daca `page.on("response")` cu `.text()` da probleme, alternativa: route intercept cu `route.fulfill()`.

### Prioritate 3: Test auto-vindecare
- Inchide fortat fereastra Chrome → trimite request nou → confirma ca worker-ul detecteaza pagina moarta si re-lanseaza contextul automat.

### Prioritate 4: Integrare completa
- Testeaza `START_DUCK_PROXY.bat` end-to-end (proxy 11434 + ANA 8766 + chat Brave).
- Verifica ca ANA chat trimite primul mesaj prin proxy, Duck raspunde, si ANA afiseaza raspunsul in UI.

### Prioritate 5: Cleanup smoke test files
- Dupa validare, sterge sau muta `ANA_MAX/tests/smoke_duck_proxy.py` si `smoke_worker.py` (scratch de test).

---

## Structura fisierelor proiect

```
ana-manus/
├── ANA_MAX/
│   ├── duck_proxy/
│   │   ├── duck_proxy_server.py    (NOU — proxy complet cu BrowserWorker)
│   │   └── START_DUCK_PROXY.bat    (NOU — startup script cu bootstrap)
│   ├── tests/
│   │   ├── smoke_duck_proxy.py     (smoke test server — temporary)
│   │   └── smoke_worker.py          (smoke test worker — temporary)
│   └── venv/                       (playwright + requests + urllib3)
├── .duck_profile/                  (profil Chrome trust-uit — persistent)
├── START_ANA_OLLAMA.bat            (neatins — Ollama real)
└── docs/
    └── DUCK_PROXY_JOURNAL.md       (ACEST FISIER)
```

## [2026-07-30] Update v5.4 - Fix Final Startup & Encoding
- **Problema**: CMD raporta "python.exe not recognized" din cauza ghilimelelor si codarii UTF-8-BOM.
- **Solutie**: Rescris `START_DUCK_PROXY.bat` cu cai absolute simple si codare ANSI.
- **Status**: Proxy v5.1 (Async) testat manual si functional. ANA Server configurat sa porneasca automat dupa Proxy.
- **Port**: 11434 (standard).
- **Mod**: Headful (Chrome vizibil) pentru a evita detectia Duck.ai.
- **Fix Aditional**: Inregistrat `OllamaLiveLoggerTool` in `tools/__init__.py` pentru a permite pornirea ANA Server.

## [2026-07-30] Update v5.5 - Reparare Arhitectura si Auto-Healing
- **Incident**: Proiectul a fost mutat din na_dev in na-manus, rupand absolut toate scurtaturile, rutele venv si referintele .duck_profile. In plus, terminalele dispareau instant in caz de eroare
- **Root-Cause Playwright Zombie**: Dupa nchiderea serverului python, procesele chrome.exe lansate de Playwright ramneau active in background, ?innd fi?ierul .duck_profile blocat. La urmatoarea lansare proxy-ul dadea crash imediat: Failed to create a ProcessSingleton.
- **Root-Cause 503 Charles**: Din cauza prabusirii invizibile a proxy-ului, ANA_SERVER trimitea requestul spre 11434 in gol, generand un timeout 503 in Charles Proxy.
- **Root-Cause Interceptare Raspuns**: Duck.ai a schimbat/extins url-ul pentru chat. Ruta veche /duckchat/v1/chat rata interceptia.
- **Rezolvari Aplicate**:
  1. START_DUCK_PROXY.bat V5.5 scaneaza automat la start procesele WMI (Windows Management Instrumentation) si executa kill pe orice chrome.exe zombie care contine flagul duck_profile in linia de comanda.
  2. Adaugat argumentul cmd /k la lansarea serverelor in batch pentru ca ferestrele sa ramana vizibile chiar daca pica Python-ul.
  3. Relansat ecranul de LIVE LOG prin PowerShell Get-Content -Tail 50 in paralel cu serverele.
  4. Largit filtrul de re?ea CHAT_ENDPOINT = "/chat" in scriptul duck_proxy_server.py pentru a capta orice variatiune de URL Duck.
  5. S-au curatat erorile de sintaxa si s-a adaugat trigger fallback in Playwright care cauta activ si da click pe butonul de Send, daca apasarea tastei Enter nu este inregistrata.
- **Ce urmeaza (Daca mai pica in viitor)**:
  - Daca fereastra de FAKE_OLLAMA ramane din nou blocata, verifica in Task Manager manual eventualele procese ramase cu numele chrome.exe.
  - Daca mesajul se trimite dar fereastra asteapta fara sa preia raspunsul, inspecteaza ce URL foloseste Duck.ai astazi apasand F12 (Network) pe site. Daca s-a modificat (ex: /v3/msg), updateaza constanta CHAT_ENDPOINT din cod.
