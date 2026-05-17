# ANA MAX v18.0 - Arhitectura Neurală Avansata

**Versiune:** 18.0.0-MAX  
**Status:** Stabil, funcțional cu OpenCode MCP  
**Last Updated:** 2026-03-26 (with v18 updates)

---

## Quick Snapshot

### Ce e important acum

- `BOOTSTRAP_ANA_MAX.bat` este punctul principal de reinstalare dupa formatare
- `SETUP_COMPLETE.bat` ramane compatibil si redirectioneaza catre bootstrap
- `SETUP_VSCODE_PYTHON.bat` face setup-ul de VS Code pentru Python
- `AI_RULES.md` defineste ordinea de lucru pentru alt AI sau alt asistent
- `PROMPT_FOR_OTHER_AI.md` este promptul scurt gata de copy-paste in alt tool
- folderul `community/` contine texte pentru testeri, prezentare si formulare tehnica
- `.vscode/settings.json` si `.vscode/extensions.json` sunt generate automat
- `Ruff` este formatterul si linterul recomandat pentru proiect

### Comenzi rapide

```cmd
cd ANA_MAX
BOOTSTRAP_ANA_MAX.bat
```

```cmd
cd ANA_MAX
SETUP_VSCODE_PYTHON.bat
```

```cmd
set ANA_MAX_NO_PAUSE=1
BOOTSTRAP_ANA_MAX.bat
```

### Istoric recent

- 2026-04-04: adaugat bootstrap complet pentru reinstalare
- 2026-04-04: adaugat setup automat pentru extensiile VS Code Python
- 2026-04-04: actualizat `SETUP_COMPLETE.bat` ca wrapper peste noul flow
- 2026-04-04: adaugat `AI_RULES.md` pentru lucru curat si consistent intre asistenti
- 2026-04-04: adaugat `PROMPT_FOR_OTHER_AI.md` pentru handoff rapid in alte tool-uri
- 2026-04-04: adaugat folderul `community/` pentru testeri si prezentare tehnica
- vezi si `docs/WORKLOG_2026-04-04.md` pentru detalii

---

## 🎯 Ce este ANA MAX?

ANA MAX este un **agent AI local** cu **20+ tools** care functionează ca "corp" pentru OpenCode (creierul).

```
┌─────────────────────────────────────────────────────────┐
│                     OPENCODE                           │
│              (Creierul - AI/LLM)                       │
│        path: %LOCALAPPDATA%\OpenCode\                  │
└───────────────────────┬─────────────────────────────────┘
                        │ MCP (Model Context Protocol)
                        ▼
┌─────────────────────────────────────────────────────────┐
│                     ANA MAX                            │
│              (Corpul - 20+ Tools)                     │
├─────────────────────────────────────────────────────────┤
│  Port: 8765 | Endpoint: http://127.0.0.1:8765         │
│  Health: http://127.0.0.1:8765/health                  │
└─────────────────────────────────────────────────────────┘
```

---

## 📁 Structura Proiectului

```
ANA_MAX/
├── main.py                    # Entry point - MCP server
├── core/                      # Nucleu
│   ├── agent.py              # Agent AI principal
│   ├── memory.py             # Memorie persistenta (SQLite)
│   ├── config.py             # Config loader (YAML)
│   ├── reliability.py        # Backup, health tracking, circuit breaker
│   ├── smart_search.py       # Semantic search (embeddings)
│   ├── advanced_features.py  # Self-healing, auto-fix
│   └── mcp_server.py         # HTTP MCP server
├── tools/                    # Tool-uri (20+)
│   ├── base.py              # Clasa de baza Tool
│   ├── files.py             # file_operations
│   ├── code.py              # code_tools
│   ├── system.py            # system_control
│   ├── web.py               # web_search
│   ├── git_tool.py          # git_operations
│   ├── memory_tool.py       # ana_memory
│   ├── conversation_learning_tool.py
│   ├── session_log_miner_tool.py
│   ├── browser_control.py  # browser_control
│   └── ... (altele)
├── config/
│   ├── settings.yaml        # Config principala v18
│   └── opencode_mcp.json    # MCP config pentru OpenCode
├── memory/
│   ├── ana_max_brain.db     # SQLite memory database
│   └── conversation_learning.jsonl  # Lecții învățate
├── docs/
│   ├── ANA_DISCIPLINE_PLAYBOOK.md  # Reguli de disciplina
│   ├── CONVERSATIONAL_LEARNING.md  # Sistem de învățare
│   └── WORKLOG_2026-03-26.md        # Istoric complet
├── tests/
│   └── test_reliability.py  # Teste pentru reliability module
├── logs/
│   └── ana_max.log          # Log principal
├── backups/                  # Backup-uri automate
├── START_ANA_MAX.bat         # Pornește doar ANA
├── START_DEV_ANA_OPENCODE.bat # Pornește ANA + OpenCode
├── ENSURE_OPENCODE_MCP.ps1   # Configurează MCP
└── requirements.txt          # Dependente Python
```

---

## 🚀 Cum Pornești

### Doar ANA (MCP Server)

```batch
START_ANA_MAX.bat
```

### ANA + OpenCode (Dev Mode)

```batch
START_DEV_ANA_OPENCODE.bat
```

### Verifică Status

```bash
curl http://127.0.0.1:8765/health
curl http://127.0.0.1:8765/tools
```

---

## 🛠️ Tool-uri Disponibile (20+)

| Tool | Descriere |
|------|-----------|
| `file_operations` | CRUD fișiere, diff, surgical edit |
| `code_tools` | Analiza cod, execuție |
| `system_control` | Vitals, procese, shell |
| `web_search` | Căutare web |
| `git_operations` | Git commands |
| `ana_memory` | Acces la memoria persistentă |
| `conversation_learning` | Salvare lecții |
| `session_log_miner` | Extrage lecții din loguri |
| `smart_search` | Semantic search cu embeddings |
| `codebase_understanding` | RAG pentru arhitectura |
| `browser_control` | Control browser (debug) |
| `debugger` | Traceback și fix plan |
| `privacy_shield` | Protecție date |
| `network_diag` | Diagnostic rețea |
| `security_audit` | Audit securitate |
| `qa_testing` | Testare automată |
| `terminal` | Execută comenzi |
| `autonomous_engine` | Task-uri autonome |
| și altele... | |

---

## 🔧 Configurare AI (settings.yaml)

```yaml
ai:
  primary_backend: opencode_zen  # Folosește OpenCode pentru AI
  fallback_backend: gemini        # Fallback la Gemini cloud
  
  # Modele disponibile (round-robin, prefer free)
  backends:
    - model: big-pickle
    - model: minimax-m2.5-free
    - model: mimo-v2-pro-free
    - model: gpt-5-nano
    - model: gemini-2.5-flash  # Reserve/Fallback

mcp:
  port: 8765
  host: "127.0.0.1"
  enabled: true
```

---

## 🔥 Advanced Mode: ANA + FRIDA (For Engineers)

### FRIDA = "Ana's Best Friend" 🤝

**FRIDA** is a **Dynamic Instrumentation Toolkit** used by security researchers and reverse engineers.

```yaml
FRIDA = Dynamic Instrumentation Toolkit
│
├── What it does:
│   ├── Intercepts Windows API calls in real-time
│   ├── Sees what processes are doing internally
│   ├── Can modify application behavior dynamically
│   └── Analyzes memory, crypto, network traffic
│
├── Why Ana needs it:
│   ├── To see what other applications are doing
│   ├── To understand user workflows deeply
│   ├── To detect hidden errors and anomalies
│   └── To automate complex system-level tasks
│
└── Why ADMIN mode:
    ├── Frida requires root/admin privileges
    ├── To hook system processes
    └── Otherwise sees only its own processes
```

### 🚀 Running with FRIDA

```batch
# Normal mode (safe, recommended for most users)
ANA_MAX.bat

# Admin mode (Frida + full system access - for engineers)
ANA_MAX_FRIDA_ADMIN.bat
```

### ⚠️ Important Notes

- **Admin mode requires UAC approval** - Accept the Windows security prompt
- **For advanced users only** - Frida is a professional reverse engineering tool
- **Full system visibility** - Ana can see ALL processes, not just her own
- **WorkGraph enhancement** - FRIDA enables deep workspace awareness

### 🔧 Prerequisites for FRIDA Mode

```bash
# Install Visual C++ Build Tools (required for Frida)
# Download from: https://visualstudio.microsoft.com/visual-cpp-build-tools/

# Install Frida
pip install frida-tools

# Install ADB (for mobile device support)
# Download from: https://developer.android.com/studio/releases/platform-tools
```

---

## 📚 Documentație

- **ANA_DISCIPLINE_PLAYBOOK.md** - Reguli de lucru, cum să folosești ANA eficient
- **CONVERSATIONAL_LEARNING.md** - Sistemul de învățare din conversații
- **WORKLOG_2026-03-26.md** - Istoric complet cu toate modificările

---

## ⚙️ Dependente

```
Flask, DrissionPage, psutil, pyttsx3, sentence-transformers,
google-genai, openai, duckduckgo-search, mem0ai, rich, pyyaml
```

Instalează cu:

```bash
pip install -r requirements.txt
```

---

## 🐛 Troubleshooting

### ANA nu pornește

```bash
# Verifică Python
python --version

# Activează venv
.\venv\Scripts\activate

# Rulează manual
python main.py --debug
```

### OpenCode nu vede tool-urile

```bash
# Verifică MCP config
powershell -File ENSURE_OPENCODE_MCP.ps1

# Verifică health
curl http://127.0.0.1:8765/health
```

### Tool-ul nu funcționează

```bash
# List all tools
python main.py --list-tools

# Run tests
python main.py --test
```

---

## 📝 Note de Development

- ANA folosește **backup automat** înainte de orice operație pe fișiere
- **Circuit breaker** dezactivează automat tools care eșuează de 3x consecutiv
- **Memory** persistă între sesiuni via SQLite
- **Health tracking** monitorizează success rate per tool

---

**Creat pentru OpenCode MCP integration | v18.0.0-MAX**
