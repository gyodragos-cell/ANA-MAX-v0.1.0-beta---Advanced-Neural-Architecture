# ANA MAX v2.0.0-RC (Advanced Neural Architecture)
<div align="center">

[![Site Live](https://img.shields.io/badge/Site-Live-brightgreen)](https://gyodragos-cell.github.io/ANA-MAX-v0.1.0-beta---Advanced-Neural-Architecture/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![MCP Tools](https://img.shields.io/badge/MCP_Tools-123-purple.svg)](#)
[![AI Model](https://img.shields.io/badge/AI-Qwen2.5--Coder:7b-orange.svg)](#)

</div>

**Advanced Neural Architecture (ANA MAX)** este cel mai puternic si autonom agent OS local (Windows-first), orientat catre orchestrare AI, pentesting automatizat si integrare totala in sistem. 

Fara dependente cloud, fara restrictii comerciale. Complet "Caveman Mode".

## 🚀 Overview (Mint Condition - v2.0.0-RC)
ANA MAX unifica orchestrarea deterministica, viziunea computerizata (Vision AI) si instrumentele de securitate (System Intelligence) intr-un singur bridge MCP local. 

**Noutati in v2.0.0-RC:**
* **123 MCP Tools**: Cea mai mare colectie de unelte locale inregistrate in registry.
* **System Intelligence**: Injectie de DLL (Frida v17.11.0), Patching de memorie in timp real, Monitorizare securitate procese, Analiza retea.
* **Vision Tools (11x)**: Captura ecran, OCR (PaddleOCR), identificare elemente UI pe Windows, click/type automatizat.
* **Gemini Proxy (gemini_proxy_v2.py)**: Suport multi-model, rutare inteligenta, bypass limitari Ollama.
* **RAG Knowledge Base**: Baza de date cu 39 intrari (HTML/CSS/JS patterns).
* **Continual Learning**: Auto-corectie si invatare din actiuni precedente via SQLite Memory Cortex.

## 🏗 Arhitectura
Sistemul ruleaza pe un server Flask (Port 8766) care expune capabilitatile prin **JSON-RPC 2.0**.
Modele de AI suportate: **Ollama qwen2.5-coder:7b** (implicit local), **Gemini 1.5 Pro/Flash** (prin proxy).

`	ext
Code / IDE (Devin, Cursor, Claude)
    ↓
MCP Server (:8766) - tool_adapters.py
    ↓
Orchestrator (Vede → Gandeste → Planifica)
    ↓
ToolBridge (123 Unelte - Vision, System, Web, Terminal)
    ↓
Execution Layer (Windows UI, Frida, PowerShell, SQLite)
    ↓
Memory Cortex (Self-heal, Evolutie, Feedback Loop)
`

## 🔮 Roadmap (Ce urmeaza)
Ne propunem sa extindem limitele sistemelor autonome locale:
1. **Malware Research & Evasion Autonomous Lab**: Integrare si mai profunda la nivel de Kernel pentru hooking si monitorizare stealth.
2. **LoRA Fine-tuning Local**: Generarea automata de seturi JSONL pe baza interactiunilor si fine-tuning direct pe RTX.
3. **Deep Sight "God View"**: Imbunatatirea agentilor de viziune pentru a intelege layout-uri complexe 3D si reverse-engineering direct din UI.
4. **Agenti Multipli Concurenti**: Swarm de agenti locali care rezolva task-uri in paralel (ex: unul face fuzzing pe retea, altul analizeaza traficul in Wireshark).

## 📦 Quick Start
`ash
# 1. Cloneaza repository-ul
git clone https://github.com/gyodragos-cell/ANA-MAX-v0.1.0-beta---Advanced-Neural-Architecture.git

# 2. Setup environment (Windows)
python -3.12 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# 3. Porneste ANA MAX Server
START_ANA_MAX_MCP_For_Devin.bat
`

## 🌐 Live Dashboard
Pentru o privire interactiva asupra diagramei de arhitectura si modulelor AI:
👉 **[View ANA MAX Dashboard](https://gyodragos-cell.github.io/ANA-MAX-v0.1.0-beta---Advanced-Neural-Architecture/)**

## 🤝 Contribuie
Fiind un mediu de laborator privat (Pentest Lab), PR-urile sunt deschise pentru:
* Noi scripturi de Frida (bypass/hooks).
* Tool-uri MCP inovative (C++/Python).
* Eficientizarea contextului (ContextEngine).

---
*Made with ❤️ for the local-first AI & Security community.*
