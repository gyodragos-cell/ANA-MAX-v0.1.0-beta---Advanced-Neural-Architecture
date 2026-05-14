"""
ANA MAX – proactive_interrupt.py
=================================
Modulul "WOW" — ANA vorbește singură când are ceva relevant de spus.

Nu așteaptă comenzi. Monitorizează continuu:
  • Ferestrele active (window_manager)
  • Clipboardul (clipboard_manager)
  • OCR pe ecran (ocr_tool)
  • Pattern-urile din SQLite (context engine existent)

Și intervine proactiv când detectează:
  1. STUCK DETECTION    — ești pe același ecran >N minute fără progres
  2. SEQUENCE TRIGGER   — ai intrat într-o secvență cunoscută (ex: Gmail→VS Code)
  3. CLIPBOARD INTENT   — ai copiat ceva și ANA știe ce urmează de obicei
  4. REPEAT ALERT       — faci același lucru pentru a 3-a oară (poate automatizezi?)
  5. CONTEXT SHIFT      — ai schimbat brusc contextul (work→social media) — îți amintește

Instalare dependențe:
    pip install pyttsx3 win10toast schedule

Integrare în main.py:
    from tools.proactive_interrupt import ProactiveInterrupt
    pi = ProactiveInterrupt(db_path="ana_memory.db")
    pi.start()   # pornește în background thread
"""

import sqlite3
import threading
import time
import logging
from datetime import datetime, timedelta
from collections import deque
from typing import Optional
import json

logger = logging.getLogger("ANA.ProactiveInterrupt")

# ── Dependențe opționale ──────────────────────────────────────────────────────
try:
    import pyttsx3
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False
    logger.info("pyttsx3 nu e instalat — vocea e dezactivată. Rulează: pip install pyttsx3")

try:
    from win10toast import ToastNotifier
    TOAST_AVAILABLE = True
    _toaster = ToastNotifier()
except ImportError:
    TOAST_AVAILABLE = False
    logger.info("win10toast nu e instalat — notificări simple. Rulează: pip install win10toast")

# ── Constante configurabile ───────────────────────────────────────────────────
STUCK_THRESHOLD_SEC     = 180    # 3 minute pe același ecran = "blocat"
REPEAT_THRESHOLD        = 3      # același pattern de N ori = sugerează automatizare
COOLDOWN_SEC            = 30     # minim între două întreruperi (ca la tine în engine)
MONITOR_INTERVAL_SEC    = 5      # cât de des verifică
SEQUENCE_WINDOW_SEC     = 60     # fereastra de timp pentru detectarea secvențelor
MAX_HISTORY             = 50     # câte evenimente păstrăm în memorie scurtă


# ─────────────────────────────────────────────────────────────────────────────
class ProactiveInterrupt:
    """
    Nucleul modulului. Se instanțiază o dată și rulează în background.

    Parametri:
        db_path      : calea către SQLite-ul ANA MAX existent
        voice        : True/False — ANA vorbește sau doar notificări
        language     : 'ro' sau 'en' pentru mesaje
        on_interrupt : callback opțional fn(message, interrupt_type) — 
                       util dacă vrei să trimiți mesajul și la LLM
    """

    def __init__(
        self,
        db_path: str = "ana_memory.db",
        voice: bool = True,
        language: str = "ro",
        on_interrupt=None,
    ):
        self.db_path       = db_path
        self.voice         = voice and TTS_AVAILABLE
        self.language      = language
        self.on_interrupt  = on_interrupt  # callback extern opțional

        self._running      = False
        self._thread: Optional[threading.Thread] = None
        self._last_interrupt_time = 0
        self._event_history: deque = deque(maxlen=MAX_HISTORY)

        # TTS engine (singleton per instanță)
        self._tts = None
        if self.voice:
            try:
                self._tts = pyttsx3.init()
                self._tts.setProperty("rate", 160)
                # Voce românească dacă există, altfel prima disponibilă
                voices = self._tts.getProperty("voices")
                for v in voices:
                    if "ro" in v.id.lower() or "romanian" in v.name.lower():
                        self._tts.setProperty("voice", v.id)
                        break
            except Exception as e:
                logger.warning(f"TTS init failed: {e}")
                self._tts = None

        self._ensure_tables()

    # ── DB setup ──────────────────────────────────────────────────────────────
    def _ensure_tables(self):
        """Creează tabelele necesare dacă nu există (nu strică ce ai deja)."""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS pi_events (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp   TEXT NOT NULL,
                    app         TEXT,
                    window_title TEXT,
                    clipboard_hash TEXT,
                    ocr_keywords TEXT
                );

                CREATE TABLE IF NOT EXISTS pi_sequences (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    sequence    TEXT NOT NULL,
                    count       INTEGER DEFAULT 1,
                    last_seen   TEXT,
                    suggestion  TEXT
                );

                CREATE TABLE IF NOT EXISTS pi_interrupts (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp       TEXT NOT NULL,
                    interrupt_type  TEXT,
                    message         TEXT,
                    accepted        INTEGER DEFAULT NULL
                );
            """)

    # ── Start / Stop ──────────────────────────────────────────────────────────
    def start(self):
        """Pornește monitorizarea în background thread."""
        if self._running:
            logger.warning("ProactiveInterrupt rulează deja.")
            return
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        logger.info("✅ ProactiveInterrupt pornit.")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=10)
        logger.info("ProactiveInterrupt oprit.")

    # ── Bucla principală ──────────────────────────────────────────────────────
    def _monitor_loop(self):
        while self._running:
            try:
                snapshot = self._take_snapshot()
                if snapshot:
                    self._event_history.append(snapshot)
                    self._save_event(snapshot)
                    self._analyze(snapshot)
            except Exception as e:
                logger.error(f"Eroare în monitor loop: {e}")
            time.sleep(MONITOR_INTERVAL_SEC)

    # ── Snapshot curent ───────────────────────────────────────────────────────
    def _take_snapshot(self) -> Optional[dict]:
        """
        Colectează starea curentă din toolurile ANA MAX existente.
        Fallback sigur dacă un tool lipsește.
        """
        snapshot = {
            "timestamp": datetime.now().isoformat(),
            "app": None,
            "window_title": None,
            "clipboard_hash": None,
            "clipboard_text": None,
            "ocr_keywords": [],
        }

        # Window Manager
        try:
            from tools.window_manager import WindowManager
            wm = WindowManager()
            active = wm.get_active_window()
            if active:
                snapshot["app"]          = active.get("app", "unknown")
                snapshot["window_title"] = active.get("title", "")
        except Exception:
            pass  # tool indisponibil, continuăm

        # Clipboard Manager
        try:
            from tools.clipboard_manager import ClipboardManager
            cm = ClipboardManager()
            clip = cm.get_content()
            if clip:
                snapshot["clipboard_text"] = clip[:500]  # primele 500 chars
                snapshot["clipboard_hash"] = str(hash(clip[:200]))
        except Exception:
            pass

        # OCR — doar dacă avem app activ (ca să nu facem screenshot degeaba)
        try:
            if snapshot["app"]:
                from tools.ocr_tool import OCRTool
                ocr = OCRTool()
                text = ocr.capture_and_read()
                if text:
                    # Extragem cuvintele cheie simple (top 5 cuvinte lungi)
                    words = [w for w in text.split() if len(w) > 5]
                    snapshot["ocr_keywords"] = list(set(words[:20]))
        except Exception:
            pass

        return snapshot if snapshot["app"] else None

    # ── Analiză și detecție ───────────────────────────────────────────────────
    def _analyze(self, snapshot: dict):
        """Rulează toți detectorii. Primul care se declanșează câștigă (cooldown)."""

        checks = [
            self._check_stuck,
            self._check_sequence_trigger,
            self._check_clipboard_intent,
            self._check_repeat_alert,
            self._check_context_shift,
        ]

        for check in checks:
            result = check(snapshot)
            if result:
                interrupt_type, message = result
                self._fire_interrupt(interrupt_type, message)
                break  # un singur interrupt per ciclu

    # ── Detector 1: STUCK ─────────────────────────────────────────────────────
    def _check_stuck(self, snapshot: dict) -> Optional[tuple]:
        """Dacă ești pe același titlu de fereastră >STUCK_THRESHOLD_SEC secunde."""
        if len(self._event_history) < 3:
            return None

        current_title = snapshot.get("window_title", "")
        if not current_title:
            return None

        # Câte evenimente consecutive au același titlu?
        consecutive_sec = 0
        for ev in reversed(self._event_history):
            if ev.get("window_title") == current_title:
                consecutive_sec += MONITOR_INTERVAL_SEC
            else:
                break

        if consecutive_sec >= STUCK_THRESHOLD_SEC:
            app = snapshot.get("app", "aplicație")
            minutes = consecutive_sec // 60
            msg = self._msg(
                ro=f"Ești în {app} de {minutes} minute. Vrei să continui sau ai nevoie de ajutor?",
                en=f"You've been in {app} for {minutes} minutes. Need help or a nudge?"
            )
            return ("stuck", msg)
        return None

    # ── Detector 2: SEQUENCE TRIGGER ─────────────────────────────────────────
    def _check_sequence_trigger(self, snapshot: dict) -> Optional[tuple]:
        """
        Dacă ultimele 2-3 app-uri formează o secvență cunoscută din trecut,
        ANA anticipează ce urmează.
        """
        if len(self._event_history) < 2:
            return None

        # Construim secvența recentă (ultimele 3 app-uri unice)
        recent_apps = []
        for ev in reversed(self._event_history):
            app = ev.get("app")
            if app and (not recent_apps or recent_apps[-1] != app):
                recent_apps.insert(0, app)
            if len(recent_apps) >= 3:
                break

        if len(recent_apps) < 2:
            return None

        seq_key = "→".join(recent_apps)

        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT count, suggestion FROM pi_sequences WHERE sequence = ?",
                (seq_key,)
            ).fetchone()

            if row:
                count, suggestion = row
                # Actualizăm
                conn.execute(
                    "UPDATE pi_sequences SET count = count+1, last_seen = ? WHERE sequence = ?",
                    (datetime.now().isoformat(), seq_key)
                )
                if count >= 3 and suggestion:
                    msg = self._msg(
                        ro=f"Recunosc acest flux: {seq_key}. De obicei urmează: {suggestion}. Să pregătesc?",
                        en=f"I recognize this flow: {seq_key}. Usually next is: {suggestion}. Shall I prepare?"
                    )
                    return ("sequence", msg)
            else:
                # Prima dată — înregistrăm, nu întrerupem încă
                conn.execute(
                    "INSERT INTO pi_sequences (sequence, count, last_seen) VALUES (?, 1, ?)",
                    (seq_key, datetime.now().isoformat())
                )

        return None

    # ── Detector 3: CLIPBOARD INTENT ─────────────────────────────────────────
    def _check_clipboard_intent(self, snapshot: dict) -> Optional[tuple]:
        """
        Dacă clipboardul s-a schimbat și conținutul sugerează o intenție specifică.
        Ex: ai copiat un URL → vrei să-l deschizi? 
            ai copiat un număr → calculezi ceva?
            ai copiat cod → vrei să-l explice ANA?
        """
        clip = snapshot.get("clipboard_text", "")
        if not clip:
            return None

        # Verificăm dacă hash-ul s-a schimbat față de ultimul snapshot
        prev_hashes = [ev.get("clipboard_hash") for ev in list(self._event_history)[-5:]]
        current_hash = snapshot.get("clipboard_hash")
        if current_hash in prev_hashes[:-1]:
            return None  # nu s-a schimbat

        # Detectare tip conținut
        clip_stripped = clip.strip()

        if clip_stripped.startswith("http://") or clip_stripped.startswith("https://"):
            msg = self._msg(
                ro=f"Ai copiat un link. Vrei să-l deschid sau să-ți spun ce conține?",
                en=f"You copied a URL. Want me to open it or summarize it?"
            )
            return ("clipboard_url", msg)

        if len(clip_stripped) > 50 and any(kw in clip_stripped.lower() for kw in
                                            ["def ", "class ", "import ", "function", "var ", "const "]):
            msg = self._msg(
                ro="Ai copiat cod. Vrei să-l explic, optimizez sau testez?",
                en="You copied code. Want me to explain, optimize, or test it?"
            )
            return ("clipboard_code", msg)

        if clip_stripped.replace(".", "").replace(",", "").replace(" ", "").isnumeric():
            msg = self._msg(
                ro=f"Ai copiat un număr: {clip_stripped[:30]}. Calculez ceva cu el?",
                en=f"You copied a number: {clip_stripped[:30]}. Need a calculation?"
            )
            return ("clipboard_number", msg)

        if len(clip_stripped) > 200:
            msg = self._msg(
                ro="Ai copiat un text lung. Vrei un rezumat sau să-l procesez?",
                en="You copied a long text. Want a summary or to process it?"
            )
            return ("clipboard_text_long", msg)

        return None

    # ── Detector 4: REPEAT ALERT ─────────────────────────────────────────────
    def _check_repeat_alert(self, snapshot: dict) -> Optional[tuple]:
        """
        Dacă aceeași fereastră/app a apărut de REPEAT_THRESHOLD ori în ultima oră,
        sugerează automatizare.
        """
        app = snapshot.get("app")
        if not app:
            return None

        one_hour_ago = (datetime.now() - timedelta(hours=1)).isoformat()

        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                """SELECT COUNT(*) FROM pi_events 
                   WHERE app = ? AND timestamp > ?""",
                (app, one_hour_ago)
            ).fetchone()

        count = row[0] if row else 0
        # Împărțim la MONITOR_INTERVAL_SEC pentru a număra vizite, nu snapshots
        visits = count * MONITOR_INTERVAL_SEC // 60  # aproximativ minute

        if count > 0 and count % (REPEAT_THRESHOLD * (60 // MONITOR_INTERVAL_SEC)) == 0:
            msg = self._msg(
                ro=f"Deschizi {app} foarte des. Pot automatiza ceva din ce faci acolo?",
                en=f"You open {app} very frequently. Want me to automate something there?"
            )
            return ("repeat", msg)

        return None

    # ── Detector 5: CONTEXT SHIFT ─────────────────────────────────────────────
    def _check_context_shift(self, snapshot: dict) -> Optional[tuple]:
        """
        Detectează schimbări bruște de context.
        Ex: lucrai la cod → ai deschis YouTube/Facebook → îți amintește de task.
        """
        distraction_apps = {
            "youtube", "facebook", "instagram", "twitter", "tiktok",
            "reddit", "netflix", "spotify", "discord", "whatsapp"
        }
        focus_apps = {
            "visual studio", "vscode", "pycharm", "intellij", "cursor",
            "word", "excel", "notepad", "obsidian", "notion"
        }

        current_app = (snapshot.get("app") or "").lower()
        current_title = (snapshot.get("window_title") or "").lower()
        combined = current_app + " " + current_title

        is_distraction = any(d in combined for d in distraction_apps)
        if not is_distraction:
            return None

        # Verificăm dacă înainte era focus
        recent = list(self._event_history)[-10:]
        was_focused = any(
            any(f in (ev.get("app") or "").lower() for f in focus_apps)
            for ev in recent
        )

        if was_focused:
            msg = self._msg(
                ro="Ai trecut de la muncă la distracție. Task-ul tău e în așteptare — mă întorc eu la el.",
                en="You switched from work to distraction. Your task is waiting — I'll keep track of it."
            )
            return ("context_shift", msg)

        return None

    # ── Fire interrupt ────────────────────────────────────────────────────────
    def _fire_interrupt(self, interrupt_type: str, message: str):
        """Declanșează notificarea + vocea, respectând cooldown-ul."""
        now = time.time()
        if now - self._last_interrupt_time < COOLDOWN_SEC:
            return  # cooldown activ

        self._last_interrupt_time = now
        logger.info(f"[INTERRUPT:{interrupt_type}] {message}")

        # Salvează în DB
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO pi_interrupts (timestamp, interrupt_type, message) VALUES (?, ?, ?)",
                (datetime.now().isoformat(), interrupt_type, message)
            )

        # Notificare Windows
        self._notify(message, interrupt_type)

        # Voce
        if self.voice and self._tts:
            try:
                self._tts.say(message)
                self._tts.runAndWait()
            except Exception as e:
                logger.warning(f"TTS error: {e}")

        # Callback extern (ex: trimite la LLM pentru răspuns)
        if self.on_interrupt:
            try:
                self.on_interrupt(message, interrupt_type)
            except Exception as e:
                logger.warning(f"on_interrupt callback error: {e}")

    def _notify(self, message: str, title_suffix: str = ""):
        title = f"ANA MAX {'– ' + title_suffix if title_suffix else ''}"
        if TOAST_AVAILABLE:
            try:
                _toaster.show_toast(title, message, duration=8, threaded=True)
                return
            except Exception:
                pass
        # Fallback: print în consolă cu formatare vizibilă
        print(f"\n{'='*60}")
        print(f"🤖 {title}")
        print(f"   {message}")
        print(f"{'='*60}\n")

    # ── Feedback API ─────────────────────────────────────────────────────────
    def feedback(self, accepted: bool, interrupt_type: Optional[str] = None):
        """
        Înregistrează feedback pentru ultimul interrupt.
        Compatibil cu sistemul tău existent de feedback loop.

        Exemplu:
            pi.feedback(accepted=True)   # ANA a avut dreptate
            pi.feedback(accepted=False)  # nu era relevant
        """
        with sqlite3.connect(self.db_path) as conn:
            # Actualizăm cel mai recent interrupt
            row = conn.execute(
                "SELECT id FROM pi_interrupts ORDER BY id DESC LIMIT 1"
            ).fetchone()
            if row:
                conn.execute(
                    "UPDATE pi_interrupts SET accepted = ? WHERE id = ?",
                    (1 if accepted else 0, row[0])
                )

        action = "✅ acceptat" if accepted else "❌ respins"
        logger.info(f"Feedback {action} pentru ultimul interrupt.")

    # ── Sugestie secvență (API manual) ───────────────────────────────────────
    def set_sequence_suggestion(self, sequence: str, suggestion: str):
        """
        Adaugă manual o sugestie pentru o secvență.
        Ex: pi.set_sequence_suggestion("Gmail→VS Code", "deschide branch-ul de feature")
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT INTO pi_sequences (sequence, count, last_seen, suggestion)
                   VALUES (?, 1, ?, ?)
                   ON CONFLICT(sequence) DO UPDATE SET suggestion = excluded.suggestion""",
                (sequence, datetime.now().isoformat(), suggestion)
            )
        logger.info(f"Sugestie setată pentru secvența '{sequence}': {suggestion}")

    # ── Stats ─────────────────────────────────────────────────────────────────
    def get_stats(self) -> dict:
        """Returnează statistici despre întreruperile ANA."""
        with sqlite3.connect(self.db_path) as conn:
            total = conn.execute("SELECT COUNT(*) FROM pi_interrupts").fetchone()[0]
            accepted = conn.execute(
                "SELECT COUNT(*) FROM pi_interrupts WHERE accepted = 1"
            ).fetchone()[0]
            by_type = conn.execute(
                "SELECT interrupt_type, COUNT(*) FROM pi_interrupts GROUP BY interrupt_type"
            ).fetchall()

        return {
            "total_interrupts": total,
            "accepted": accepted,
            "rejected": total - accepted,
            "accuracy": round(accepted / total * 100, 1) if total else 0,
            "by_type": dict(by_type),
        }

    # ── Helper mesaje bilingv ─────────────────────────────────────────────────
    def _msg(self, ro: str, en: str) -> str:
        return ro if self.language == "ro" else en

    # ── Salvare event în DB ───────────────────────────────────────────────────
    def _save_event(self, snapshot: dict):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT INTO pi_events 
                   (timestamp, app, window_title, clipboard_hash, ocr_keywords)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    snapshot["timestamp"],
                    snapshot.get("app"),
                    snapshot.get("window_title"),
                    snapshot.get("clipboard_hash"),
                    json.dumps(snapshot.get("ocr_keywords", [])),
                )
            )


# ─────────────────────────────────────────────────────────────────────────────
# Exemplu de integrare în main.py
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    def my_callback(message: str, interrupt_type: str):
        """
        Opțional: trimite mesajul și la LLM pentru un răspuns mai inteligent.
        Poți înlocui cu apelul tău către Ollama / Claude API.
        """
        print(f"\n[CALLBACK] Tipul: {interrupt_type}")
        print(f"[CALLBACK] Mesaj ANA: {message}")
        # Exemplu: requests.post("http://localhost:11434/api/generate", ...)

    pi = ProactiveInterrupt(
        db_path="ana_memory.db",
        voice=True,       # False dacă nu ai pyttsx3
        language="ro",    # "en" pentru engleză
        on_interrupt=my_callback,
    )

    # Setează manual o secvență cu sugestie (opțional)
    pi.set_sequence_suggestion(
        sequence="Gmail→Visual Studio Code",
        suggestion="deschide fișierul la care ai lucrat ultima dată"
    )

    pi.start()
    print("ANA MAX ProactiveInterrupt rulează. Ctrl+C pentru oprire.")

    try:
        while True:
            time.sleep(60)
            print(f"Stats: {pi.get_stats()}")
    except KeyboardInterrupt:
        pi.stop()
        print("Oprit.")
