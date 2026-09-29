# Laptop Model Recommendations - GTX 1650 4GB VRAM

**Laptop Specs:**
- **CPU:** Intel Core i7-9750H @ 2.60GHz (6 cores, 12 threads)
- **RAM:** 16GB
- **GPU:** NVIDIA GeForce GTX 1650 (4GB VRAM)
- **Integrated:** Intel UHD Graphics 630 (1GB)

**Ollama Version:** 0.34.4 (✅ Updated)
**Current Models:**
- qwen-ana:7b (4.7 GB) - ❌ Too large for 4GB VRAM
- qwen2.5-coder:3b (1.9 GB) - ✅ Perfect fit
- qwen2.5-coder:7b (4.7 GB) - ❌ Too large for 4GB VRAM

---

## 🏆 TOP MODELE RECOMANDATE (4GB VRAM)

### **#1 WINNER: qwen3.5:2b (2.7GB default, 1.9GB q4_K_M)**
**CE ESTE:** Cel mai capabil model care inca lasa 4GB VRAM utilizabil
**VRAM Usage:** 2.7GB (default) sau 1.9GB (q4_K_M quantization)
**Features:**
- ✅ Tool calling
- ✅ Thinking (reasoning)
- ✅ Image input (vision)
- ✅ 256K native context
- ✅ Best quality per VRAM
**Performance:** ~25 tokens/sec pe GTX 1650
**Recommendation:** **PULL PRIMUL ACESTA!**

**Command:**
```bash
ollama pull qwen3.5:2b-q4_K_M
```

### **#2: phi4-mini (2.5GB)**
**CE ESTE:** Cel mai puternic model text-only per gigabyte
**VRAM Usage:** 2.5GB
**Features:**
- ✅ Function calling
- ✅ Strong instruction following
- ✅ Good for coding
- ⚠️ No vision
**Performance:** ~20-25 tokens/sec
**Recommendation:** **Excellent pentru coding tasks**

**Command:**
```bash
ollama pull phi4-mini
```

### **#3: qwen3:4b (2.5GB)**
**CE ESTE:** Largest parameter count care inca incapa
**VRAM Usage:** 2.5GB
**Features:**
- ✅ Strong reasoning
- ✅ Technical help
- ✅ 256K context (theoretical, but 4GB VRAM limits to 2-4K)
**Performance:** ~15-20 tokens/sec
**Recommendation:** **Good pentru technical tasks**

**Command:**
```bash
ollama pull qwen3:4b
```

### **#4: llama3.2:3b (2.0GB)**
**CE ESTE:** Good balance pentru general chat
**VRAM Usage:** 2.0GB
**Features:**
- ✅ General chat
- ✅ Document summarization
- ✅ Simple coding
**Performance:** ~20-25 tokens/sec
**Recommendation:** **Good pentru daily use**

**Command:**
```bash
ollama pull llama3.2:3b
```

### **#5: qwen2.5-coder:3b (1.9GB) - AI AI LA TINE!**
**CE ESTE:** Coding-focused model - perfect pentru 4GB VRAM
**VRAM Usage:** 1.9GB
**Features:**
- ✅ **CODING SPECIALIST**
- ✅ Good for code generation
- ✅ Fast performance
**Performance:** ~25-30 tokens/sec
**Recommendation:** **PERFECT - already have it!**

**Status:** ✅ **Already installed!**

---

## 🎯 RECOMANDARE FINALA

### **STRATEGIE OPTIMA:**

**1. PASTREAZA:**
- ✅ **qwen2.5-coder:3b** - Perfect pentru coding tasks
- ✅ **qwen2.5-coder:7b** - Foloseste pe CPU cand nevoie de mai multa putere (16GB RAM)
- ✅ **qwen-ana:7b** - Documenteaza sau sterge daca nu e folosit

**2. PULL NOU:**
- 🆕 **qwen3.5:2b-q4_K_M** - Best general purpose cu vision
- 🆕 **phi4-mini** - Best text-only per VRAM

**3. MODELE DE EVITAT:**
- ❌ **Llama 3 8B** - Nu incap in 4GB VRAM (needs 5.5GB+)
- ❌ **Qwen 14B+** - Prea mari pentru 4GB VRAM
- ❌ **Mistral Small** - Prea mare pentru 4GB VRAM

---

## 📊 COMPARATIE VRAM USAGE

| Model | VRAM Usage | Context | Vision | Coding | Speed |
|-------|-----------|---------|--------|--------|-------|
| qwen3.5:2b-q4_K_M | 1.9GB | 256K | ✅ | ✅ | ~25 t/s |
| phi4-mini | 2.5GB | 4K | ❌ | ✅ | ~20 t/s |
| qwen3:4b | 2.5GB | 2-4K | ❌ | ✅ | ~15 t/s |
| llama3.2:3b | 2.0GB | 2-4K | ❌ | ✅ | ~20 t/s |
| qwen2.5-coder:3b | 1.9GB | 4K | ❌ | ✅ | ~25 t/s |
| qwen2.5-coder:7b | 4.7GB | 8K | ❌ | ✅ | ~10 t/s (CPU) |

---

## 🚀 IMPLEMENTARE RECOMANDATA

### **Step 1: Pull qwen3.5:2b-q4_K_M**
```bash
ollama pull qwen3.5:2b-q4_K_M
```

### **Step 2: Pull phi4-mini**
```bash
ollama pull phi4-mini
```

### **Step 3: Update ANA MAX config**
**In `config/settings.yaml`:**
```yaml
ai:
  primary_backend: ollama
  ollama:
    api_url: http://127.0.0.1:11434/api/chat
    model: qwen3.5:2b-q4_K_M  # NEW PRIMARY
  model_rotation:
    active_models:
      - qwen3.5:2b-q4_K_M
      - qwen2.5-coder:3b
      - phi4-mini
```

### **Step 4: Testare**
```bash
ollama run qwen3.5:2b-q4_K_M "Hello, write a Python function to sort a list"
```

---

## 💡 CONCLUZIE

**Laptopul tau GTX 1650 4GB VRAM este PERFECT pentru:**
- ✅ **qwen2.5-coder:3b** (already have - 1.9GB)
- ✅ **qwen3.5:2b-q4_K_M** (recommended - 1.9GB)
- ✅ **phi4-mini** (recommended - 2.5GB)

**Evita modele 7B+ pe GPU - foloseste-le pe CPU cu 16GB RAM daca nevoie.**

**Sistemul actual este EXCELENT pentru development local!** 🚀
