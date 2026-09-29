# Ollama Integration Analysis - Raport Complet

**Date:** 2026-09-28
**Analiza:** Integrare Ollama in ANA MAX si verificare elemente uitate/nedocumentate

---

## 🔍 CE AM GASIT

### 1. **Ollama Current Status**
- **Version:** 0.31.2
- **Models locale:**
  - qwen-ana:7b (4.7 GB) - custom model
  - qwen2.5-coder:3b (1.9 GB)
  - qwen2.5-coder:7b (4.7 GB)
- **Update disponibil:** v0.34.4 (released 23 Sep 2026)

### 2. **Launcher Principal: START_ANA_OLLAMA.bat**
**Locatie:** `C:\Users\billy\Desktop\ana-manus\launchers\START_ANA_OLLAMA.bat`

**Ce face:**
1. Auto-maintenance (curatare diacritice, organizare fisiere)
2. Verificare CUDA/GPU (GTX 1650)
3. Verificare environment (.env, venv)
4. **Pornire Ollama** cu lock manager protection (port 11434)
5. **Pornire ANA MAX Server** cu `ANA_BACKEND=ollama` (port 8766)
6. Live log monitor
7. Deschidere dashboard & chat in browser

**Shortcut:** `C:\Users\billy\Desktop\START_ANA_OLLAMA.bat - Shortcut.lnk`

### 3. **Ollama Lock Manager**
**Locatie:** `C:\Users\billy\Desktop\ana-manus\ANA_MAX\ollama_lock_manager.py`

**Functionalitati:**
- Previne pornirea multipla a Ollama local
- Protejeaza GPU impotriva supraincalzirii
- Lock file: `.ollama_session.lock`
- Comenzi: acquire, release, check, force-cleanup
- Auto-cleanup pentru procese zombie (ollama, llama-server)

### 4. **Ollama Live Logger**
**Locatie:** `C:\Users\billy\Desktop\ana-manus\ANA_MAX\tools\ollama_live_logger.py`

**Functionalitati:**
- Monitor live Ollama server logs
- Detecteaza log-uri rotate (server-*.log)
- Exclude `ollama_reasoning.log` (duplicate tokens)
- Tail la LOCALAPPDATA\Ollama\server*.log
- Tail la ANA_ROOT\ollama.log

### 5. **Ollama Backend**
**Locatie:** `C:\Users\billy\Desktop\ana-manus\ANA_MAX\core\backends\ollama_backend.py`

**Functionalitati:**
- Full backend integration pentru Ollama
- OS27 telemetry injection
- Live logs context injection
- Tool description injection
- Deterministic mode pentru queries simple
- Desktop vision context
- Drive listing context
- Copilot vision context

### 6. **Configurare Backend Connections**
**Locatie:** `C:\Users\billy\Desktop\ana-manus\ANA_MAX\config\backend_connections.json`

**Config:**
```json
{
  "ollama_to_mcp": {
    "enabled": true,
    "endpoint": "http://localhost:11434",
    "mcp_config": "config/mcp_ana_max_agent.json",
    "sync_interval": 30
  },
  "mcp_to_ollama": {
    "enabled": true,
    "fallback": true,
    "priority": 2
  }
}
```

### 7. **Settings.yaml - Ollama Config**
**Locatie:** `C:\Users\billy\Desktop\ana-manus\ANA_MAX\config\settings.yaml`

**Config:**
```yaml
ai:
  primary_backend: ollama
  fallback_backend: omniroute
  model_rotation:
    enabled: true
    prefer_free_models: true
    active_models:
      - qwen2.5-coder:7b
  ollama:
    api_url: http://127.0.0.1:11434/api/chat
    model: qwen2.5-coder:7b
```

---

## 🎯 INTEGRAREA MCP + OLLAMA

### **Arhitectura Actuala:**

```
START_ANA_OLLAMA.bat
  ↓
Pornire Ollama (lock manager)
  ↓
Pornire ANA MAX Server (ANA_BACKEND=ollama)
  ↓
MCP Server (port 8766)
  ↓
Devin/Claude/Windsurf → MCP → ANA MAX → Ollama
```

### **Backend Routing:**
1. **Primary:** Ollama (qwen2.5-coder:7b)
2. **Fallback:** Omniroute (deepseek-v4-flash-free)
3. **Reserve:** OpenRouter (qwen/qwen3-coder), Foundry (phi-4-mini)

---

## ⚠️ ELEMENTE UITATE / NEDOCUMENTATE

### 1. **Model Custom: qwen-ana:7b**
- **Ce e:** Custom model (4.7 GB)
- **Status:** Folosit? Nu e clar din config
- **Problema:** Nu e documentat ce face sau cum e diferit de qwen2.5-coder:7b
- **Recomandare:** Documentatie sau merge la qwen2.5-coder:7b

### 2. **Backend Connections Priority**
- **Current config:** default_backend = "openrouter" (in backend_connections.json)
- **Settings.yaml:** primary_backend = "ollama"
- **Conflict:** Doua config-uri diferite!
- **Problema:** Confuzie care backend e folosit realmente
- **Recomandare:** Unificare config

### 3. **Multiple MCP Ports**
- **Settings.yaml:** MCP port 8768
- **Launcher:** MCP port 8766
- **Conflict:** Porte diferite in configuri
- **Problema:** Poate cauzeaza probleme de conectare
- **Recomandare:** Unificare la un singur port

### 4. **API Key in config (SECURITY RISK)**
- **Omniroute:** API key hardcodat in settings.yaml (sk-68d41781bd175781-48f687-31b4501a)
- **Problema:** API key in plain text in repo
- **Recomandare:** Mutat in .env sau secrets manager

### 5. **Model qwen-ana:7b Usage**
- **Config:** Nu e in settings.yaml
- **Actual:** Prezent in Ollama (list)
- **Problema:** Nu e clar cand e folosit
- **Recomandare:** Documentatie sau rename la qwen2.5-coder:7b

### 6. **GPU Memory Config**
- **Settings.yaml:** GTX 1650 (4GB VRAM) - Model 7b cu offloading RAM (~4.5GB VRAM needed)
- **Problema:** 4GB VRAM vs 4.5GB needed - overflow in RAM
- **Recomandare:** Documentatie clara despre VRAM usage sau switch la 3b model

### 7. **Missing Dashboard/Chat Documentation**
- **Launcher:** Deschide http://127.0.0.1:8766/dashboard si /chat
- **Problema:** Nu e documentat ce fac aceste endpoints
- **Recomandare:** Documentatie dashboard/chat features

### 8. **Live Log Monitor Script**
- **Launcher:** Foloseste `scripts\live_log_monitor.ps1`
- **Problema:** Nu e clar daca exista sau ce face
- **Recomandare:** Verificare existenta si documentare

---

## 🚀 RECOMANDARI PRIORITARE

### **HIGH PRIORITY:**

1. **Unificare Backend Config**
   - Conflict intre backend_connections.json si settings.yaml
   - Decidere: Ollama vs OpenRouter ca primary

2. **Security Fix - API Key**
   - Mutat omniroute API key in .env
   - Never commit in repo

3. **Unificare MCP Port**
   - Decidere: 8766 vs 8768
   - Update in toate config-urile

### **MEDIUM PRIORITY:**

4. **Documentatie qwen-ana:7b**
   - Ce e custom model?
   - Merge la qwen2.5-coder:7b?

5. **GPU Memory Documentation**
   - Clar 4GB vs 4.5GB needed
   - RAM overflow documentation

6. **Dashboard/Chat Documentation**
   - Ce fac /dashboard si /chat?
   - Features si usage

### **LOW PRIORITY:**

7. **Live Log Monitor Script**
   - Verificare existenta
   - Documentatie features

8. **Update Ollama**
   - v0.31.2 → v0.34.4
   - Structured outputs pe thinking models
   - Fix "model not found" errors

---

## 📊 SUMMARY

### **Integration Status:**
- ✅ Ollama FULL integrat in ANA MAX
- ✅ Lock manager protection
- ✅ Live logger
- ✅ Multiple backends (Ollama, OpenRouter, Foundry, Omniroute)
- ✅ MCP integration
- ✅ Dashboard & chat

### **Issues Found:**
- ⚠️ Backend config conflict (2 locatii diferite)
- ⚠️ MCP port conflict (8766 vs 8768)
- ⚠️ API key in plain text (security risk)
- ⚠️ Custom model nedocumentat (qwen-ana:7b)
- ⚠️ GPU memory mismatch (4GB vs 4.5GB needed)
- ⚠️ Dashboard/chat nedocumentat

### **Recommendation:**
Fix HIGH priority issues first (config unification, security, port conflict), apoi documentatie pentru rest.

---

## 🎯 NEXT STEPS

1. **Unificare backend config** (settings.yaml vs backend_connections.json)
2. **Security fix** (mutat API key in .env)
3. **Unificare MCP port** (8766 vs 8768)
4. **Documentatie qwen-ana:7b** (merge sau nu?)
5. **GPU memory documentation** (clar VRAM usage)
6. **Update Ollama** (v0.31.2 → v0.34.4)
