# ANA MAX v18.0 - Arhitectura Neurala Avansata

**Versiune:** 18.0.0-MAX  
**Status:** Stabil, functional cu OpenCode MCP  
**Last Updated:** 2026-03-26 (with v18 updates)

---

## ️ LEGAL DISCLAIMER & ETHICAL USE POLICY

### 🔒 WHITE HAT ONLY - AUTHORIZED USE REQUIRED

**ANA MAX is designed EXCLUSIVELY for:**
- ✅ Authorized penetration testing (with explicit permission)
- ✅ Security research on your own systems
- ✅ System monitoring and automation
- ✅ Educational and learning purposes
- ✅ Defensive security and protection

** STRICTLY PROHIBITED:**
- ❌ Unauthorized access to systems you don't own
- ❌ Spying on other users or applications without consent
- ❌ Exploiting vulnerabilities without permission
- ❌ Any illegal activity or malicious use
- ❌ Bypassing security controls on third-party systems

**⚖️ LEGAL NOTICE:**

Unauthorized use of ANA MAX tools may violate laws including:
- Computer Fraud and Abuse Act (CFAA) - USA
- GDPR Article 32 - European Union (for privacy tools)
- Local computer crime laws in your jurisdiction
- Anti-hacking legislation worldwide

**📜 RESPONSIBILITY:**

The authors and contributors of ANA MAX are **NOT responsible** for any misuse of this software. By using ANA MAX, you agree to:
1. Use tools only on systems you own or have explicit written permission to test
2. Comply with all applicable laws and regulations
3. Follow ethical security research practices
4. Report vulnerabilities responsibly to affected parties

** INTENDED AUDIENCE:**
- Security professionals and researchers
- System administrators
- Developers learning about security
- Ethical hackers and penetration testers
- Privacy advocates and educators

**🔐 DUAL-USE AWARENESS:**

Like all security tools (Metasploit, Nmap, Burp Suite, Kali Linux), ANA MAX is a **dual-use technology**. The same capabilities that protect systems can be misused to attack them. **The difference is YOUR INTENT and LEGAL AUTHORIZATION.**

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

ANA MAX este un **agent AI local** cu **20+ tools** care functioneaza ca "corp" pentru OpenCode (creierul).

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
│   └── conversation_learning.jsonl  # Lectii invatate
├── docs/
│   ├── ANA_DISCIPLINE_PLAYBOOK.md  # Reguli de disciplina
│   ├── CONVERSATIONAL_LEARNING.md  # Sistem de invatare
│   └── WORKLOG_2026-03-26.md        # Istoric complet
├── tests/
│   └── test_reliability.py  # Teste pentru reliability module
├── logs/
│   └── ana_max.log          # Log principal
├── backups/                  # Backup-uri automate
├── START_ANA_MAX.bat         # Porneste doar ANA
├── START_DEV_ANA_OPENCODE.bat # Porneste ANA + OpenCode
├── ENSURE_OPENCODE_MCP.ps1   # Configureaza MCP
└── requirements.txt          # Dependente Python
```

---

## 🚀 Cum Pornesti

### Doar ANA (MCP Server)

```batch
START_ANA_MAX.bat
```

### ANA + OpenCode (Dev Mode)

```batch
START_DEV_ANA_OPENCODE.bat
```

### Verifica Status

```bash
curl http://127.0.0.1:8765/health
curl http://127.0.0.1:8765/tools
```

---

## 🛠️ Tool-uri Disponibile (20+)

| Tool | Descriere |
|------|-----------|
| `file_operations` | CRUD fisiere, diff, surgical edit |
| `code_tools` | Analiza cod, executie |
| `system_control` | Vitals, procese, shell |
| `web_search` | Cautare web |
| `git_operations` | Git commands |
| `ana_memory` | Acces la memoria persistenta |
| `conversation_learning` | Salvare lectii |
| `session_log_miner` | Extrage lectii din loguri |
| `smart_search` | Semantic search cu embeddings |
| `codebase_understanding` | RAG pentru arhitectura |
| `browser_control` | Control browser (debug) |
| `debugger` | Traceback si fix plan |
| `privacy_shield` | Protectie date |
| `network_diag` | Diagnostic retea |
| `security_audit` | Audit securitate |
| `qa_testing` | Testare automata |
| `terminal` | Executa comenzi |
| `autonomous_engine` | Task-uri autonome |
| si altele... | |

---

## 🔧 Configurare AI (settings.yaml)

```yaml
ai:
  primary_backend: opencode_zen  # Foloseste OpenCode pentru AI
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

## 🗣️ Voice Feature (Built-in Capability)

### Ana Speaks Like Jarvis from Iron Man 🎙️

Ana MAX includes **built-in Text-to-Speech (TTS)** using `pyttsx3` as an integrated feature (not a standalone tool).

**Voice is embedded in:**
- `ana_orchestrator` - Task execution feedback
- `context_engine` - Active communication
- `proactive_interrupt` - Intelligent interruptions

```python
# Ana can speak when these tools are active:
├── Announcing task completion
├── Reading errors aloud
── Giving vocal feedback during autonomous mode
└── Warning about critical issues
```

### ️ How It Works:

Voice is **automatically available** when using orchestrator or context tools - no separate tool needed.

```python
# Voice is enabled by default in orchestrator:
voice_feedback: True   # Ana talks (Jarvis mode 😄)
voice_feedback: False  # Silent mode (recommended for focus)
```

### ⚠️ Funny Warning:

> **Don't enable voice unless you're ready!**  
> Ana will talk to you ALL DAY like JARVIS from Iron Man.  
> You might start arguing with her like in the movies! 😂  
> *(This is a real feature, not a joke!)*

### 🔧 Enable TTS:

```bash
pip install pyttsx3
```

---

## 📚 Documentatie

- **ANA_DISCIPLINE_PLAYBOOK.md** - Reguli de lucru, cum sa folosesti ANA eficient
- **CONVERSATIONAL_LEARNING.md** - Sistemul de invatare din conversatii
- **WORKLOG_2026-03-26.md** - Istoric complet cu toate modificarile

---

## ⚙️ Dependente

```
Flask, DrissionPage, psutil, pyttsx3, sentence-transformers,
google-genai, openai, duckduckgo-search, mem0ai, rich, pyyaml
```

Instaleaza cu:

```bash
pip install -r requirements.txt
```

---

## 🐛 Troubleshooting

### ANA nu porneste

```bash
# Verifica Python
python --version

# Activeaza venv
.\venv\Scripts\activate

# Ruleaza manual
python main.py --debug
```

### OpenCode nu vede tool-urile

```bash
# Verifica MCP config
powershell -File ENSURE_OPENCODE_MCP.ps1

# Verifica health
curl http://127.0.0.1:8765/health
```

### Tool-ul nu functioneaza

```bash
# List all tools
python main.py --list-tools

# Run tests
python main.py --test
```

---

## 📝 Note de Development

- ANA foloseste **backup automat** inainte de orice operatie pe fisiere
- **Circuit breaker** dezactiveaza automat tools care esueaza de 3x consecutiv
- **Memory** persista intre sesiuni via SQLite
- **Health tracking** monitorizeaza success rate per tool

---

**Creat pentru OpenCode MCP integration | v18.0.0-MAX**
