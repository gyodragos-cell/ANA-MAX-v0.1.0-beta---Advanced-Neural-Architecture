# 🗺️ ANA MAX - Arhitectura și Ghid de Lucru pentru Agenții AI

> **SCOPUL ACESTUI DOCUMENT:** 
> Acest fișier reprezintă "Harta" oficială a proiectului. Orice agent AI care lucrează pe acest proiect TREBUIE să citească acest fișier înainte de a face modificări, pentru a câștiga timp, a preveni rescrierea redundantă și a menține proiectul "curat și fără zgomot".

## 📂 1. Harta Fișierelor (Ce este și unde se află)

### ⚙️ `core/` (Creierul și Nucleul)
Aici stă logica de bază. **Nu adăugați tool-uri aici!**
* `agent.py`: Logica de rutare a modelelor LLM și crearea agentului ANA.
* `mcp_server.py`: Serverul Flask/MCP. Expune capabilitățile A.N.A. către exterior. (Protejat prin `Bearer Token`).
* `memory.py`: Gestiunea SQLite. **Regulă:** Folosește un Singleton cu conexiune persistentă (`_conn`), NU deschide fișierul la fiecare interogare.
* `license_manager.py`: Licensing Free/Pro. **Status v0.2.0:** `desktop_capture` este FREE; premium rămân doar streaming/control/insight/deep sight. Folosește `uuid.getnode()` pentru machine id, nu `platform.uuid4()`.

### 🛠️ `tools/` (Mâinile și Ochii - Capacitățile Agentului)
Orice abilitate nouă a agentului devine un Tool aici.

**Desktop Control & UI Automation:**
* `windows_uia_bridge.py`: Vederea interfeței grafice. NATIV, structural, bazat pe `pywinauto` (FĂRĂ OCR, FĂRĂ Screenshots oarbe).
* `desktop_capture.py`: Capturi de ecran efective. **FREE în v0.2.0**; folosit pentru Vision AI, SEE/VERIFY și fallback când UIA nu ajunge.
* `live_desktop_viewer.py`: Streaming desktop real-time. **PREMIUM**.
* `desktop_control_tool.py`: Control avansat desktop: click pe text, tastare, screenshot. **PREMIUM**.
* `windows_insight_tool.py`: Monitorizare avansată a sistemului Windows. **PREMIUM**.
* `window_manager.py`: Gestionare ferestre: listare, snap, move, tile, focus, minimize, maximize, close.
* `clipboard_manager.py`: Clipboard intelligence: citire, scriere, istoric, monitorizare, transformări.
* `ocr_tool.py`: OCR pe ecran, regiune, fișier sau clipboard (PaddleOCR/Tesseract).

**AI Core Intelligence (2026-05-14):**
* `context_engine.py`: Observă continuu (ferestre active, clipboard, procese, CPU/RAM), clasifică activitatea, prezice intenții cu scor de confidență, învață din comportament.
* `proactive_interrupt.py`: 5 detectori activi: STUCK (blocat), SEQUENCE (fluxuri repetitive), CLIPBOARD INTENT, REPEAT, CONTEXT SHIFT.
* `self_evolving_tool.py`: Auto-fix runtime errors, auto-improve code, auto-install missing libraries, changelog în SQLite.
* `memory_cortex.py`: 4 tipuri de memorie: Episodică (conversații), Semantică (fapte stabile), Procedurală (abordări funcționale), Error Log (greșeli corectate).
* `ana_orchestrator.py`: Orchestrator principal: execută taskuri în limbaj natural, batch processing, tool coordination, self-healing.
* `context_bridge.py`: Memoria persistentă dintre sesiuni: restore_session(), observe_event(), save_session().
* `tool_adapters.py`: 9 adaptoare care expun AI Core prin interfața standard registry (get_definition, execute).

**Security & Network:**
* `windows_deep_sight.py`: "God View" sub capotă (procese, rețea, registry, fișiere). Bazat strict pe `psutil` și `Frida`.
* `security_tool.py`: Audit securitate: scanare secrete (keys), vulnerabilități.
* `network_tool.py`: Diagnoză rețea: ping, port scan, DNS, IP info.
* `network_pentest_tool.py`: Network penetration testing (White Hat).
* `mitm_analyzer_tool.py`: Analiză trafic MITM (Charles/Wireshark) pentru bug bounty.
* `hardware_scanner_tool.py`: Hardware security scanner - scan IoT, routers, devices.

**Development & Code:**
* `code.py`: Instrumente pentru cod: analiză, execuție, creare proiecte.
* `code_search.py`: Căutare avansată în cod: grep cu regex, symbol lookup.
* `codebase_understanding_tool.py`: Interogare semantică și analiză de arhitectură.
* `edit_tool.py`: Editează punctual un fișier prin replace exact sau inserții.
* `git_tool.py`: Controlul versiunilor folosind Git.
* `debugger_tool.py`: Analiză de traceback și propuneri de reparații automate.

**Mobile & Advanced:**
* `adb_tool.py`: Operații ADB pentru control dispozitive Android.
* `frida_automation.py`: Instrumentare dinamică cu Frida.
* `apk_analyzer.py`: Reverse engineering APK: decompile, parse manifest.
* `advanced_scanner.py`: Scanare avansată de securitate: Deep Recon, Service Fingerprinting.

**Productivity & Automation:**
* `terminal_tool.py`: Terminal persistent cu sesiune păstrată.
* `browser_control.py`: Deschide browserul local sau inspectează o pagină web.
* `web_scraper.py`: Web scraping: fetch URL, parse HTML, extrage linkuri/text.
* `task_tool.py`: Planifică sau execută un task multi-pas.
* `autonomous_tool.py`: Activează modul de lucru autonom (Plan → Execute → Verify).
* `todo_tool.py`: Gestionează o listă persistentă de task-uri.
* `system_optimization_tool.py`: Optimizează sistemul Windows: curăță temp, recycle bin, DNS.

**Memory & Learning:**
* `memory_tool.py`: Acces curat la memoria persistentă ANA.
* `conversation_learning_tool.py`: Salvează și caută lecții învățate din conversații.
* `session_log_miner_tool.py`: Extrage lecții utile din fișiere de sesiune.
* `smart_search_tool.py`: Căutare ultra-rapidă în proiecte mari.

**System & Utilities:**
* `system.py`: Monitorizare și control sistem: vitals, procese, comenzi shell.
* `files.py`: Operații cu fișiere: citire, scriere, căutare, editare.
* `web.py`: Caută informații pe web folosind DuckDuckGo (anonim).
* `qa_tool.py`: Asigurarea calității: generare teste, edge-cases, mock data.
* `privacy.py`: Protejează anonimitatea Operatorului.
* `science_tool.py`: Analiză statistică, procesare de date și simulări.
* `tool_healthcheck.py`: Verifică rapid starea tool-urilor ANA.

**⚠️ Regulă:** Orice tool nou din folderul `tools/` **trebuie** înregistrat în `tools/__init__.py` și în `main.py`!

### 📄 `docs/` (Memoria și Planificarea)
* `PLAN_VIITOR_OCHI_ANA_MAX.md`: Arhitectura și etapele pentru sistemul UIA complet.
* `PROJECT_MAP_AI_GUIDE.md`: Harta de lucru pentru agenți AI. Ține acest fișier sincronizat cu release-ul GitHub înainte de publicare.
* `PATCH_main.md`: Notă istorică pentru patch-ul AI Core. **Nu trebuie să fie `.py`**, altfel `compileall` încearcă să-l compileze.
* (Aici trebuie salvate viitoarele summary-uri ca agentul nou să nu o ia de la zero).

### 🚀 Fișiere și Foldere Root
* `main.py`: Punctul de intrare central. Pornește serverul, rutează totul.
* `install.bat` / launcher scripts: Scripturi Windows pentru instalare sau pornire. Verifică numele exact din release înainte să documentezi un shortcut.
* `archives/` și `backups/`: Conțin cod vechi (ex: teste, versiuni anterioare). **Regulă AI:** Ignoră complet aceste foldere când analizezi codul sursă. Nu încerca să repari erori din interiorul lor.

---

## ⚖️ 2. Filosofia de Dezvoltare (The ANA MAX Way)
**Orice AI care modifică cod trebuie să respecte aceste 3 reguli absolute:**

1. **🚫 Fără "Zgomot" (Silent System):**
   - Folosește log-level `DEBUG` pentru evenimente recurente (creare de procese, mouse tracking, heartbeat). 
   - Folosește `INFO` exclusiv pentru pornirea/oprirea modulelor majore. Nu spamma terminalul utilizatorului!
   
2. **⚡ API-uri Native > Subprocese (Performanță Maximă):**
   - **NICIODATĂ** nu folosi `subprocess.run(["powershell", "-Command"...])` pentru a obține o listă de fișiere sau procese dacă există un modul nativ.
   - Procese? Folosește `psutil`.
   - Baze de date? Folosește module native cu `threading.Lock()`.
   - UI Click/Search? Folosește `pywinauto` (UIAutomation). Apelarea repetată a subprocess este inacceptabilă din cauza overhead-ului CPU.

3. **🔒 Securitate Built-In (God Mode protejat):**
   - ANA are acces total la OS. Niciun endpoint HTTP (ex: rutele din `mcp_server.py`) nu trebuie lăsat liber. Verifică mereu existența cheii din `config.get("mcp.api_key")` prin header-ul `Authorization: Bearer`.

## 🔄 3. Cum adaugi o Funcție Nouă (Ghid Rapid AI)
1. Analizează dacă funcția e un Tool (ex: `cautare_fisiere`) sau e un Core update.
2. Creează fișierul curat în `tools/`. 
3. Importă-l în `tools/__init__.py`.
4. Înregistrează-l în array-urile din `main.py` (`desktop_tools` sau `new_tools`).
5. Rulează obligatoriu `python main.py --test` înainte să confirmi utilizatorului că funcționează.
6. Pentru release, rulează și:
   ```bash
   python -m compileall -q main.py core tools vscode_extension
   python -m unittest discover -s tests -v
   python main.py --list-tools
   ```

---

## 📦 4. Dependențe și Configurare (Setup Complet)

### 🔧 Dependențe Principale (Obligatorii)
```bash
# Se instalează automat cu:
pip install -r requirements.txt

# Sau manual:
pip install flask pywinauto psutil python-dotenv pyyaml
```

### 🖥️ Desktop Control & UI Automation
```bash
# Deja incluse în requirements.txt:
pip install pywinauto    # UI Automation (windows_uia_bridge)
pip install pywin32      # Win32 API (window_manager, clipboard_manager)
pip install mss          # Screen capture (desktop_capture, ocr_tool)
pip install pillow       # Image processing (ocr_tool, desktop_capture)
```

### 📸 OCR Tool (Opțional - la prima utilizare)
```bash
# Opțiunea 1 (Recomandat - mai precis):
pip install paddleocr paddlepaddle

# Opțiunea 2 (Mai ușor):
pip install pytesseract
# + instalează Tesseract OCR de la: https://github.com/UB-Mannheim/tesseract/wiki
```

### 🤖 AI Core Intelligence (Nu necesită dependențe noi)
Toate modulele AI Core folosesc doar:
- `threading` (stdlib)
- `sqlite3` (stdlib) 
- `win32gui`, `win32con` (pywin32 - deja instalat)
- `psutil` (deja instalat)

### 📡 Security & Mobile (Opționale)
```bash
# Frida (pentru instrumentare mobilă):
pip install frida-tools

# ADB (Android Debug Bridge):
# Descarcă de la: https://developer.android.com/studio/releases/platform-tools
# Adaugă în PATH
```

### 🌐 Environment Variables (`.env`)
```env
# Createază .env din .env.example
copy .env.example .env

# Completează DOAR ce ai nevoie:
OPENCODE_API_KEY=your_key_here        # Pentru OpenCode Zen backend
OPENROUTER_API_KEY=your_key_here      # Pentru OpenRouter fallback
OLLAMA_BASE_URL=http://localhost:11434  # Pentru LLM local (opțional)
MCP_API_KEY=your_mcp_secret_key       # Pentru protecția MCP server
```

### ⚙️ Configurare MCP Server
```bash
# Pornire standard:
python main.py

# Cu port custom:
python main.py --port 8765

# Cu debug logging:
python main.py --debug

# Listare tool-uri:
python main.py --list-tools

# Testare rapidă:
python main.py --test
```

### 🔑 MCP Client Configuration
```json
// claude_desktop_config.json sau similar
{
  "mcpServers": {
    "ana-max": {
      "command": "python",
      "args": ["C:\\path\\to\\ANA_MAX\\main.py"],
      "env": {
        "MCP_API_KEY": "your_secret_key"
      }
    }
  }
}
```

### 🚀 Quick Start (Windows)
```bash
# 1. Clone repository
git clone https://github.com/gyodragos-cell/ANA-MAX.git
cd ANA_MAX

# 2. Create virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# 3. Install dependencies
pip install -r docs/requirements.txt

# 4. Configure environment
copy .env.example .env
# Editează .env cu cheile tale

# 5. Test installation
python main.py --list-tools
python main.py --test

# 6. Start MCP server
python main.py

# SAU folosește shortcut-ul:
# Double-click: Start ANA MAX.bat
```

---

## 📊 5. Status Proiect (2026-05-15)

### ✅ Feature-uri Implementate:
- **52 tools încărcate în verificarea release curentă** (`python main.py --list-tools`)
- **56 capabilități documentate** în totalul de produs (43 Free + 4 Premium + 9 AI Core)
- **AI Core Intelligence** (9 module): context, memory, evolution, orchestration, proactive detection
- **Vision AI** (FREE): Screenshot capture + OCR text recognition
- **Desktop Control**: UIA, screenshots, windows, clipboard, OCR
- **Security Suite** (6 tools): pentest, MITM, scanning, hardware
- **Mobile Tools** (4 tools): ADB, Frida, APK analysis
- **Development Tools** (8 tools): code, git, debugging, editing
- **Memory & Learning** (4 tools): persistent memory, conversation learning
- **License System** (Pro): Enterprise-grade licensing with Fernet encryption

### 🎯 Arhitectură:
```
ANA MAX
├── AI Core (9 modules)
│   ├── Context Engine (observă, clasifică, prezice)
│   ├── Memory Cortex (4 tipuri de memorie)
│   ├── Proactive Interrupt (5 detectori)
│   ├── Self-Evolving Tool (auto-fix, auto-improve)
│   ├── ANA Orchestrator (task execution)
│   ├── Context Bridge (session persistence)
│   ├── Window Manager (snap, tile, focus)
│   ├── Clipboard Manager (history, monitor)
│   └── Tool Adapters (expose AI Core via registry)
│
├── Vision AI (FREE - NEW in v0.2.0)
│   ├── Desktop Capture (screenshot)
│   └── OCR Tool (PaddleOCR text recognition)
│
├── Desktop Control (7 tools)
│   ├── Windows UIA Bridge (pywinauto)
│   ├── Window Manager (snap, tile, focus)
│   ├── Clipboard Manager (history, monitor)
│   └── OCR Tool (PaddleOCR/Tesseract)
│
├── Security & Network (6 tools)
├── Mobile & Advanced (4 tools)
├── Development & Code (8 tools)
├── Productivity & Automation (7 tools)
├── Memory & Learning (4 tools)
└── System & Utilities (12 tools)
```

### 📈 Versiune Curentă:
- **GitHub:** v0.2.0-beta
- **VS Code Marketplace:** Ready for publishing (v0.2.0)
- **Release Count:** 43 Free + 4 Premium + 9 AI Core
- **Verificare locală:** 52 tool-uri încărcate de `main.py --list-tools`
- **Status:** Funcțional; `compileall`, `main.py --test`, `main.py --list-tools` și `unittest` trecute în release

---

## 🆕 6. Changelog Recent (v0.2.0 - 2026-05-15)

### 🎯 Free Vision Features - Major Release

#### Ce s-a realizat:
1. **desktop_capture** mutat de la Premium la FREE
2. **OCR activat** - PaddleOCR inclus în requirements.txt
3. **Vision AI** - AI-ul poate acum să vadă și să citească text de pe ecran

#### Modificări în arhitectură:
- **main.py**: `desktop_capture` decomentat și activat
- **main.py**: `_list_tools()` și `_run_tests()` încarcă registry-ul dacă este gol
- **main.py**: output CLI tolerant UTF-8 pentru diacritice/emoji pe Windows
- **core/license_manager.py**: `desktop_capture` scos din `PREMIUM_TOOLS`; `uuid.getnode()` folosit pentru machine id
- **requirements.txt**: `paddleocr` și `paddlepaddle` decomentate
- **index.html**: statistici actualizate (43 Free, 4 Premium)
- **vscode_extension/**: versiune 0.2.0, descriere actualizată
- **tools/PATCH_main.py**: mutat în `docs/PATCH_main.md` ca să nu mai rupă compilarea Python

#### Tool-uri Free vs Premium:
**FREE (43 tools):**
- ✅ desktop_capture (Vision AI - screenshot)
- ✅ OCR (PaddleOCR text recognition)
- ✅ Toate tool-urile de cod, web, sistem, securitate, UI Automation

**PREMIUM (4 tools):**
- 🔒 live_desktop_viewer (real-time streaming)
- 🔒 desktop_control (full automation)
- 🔒 windows_insight (advanced monitoring)
- 🔒 windows_deep_sight (God View)

#### Verificări release trecute:
```bash
python -m compileall -q main.py core tools vscode_extension
python main.py --test
python main.py --list-tools
python -m unittest discover -s tests -v
```

Rezultate confirmate în `ANA_MAX_GitHub_Release`:
- `main.py --test`: 2 PASS / 0 FAIL
- `main.py --list-tools`: 52 tool-uri încărcate
- `unittest`: 59 teste OK

### 📦 Extensie VS Code:
- **Versiune:** 0.2.0
- **Pachet:** `advanced-neural-architecture-0.2.0.vsix`
- **Descriere:** Actualizată cu Vision AI
- **README:** Actualizat cu noile funcționalități free
