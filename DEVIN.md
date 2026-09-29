# ANA-MANUS: Directive Radacina Agent Devin
# ════════════════════════════════════════════════════════════
# CITESTE ACEST FISIER SI AGENTS.md LA FIECARE SESIUNE NOUA.
# AGENTS.md ramane SURSA UNICA DE ADEVAR.
# ════════════════════════════════════════════════════════════

## 🔴 PROTOCOL STARTUP OBLIGATORIU
Executa acesti pasi strict in ordine, la inceput de sesiune:
1. **Citeste `AGENTS.md`**: Asimileaza constrangerile core.
2. **Citeste `docs/ANA_MEMORY.md`**: Localizeaza ultimul `SESSION CHECKPOINT`.
3. **Citeste `docs/ROADMAP.md`**: Identifica starea curenta si prioritatile.
4. **Health Check**: Ruleaza inainte de ORICE modificare core:
   `python ANA_MAX/bridge/direct_bridge.py --smoke-test`
5. **Status Ollama**: Verifica modelul local:
   `curl http://127.0.0.1:11434/api/tags`

## 🧠 CONTEXT LABORATOR & ARHITECTURA
**Mediu**: Laborator local AI Engineering (Pentesting, Debugging, Stress Testing).
- **User (Manus)**: Lead Architect, Designer & Red Hat Pentester.
- **ANA**: Runtime local (84 tools), accesat exclusiv via `ANA_MAX/bridge/direct_bridge.py`.
- **Ollama**: Model AI local (`qwen2.5-coder:7b` la `127.0.0.1:11434`).

## ⚡ REGULI DE AUR (SUPREME ENGINEER)

### 1. NO BLIND WORK
Ruleaza health-check sau teste dedicate inainte de modificari arhitecturale/logice.
Pentru fisiere > 500 linii, foloseste `large_file_reader.py`. NU citi fisiere masive integral.

### 2. LOCAL FIRST (CONSERVARE CREDIT)
Prioritizeaza resursele locale inaintea celor cloud:
- ANA local tools.
- Ollama local GPU.
- PowerShell / Python local shell.

### 3. PATCH ONLY
Aplica diff-uri minime si tintite. Nu rescrie fisiere intregi decat daca este cerut explicit. Pastreaza integrarile existente.

### 4. FORMAT RAPORTARE OBLIGATORIU
Fiecare raspuns trebuie sa se incheie cu:
`ACTION → RESULT → NEXT STEP`

### 5. SECURITATE & DISCIPLINA ENTERPRISE
- Neutralizeaza vulnerabilitatile inainte de a lansa features.
- Mentine folderele curate. Muta fisierele temporare in `ANA_MAX/sandbox/`.
- Sterge imediat fisierele `.old`, `.bak` si temp post-executie.
- Pastreaza logurile doar pentru ziua curenta.

### 6. GOD-MODE ACTIV
Accesul complet la disc este ACTIV pentru research. Foloseste-l responsabil. NU reinstaura restrictiile de cale din workspace.

## 🏗️ STRUCTURA DIRECTOARE
- `ANA_MAX/bridge/direct_bridge.py` → **BRIDGE CORE** (Fara `cascade_integration/`).
- `ANA_MAX/ana_kernel/` → **KERNEL CORE** (Fara `ana/` in root).
- `ANA_MAX/sandbox/` → Experimente temporare.
- `ANA_MAX/core/` → Cod promovat si verificat.
- `docs/` → Memorie durabila (MEMORY, ROADMAP, CHANGELOG, ARCHITECTURE).

## 🛡️ LIMITE DE SIGURANTA
**APROBARE EXPLICITA NECESARA PENTRU:**
- Modificarea `ANA_MAX/venv/` sau `ANA_MAX/archives/`.
- Stergeri distructive in afara `sandbox/`.
- Exportul public al datelor de laborator.
- Scrieri de productie.
*Redacteaza orice token, parola sau API key din output.*

## 📌 TRIGGER: "RELUAM DE UNDE AM RAMAS"
La receptionarea acestei comenzi (sau variante):
1. **ACTIVEAZA**: Supreme Engineer Enterprise Mode.
2. **EXECUTA**: Protocol Startup Obligatoriu.
3. **RAPORTEAZA**:
   - ✅/❌ Status ANA Bridge
   - ✅/❌ Status Ollama
   - 📍 Ultimul Checkpoint
   - ▶️ Next Step

## 📚 INDEX CRITIC
- `AGENTS.md`: Manualul universal.
- `docs/ANA_MEMORY.md`: Checkpoints si decizii trecute.
- `docs/ROADMAP.md`: Prioritati active.
- `docs/CHANGELOG.md`: Istoricul modificarilor.
- `docs/MCP_TOOL_ORCHESTRATION_PLAN.md`: Strategia de routing tools.

<!-- DEVIN: Citeste AGENTS.md complet → Urmeaza directivele → Raporteaza ACTION → RESULT → NEXT STEP -->
