# ANA WorkGraph - Arhitectură Completă

## 🎯 Viziune Principală

ANA WorkGraph transformă ANA MAX dintr-un agent care "execută comenzi" într-un **agent cu conștiență operațională** care:

1. **Înțelege** contextul de lucru (nu doar aplicații deschise)
2. **Învață** workflow-uri repetabile (nu doar execuție oarbă)
3. **Anticipează** erori înainte să apară (nu doar reacționează)
4. **Se recuperează autonom** când ceva merge greșit (nu se oprește)

**Principiul de bază:** nu urmărim perfecțiune sau autonomie totală. Urmărim utilitate practică: un agent care reduce timpul unui task real, vede erorile mai repede decât utilizatorul și verifică înainte să spună "gata".

**North Star:** un task de 2 ore trebuie să devină un task de 30-45 minute prin vedere structurală, verificări automate, reutilizarea pașilor și recuperare din erori comune.

---

## 🏗️ Arhitectura WorkGraph

### **Stratul 1: Structural Eyes (Ochi Structurali)**
*Ce vede ANA în timp real*

```
┌─────────────────────────────────────────────────────┐
│           WORKSPACE SITUATIONAL AWARENESS           │
├─────────────────────────────────────────────────────┤
│ • UIA Tree (ferestre Windows)                       │
│ • DOM Tree (browser Chrome)                         │
│ • File System (VS Code workspace)                   │
│ • Terminal State (comenzi, erori, output)           │
│ • Git State (modified files, branch, status)        │
│ • Error Signals (toate sursele)                     │
└────────────────────────┬────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────┐
│           CONSOLIDATED STATE JSON                   │
│                                                     │
│ {                                                   │
│   "active_app": "VS Code",                          │
│   "repo": "ANA_MAX_GitHub_Release",                 │
│   "git_status": "clean",                            │
│   "open_files": ["PLAN_VIITOR...", "PROJECT_MAP..."],│
│   "terminal_last_error": null,                      │
│   "visible_errors": [],                             │
│   "recommended_next_step": "run release checks",    │
│   "confidence": 0.86                                │
│ }                                                   │
└─────────────────────────────────────────────────────┘
```

**Implementare:** `workspace_situational_awareness.py`

**Reguli MVP:**
- Returnează JSON compact, nu dump UIA uriaș.
- Include maximum 30-50 elemente UI relevante din fereastra activă.
- Marchează explicit posibile erori: dialoguri, texte cu "error", "failed", "exception", "warning".
- Nu execută acțiuni. Doar observă și recomandă.
- Folosește API-uri native Python/Windows unde se poate; evită subprocess pentru operații simple.

---

### **Stratul 2: Task Replay & Workflow Learning**
*ANA învață din ce faci*

```
USER EXECUTES (first time):
1. cd ANA_MAX_GitHub_Release
2. python -m pytest tests/
3. Fix failing test
4. git add -A
5. git commit -m "fix: ..."
6. git push origin main
7. Verify on GitHub

↓ ANA OBSERVĂ ȘI ÎNVAȚĂ

WORKFLOW CAPTURED:
{
  "workflow_name": "release_preparation",
  "steps": [
    {"action": "navigate", "target": "repo_folder"},
    {"action": "run_tests", "expected": "all_pass"},
    {"action": "git_commit", "message_pattern": "fix|feat|docs"},
    {"action": "git_push", "remote": "origin/main"},
    {"action": "verify", "target": "github_pages"}
  ],
  "error_handlers": {
    "test_failure": "read_error → fix → rerun",
    "git_conflict": "pull → merge → push",
    "network_error": "retry_3_times"
  }
}

NEXT TIME:
User: "pregătește release-ul"
ANA: Execute workflow autonomously with error recovery
```

**Implementare:** `workflow_learner.py` + `task_replay.py`

---

### **Stratul 3: Error Radar**
*Scanează activ toate sursele de erori*

```
┌──────────────────────────────────────────────────┐
│              ERROR RADAR (continuous)            │
├──────────────────────────────────────────────────┤
│ 🔍 Terminal Output                               │
│    - Last command exit code                      │
│    - stderr pattern matching                     │
│    - Python tracebacks                           │
│                                                  │
│ 🔍 VS Code Problems Panel                        │
│    - Syntax errors                               │
│    - Linter warnings                             │
│    - Type errors                                 │
│                                                  │
│ 🔍 Browser Console                               │
│    - JavaScript errors                           │
│    - Network failures                            │
│    - CORS issues                                 │
│                                                  │
│ 🔍 Windows UI Dialogs                            │
│    - Error popups                                │
│    - Confirmation dialogs                        │
│    - Crash reports                               │
│                                                  │
│ 🔍 Log Files                                     │
│    - ANA MAX logs                                │
│    - System logs                                 │
│    - Application logs                            │
└───────────────────┬──────────────────────────────┘
                    ↓
┌──────────────────────────────────────────────────┐
│           ERROR AGGREGATION ENGINE               │
│                                                  │
│ {                                                │
│   "critical_errors": [                           │
│     {                                            │
│       "source": "terminal",                      │
│       "message": "ModuleNotFoundError: ...",     │
│       "severity": "critical",                    │
│       "suggested_fix": "pip install ...",        │
│       "confidence": 0.92                         │
│     }                                            │
│   ],                                             │
│   "warnings": [...],                             │
│   "recommendation": "Fix critical errors first"  │
│ }                                                │
└──────────────────────────────────────────────────┘
```

**Implementare:** `error_radar.py`

---

### **Stratul 4: Self QA Agent**
*ANA se verifică înainte să spună "gata"*

```
PRE-COMMIT CHECKLIST (automated):
┌──────────────────────────────────────────────────┐
│ ✓ Code Quality                                   │
│   - No syntax errors                            │
│   - No linter warnings                          │
│   - Type hints present                          │
│                                                  │
│ ✓ Tests                                          │
│   - All tests passing                           │
│   - Coverage > 80%                              │
│   - No regressions                              │
│                                                  │
│ ✓ Documentation                                  │
│   - README updated                              │
│   - CHANGELOG updated                           │
│   - Inline docs current                         │
│                                                  │
│ ✓ Security                                       │
│   - No secrets in code                          │
│   - No API keys exposed                         │
│   - .gitignore complete                         │
│                                                  │
│ ✓ Git                                            │
│   - Clean working tree                          │
│   - Branch up to date                           │
│   - Commit message follows convention           │
│                                                  │
│ ✓ Backup                                         │
│   - Release can be restored                     │
│   - Git tag created                             │
│   - GitHub Pages updated                        │
└───────────────────┬──────────────────────────────┘
                    ↓
           ALL CHECKS PASSED? 
           ├─ YES → "Ready to commit!"
           └─ NO  → "Found 3 issues: [list]"
                    + Auto-fix suggestions
```

**Implementare:** `self_qa_agent.py`

---

### **Stratul 5: Autonomous Recovery**
*Când ceva merge greșit, ANA repară singură*

```
ERROR DETECTED:
"Test failed: test_context_engine.py:42"

↓

AUTONOMOUS RECOVERY LOOP:
1. READ ERROR
   - Parse traceback
   - Identify root cause
   - Search error patterns in memory

2. DIAGNOSE
   - Is this a known error? → Check memory_cortex
   - Similar to past errors? → Apply previous fix
   - New error? → Analyze code

3. FIX
   - Small fix: Apply directly (import missing, typo)
   - Medium fix: Propose to user, wait confirmation
   - Large fix: Ask user for guidance

4. VERIFY
   - Run test again
   - If passes → Log success in memory
   - If fails → Try alternative fix

5. LEARN
   - Store error + fix in memory_cortex
   - Update error_radar patterns
   - Improve future detection

EXAMPLE:
Error: "ModuleNotFoundError: no module named 'paddleocr'"
ANA Diagnosis: "OCR tool needs paddleocr installed"
Auto-Fix: Run "pip install paddleocr paddlepaddle"
Verify: Import paddleocr → Success!
Learn: Store "paddleocr required for OCR tools" in memory
```

**Implementare:** `autonomous_recovery.py`

---

## 🚀 Plan de Implementare (Faze)

### **Principii Anti-Hype**

- Fiecare fază trebuie să producă un tool apelabil, testabil și util.
- Orice output trebuie să fie suficient de scurt ca să poată fi citit de un agent AI.
- Orice automatizare care poate schimba fișiere, da click sau rula comenzi destructive trebuie să aibă mod `dry_run` sau confirmare.
- ANA trebuie să raporteze ce știe, ce presupune și ce nu poate vedea.
- Prima versiune bună este una care ajută la debugging și verificare, nu una care promite autonomie completă.

### **FAZA 1: Structural Eyes (2-3 zile)**
**Prioritate:** 🔥 CRITICĂ

**Deliverables:**
- [ ] `workspace_situational_awareness.py` - JSON consolidat
- [ ] `foreground_snapshot.py` - UIA tree snapshot
- [ ] Integration cu `windows_uia_bridge.py`

**MVP:**
```python
def get_workspace_state():
    """Returnează starea completă a workspace-ului."""
    return {
        "active_app": get_active_window(),
        "ui_elements": get_uia_tree(),
        "open_files": get_vscode_files(),
        "git_status": get_git_state(),
        "terminal_state": get_terminal_output(),
        "errors": scan_all_errors(),
        "recommended_action": ai_decide_next_step()
    }
```

**Criterii de succes FAZA 1:**
- Pe VS Code: detectează fereastra activă, titlul, repo-ul, fișierele deschise dacă sunt vizibile și eventuale texte de eroare.
- Pe Calculator/Notepad: detectează titlul aplicației, controalele principale și textele vizibile.
- Pe repo Git: returnează branch, stare curată/murdară și fișiere modificate.
- Output-ul complet rămâne sub aproximativ 8 KB pentru a fi ușor de folosit în prompt.
- Dacă UIA nu vede destul, marchează `visibility_quality: "partial"` și recomandă fallback OCR.

---

### **FAZA 2: Error Radar (2-3 zile)**
**Prioritate:** 🔥 CRITICĂ

**Deliverables:**
- [ ] `error_radar.py` - Multi-source error scanning
- [ ] Pattern matching pentru erori comune
- [ ] Integration cu `memory_cortex` (istoric erori)

**MVP:**
```python
class ErrorRadar:
    def scan_all_sources(self):
        return {
            "terminal_errors": self.scan_terminal(),
            "vscode_errors": self.scan_vscode_problems(),
            "browser_errors": self.scan_browser_console(),
            "windows_dialogs": self.scan_ui_errors(),
            "log_errors": self.scan_log_files(),
            "aggregated": self.prioritize_errors()
        }
```

---

### **FAZA 3: Self QA Agent (3-4 zile)**
**Prioritate:** ⭐ IMPORTANTĂ

**Deliverables:**
- [ ] `self_qa_agent.py` - Pre-commit checklist
- [ ] Automated verification hooks
- [ ] Integration cu git pre-commit

**MVP:**
```python
class SelfQAAgent:
    def pre_commit_check(self):
        checks = [
            self.check_code_quality(),
            self.run_tests(),
            self.check_documentation(),
            self.scan_for_secrets(),
            self.verify_git_status(),
        ]
        return {
            "passed": all(c.passed for c in checks),
            "failed_checks": [c for c in checks if not c.passed],
            "ready_to_commit": all(c.passed for c in checks)
        }
```

---

### **FAZA 4: Workflow Learning (4-5 zile)**
**Prioritate:** ⭐ IMPORTANTĂ

**Deliverables:**
- [ ] `workflow_learner.py` - Capture workflows
- [ ] `task_replay.py` - Execute learned workflows
- [ ] Error handling în workflows

**MVP:**
```python
class WorkflowLearner:
    def observe_and_learn(self):
        """Învață din acțiunile utilizatorului."""
        workflow = {
            "name": detect_workflow_name(),
            "steps": capture_user_actions(),
            "success_criteria": detect_completion(),
            "error_patterns": observe_failures()
        }
        self.save_workflow(workflow)
    
    def execute_workflow(self, name):
        """Execută un workflow învățat."""
        workflow = self.load_workflow(name)
        for step in workflow.steps:
            try:
                self.execute_step(step)
            except Error as e:
                self.recover(step, e)
```

---

### **FAZA 5: Autonomous Recovery (5-6 zile)**
**Prioritate:** 🚀 AVANSATĂ

**Deliverables:**
- [ ] `autonomous_recovery.py` - Error recovery loop
- [ ] Integration cu `self_evolving_tool`
- [ ] Memory-based learning

**MVP:**
```python
class AutonomousRecovery:
    def handle_error(self, error, context):
        # 1. Diagnose
        diagnosis = self.diagnose(error)
        
        # 2. Check memory
        past_fix = self.memory_cortex.search_similar(error)
        
        # 3. Apply fix
        if past_fix:
            self.apply_fix(past_fix)
        else:
            fix = self.generate_fix(error, context)
            self.apply_fix(fix)
        
        # 4. Verify
        if self.verify_fix():
            self.memory_cortex.store_lesson(error, fix)
            return True
        else:
            return self.try_alternative_fix()
```

---

## 📊 Impact Estimativ

| Feature | Timp | Impact | Complexitate |
|---------|------|--------|--------------|
| Structural Eyes | 2-3 zile | ⭐⭐⭐⭐⭐ | Medie |
| Error Radar | 2-3 zile | ⭐⭐⭐⭐⭐ | Medie |
| Self QA Agent | 3-4 zile | ⭐⭐⭐⭐ | Medie |
| Workflow Learning | 4-5 zile | ⭐⭐⭐⭐⭐ | Ridicată |
| Autonomous Recovery | 5-6 zile | ⭐⭐⭐⭐⭐ | Foarte Ridicată |

**Timp Total:** 16-21 zile (3-4 săptămâni)

---

## 🎯 Rezultat Final (v0.3.0)

**ANA MAX devine:**

✅ **Agent cu conștiență operațională**
- Știe ce se întâmplă pe calculator în timp real
- Înțelege contextul, nu doar aplicațiile

✅ **Agent care învață workflow-uri**
- Observă cum lucrezi o dată
- Reproduce și adaptează automat

✅ **Agent cu auto-vindecare**
- Detectează erori înainte să le vezi tu
- Se repară singură când e posibil

✅ **Agent cu QA integrat**
- Verifică totul înainte să spună "gata"
- Zero suprize neplăcute

---

## 💡 Exemplu Practic (v0.3.0)

**User:** "Pregătește release-ul v0.3.0"

**ANA MAX face autonom:**

```
1. SEE (Conștiență)
   ├─ Workspace: ANA_MAX_GitHub_Release
   ├─ Git: 3 modified files (README, main.py, index.html)
   ├─ Errors: None detected
   └─ Last action: User committed docs update

2. PLAN (Workflow Learning)
   ├─ Load workflow: "release_preparation"
   ├─ Steps: tests → docs → commit → push → verify
   └─ Error handlers: ready

3. EXECUTE (Task Replay)
   ├─ ✓ Run tests: 25 passed
   ├─ ✓ Check docs: README updated
   ├─ ✓ Self QA: All checks passed
   ├─ ✓ Git commit: "release: v0.3.0"
   ├─ ✓ Git push: origin/main
   └─ ✓ Verify: GitHub Pages updated

4. VERIFY (Self QA)
   ├─ Code quality: ✓
   ├─ Tests: ✓
   ├─ Docs: ✓
   ├─ Security: ✓
   ├─ Git: ✓
   └─ Backup: ✓

5. REPORT
   "✅ Release v0.3.0 pregătit cu succes!
    - 25 teste trecute
    - 3 fișiere actualizate
    - Push pe GitHub făcut
    - GitHub Pages actualizat
    - Zero erori detectate"
```

**Timp:** 30 secunde (față de 15 minute manual)

---

## 🚀 Primul Pas (ACUM)

**Implementează `workspace_situational_awareness.py`:**

```python
"""
workspace_situational_awareness.py

Returnează un JSON compact cu starea completă a workspace-ului.
"""

from pywinauto import Desktop
import psutil
import json

def get_workspace_state():
    """Starea completă a workspace-ului."""
    
    # 1. Active application
    active_window = get_active_window()
    
    # 2. VS Code state
    vscode_state = get_vscode_state()
    
    # 3. Git status
    git_status = get_git_status()
    
    # 4. Terminal state
    terminal_state = get_terminal_state()
    
    # 5. Error scan
    errors = scan_all_errors()
    
    # 6. AI recommendation
    recommendation = ai_recommend_next_step(
        active_window, vscode_state, git_status, errors
    )
    
    return {
        "active_app": active_window["name"],
        "repo": vscode_state.get("repo"),
        "open_files": vscode_state.get("files", []),
        "git_status": git_status["status"],
        "modified_files": git_status.get("modified", []),
        "terminal_last_error": terminal_state.get("last_error"),
        "visible_errors": errors,
        "recommended_next_step": recommendation,
        "confidence": calculate_confidence()
    }

# Funcții helper implementate mai jos...
```

### Output MVP recomandat

```json
{
  "schema": "ana.workgraph.workspace_state.v1",
  "timestamp": "2026-05-15T06:55:00",
  "active_window": {
    "app": "Code.exe",
    "title": "ANA_MAX - Visual Studio Code",
    "visibility_quality": "good"
  },
  "workspace": {
    "repo": "ANA_MAX_GitHub_Release",
    "branch": "main",
    "git_clean": true,
    "modified_files": []
  },
  "visible_signals": {
    "errors": [],
    "warnings": [],
    "important_text": ["59 tests OK", "52 tools loaded"]
  },
  "recommended_next_step": "No blocking errors detected. Safe to continue release workflow.",
  "confidence": 0.86
}
```

---

## 🎬 Următorul Pas

**Vrei să începem implementarea FAZEI 1 (Structural Eyes)?**

Pot să te ajut să:
1. ✅ Creezi `workspace_situational_awareness.py`
2. ✅ Testezi pe VS Code + Calculator
3. ✅ Verifici output-ul JSON
4. ✅ Integrezi cu MCP

Primul pas real ar fi workspace_situational_awareness.py, nu workflow learning încă. Întâi îi dăm ochi buni, apoi memorie de workflow.
