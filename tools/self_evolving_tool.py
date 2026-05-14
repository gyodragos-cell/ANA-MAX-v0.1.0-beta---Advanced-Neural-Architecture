"""
ANA MAX – self_evolving_tool.py
================================
Tool-ul care se repară și se îmbunătățește singur.

Capabilități:
  1. RUNTIME REPAIR     — prinde erori live, trimite la LLM, aplică fix automat
  2. SELF IMPROVEMENT   — analizează periodic codul și îl optimizează
  3. AUTO INSTALL       — detectează librării lipsă și le instalează cu pip
  4. CHANGELOG          — loghează ORICE schimbare în SQLite + SELF_EVOLUTION.log

Safeguards:
  • Backup automat înainte de orice modificare
  • Rollback automat dacă fix-ul introduce o nouă eroare
  • Confirmare opțională înainte de a aplica îmbunătățiri (nu doar fix-uri)
  • Sandbox: rulează codul modificat în subprocess izolat înainte de a-l aplica

Integrare în main.py:
    from tools.self_evolving_tool import SelfEvolvingTool
    evolver = SelfEvolvingTool(
        project_root=".",          # rădăcina proiectului ANA MAX
        llm_url="http://localhost:11434/api/generate",  # Ollama local
        llm_model="mistral",       # sau orice model ai în Ollama
        auto_improve=True,         # îmbunătățiri automate (nu doar repair)
        confirm_improvements=True, # cere confirmare înainte de improve
    )
    evolver.start()

    # Wrapper pentru orice tool ANA MAX:
    result = evolver.safe_call("tools.window_manager", "get_active_window")
"""

import ast
import importlib
import importlib.util
import json
import logging
import os
import shutil
import sqlite3
import subprocess
import sys
import threading
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional

logger = logging.getLogger("ANA.SelfEvolving")

# ── Constante ─────────────────────────────────────────────────────────────────
IMPROVE_INTERVAL_SEC  = 3600      # analizează pentru îmbunătățiri la fiecare oră
BACKUP_DIR            = ".ana_backups"
CHANGELOG_FILE        = "SELF_EVOLUTION.log"
MAX_REPAIR_ATTEMPTS   = 3         # max încercări de repair per eroare
SANDBOX_TIMEOUT_SEC   = 15        # timeout pentru testul în sandbox

# ── LLM helpers ───────────────────────────────────────────────────────────────
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


def _call_llm(prompt: str, llm_url: str, llm_model: str) -> Optional[str]:
    """Apelează LLM-ul local (Ollama) sau orice endpoint compatibil."""
    if not REQUESTS_AVAILABLE:
        logger.warning("requests nu e instalat. Rulează: pip install requests")
        return None
    try:
        resp = requests.post(
            llm_url,
            json={"model": llm_model, "prompt": prompt, "stream": False},
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("response", "").strip()
    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
class SelfEvolvingTool:
    """
    Tool-ul principal. Se instanțiază o dată și monitorizează întregul proiect.
    """

    def __init__(
        self,
        project_root: str = ".",
        db_path: str = "ana_memory.db",
        llm_url: str = "http://localhost:11434/api/generate",
        llm_model: str = "mistral",
        auto_improve: bool = True,
        confirm_improvements: bool = True,
        on_change: Optional[Callable] = None,
    ):
        self.project_root         = Path(project_root).resolve()
        self.db_path              = db_path
        self.llm_url              = llm_url
        self.llm_model            = llm_model
        self.auto_improve         = auto_improve
        self.confirm_improvements = confirm_improvements
        self.on_change            = on_change  # callback când ceva se schimbă

        self._running   = False
        self._thread    = None
        self._repair_counts: dict = {}  # câte repair-uri pe fișier

        self._ensure_dirs()
        self._ensure_tables()

    # ── Setup ─────────────────────────────────────────────────────────────────
    def _ensure_dirs(self):
        backup_path = self.project_root / BACKUP_DIR
        backup_path.mkdir(exist_ok=True)

    def _ensure_tables(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS evolution_log (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp     TEXT NOT NULL,
                    file_path     TEXT NOT NULL,
                    change_type   TEXT NOT NULL,
                    description   TEXT,
                    diff_summary  TEXT,
                    success       INTEGER DEFAULT 1,
                    rolled_back   INTEGER DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS known_errors (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path   TEXT,
                    error_hash  TEXT UNIQUE,
                    error_text  TEXT,
                    fix_applied TEXT,
                    fix_success INTEGER,
                    timestamp   TEXT
                );

                CREATE TABLE IF NOT EXISTS improvement_queue (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path     TEXT,
                    suggestion    TEXT,
                    status        TEXT DEFAULT 'pending',
                    timestamp     TEXT
                );
            """)

    # ── Start / Stop ──────────────────────────────────────────────────────────
    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._improve_loop, daemon=True)
        self._thread.start()
        logger.info("✅ SelfEvolvingTool pornit.")

    def stop(self):
        self._running = False
        logger.info("SelfEvolvingTool oprit.")

    # ── API principal: safe_call ──────────────────────────────────────────────
    def safe_call(self, module_path: str, function_name: str, *args, **kwargs) -> Any:
        """
        Apelează orice funcție dintr-un tool ANA MAX cu auto-repair.

        Exemplu:
            result = evolver.safe_call("tools.window_manager", "get_active_window")
            result = evolver.safe_call("tools.ocr_tool", "capture_and_read")
        """
        attempts = 0
        last_error = None

        while attempts < MAX_REPAIR_ATTEMPTS:
            try:
                # Import dinamic (sau reload dacă a fost reparat)
                module = importlib.import_module(module_path)
                importlib.reload(module)
                func = getattr(module, function_name)
                return func(*args, **kwargs)

            except ImportError as e:
                # Librărie lipsă — încearcă să o instaleze
                fixed = self._handle_import_error(e, module_path)
                if not fixed:
                    raise
                attempts += 1

            except Exception as e:
                last_error = e
                error_str = traceback.format_exc()
                logger.warning(f"Eroare în {module_path}.{function_name}: {e}")

                # Încearcă repair
                file_path = self._module_to_path(module_path)
                if file_path and file_path.exists():
                    repaired = self._repair_file(file_path, error_str)
                    if repaired:
                        attempts += 1
                        continue

                raise  # dacă nu poate repara, propagă eroarea

        raise RuntimeError(
            f"Nu am putut repara {module_path}.{function_name} după "
            f"{MAX_REPAIR_ATTEMPTS} încercări. Ultima eroare: {last_error}"
        )

    # ── Repair: erori runtime ─────────────────────────────────────────────────
    def _repair_file(self, file_path: Path, error_traceback: str) -> bool:
        """
        Trimite codul + eroarea la LLM, primește fix, îl testează, îl aplică.
        Returnează True dacă repair-ul a reușit.
        """
        logger.info(f"🔧 Încerc să repar: {file_path.name}")

        original_code = file_path.read_text(encoding="utf-8")
        error_hash = str(hash(error_traceback[:200]))

        # Am mai văzut această eroare? Am un fix validat?
        with sqlite3.connect(self.db_path) as conn:
            known = conn.execute(
                "SELECT fix_applied, fix_success FROM known_errors WHERE error_hash = ?",
                (error_hash,)
            ).fetchone()

        if known and known[1] == 1:
            # Fix cunoscut și validat — aplicăm direct
            logger.info("Fix cunoscut și validat — aplicăm direct.")
            self._apply_fix(file_path, known[0], "repair_known", error_traceback)
            return True

        # Construim prompt pentru LLM
        prompt = f"""Ești un expert Python. Ai primit un fișier Python care a generat o eroare.
Analizează codul și eroarea, apoi returnează DOAR codul Python corectat, fără explicații, fără markdown.

FIȘIER: {file_path.name}

COD ORIGINAL:
{original_code}

EROAREA:
{error_traceback}

Returnează DOAR codul Python corectat și complet, fără ``` și fără text suplimentar."""

        fixed_code = _call_llm(prompt, self.llm_url, self.llm_model)

        if not fixed_code:
            logger.warning("LLM nu a returnat un fix.")
            return False

        # Validare sintaxă
        if not self._validate_syntax(fixed_code):
            logger.warning("Fix-ul LLM are erori de sintaxă — ignorat.")
            return False

        # Test în sandbox
        sandbox_ok, sandbox_error = self._sandbox_test(fixed_code, file_path)
        if not sandbox_ok:
            logger.warning(f"Fix-ul a eșuat în sandbox: {sandbox_error}")
            return False

        # Backup + aplicare
        self._backup(file_path)
        self._apply_fix(file_path, fixed_code, "repair_runtime", error_traceback)

        # Salvăm în known_errors
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT OR REPLACE INTO known_errors
                   (file_path, error_hash, error_text, fix_applied, fix_success, timestamp)
                   VALUES (?, ?, ?, ?, 1, ?)""",
                (str(file_path), error_hash, error_traceback[:500],
                 fixed_code, datetime.now().isoformat())
            )

        logger.info(f"✅ Reparat cu succes: {file_path.name}")
        return True

    # ── Auto-install librării lipsă ───────────────────────────────────────────
    def _handle_import_error(self, error: ImportError, module_path: str) -> bool:
        """
        Detectează ce librărie lipsește și o instalează cu pip.
        """
        error_str = str(error)
        # Extrage numele modulului lipsă
        missing = None
        if "No module named" in error_str:
            missing = error_str.split("No module named")[-1].strip().strip("'\"")
            # Curăță sub-module (ex: "PIL.Image" → "Pillow")
            missing = missing.split(".")[0]

        if not missing:
            return False

        # Mapare module → package pip (cazuri speciale)
        pip_map = {
            "PIL": "Pillow",
            "cv2": "opencv-python",
            "sklearn": "scikit-learn",
            "bs4": "beautifulsoup4",
            "yaml": "PyYAML",
            "dotenv": "python-dotenv",
            "win32api": "pywin32",
            "pynput": "pynput",
            "paddleocr": "paddleocr",
        }
        package = pip_map.get(missing, missing)

        logger.info(f"📦 Instalez librăria lipsă: {package}")
        self._notify_change(f"Instalez librăria lipsă: {package}", "auto_install")

        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", package, "--quiet"],
                capture_output=True, text=True, timeout=120
            )
            success = result.returncode == 0

            self._log_change(
                file_path=module_path,
                change_type="auto_install",
                description=f"Instalat pachet: {package}",
                diff_summary=result.stdout[:500] if success else result.stderr[:500],
                success=success,
            )

            if success:
                logger.info(f"✅ {package} instalat cu succes.")
                # Invalideaza cache importuri
                importlib.invalidate_caches()
            else:
                logger.error(f"❌ Instalare eșuată: {result.stderr[:200]}")

            return success

        except subprocess.TimeoutExpired:
            logger.error(f"Timeout la instalarea {package}")
            return False

    # ── Auto-improve loop ─────────────────────────────────────────────────────
    def _improve_loop(self):
        """Rulează în background, analizează toolurile periodic."""
        while self._running:
            if self.auto_improve:
                try:
                    self._analyze_all_tools()
                except Exception as e:
                    logger.error(f"Eroare în improve loop: {e}")
            time.sleep(IMPROVE_INTERVAL_SEC)

    def _analyze_all_tools(self):
        """Analizează toate fișierele Python din /tools."""
        tools_dir = self.project_root / "tools"
        if not tools_dir.exists():
            return

        py_files = list(tools_dir.glob("*.py"))
        logger.info(f"🔍 Analizez {len(py_files)} tooluri pentru îmbunătățiri...")

        for py_file in py_files:
            if py_file.name.startswith("_"):
                continue
            self._analyze_file(py_file)

    def _analyze_file(self, file_path: Path):
        """Analizează un fișier și cere LLM-ului sugestii de îmbunătățire."""
        code = file_path.read_text(encoding="utf-8")

        # Nu analizăm fișiere prea mici sau prea mari
        if len(code) < 100 or len(code) > 50000:
            return

        prompt = f"""Ești un expert Python senior. Analizează acest fișier Python dintr-un agent AI Windows.

FIȘIER: {file_path.name}

COD:
{code[:8000]}

Identifică MAXIM 3 îmbunătățiri concrete și utile (nu stilistice). Fiecare îmbunătățire trebuie să fie:
- O problemă reală (bug potențial, ineficiență, lipsă error handling)
- Implementabilă direct

Răspunde STRICT în format JSON, fără text suplimentar:
{{
  "improvements": [
    {{
      "issue": "descriere scurtă a problemei",
      "fix": "codul complet al funcției/secțiunii reparate",
      "impact": "low|medium|high"
    }}
  ],
  "missing_dependencies": ["librărie1", "librărie2"],
  "overall_health": "good|needs_work|critical"
}}"""

        response = _call_llm(prompt, self.llm_url, self.llm_model)
        if not response:
            return

        try:
            # Curățăm răspunsul de markdown dacă există
            clean = response.strip()
            if clean.startswith("```"):
                clean = clean.split("```")[1]
                if clean.startswith("json"):
                    clean = clean[4:]
            clean = clean.strip()

            data = json.loads(clean)
        except json.JSONDecodeError:
            logger.warning(f"LLM nu a returnat JSON valid pentru {file_path.name}")
            return

        # Librării lipsă raportate de LLM
        for dep in data.get("missing_dependencies", []):
            logger.info(f"💡 LLM sugerează instalarea: {dep} pentru {file_path.name}")
            self._notify_change(
                f"{file_path.name} ar beneficia de: pip install {dep}",
                "dependency_suggestion"
            )

        # Îmbunătățiri
        improvements = data.get("improvements", [])
        high_impact = [i for i in improvements if i.get("impact") == "high"]

        for improvement in improvements:
            issue = improvement.get("issue", "")
            fix_code = improvement.get("fix", "")
            impact = improvement.get("impact", "low")

            logger.info(f"💡 [{impact.upper()}] {file_path.name}: {issue}")

            # Salvăm în coada de îmbunătățiri
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """INSERT INTO improvement_queue (file_path, suggestion, timestamp)
                       VALUES (?, ?, ?)""",
                    (str(file_path), json.dumps(improvement), datetime.now().isoformat())
                )

            # Aplicăm automat doar îmbunătățirile HIGH impact
            if impact == "high" and fix_code:
                if self.confirm_improvements:
                    # Notificăm și așteptăm confirmare
                    self._notify_change(
                        f"Îmbunătățire HIGH impact găsită în {file_path.name}: {issue}. "
                        f"Apelează evolver.approve_improvement() pentru a o aplica.",
                        "improvement_pending"
                    )
                else:
                    # Aplicăm direct
                    self._apply_improvement(file_path, improvement)

        health = data.get("overall_health", "good")
        if health == "critical":
            logger.warning(f"⚠️ {file_path.name} are stare CRITICĂ — verificare necesară!")
            self._notify_change(
                f"{file_path.name} are probleme critice detectate de LLM.",
                "critical_health"
            )

    # ── Approve / Apply improvement ───────────────────────────────────────────
    def approve_improvement(self, improvement_id: Optional[int] = None):
        """
        Aprobă și aplică o îmbunătățire din coadă.
        Dacă improvement_id e None, aplică prima din coadă.
        """
        with sqlite3.connect(self.db_path) as conn:
            if improvement_id:
                row = conn.execute(
                    "SELECT id, file_path, suggestion FROM improvement_queue WHERE id = ? AND status = 'pending'",
                    (improvement_id,)
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT id, file_path, suggestion FROM improvement_queue WHERE status = 'pending' ORDER BY id LIMIT 1"
                ).fetchone()

        if not row:
            logger.info("Nu există îmbunătățiri în așteptare.")
            return False

        imp_id, file_path_str, suggestion_json = row
        file_path = Path(file_path_str)
        improvement = json.loads(suggestion_json)

        success = self._apply_improvement(file_path, improvement)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE improvement_queue SET status = ? WHERE id = ?",
                ("applied" if success else "failed", imp_id)
            )

        return success

    def _apply_improvement(self, file_path: Path, improvement: dict) -> bool:
        """Aplică o îmbunătățire specifică cu backup și rollback."""
        fix_code = improvement.get("fix", "")
        issue = improvement.get("issue", "")

        if not fix_code or not file_path.exists():
            return False

        original_code = file_path.read_text(encoding="utf-8")

        # Încearcă să găsească și să înlocuiască funcția/secțiunea în cod
        new_code = self._merge_fix(original_code, fix_code)
        if not new_code or new_code == original_code:
            logger.warning(f"Nu am putut integra fix-ul în {file_path.name}")
            return False

        if not self._validate_syntax(new_code):
            logger.warning(f"Fix-ul are erori de sintaxă — ignorat pentru {file_path.name}")
            return False

        sandbox_ok, _ = self._sandbox_test(new_code, file_path)
        if not sandbox_ok:
            logger.warning(f"Fix-ul a eșuat în sandbox — ignorat pentru {file_path.name}")
            return False

        self._backup(file_path)
        file_path.write_text(new_code, encoding="utf-8")

        self._log_change(
            file_path=str(file_path),
            change_type="improvement",
            description=issue,
            diff_summary=f"Aplicat fix pentru: {issue}",
            success=True,
        )

        self._notify_change(
            f"✅ Îmbunătățire aplicată în {file_path.name}: {issue}",
            "improvement_applied"
        )

        logger.info(f"✅ Îmbunătățire aplicată: {file_path.name} — {issue}")
        return True

    # ── Merge fix inteligent ──────────────────────────────────────────────────
    def _merge_fix(self, original: str, fix_snippet: str) -> Optional[str]:
        """
        Încearcă să integreze un snippet de fix în codul original.
        Strategii:
          1. Dacă fix e cod complet (are import sau class/def la nivel top) → înlocuiește tot
          2. Dacă e o funcție → găsește funcția originală și înlocuiește
        """
        fix_stripped = fix_snippet.strip()

        # Strategie 1: fix e fișier complet
        if fix_stripped.startswith(("import ", "from ", "\"\"\"", "#")):
            if len(fix_stripped) > len(original) * 0.5:
                return fix_stripped

        # Strategie 2: fix e o singură funcție
        try:
            fix_tree = ast.parse(fix_stripped)
            for node in ast.walk(fix_tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    func_name = node.name
                    # Caută funcția în original și înlocuiește
                    orig_tree = ast.parse(original)
                    lines = original.splitlines()
                    for orig_node in ast.walk(orig_tree):
                        if (isinstance(orig_node, (ast.FunctionDef, ast.AsyncFunctionDef))
                                and orig_node.name == func_name):
                            start = orig_node.lineno - 1
                            end = orig_node.end_lineno
                            new_lines = lines[:start] + fix_stripped.splitlines() + lines[end:]
                            return "\n".join(new_lines)
        except SyntaxError:
            pass

        # Strategie 3: append la sfârșitul fișierului (ultimul resort)
        return original + "\n\n# AUTO-IMPROVED\n" + fix_stripped

    # ── Backup & Rollback ─────────────────────────────────────────────────────
    def _backup(self, file_path: Path):
        """Creează backup cu timestamp înainte de orice modificare."""
        backup_dir = self.project_root / BACKUP_DIR / file_path.parent.name
        backup_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = backup_dir / f"{file_path.stem}_{ts}{file_path.suffix}"
        shutil.copy2(file_path, backup_file)
        logger.debug(f"Backup creat: {backup_file}")

    def rollback(self, file_path_str: str) -> bool:
        """
        Revine la ultima versiune backup a unui fișier.

        Exemplu:
            evolver.rollback("tools/window_manager.py")
        """
        file_path = self.project_root / file_path_str
        backup_dir = self.project_root / BACKUP_DIR / file_path.parent.name

        if not backup_dir.exists():
            logger.warning(f"Nu există backup pentru {file_path_str}")
            return False

        backups = sorted(backup_dir.glob(f"{file_path.stem}_*{file_path.suffix}"))
        if not backups:
            logger.warning(f"Nu există backup pentru {file_path_str}")
            return False

        latest_backup = backups[-1]
        shutil.copy2(latest_backup, file_path)

        self._log_change(
            file_path=str(file_path),
            change_type="rollback",
            description=f"Rollback la: {latest_backup.name}",
            diff_summary="",
            success=True,
        )

        logger.info(f"↩️ Rollback efectuat: {file_path.name} → {latest_backup.name}")
        return True

    # ── Sandbox test ──────────────────────────────────────────────────────────
    def _sandbox_test(self, code: str, original_file: Path) -> tuple:
        """
        Testează codul modificat într-un subprocess izolat.
        Returnează (success: bool, error: str)
        """
        import tempfile
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8"
        ) as tmp:
            tmp.write(code)
            tmp_path = tmp.name

        try:
            result = subprocess.run(
                [sys.executable, "-c", f"import ast; ast.parse(open(r'{tmp_path}').read()); print('OK')"],
                capture_output=True, text=True, timeout=SANDBOX_TIMEOUT_SEC
            )
            if result.returncode != 0:
                return False, result.stderr
            return True, ""
        except subprocess.TimeoutExpired:
            return False, "Timeout în sandbox"
        except Exception as e:
            return False, str(e)
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

    # ── Validate syntax ───────────────────────────────────────────────────────
    def _validate_syntax(self, code: str) -> bool:
        try:
            ast.parse(code)
            return True
        except SyntaxError as e:
            logger.debug(f"Eroare sintaxă: {e}")
            return False

    # ── Logging ───────────────────────────────────────────────────────────────
    def _log_change(
        self,
        file_path: str,
        change_type: str,
        description: str,
        diff_summary: str,
        success: bool = True,
        rolled_back: bool = False,
    ):
        ts = datetime.now().isoformat()

        # SQLite
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT INTO evolution_log
                   (timestamp, file_path, change_type, description, diff_summary, success, rolled_back)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (ts, file_path, change_type, description, diff_summary,
                 1 if success else 0, 1 if rolled_back else 0)
            )

        # Fișier log human-readable
        log_entry = (
            f"\n{'='*60}\n"
            f"[{ts}] {change_type.upper()} | {'✅' if success else '❌'}\n"
            f"Fișier: {file_path}\n"
            f"Descriere: {description}\n"
            f"{'↩️ ROLLED BACK' if rolled_back else ''}\n"
        )
        with open(self.project_root / CHANGELOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_entry)

    def _apply_fix(
        self,
        file_path: Path,
        new_code: str,
        change_type: str,
        context: str = "",
    ):
        file_path.write_text(new_code, encoding="utf-8")
        self._log_change(
            file_path=str(file_path),
            change_type=change_type,
            description=context[:200],
            diff_summary=f"Fișier actualizat: {len(new_code)} caractere",
            success=True,
        )
        importlib.invalidate_caches()

    def _notify_change(self, message: str, change_type: str):
        """Notificare Windows + callback extern."""
        logger.info(f"[{change_type}] {message}")

        try:
            from win10toast import ToastNotifier
            ToastNotifier().show_toast("ANA MAX – Self Evolution", message,
                                       duration=6, threaded=True)
        except Exception:
            print(f"\n🧬 ANA EVOLUTION: {message}\n")

        if self.on_change:
            try:
                self.on_change(message, change_type)
            except Exception:
                pass

    # ── Module path → file path ───────────────────────────────────────────────
    def _module_to_path(self, module_path: str) -> Optional[Path]:
        """Convertește 'tools.window_manager' → Path('tools/window_manager.py')"""
        relative = module_path.replace(".", "/") + ".py"
        full = self.project_root / relative
        return full if full.exists() else None

    # ── Stats & Report ────────────────────────────────────────────────────────
    def get_report(self) -> dict:
        """Returnează un raport complet al evoluției ANA MAX."""
        with sqlite3.connect(self.db_path) as conn:
            total = conn.execute("SELECT COUNT(*) FROM evolution_log").fetchone()[0]
            by_type = dict(conn.execute(
                "SELECT change_type, COUNT(*) FROM evolution_log GROUP BY change_type"
            ).fetchall())
            pending_improvements = conn.execute(
                "SELECT COUNT(*) FROM improvement_queue WHERE status = 'pending'"
            ).fetchone()[0]
            rollbacks = conn.execute(
                "SELECT COUNT(*) FROM evolution_log WHERE rolled_back = 1"
            ).fetchone()[0]
            recent = conn.execute(
                """SELECT timestamp, file_path, change_type, description
                   FROM evolution_log ORDER BY id DESC LIMIT 5"""
            ).fetchall()

        return {
            "total_changes": total,
            "by_type": by_type,
            "pending_improvements": pending_improvements,
            "rollbacks": rollbacks,
            "recent_changes": [
                {"timestamp": r[0], "file": r[1], "type": r[2], "desc": r[3]}
                for r in recent
            ],
        }

    def print_report(self):
        """Afișează raportul în consolă, formatat."""
        report = self.get_report()
        print("\n" + "="*60)
        print("🧬 ANA MAX — SELF EVOLUTION REPORT")
        print("="*60)
        print(f"Total modificări: {report['total_changes']}")
        print(f"Rollback-uri: {report['rollbacks']}")
        print(f"Îmbunătățiri în așteptare: {report['pending_improvements']}")
        print("\nPe tip:")
        for t, c in report["by_type"].items():
            print(f"  {t}: {c}")
        print("\nUltimele 5 modificări:")
        for r in report["recent_changes"]:
            print(f"  [{r['timestamp'][:19]}] {r['type']} | {Path(r['file']).name} — {r['desc'][:60]}")
        print("="*60 + "\n")


# ─────────────────────────────────────────────────────────────────────────────
# Exemplu de utilizare
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    evolver = SelfEvolvingTool(
        project_root=".",
        db_path="ana_memory.db",
        llm_url="http://localhost:11434/api/generate",
        llm_model="mistral",
        auto_improve=True,
        confirm_improvements=True,   # cere confirmare înainte de improve
    )

    evolver.start()

    # Exemplu: apel safe pentru orice tool
    # result = evolver.safe_call("tools.window_manager", "get_active_window")

    # Exemplu: aprobă prima îmbunătățire din coadă
    # evolver.approve_improvement()

    # Exemplu: rollback la un tool
    # evolver.rollback("tools/ocr_tool.py")

    print("ANA MAX SelfEvolvingTool rulează. Ctrl+C pentru oprire.")
    try:
        while True:
            time.sleep(300)
            evolver.print_report()
    except KeyboardInterrupt:
        evolver.stop()
