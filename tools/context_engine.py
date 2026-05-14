"""
ANA MAX - Context Intelligence Engine v2 (JARVIS Mode)
tools/context_engine.py

Trei piloni:
  1. MEMORIE PE TERMEN LUNG  — SQLite via memory.py, învață din sesiuni trecute
  2. COMUNICARE ACTIVĂ       — notificări Windows + TTS (pyttsx3) opțional
  3. BUCLĂ DE FEEDBACK       — DA/NU la sugestii → confidența crește/scade

Filozofie ANA MAX:
  - Win32 / psutil nativ, zero subprocess
  - Threading cu Lock
  - Logging silent (DEBUG recurent, INFO doar la pornire/oprire)
  - Toate persistențele prin memory.py (Singleton)
"""

import json
import logging
import threading
import time
from collections import Counter, deque
from datetime import datetime
from typing import Optional, Callable

logger = logging.getLogger(__name__)

# ── Configurare ───────────────────────────────────────────────────────────────
OBSERVE_INTERVAL    = 2.0    # secunde între snapshot-uri
PATTERN_MIN_COUNT   = 3      # apariții minime pentru a fi "pattern"
SESSION_MEMORY      = 300    # snapshot-uri în RAM
PREDICT_THRESHOLD   = 0.55   # confidență minimă pentru sugestie
FEEDBACK_BOOST      = 0.08   # cât crește confidența la DA
FEEDBACK_PENALTY    = 0.12   # cât scade la NU
MAX_CONFIDENCE      = 0.97
MIN_CONFIDENCE      = 0.10
NOTIFY_COOLDOWN     = 30     # secunde între notificări pentru același intent
LONG_TERM_KEEP_DAYS = 30     # zile de reținut în SQLite

# ── State intern (Singleton-like) ─────────────────────────────────────────────
_lock               = threading.Lock()
_observer_active    = False
_observer_thread: Optional[threading.Thread] = None

_session_log: deque             = deque(maxlen=SESSION_MEMORY)
_learned_patterns: dict         = {}   # key → {count, confidence, next_action, last_seen}
_last_notify: dict              = {}   # intent_key → timestamp (cooldown)
_feedback_callbacks: list[Callable] = []

# TTS engine (lazy)
_tts_engine = None
_tts_lock   = threading.Lock()


# ════════════════════════════════════════════════════════════════════════════════
# 1. HELPERS SISTEM (Win32 + psutil nativ)
# ════════════════════════════════════════════════════════════════════════════════

def _get_foreground_window() -> str:
    try:
        import ctypes, ctypes.wintypes
        u = ctypes.windll.user32
        hwnd = u.GetForegroundWindow()
        n = u.GetWindowTextLengthW(hwnd)
        if n == 0:
            return ""
        buf = ctypes.create_unicode_buffer(n + 1)
        u.GetWindowTextW(hwnd, buf, n + 1)
        return buf.value.strip()
    except Exception as e:
        logger.debug("_get_foreground_window: %s", e)
        return ""


def _get_visible_windows() -> list[str]:
    try:
        import ctypes, ctypes.wintypes
        u = ctypes.windll.user32
        titles = []

        @ctypes.WINFUNCTYPE(ctypes.c_bool,
                            ctypes.wintypes.HWND,
                            ctypes.wintypes.LPARAM)
        def cb(hwnd, _):
            if not u.IsWindowVisible(hwnd):
                return True
            n = u.GetWindowTextLengthW(hwnd)
            if n == 0:
                return True
            buf = ctypes.create_unicode_buffer(n + 1)
            u.GetWindowTextW(hwnd, buf, n + 1)
            t = buf.value.strip()
            if t:
                titles.append(t)
            return True

        u.EnumWindows(cb, 0)
        return titles
    except Exception as e:
        logger.debug("_get_visible_windows: %s", e)
        return []


def _get_clipboard_preview() -> str:
    try:
        import ctypes
        CF_UNICODETEXT = 13
        u = ctypes.windll.user32
        k = ctypes.windll.kernel32
        if not u.OpenClipboard(None):
            return ""
        h = u.GetClipboardData(CF_UNICODETEXT)
        if not h:
            u.CloseClipboard()
            return ""
        ptr  = k.GlobalLock(h)
        text = ctypes.wstring_at(ptr)[:120] if ptr else ""
        k.GlobalUnlock(h)
        u.CloseClipboard()
        return text
    except Exception:
        try:
            ctypes.windll.user32.CloseClipboard()
        except Exception:
            pass
        return ""


def _get_processes() -> list[str]:
    try:
        import psutil
        return list({p.name() for p in psutil.process_iter(['name'])
                     if p.info['name']})
    except Exception as e:
        logger.debug("_get_processes: %s", e)
        return []


def _get_perf() -> dict:
    try:
        import psutil
        return {
            "cpu":    psutil.cpu_percent(interval=None),
            "memory": psutil.virtual_memory().percent,
        }
    except Exception:
        return {"cpu": 0, "memory": 0}


def _classify_activity(fg: str, windows: list[str], procs: list[str]) -> str:
    f  = fg.lower()
    pw = " ".join(windows).lower()
    pp = " ".join(procs).lower()

    rules = [
        (["code", "visual studio", "pycharm", "cursor",
          "windsurf", "notepad++", "sublime", "vim"],          "coding"),
        (["chrome", "firefox", "edge", "brave", "opera"],       "browsing"),
        (["excel", "word", "powerpoint", "sheets",
          "libreoffice", "calc"],                               "office"),
        (["explorer", "total commander", "everything"],         "file_management"),
        (["teams", "slack", "discord", "zoom",
          "skype", "whatsapp", "telegram"],                     "communication"),
        (["vlc", "mpv", "spotify", "netflix", "youtube"],       "media"),
        (["cmd", "powershell", "windowsterminal", "wt.exe"],    "terminal"),
    ]
    for keywords, category in rules:
        if any(k in f for k in keywords):
            return category
    return "general"


# ════════════════════════════════════════════════════════════════════════════════
# 2. MEMORIE PE TERMEN LUNG (SQLite via memory.py)
# ════════════════════════════════════════════════════════════════════════════════

def _mem_store(key: str, value: dict, category: str = "context"):
    """Salvează în SQLite prin memory.py (Singleton)."""
    try:
        from core.memory import Memory
        Memory().store(key=key, value=json.dumps(value), category=category)
    except Exception as e:
        logger.debug("_mem_store skip: %s", e)


def _mem_get(key: str) -> Optional[dict]:
    """Citește din SQLite prin memory.py."""
    try:
        from core.memory import Memory
        raw = Memory().retrieve(key=key)
        return json.loads(raw) if raw else None
    except Exception as e:
        logger.debug("_mem_get skip: %s", e)
        return None


def _load_long_term_patterns():
    """Încarcă pattern-urile salvate din sesiunile anterioare."""
    global _learned_patterns
    try:
        data = _mem_get("context:patterns:v2")
        if data and isinstance(data, dict):
            _learned_patterns = data
            logger.info("ContextEngine: %d pattern-uri încărcate din memorie",
                        len(_learned_patterns))
    except Exception as e:
        logger.debug("_load_long_term_patterns: %s", e)


def _save_long_term_patterns():
    """Persistează pattern-urile curente în SQLite."""
    try:
        _mem_store("context:patterns:v2", _learned_patterns, category="patterns")
        logger.debug("pattern-uri salvate: %d", len(_learned_patterns))
    except Exception as e:
        logger.debug("_save_long_term_patterns: %s", e)


def _save_session_summary(summary: dict):
    """Salvează sumarul sesiunii cu timestamp unic."""
    key = f"context:session:{int(time.time())}"
    _mem_store(key, summary, category="session_history")


def _learn_from_log():
    """
    Analizează session_log și actualizează _learned_patterns.
    Apelat periodic din observer loop.
    """
    global _learned_patterns
    try:
        with _lock:
            log = list(_session_log)

        if len(log) < 6:
            return

        # Secvențe de 2 activități consecutive
        for i in range(len(log) - 1):
            a1  = log[i].get("activity", "")
            a2  = log[i + 1].get("activity", "")
            fg  = log[i].get("foreground", "")[:40]
            key = f"{a1}|{fg}"

            if key not in _learned_patterns:
                _learned_patterns[key] = {
                    "count":       0,
                    "confidence":  0.60,
                    "next_activity": a2,
                    "next_action": None,
                    "last_seen":   time.time(),
                }

            p = _learned_patterns[key]
            p["count"]      += 1
            p["last_seen"]   = time.time()
            p["next_activity"] = a2  # actualizăm cu ultima observație

            # Ajustăm confidența în funcție de consistență
            p["confidence"] = min(MAX_CONFIDENCE,
                                  0.55 + p["count"] * 0.04)

        # Eliminăm pattern-urile foarte vechi (>LONG_TERM_KEEP_DAYS zile)
        cutoff = time.time() - LONG_TERM_KEEP_DAYS * 86400
        _learned_patterns = {
            k: v for k, v in _learned_patterns.items()
            if v.get("last_seen", 0) > cutoff
        }

    except Exception as e:
        logger.debug("_learn_from_log: %s", e)


# ════════════════════════════════════════════════════════════════════════════════
# 3. COMUNICARE ACTIVĂ (Notificări Windows + TTS opțional)
# ════════════════════════════════════════════════════════════════════════════════

def _win_notify(title: str, message: str):
    """Trimite o notificare nativă Windows (balloon tip sau toast)."""
    try:
        # Încearcă win10toast (mai modern)
        from win10toast import ToastNotifier
        ToastNotifier().show_toast(
            title, message,
            duration=6,
            threaded=True,
            icon_path=None,
        )
        logger.debug("notify (toast): %s", message[:60])
        return
    except ImportError:
        pass

    # Fallback: ctypes MessageBeep + tray balloon via Shell_NotifyIcon
    try:
        import ctypes
        ctypes.windll.user32.MessageBeep(0)
        logger.debug("notify (beep fallback): %s", message[:60])
    except Exception as e:
        logger.debug("_win_notify error: %s", e)


def _speak(text: str):
    """TTS opțional — dacă pyttsx3 e instalat."""
    global _tts_engine
    try:
        with _tts_lock:
            if _tts_engine is None:
                import pyttsx3
                _tts_engine = pyttsx3.init()
                _tts_engine.setProperty("rate", 175)
            _tts_engine.say(text)
            _tts_engine.runAndWait()
        logger.debug("TTS: %s", text[:60])
    except Exception as e:
        logger.debug("_speak skip: %s", e)


def _notify_user(intent_key: str, title: str, message: str,
                 speak: bool = False):
    """
    Trimite notificare cu cooldown per intent_key.
    Evită spam-ul dacă același intent se repetă rapid.
    """
    now = time.time()
    last = _last_notify.get(intent_key, 0)
    if now - last < NOTIFY_COOLDOWN:
        logger.debug("notify cooldown activ pentru '%s'", intent_key)
        return

    _last_notify[intent_key] = now
    _win_notify(title, message)
    if speak:
        threading.Thread(target=_speak, args=(message,),
                         daemon=True).start()


# ════════════════════════════════════════════════════════════════════════════════
# 4. PREDICȚIE INTENȚII
# ════════════════════════════════════════════════════════════════════════════════

def _detect_intents(obs: dict) -> list[dict]:
    """Generează lista de intenții posibile din observația curentă."""
    intents  = []
    fg       = obs.get("foreground", "").lower()
    clip     = obs.get("clipboard_preview", "").lower()
    activity = obs.get("activity", "general")
    windows  = obs.get("windows", [])
    hour     = datetime.now().hour

    # ── Reguli hard-coded ────────────────────────────────────────────────────

    if clip.startswith("http"):
        intents.append({
            "intent":     "open_url",
            "confidence": 0.85,
            "title":      "ANA MAX — URL detectat",
            "suggestion": f"Deschid URL-ul din clipboard?\n{clip[:70]}",
            "action":     {"tool": "windows_uia_bridge",
                           "args": {"action": "open_url", "url": clip}},
        })

    if activity == "browsing" and 3 < len(clip) < 80 and not clip.startswith("http"):
        intents.append({
            "intent":     "web_search",
            "confidence": 0.72,
            "title":      "ANA MAX — Căutare web",
            "suggestion": f"Caut pe web: '{clip[:50]}'?",
            "action":     {"tool": "windows_uia_bridge",
                           "args": {"action": "search", "query": clip}},
        })

    if len(windows) >= 6:
        intents.append({
            "intent":     "organize_windows",
            "confidence": 0.68,
            "title":      "ANA MAX — Ferestre aglomerate",
            "suggestion": f"{len(windows)} ferestre deschise. Aranjez automat în grid?",
            "action":     {"tool": "window_manager",
                           "args": {"action": "tile", "layout": "grid"}},
        })

    if hour >= 23 or hour <= 5:
        intents.append({
            "intent":     "end_session",
            "confidence": 0.60,
            "title":      "ANA MAX — Sesiune târzie",
            "suggestion": "E târziu. Salvez sesiunea și minimizez tot?",
            "action":     {"tool": "window_manager",
                           "args": {"action": "tile", "layout": "minimize_all"}},
        })

    # ── Pattern-uri învățate ─────────────────────────────────────────────────
    pattern_key = f"{activity}|{fg[:40]}"
    if pattern_key in _learned_patterns:
        p    = _learned_patterns[pattern_key]
        conf = p.get("confidence", 0.60)
        if p["count"] >= PATTERN_MIN_COUNT and conf >= PREDICT_THRESHOLD:
            next_act = p.get("next_activity", "?")
            intents.append({
                "intent":     "learned_pattern",
                "confidence": conf,
                "title":      "ANA MAX — Pattern detectat",
                "suggestion": (f"De {p['count']} ori după '{activity}' "
                               f"ai trecut la '{next_act}'. Fac eu?"),
                "action":     p.get("next_action"),
                "pattern_key": pattern_key,
            })

    intents.sort(key=lambda x: x["confidence"], reverse=True)
    return [i for i in intents if i["confidence"] >= PREDICT_THRESHOLD]


# ════════════════════════════════════════════════════════════════════════════════
# 5. BUCLĂ DE FEEDBACK
# ════════════════════════════════════════════════════════════════════════════════

def apply_feedback(pattern_key: str, accepted: bool) -> dict:
    """
    Utilizatorul a răspuns DA sau NU la o sugestie.
    Ajustăm confidența pattern-ului corespunzător.
    """
    global _learned_patterns
    try:
        if pattern_key not in _learned_patterns:
            return {"success": False,
                    "error": f"Pattern necunoscut: '{pattern_key}'"}

        p       = _learned_patterns[pattern_key]
        old_c   = p["confidence"]

        if accepted:
            p["confidence"] = min(MAX_CONFIDENCE, old_c + FEEDBACK_BOOST)
            p["accepted"]   = p.get("accepted", 0) + 1
            msg = f"Confidență crescută: {old_c:.2f} → {p['confidence']:.2f}"
        else:
            p["confidence"] = max(MIN_CONFIDENCE, old_c - FEEDBACK_PENALTY)
            p["rejected"]   = p.get("rejected", 0) + 1
            msg = f"Confidență scăzută: {old_c:.2f} → {p['confidence']:.2f}"

        _learned_patterns[pattern_key] = p
        _save_long_term_patterns()

        logger.info("feedback '%s': accepted=%s — %s", pattern_key, accepted, msg)
        return {"success": True, "pattern_key": pattern_key,
                "accepted": accepted, "message": msg,
                "new_confidence": p["confidence"]}

    except Exception as e:
        logger.error("apply_feedback error: %s", e)
        return {"success": False, "error": str(e)}


def register_feedback_callback(cb: Callable):
    """Înregistrează un callback apelat după fiecare feedback."""
    if cb not in _feedback_callbacks:
        _feedback_callbacks.append(cb)


# ════════════════════════════════════════════════════════════════════════════════
# 6. OBSERVER LOOP
# ════════════════════════════════════════════════════════════════════════════════

def _observer_loop():
    global _observer_active
    _load_long_term_patterns()
    logger.info("ContextEngine v2: observare pornită (JARVIS mode)")

    tick = 0
    while _observer_active:
        try:
            fg       = _get_foreground_window()
            windows  = _get_visible_windows()
            procs    = _get_processes()
            clip     = _get_clipboard_preview()
            perf     = _get_perf()
            activity = _classify_activity(fg, windows, procs)

            obs = {
                "timestamp":         time.time(),
                "foreground":        fg,
                "windows":           windows,
                "window_count":      len(windows),
                "clipboard_preview": clip,
                "activity":          activity,
                "cpu":               perf["cpu"],
                "memory":            perf["memory"],
                "hour":              datetime.now().hour,
            }

            with _lock:
                _session_log.appendleft(obs)

            tick += 1

            # La fiecare ~20 sec: imprimă intențiile și notifică
            if tick % 10 == 0:
                intents = _detect_intents(obs)
                for intent in intents[:1]:   # doar cea mai sigură
                    _notify_user(
                        intent_key=intent["intent"],
                        title=intent["title"],
                        message=intent["suggestion"],
                        speak=False,         # pune True dacă ai pyttsx3
                    )

            # La fiecare ~60 sec: învață și salvează
            if tick % 30 == 0:
                _learn_from_log()
                _save_long_term_patterns()

            # La fiecare ~10 min: salvează sumarul sesiunii
            if tick % 300 == 0:
                _save_session_summary(_build_summary())

            logger.debug("observe tick=%d activity=%s fg='%s' wins=%d",
                         tick, activity, fg[:40], len(windows))

        except Exception as e:
            logger.debug("_observer_loop error: %s", e)

        time.sleep(OBSERVE_INTERVAL)

    # La oprire: salvăm tot
    _learn_from_log()
    _save_long_term_patterns()
    _save_session_summary(_build_summary())
    logger.info("ContextEngine v2: oprit, date salvate")


# ════════════════════════════════════════════════════════════════════════════════
# 7. API PUBLIC
# ════════════════════════════════════════════════════════════════════════════════

def start_observing() -> dict:
    global _observer_thread, _observer_active
    if _observer_active:
        return {"success": True, "message": "Deja activ."}
    _observer_active = True
    _observer_thread = threading.Thread(
        target=_observer_loop, daemon=True, name="ContextObserver"
    )
    _observer_thread.start()
    return {"success": True, "message": "JARVIS mode pornit."}


def stop_observing() -> dict:
    global _observer_active
    _observer_active = False
    return {"success": True, "message": "Observare oprită."}


def get_current_context() -> dict:
    try:
        fg       = _get_foreground_window()
        windows  = _get_visible_windows()
        procs    = _get_processes()
        activity = _classify_activity(fg, windows, procs)
        perf     = _get_perf()

        with _lock:
            log = list(_session_log)

        dominant = Counter(o.get("activity") for o in log).most_common(3)

        return {
            "success": True,
            "current": {
                "foreground":   fg,
                "activity":     activity,
                "window_count": len(windows),
                "cpu":          perf["cpu"],
                "memory":       perf["memory"],
                "hour":         datetime.now().hour,
            },
            "session": {
                "observations":       len(log),
                "dominant_activities": [{"activity": a, "count": c}
                                         for a, c in dominant],
                "patterns_learned":   len(_learned_patterns),
                "observer_active":    _observer_active,
            },
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def predict_intent() -> dict:
    try:
        fg       = _get_foreground_window()
        windows  = _get_visible_windows()
        procs    = _get_processes()
        clip     = _get_clipboard_preview()
        activity = _classify_activity(fg, windows, procs)

        obs = {
            "foreground":        fg,
            "windows":           windows,
            "clipboard_preview": clip,
            "activity":          activity,
            "timestamp":         time.time(),
        }
        intents = _detect_intents(obs)
        return {
            "success":     True,
            "context":     {"activity": activity, "foreground": fg},
            "predictions": intents,
            "count":       len(intents),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def _build_summary() -> dict:
    with _lock:
        log = list(_session_log)
    if not log:
        return {}
    activities  = [o.get("activity", "general") for o in log]
    act_counter = Counter(activities)
    duration_s  = (log[0]["timestamp"] - log[-1]["timestamp"]) if len(log) > 1 else 0
    avg_cpu     = sum(o.get("cpu", 0) for o in log) / len(log)
    avg_mem     = sum(o.get("memory", 0) for o in log) / len(log)
    return {
        "duration_minutes":    round(duration_s / 60, 1),
        "observations":        len(log),
        "top_activities":      [{"activity": a, "count": c}
                                 for a, c in act_counter.most_common(5)],
        "avg_cpu":             round(avg_cpu, 1),
        "avg_memory":          round(avg_mem, 1),
        "patterns_total":      len(_learned_patterns),
        "top_patterns":        sorted(
            [{"key": k, "count": v["count"],
              "confidence": round(v["confidence"], 2)}
             for k, v in _learned_patterns.items()],
            key=lambda x: x["count"], reverse=True
        )[:5],
    }


def get_session_summary() -> dict:
    summary = _build_summary()
    if not summary:
        return {"success": True, "message": "Sesiune nouă, nicio observație încă."}
    return {"success": True, "summary": summary}


def record_action(action_name: str, context: Optional[dict] = None) -> dict:
    """
    Alte tool-uri apelează asta după ce execută o acțiune.
    Îmbunătățește predicțiile viitoare.
    """
    try:
        entry = {
            "action":    action_name,
            "context":   context or {},
            "timestamp": time.time(),
        }
        _mem_store(f"action:{int(time.time())}", entry, category="action_log")
        logger.debug("record_action: %s", action_name)
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ════════════════════════════════════════════════════════════════════════════════
# 8. MCP ENTRY POINT
# ════════════════════════════════════════════════════════════════════════════════

def run(args: dict) -> dict:
    """
    Entry point MCP.

    action:
      'start'    — pornește observer
      'stop'     — oprește observer
      'context'  — context curent
      'predict'  — predicție intenții
      'summary'  — sumar sesiune
      'feedback' — DA/NU la o sugestie (pattern_key + accepted: bool)
      'record'   — înregistrează o acțiune (action_name)
    """
    action = args.get("action", "context")

    if action == "start":
        return start_observing()
    elif action == "stop":
        return stop_observing()
    elif action == "context":
        return get_current_context()
    elif action == "predict":
        return predict_intent()
    elif action == "summary":
        return get_session_summary()
    elif action == "feedback":
        key      = args.get("pattern_key", "")
        accepted = bool(args.get("accepted", False))
        return apply_feedback(key, accepted)
    elif action == "record":
        return record_action(args.get("action_name", "unknown"),
                             args.get("context"))
    else:
        return {"success": False, "error": f"Acțiune necunoscută: '{action}'"}
