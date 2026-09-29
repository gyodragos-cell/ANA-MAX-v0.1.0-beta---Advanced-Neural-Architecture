"""
ANA MAX - context_bridge.py
============================
Memoria dintre sesiuni. Creierul care nu uita.

Problema pe care o rezolva:
  Fiecare sesiune noua, agentul porneste orb.
  Nu stie ce proiecte ai, ce aplicatii folosesti,
  unde sunt fisierele tale, ce taskuri ai lasat la jumatate.
  Rezultat: pierzi 5-10 minute la fiecare sesiune explicand contextul.

Solutia:
  La INCHIDEREA sesiunii  salveaza un snapshot complet:
    - ce aplicatii erau deschise
    - ce foldere ai accesat
    - ce taskuri au ramas incomplete
    - preferintele tale de lucru detectate automat
    - "starea de spirit" a proiectului (e in debug? in build? in review?)

  La DESCHIDEREA sesiunii  incarca contextul si injecteaza-l
  in toti agentii activi. ANA stie deja unde ai ramas.

Rezultat practic:
  "Continua unde am ramas" functioneaza cu adevarat.
  Agentul stie ca 'proiect' = C:/dev/ana-max
  Agentul stie ca preferi PowerShell, nu CMD
  Agentul stie ca taskul de ieri a ramas la pasul 3

Integrare in main.py:
    from tools.context_bridge import ContextBridge

    bridge = ContextBridge(db_path="ana_memory.db")

    # La pornire - incarca contextul sesiunii precedente:
    ctx = bridge.restore_session()
    print(ctx.summary())   # "Bun venit inapoi! Ai lasat 2 taskuri incomplete..."

    # In timpul sesiunii - actualizeaza automat:
    bridge.observe_event("file_opened", {"path": "C:/dev/ana/main.py"})
    bridge.observe_event("app_used",    {"name": "VS Code", "project": "ANA MAX"})
    bridge.observe_event("task_started",{"task": "Fix OCR bug", "step": 1})

    # La inchidere - salveaza snapshot:
    bridge.save_session()

    # Din orice tool - obtine contextul curent:
    ctx = bridge.get_current_context()
    active_project = ctx.active_project   # "ANA MAX"
    last_folder    = ctx.last_folders[0]  # "C:/dev/ana-max"
"""

import json
import logging
import os
import sqlite3
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("ANA.ContextBridge")


# -- Structuri de date ---------------------------------------------------------

@dataclass
class WorkingContext:
    """
    Contextul complet al unei sesiuni de lucru.
    Asta stie ANA despre tine si proiectul tau.
    """
    session_id: str = ""
    session_start: str = ""
    session_end: str = ""

    # Proiect activ
    active_project: str = ""          # "ANA MAX"
    project_path: str = ""            # "C:/dev/ana-max"
    project_type: str = ""            # "python", "web", "data", etc.

    # Aplicatii si foldere
    open_apps: List[str] = field(default_factory=list)       # ["VS Code", "Chrome", "Terminal"]
    recent_folders: List[str] = field(default_factory=list)  # ultimele foldere accesate
    recent_files: List[str] = field(default_factory=list)    # ultimele fisiere deschise

    # Taskuri
    incomplete_tasks: List[dict] = field(default_factory=list)  # taskuri lasate la jumatate
    completed_tasks: List[str] = field(default_factory=list)    # taskuri finalizate in sesiune
    current_task: str = ""                                       # ce facea chiar acum

    # Preferinte detectate automat
    preferred_shell: str = "powershell"   # powershell | cmd | wsl
    preferred_editor: str = ""            # VS Code | Notepad++ | etc.
    preferred_browser: str = ""           # Chrome | Firefox | Edge
    work_language: str = "ro"            # ro | en

    # Starea proiectului
    project_phase: str = ""   # "development" | "debugging" | "testing" | "review"
    last_error: str = ""      # ultima eroare vazuta
    last_error_solved: bool = False

    # Metadata
    total_sessions: int = 0
    total_tasks_done: int = 0
    last_seen: str = ""

    def summary(self) -> str:
        """Rezumat human-readable pentru injectat in prompt."""
        lines = []

        if self.active_project:
            lines.append(f"Proiect activ: {self.active_project}")
            if self.project_path:
                lines.append(f"  Path: {self.project_path}")
            if self.project_phase:
                lines.append(f"  Faza: {self.project_phase}")

        if self.incomplete_tasks:
            lines.append(f"Taskuri incomplete ({len(self.incomplete_tasks)}):")
            for t in self.incomplete_tasks[:3]:
                step_info = f" (la pasul {t.get('step', '?')})" if t.get("step") else ""
                lines.append(f"   {t.get('task', '?')}{step_info}")

        if self.current_task:
            lines.append(f"Ultima activitate: {self.current_task}")

        if self.recent_folders:
            lines.append(f"Foldere recente: {', '.join(self.recent_folders[:3])}")

        if self.preferred_editor:
            lines.append(f"Editor preferat: {self.preferred_editor}")

        if self.last_error and not self.last_error_solved:
            lines.append(f"[WARN]  Eroare nerezolvata: {self.last_error[:100]}")

        if self.last_seen:
            lines.append(f"Ultima sesiune: {self.last_seen}")

        if not lines:
            return "Sesiune noua - nu exista context anterior."

        return "CONTEXT SESIUNE ANTERIOARA:\n" + "\n".join(lines)

    def to_prompt_injection(self) -> str:
        """
        Format optimizat pentru injectat direct in system prompt-ul LLM-ului.
        Concis, fara redundanta.
        """
        parts = []

        if self.active_project:
            parts.append(f"Proiect: {self.active_project}")
            if self.project_path:
                parts.append(f"Path: {self.project_path}")

        if self.incomplete_tasks:
            task_names = [t.get("task", "?") for t in self.incomplete_tasks[:2]]
            parts.append(f"Task-uri in curs: {'; '.join(task_names)}")

        if self.preferred_shell:
            parts.append(f"Shell: {self.preferred_shell}")

        if self.preferred_editor:
            parts.append(f"Editor: {self.preferred_editor}")

        if self.recent_folders:
            parts.append(f"Folder activ: {self.recent_folders[0]}")

        if self.last_error and not self.last_error_solved:
            parts.append(f"Eroare activa: {self.last_error[:80]}")

        return " | ".join(parts) if parts else ""


# -- Context Bridge ------------------------------------------------------------

class ContextBridge:
    """
    Memoria persistenta dintre sesiuni ANA MAX.

    Salveaza si restaureaza contextul complet de lucru,
    astfel incat fiecare sesiune noua porneste de unde a ramas.
    """

    def __init__(
        self,
        db_path: str = "ana_memory.db",
        auto_observe: bool = True,     # observa automat aplicatii deschise
        max_recent_files: int = 20,
        max_recent_folders: int = 10,
        max_incomplete_tasks: int = 10,
        session_timeout_hours: int = 24,  # dupa cate ore se considera sesiune noua
    ):
        self.db_path = db_path
        self.auto_observe = auto_observe
        self.max_recent_files = max_recent_files
        self.max_recent_folders = max_recent_folders
        self.max_incomplete_tasks = max_incomplete_tasks
        self.session_timeout_hours = session_timeout_hours

        self._session_id = self._generate_session_id()
        self._session_start = datetime.now().isoformat()
        self._events: List[dict] = []        # evenimente din sesiunea curenta
        self._current_context: Optional[WorkingContext] = None

        self._init_db()
        logger.info(" ContextBridge initializat.")

    # -- DB --------------------------------------------------------------------

    def _init_db(self):
        """Creeaza tabelele necesare daca nu exista."""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS context_sessions (
                    session_id   TEXT PRIMARY KEY,
                    session_start TEXT NOT NULL,
                    session_end   TEXT,
                    context_json  TEXT NOT NULL,
                    created_at    TEXT DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS context_events (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id   TEXT NOT NULL,
                    event_type   TEXT NOT NULL,
                    event_data   TEXT,
                    timestamp    TEXT DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS context_preferences (
                    key          TEXT PRIMARY KEY,
                    value        TEXT NOT NULL,
                    confidence   REAL DEFAULT 0.5,
                    seen_count   INTEGER DEFAULT 1,
                    updated_at   TEXT DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS context_projects (
                    path         TEXT PRIMARY KEY,
                    name         TEXT NOT NULL,
                    type         TEXT,
                    last_active  TEXT,
                    total_time_sec INTEGER DEFAULT 0,
                    notes        TEXT
                );
            """)

    def _generate_session_id(self) -> str:
        return f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # -- RESTORE - la pornirea sesiunii ---------------------------------------

    def restore_session(self) -> WorkingContext:
        """
        Restaureaza contextul din sesiunea precedenta.
        Apeleaza asta la pornirea ANA MAX, inainte de orice alt tool.

        Returns:
            WorkingContext cu tot ce stia ANA ultima data.
        """
        ctx = WorkingContext(
            session_id=self._session_id,
            session_start=self._session_start,
        )

        try:
            # Gasim ultima sesiune salvata
            with sqlite3.connect(self.db_path) as conn:
                row = conn.execute("""
                    SELECT context_json, session_end
                    FROM context_sessions
                    ORDER BY created_at DESC
                    LIMIT 1
                """).fetchone()

            if not row:
                logger.info("   Prima sesiune - context gol.")
                self._current_context = ctx
                return ctx

            last_ctx_json, last_end = row

            # Verificam daca sesiunea e recenta (nu timeout)
            if last_end:
                last_end_dt = datetime.fromisoformat(last_end)
                hours_ago = (datetime.now() - last_end_dt).total_seconds() / 3600
                if hours_ago > self.session_timeout_hours:
                    logger.info(f"   Sesiune veche ({hours_ago:.0f}h) - context partial resetat.")
            else:
                hours_ago = 0

            # Deserializam contextul anterior
            saved = json.loads(last_ctx_json)

            ctx.active_project    = saved.get("active_project", "")
            ctx.project_path      = saved.get("project_path", "")
            ctx.project_type      = saved.get("project_type", "")
            ctx.project_phase     = saved.get("project_phase", "")
            ctx.recent_folders    = saved.get("recent_folders", [])
            ctx.recent_files      = saved.get("recent_files", [])
            ctx.incomplete_tasks  = saved.get("incomplete_tasks", [])
            ctx.completed_tasks   = []   # cele noi din sesiunea anterioara nu mai sunt relevante
            ctx.current_task      = saved.get("current_task", "")
            ctx.preferred_shell   = saved.get("preferred_shell", "powershell")
            ctx.preferred_editor  = saved.get("preferred_editor", "")
            ctx.preferred_browser = saved.get("preferred_browser", "")
            ctx.work_language     = saved.get("work_language", "ro")
            ctx.last_error        = saved.get("last_error", "")
            ctx.last_error_solved = saved.get("last_error_solved", False)
            ctx.total_sessions    = saved.get("total_sessions", 0) + 1
            ctx.total_tasks_done  = saved.get("total_tasks_done", 0)
            ctx.last_seen         = saved.get("session_end", "")

            logger.info(
                f"   Context restaurat: proiect='{ctx.active_project}', "
                f"{len(ctx.incomplete_tasks)} taskuri incomplete, "
                f"sesiunea #{ctx.total_sessions}"
            )

        except Exception as e:
            logger.warning(f"  [WARN] Restaurare context esuata (non-critical): {e}")

        self._current_context = ctx

        # Daca auto_observe, scanam imediat starea curenta
        if self.auto_observe:
            self._auto_observe_current_state(ctx)

        return ctx

    def _auto_observe_current_state(self, ctx: WorkingContext):
        """Scaneaza automat ce e deschis acum pe Windows."""
        try:
            import subprocess

            # Aplicatii deschise via tasklist
            result = subprocess.run(
                ["tasklist", "/fo", "csv", "/nh"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                known_apps = {
                    "code.exe":        "VS Code",
                    "notepad++.exe":   "Notepad++",
                    "notepad.exe":     "Notepad",
                    "chrome.exe":      "Chrome",
                    "firefox.exe":     "Firefox",
                    "msedge.exe":      "Edge",
                    "powershell.exe":  "PowerShell",
                    "cmd.exe":         "CMD",
                    "windowsterminal.exe": "Windows Terminal",
                    "pycharm64.exe":   "PyCharm",
                    "cursor.exe":      "Cursor",
                    "windsurf.exe":    "Windsurf",
                    "excel.exe":       "Excel",
                    "winword.exe":     "Word",
                    "python.exe":      "Python",
                    "ollama.exe":      "Ollama",
                }
                running = result.stdout.lower()
                found_apps = [
                    name for exe, name in known_apps.items()
                    if exe in running
                ]
                if found_apps:
                    ctx.open_apps = found_apps
                    logger.info(f"   Aplicatii deschise: {', '.join(found_apps)}")

                    # Detectam preferinte din ce e deschis
                    if "VS Code" in found_apps or "Cursor" in found_apps or "Windsurf" in found_apps:
                        ctx.preferred_editor = next(
                            (a for a in ["Cursor", "Windsurf", "VS Code"] if a in found_apps),
                            ctx.preferred_editor
                        )
                    if "Chrome" in found_apps:
                        ctx.preferred_browser = "Chrome"
                    elif "Firefox" in found_apps:
                        ctx.preferred_browser = "Firefox"
                    if "PowerShell" in found_apps or "Windows Terminal" in found_apps:
                        ctx.preferred_shell = "powershell"

        except Exception as e:
            logger.debug(f"Auto-observe failed (non-critical): {e}")

    # -- OBSERVE - in timpul sesiunii -----------------------------------------

    def observe_event(self, event_type: str, data: dict):
        """
        Inregistreaza un eveniment din sesiunea curenta.
        Apeleaza asta din orice tool cand se intampla ceva relevant.

        Tipuri de events:
            "file_opened"     {"path": "C:/dev/main.py"}
            "folder_accessed" {"path": "C:/dev/ana-max"}
            "app_used"        {"name": "VS Code", "project": "ANA MAX"}
            "task_started"    {"task": "Fix OCR", "step": 1, "tool": "ocr_tool"}
            "task_completed"  {"task": "Fix OCR"}
            "task_failed"     {"task": "Fix OCR", "error": "..."}
            "error_seen"      {"error": "ModuleNotFoundError: ...", "file": "main.py"}
            "error_solved"    {"error": "ModuleNotFoundError: ..."}
            "project_detected" {"path": "C:/dev/ana", "name": "ANA MAX", "type": "python"}
            "shell_used"      {"shell": "powershell", "command": "python main.py"}
        """
        event = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.now().isoformat(),
            "session_id": self._session_id,
        }
        self._events.append(event)

        # Salvam in DB imediat (nu pierdem nimic daca crapa)
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT INTO context_events (session_id, event_type, event_data) VALUES (?, ?, ?)",
                    (self._session_id, event_type, json.dumps(data))
                )
        except Exception:
            pass

        # Actualizam contextul in memorie
        if self._current_context:
            self._update_context_from_event(self._current_context, event_type, data)

    def _update_context_from_event(self, ctx: WorkingContext, event_type: str, data: dict):
        """Actualizeaza contextul in timp real pe baza evenimentelor."""

        if event_type == "file_opened":
            path = data.get("path", "")
            if path and path not in ctx.recent_files:
                ctx.recent_files.insert(0, path)
                ctx.recent_files = ctx.recent_files[:self.max_recent_files]
            # Detectam folderul
            folder = str(Path(path).parent) if path else ""
            if folder and folder not in ctx.recent_folders:
                ctx.recent_folders.insert(0, folder)
                ctx.recent_folders = ctx.recent_folders[:self.max_recent_folders]

        elif event_type == "folder_accessed":
            folder = data.get("path", "")
            if folder and folder not in ctx.recent_folders:
                ctx.recent_folders.insert(0, folder)
                ctx.recent_folders = ctx.recent_folders[:self.max_recent_folders]

        elif event_type == "app_used":
            app = data.get("name", "")
            if app and app not in ctx.open_apps:
                ctx.open_apps.insert(0, app)
            # Detectam proiect din context app
            if data.get("project") and not ctx.active_project:
                ctx.active_project = data["project"]

        elif event_type == "task_started":
            task_entry = {
                "task": data.get("task", ""),
                "step": data.get("step", 1),
                "tool": data.get("tool", ""),
                "started_at": datetime.now().isoformat(),
            }
            ctx.current_task = data.get("task", "")
            # Adaugam la incomplete daca nu e deja acolo
            existing = [t for t in ctx.incomplete_tasks if t.get("task") == task_entry["task"]]
            if not existing:
                ctx.incomplete_tasks.insert(0, task_entry)
                ctx.incomplete_tasks = ctx.incomplete_tasks[:self.max_incomplete_tasks]

        elif event_type == "task_completed":
            task_name = data.get("task", "")
            # Scoatem din incomplete
            ctx.incomplete_tasks = [
                t for t in ctx.incomplete_tasks
                if t.get("task") != task_name
            ]
            ctx.completed_tasks.append(task_name)
            ctx.total_tasks_done += 1
            if ctx.current_task == task_name:
                ctx.current_task = ""

        elif event_type == "task_failed":
            task_name = data.get("task", "")
            # Actualizam step-ul in incomplete
            for t in ctx.incomplete_tasks:
                if t.get("task") == task_name:
                    t["step"] = data.get("step", t.get("step", 1))
                    t["last_error"] = data.get("error", "")[:100]
                    break

        elif event_type == "error_seen":
            ctx.last_error = data.get("error", "")[:200]
            ctx.last_error_solved = False

        elif event_type == "error_solved":
            if ctx.last_error and data.get("error", "") in ctx.last_error:
                ctx.last_error_solved = True

        elif event_type == "project_detected":
            ctx.active_project = data.get("name", ctx.active_project)
            ctx.project_path   = data.get("path", ctx.project_path)
            ctx.project_type   = data.get("type", ctx.project_type)
            # Salvam si in tabelul de proiecte
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("""
                        INSERT INTO context_projects (path, name, type, last_active)
                        VALUES (?, ?, ?, ?)
                        ON CONFLICT(path) DO UPDATE SET
                            last_active = excluded.last_active,
                            name = excluded.name
                    """, (
                        data.get("path", ""),
                        data.get("name", ""),
                        data.get("type", ""),
                        datetime.now().isoformat(),
                    ))
            except Exception:
                pass

        elif event_type == "shell_used":
            ctx.preferred_shell = data.get("shell", ctx.preferred_shell)

        elif event_type == "project_phase":
            ctx.project_phase = data.get("phase", "")  # debugging / testing / etc.

    # -- SAVE - la inchiderea sesiunii -----------------------------------------

    def save_session(self) -> bool:
        """
        Salveaza snapshot-ul complet al sesiunii curente.
        Apeleaza asta la aterizarea ANA MAX sau la orice punct de checkpoint.

        Returns:
            True daca a salvat cu succes.
        """
        if not self._current_context:
            logger.warning("  [WARN] Nimic de salvat - contextul e gol.")
            return False

        ctx = self._current_context
        ctx.session_end = datetime.now().isoformat()

        try:
            ctx_dict = asdict(ctx)
            ctx_dict["session_end"] = ctx.session_end

            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO context_sessions (session_id, session_start, session_end, context_json)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(session_id) DO UPDATE SET
                        session_end  = excluded.session_end,
                        context_json = excluded.context_json
                """, (
                    ctx.session_id,
                    ctx.session_start,
                    ctx.session_end,
                    json.dumps(ctx_dict, ensure_ascii=False),
                ))

                # Actualizam preferintele detectate
                prefs = {
                    "preferred_shell":   ctx.preferred_shell,
                    "preferred_editor":  ctx.preferred_editor,
                    "preferred_browser": ctx.preferred_browser,
                    "work_language":     ctx.work_language,
                    "active_project":    ctx.active_project,
                    "project_path":      ctx.project_path,
                }
                for key, val in prefs.items():
                    if val:
                        conn.execute("""
                            INSERT INTO context_preferences (key, value, seen_count)
                            VALUES (?, ?, 1)
                            ON CONFLICT(key) DO UPDATE SET
                                value      = excluded.value,
                                seen_count = seen_count + 1,
                                confidence = MIN(1.0, confidence + 0.1),
                                updated_at = datetime('now')
                        """, (key, val))

            logger.info(
                f"   Sesiune salvata: {len(ctx.completed_tasks)} taskuri finalizate, "
                f"{len(ctx.incomplete_tasks)} incomplete, "
                f"proiect='{ctx.active_project}'"
            )
            return True

        except Exception as e:
            logger.error(f"  [FAIL] Salvare sesiune esuata: {e}")
            return False

    # -- GET - acces la context din orice tool --------------------------------

    def get_current_context(self) -> WorkingContext:
        """
        Returneaza contextul curent.
        Apeleaza asta din orice tool care are nevoie de context.
        """
        if not self._current_context:
            return self.restore_session()
        return self._current_context

    def get_prompt_injection(self) -> str:
        """
        Returneaza un string concis pentru injectat in prompt-ul LLM-ului.
        Foloseste asta in _plan() din orchestrator sau in orice prompt dinamic.

        Exemplu output:
            "Proiect: ANA MAX | Path: C:/dev/ana | Task in curs: Fix OCR bug | Shell: powershell"
        """
        ctx = self.get_current_context()
        return ctx.to_prompt_injection()

    def get_active_project_path(self) -> Optional[str]:
        """Shortcut: returneaza path-ul proiectului activ."""
        ctx = self.get_current_context()
        return ctx.project_path or None

    def get_incomplete_tasks(self) -> List[dict]:
        """Shortcut: returneaza taskurile incomplete."""
        ctx = self.get_current_context()
        return ctx.incomplete_tasks

    def get_preferences(self) -> dict:
        """
        Returneaza preferintele detectate cu confidence score.
        Preferintele cu confidence > 0.7 sunt de incredere.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                rows = conn.execute(
                    "SELECT key, value, confidence, seen_count FROM context_preferences"
                ).fetchall()
            return {
                row[0]: {
                    "value": row[1],
                    "confidence": row[2],
                    "seen_count": row[3],
                }
                for row in rows
            }
        except Exception:
            return {}

    # -- DETECT - detectare automata proiect ----------------------------------

    def detect_project_from_path(self, path: str) -> Optional[dict]:
        """
        Detecteaza tipul proiectului dintr-un path.
        Apeleaza asta cand deschizi un fisier sau folder.

        Returns:
            {"name": "ANA MAX", "type": "python", "path": "C:/dev/ana"}
        """
        p = Path(path)
        if p.is_file():
            p = p.parent

        # Urcam in arbore cautand markeri de proiect
        for folder in [p, *p.parents]:
            project_info = self._identify_project_type(folder)
            if project_info:
                project_info["path"] = str(folder)
                project_info["name"] = project_info.get("name") or folder.name
                self.observe_event("project_detected", project_info)
                return project_info

        return None

    def _identify_project_type(self, folder: Path) -> Optional[dict]:
        """Identifica tipul proiectului dintr-un folder."""
        markers = {
            "requirements.txt":  "python",
            "setup.py":          "python",
            "pyproject.toml":    "python",
            "package.json":      "node",
            "Cargo.toml":        "rust",
            "go.mod":            "go",
            "pom.xml":           "java",
            "*.sln":             "dotnet",
            "Makefile":          "c/cpp",
            "docker-compose.yml":"docker",
        }
        try:
            files = set(f.name for f in folder.iterdir() if f.is_file())
            for marker, ptype in markers.items():
                if marker in files:
                    # Incearca sa extraga numele proiectului
                    name = self._extract_project_name(folder, ptype)
                    return {"type": ptype, "name": name}
        except Exception:
            pass
        return None

    def _extract_project_name(self, folder: Path, ptype: str) -> str:
        """Extrage numele proiectului din fisierele de config."""
        try:
            if ptype == "python":
                req = folder / "requirements.txt"
                readme = folder / "README.md"
                if readme.exists():
                    first_line = readme.read_text(encoding="utf-8", errors="ignore").split("\n")[0]
                    name = first_line.strip("# ").strip()
                    if name:
                        return name[:50]

            if ptype == "node":
                pkg = folder / "package.json"
                if pkg.exists():
                    data = json.loads(pkg.read_text(encoding="utf-8"))
                    return data.get("name", folder.name)

        except Exception:
            pass
        return folder.name

    # -- HISTORY ---------------------------------------------------------------

    def get_session_history(self, last_n: int = 10) -> List[dict]:
        """
        Returneaza istoricul sesiunilor recente.
        Util pentru debug sau pentru a afisa un rezumat utilizatorului.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                rows = conn.execute("""
                    SELECT session_id, session_start, session_end, context_json
                    FROM context_sessions
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (last_n,)).fetchall()

            sessions = []
            for row in rows:
                try:
                    ctx_data = json.loads(row[3])
                    sessions.append({
                        "session_id":    row[0],
                        "start":         row[1],
                        "end":           row[2],
                        "project":       ctx_data.get("active_project", ""),
                        "tasks_done":    len(ctx_data.get("completed_tasks", [])),
                        "tasks_pending": len(ctx_data.get("incomplete_tasks", [])),
                    })
                except Exception:
                    pass
            return sessions
        except Exception:
            return []

    def get_known_projects(self) -> List[dict]:
        """Returneaza toate proiectele cunoscute de ANA."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                rows = conn.execute("""
                    SELECT path, name, type, last_active, total_time_sec
                    FROM context_projects
                    ORDER BY last_active DESC
                """).fetchall()
            return [
                {"path": r[0], "name": r[1], "type": r[2],
                 "last_active": r[3], "total_time_sec": r[4]}
                for r in rows
            ]
        except Exception:
            return []

    # -- RESET -----------------------------------------------------------------

    def reset_context(self, keep_preferences: bool = True):
        """
        Reseteaza contextul curent (util daca schimbi proiectul complet).
        Daca keep_preferences=True, pastreaza preferintele detectate.
        """
        prefs = {}
        if keep_preferences and self._current_context:
            prefs = {
                "preferred_shell":   self._current_context.preferred_shell,
                "preferred_editor":  self._current_context.preferred_editor,
                "preferred_browser": self._current_context.preferred_browser,
                "work_language":     self._current_context.work_language,
            }

        self._current_context = WorkingContext(
            session_id=self._session_id,
            session_start=self._session_start,
            **prefs,
        )
        logger.info("   Context resetat.")

    # -- MCP integration -------------------------------------------------------

    def register_as_mcp_tool(self, mcp_app) -> None:
        """
        Inregistreaza ContextBridge ca tool MCP.
        Apeleaza din mcp_server.py.

        Endpoints expuse:
            GET  /tools/ana_context           contextul curent
            POST /tools/ana_context/event     inregistreaza un eveniment
            POST /tools/ana_context/save      salveaza sesiunea
            GET  /tools/ana_context/projects  proiecte cunoscute
            GET  /tools/ana_context/history   istoric sesiuni
        """
        try:
            from flask import request, jsonify
        except ImportError:
            logger.error("Flask indisponibil - MCP registration esuata.")
            return

        bridge = self

        @mcp_app.route("/tools/ana_context", methods=["GET"])
        def mcp_context_get():
            ctx = bridge.get_current_context()
            return jsonify({
                "summary":         ctx.summary(),
                "prompt_injection": ctx.to_prompt_injection(),
                "active_project":  ctx.active_project,
                "project_path":    ctx.project_path,
                "project_phase":   ctx.project_phase,
                "open_apps":       ctx.open_apps,
                "recent_folders":  ctx.recent_folders[:5],
                "incomplete_tasks": ctx.incomplete_tasks[:5],
                "current_task":    ctx.current_task,
                "preferred_shell": ctx.preferred_shell,
                "preferred_editor":ctx.preferred_editor,
                "last_error":      ctx.last_error,
                "last_error_solved": ctx.last_error_solved,
                "total_sessions":  ctx.total_sessions,
                "total_tasks_done":ctx.total_tasks_done,
            })

        @mcp_app.route("/tools/ana_context/event", methods=["POST"])
        def mcp_context_event():
            data = request.get_json(force=True) or {}
            event_type = data.get("event_type", "")
            event_data = data.get("data", {})
            if not event_type:
                return jsonify({"error": "event_type obligatoriu"}), 400
            bridge.observe_event(event_type, event_data)
            return jsonify({"ok": True, "event": event_type})

        @mcp_app.route("/tools/ana_context/save", methods=["POST"])
        def mcp_context_save():
            ok = bridge.save_session()
            return jsonify({"ok": ok})

        @mcp_app.route("/tools/ana_context/projects", methods=["GET"])
        def mcp_context_projects():
            return jsonify(bridge.get_known_projects())

        @mcp_app.route("/tools/ana_context/history", methods=["GET"])
        def mcp_context_history():
            n = int(request.args.get("n", 10))
            return jsonify(bridge.get_session_history(last_n=n))

        logger.info("   ContextBridge inregistrat ca MCP tools:")
        logger.info("     GET  /tools/ana_context")
        logger.info("     POST /tools/ana_context/event")
        logger.info("     POST /tools/ana_context/save")
        logger.info("     GET  /tools/ana_context/projects")
        logger.info("     GET  /tools/ana_context/history")


# -----------------------------------------------------------------------------
# Integrare cu Orchestratorul
# -----------------------------------------------------------------------------

def inject_context_into_orchestrator(orchestrator, bridge: ContextBridge):
    """
    Conecteaza ContextBridge la AnaOrchestrator.
    Orchestratorul va injecta automat contextul in fiecare plan generat
    si va inregistra automat evenimentele din executie.

    Exemplu in main.py:
        from tools.context_bridge import ContextBridge, inject_context_into_orchestrator
        from tools.ana_orchestrator import AnaOrchestrator

        bridge = ContextBridge(db_path="ana_memory.db")
        ctx = bridge.restore_session()
        print(ctx.summary())

        orchestrator = AnaOrchestrator(db_path="ana_memory.db", ...)
        inject_context_into_orchestrator(orchestrator, bridge)

        # De-acum orchestratorul stie tot ce stie bridge-ul
        result = orchestrator.execute("Continua taskul de ieri")
    """
    original_plan = orchestrator._plan
    original_execute_plan = orchestrator._execute_plan
    original_learn = orchestrator._learn_from_execution

    def patched_plan(task, visual_context, memory_context, extra_context, max_steps):
        # Injectam contextul sesiunii in planning
        context_injection = bridge.get_prompt_injection()
        if context_injection and extra_context:
            extra_context = f"{context_injection}\n{extra_context}"
        elif context_injection:
            extra_context = context_injection

        # Inregistram ca am inceput un task
        bridge.observe_event("task_started", {"task": task, "step": 1})

        return original_plan(task, visual_context, memory_context, extra_context, max_steps)

    def patched_execute_plan(plan):
        results = original_execute_plan(plan)

        # Inregistram fisierele/folderele accesate din args
        for step in plan:
            for key, val in step.args.items():
                if isinstance(val, str):
                    if os.path.isfile(val):
                        bridge.observe_event("file_opened", {"path": val})
                    elif os.path.isdir(val):
                        bridge.observe_event("folder_accessed", {"path": val})

        return results

    def patched_learn(task, plan, result):
        original_learn(task, plan, result)

        # Inregistram finalul taskului in bridge
        if result.success:
            bridge.observe_event("task_completed", {"task": task})
        else:
            bridge.observe_event("task_failed", {
                "task": task,
                "error": "; ".join(result.errors[:2]),
            })

        # Salvam sesiunea la fiecare task finalizat (checkpoint)
        bridge.save_session()

    # Patch metodele orchestratorului
    orchestrator._plan = patched_plan
    orchestrator._execute_plan = patched_execute_plan
    orchestrator._learn_from_execution = patched_learn

    logger.info("   ContextBridge conectat la AnaOrchestrator.")


# -----------------------------------------------------------------------------
# Exemplu de utilizare
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    bridge = ContextBridge(
        db_path="ana_memory.db",
        auto_observe=True,
    )

    # La pornire - restaureaza contextul
    print("\n=== RESTAURARE SESIUNE ===")
    ctx = bridge.restore_session()
    print(ctx.summary())

    # Simulam o sesiune de lucru
    print("\n=== SESIUNE DE LUCRU ===")
    bridge.observe_event("project_detected", {
        "path": "C:/dev/ana-max",
        "name": "ANA MAX",
        "type": "python",
    })
    bridge.observe_event("app_used",    {"name": "VS Code"})
    bridge.observe_event("file_opened", {"path": "C:/dev/ana-max/tools/ocr_tool.py"})
    bridge.observe_event("task_started", {"task": "Imbunatatire OCR accuracy", "step": 1})
    bridge.observe_event("error_seen",   {"error": "PaddleOCR: model not found"})

    # Afisam contextul curent
    print("\n=== CONTEXT CURENT ===")
    print(ctx.to_prompt_injection())

    # La inchidere - salvam sesiunea
    print("\n=== SALVARE SESIUNE ===")
    bridge.save_session()

    # Afisam proiectele cunoscute
    print("\n=== PROIECTE CUNOSCUTE ===")
    for p in bridge.get_known_projects():
        print(f"   {p['name']} ({p['type']}) - {p['path']}")

    # Afisam preferintele
    print("\n=== PREFERINTE DETECTATE ===")
    for key, info in bridge.get_preferences().items():
        print(f"   {key}: {info['value']} (confidence: {info['confidence']:.1f})")
