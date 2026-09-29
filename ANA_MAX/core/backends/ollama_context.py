import os
import json
from typing import Any


def _safe_compact_json(value: Any, limit: int = 1600) -> str:
    """Compact JSON serialization with truncation."""
    text = json.dumps(value, ensure_ascii=False, default=str)
    return text[:limit] + ("..." if len(text) > limit else "")

def _desktop_listing(limit: int = 80) -> dict:
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    try:
        entries = []
        for name in sorted(os.listdir(desktop), key=str.lower)[:limit]:
            path = os.path.join(desktop, name)
            entries.append({
                "name": name,
                "type": "dir" if os.path.isdir(path) else "file",
            })
        return {"path": desktop, "count_shown": len(entries), "entries": entries}
    except Exception as exc:
        return {"path": desktop, "error": str(exc)}



def _drive_listing(limit_per_drive: int = 40) -> dict:
    drives: dict[str, Any] = {}
    if os.name == "nt":
        candidates = [f"{letter}:\\" for letter in "CDEFGHIJKLMNOPQRSTUVWXYZ"]
    else:
        candidates = ["/"]
    for drive in candidates:
        if not os.path.exists(drive):
            continue
        try:
            entries = []
            for name in sorted(os.listdir(drive), key=str.lower)[:limit_per_drive]:
                path = os.path.join(drive, name)
                entries.append({
                    "name": name,
                    "type": "dir" if os.path.isdir(path) else "file",
                })
            drives[drive] = {"count_shown": len(entries), "entries": entries}
        except Exception as exc:
            drives[drive] = {"error": str(exc)}
    return drives



def _build_copilot_vision_context(reg: Any, available: set) -> dict:
    """
    COPILOT VISION LAYER — exact cum Windows Copilot 'vede' sistemul.
    Combina:
      1. Fereastra activa (titlu + app + PID) via Win32/UIA
      2. UIA tree (butoane, input-uri, texte vizibile) via foreground_ui_snapshot
      3. Clipboard curent (text) via clipboard_manager
      4. Procese active top-10 (PID, CPU, RAM) via system_control
      5. System vitals (CPU%, RAM%, GPU) via system_control
      6. Desktop shortcuts + drives listing
      7. Erori recente din log (workspace_situational_awareness)
    Returneaza dict compact pentru injectare in context Qwen.
    """
    vision: dict[str, Any] = {}

    # ── 1. Fereastra activa — Win32 direct (rapid, fara dependente) ──────────
    try:
        import ctypes
        import psutil
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        if hwnd:
            length = user32.GetWindowTextLengthW(hwnd)
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, length + 1)
            pid = ctypes.c_ulong()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            app_name = None
            try:
                app_name = psutil.Process(pid.value).name().replace(".exe", "")
            except Exception:
                pass
            vision["active_window"] = {
                "title": buf.value or None,
                "app": app_name,
                "pid": int(pid.value),
                "hwnd": int(hwnd),
            }
    except Exception as exc:
        vision["active_window_error"] = str(exc)

    # ── 2. UIA snapshot (butoane + inputs + texte vizibile) ──────────────────
    if "foreground_ui_snapshot" in available:
        try:
            result = reg.execute("foreground_ui_snapshot", include_text=True, max_elements="12")
            if result.is_success and result.data:
                d = result.data
                vision["ui_elements"] = {
                    "buttons": d.get("buttons", [])[:8],
                    "inputs": d.get("inputs", [])[:6],
                    "visible_text": d.get("visible_text", [])[:10],
                    "detected_errors": d.get("detected_errors", [])[:4],
                    "suggested_actions": d.get("suggested_actions", [])[:3],
                }
        except Exception as exc:
            vision["ui_elements_error"] = str(exc)

    # ── 3. Clipboard curent ──────────────────────────────────────────────────
    if "clipboard_manager" in available:
        try:
            result = reg.execute("clipboard_manager", operation="read")
            if result.is_success and result.data:
                clip_text = str(result.data.get("text") or result.data or "").strip()[:300]
                if clip_text:
                    vision["clipboard"] = clip_text
        except Exception:
            pass
    else:
        # Fallback: citim clipboard direct via win32
        try:
            import ctypes
            ctypes.windll.user32.OpenClipboard(0)
            CF_UNICODETEXT = 13
            h = ctypes.windll.user32.GetClipboardData(CF_UNICODETEXT)
            if h:
                ptr = ctypes.windll.kernel32.GlobalLock(h)
                text = ctypes.wstring_at(ptr)[:300]
                ctypes.windll.kernel32.GlobalUnlock(h)
                if text.strip():
                    vision["clipboard"] = text.strip()
            ctypes.windll.user32.CloseClipboard()
        except Exception:
            pass

    # ── 4. Procese active top-10 ─────────────────────────────────────────────
    if "system_control" in available:
        try:
            result = reg.execute("system_control", operation="processes")
            if result.is_success:
                raw = str(result.data)
                lines = [l for l in raw.splitlines() if l.strip()][:12]
                vision["top_processes"] = lines
        except Exception as exc:
            vision["top_processes_error"] = str(exc)

        # ── 5. System vitals (CPU, RAM, GPU) ─────────────────────────────────
        try:
            vitals = reg.execute("system_control", operation="vitals")
            if vitals.is_success:
                vision["system_vitals"] = str(vitals.data)[:500]
        except Exception as exc:
            vision["system_vitals_error"] = str(exc)

    # ── 6. Desktop shortcuts + drives ────────────────────────────────────────
    vision["desktop"] = _desktop_listing(limit=60)
    vision["drives"] = _drive_listing(limit_per_drive=20)

    # ── 7. Erori recente log (via workspace_situational_awareness) ───────────
    if "workspace_situational_awareness" in available:
        try:
            result = reg.execute(
                "workspace_situational_awareness",
                include_uia=False,   # UIA deja capturat mai sus
                include_errors=True,
            )
            if result.is_success and isinstance(result.data, dict):
                log_signals = result.data.get("log_signals") or result.data.get("errors")
                if log_signals:
                    vision["recent_log_errors"] = str(log_signals)[:600]
        except Exception:
            pass

    # ── 8. REFLEX CORE — live Frida/system telemetry (OS-23/OS-25) ─────────
    try:
        from tools.reflex_core import reflex_engine
        from tools.reflex_dispatcher import dispatcher
        
        recent = reflex_engine.get_recent_reflexes()
        if recent:
            compact_events = []
            for evt in recent[-8:]:  # ultimele 8 evenimente
                data = evt.get('data', {})
                api = data.get('api', evt.get('type', '?'))
                details = data.get('details', data)
                compact_events.append(f"{evt.get('timestamp','?')} {api}: {details}")
            vision["live_reflexes"] = compact_events
            
        alerts = dispatcher.get_active_alerts()
        if alerts:
            vision["reflex_alerts"] = alerts
    except Exception:
        pass

    return vision



def _build_preflight_context(message: str, tool_names: list[str]) -> str:
    """
    COPILOT VISION PREFLIGHT + OS27 INTELLIGENT CONTEXT — injecteaza context complet in Qwen inainte de orice actiune.
    IMPORTANT: limitat la 400 chars pentru a nu trunchia prompt-ul de sistem GOD-MODE.
    """
    try:
        reg = _get_tool_registry()
        available = set(getattr(reg, "_tools", {}).keys()) if reg is not None else set()

        # Context minimal: doar desktop + fereastra activa (fara drive listing, fara procese — prea mare)
        context: dict = {}

        # Fereastra activa (rapid, via ctypes)
        try:
            import ctypes, psutil
            user32 = ctypes.windll.user32
            hwnd = user32.GetForegroundWindow()
            if hwnd:
                length = user32.GetWindowTextLengthW(hwnd)
                buf = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buf, length + 1)
                pid = ctypes.c_ulong()
                user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                app_name = None
                try:
                    app_name = psutil.Process(pid.value).name().replace(".exe", "")
                except Exception:
                    pass
                context["active_window"] = {"title": buf.value or None, "app": app_name}
        except Exception:
            pass

        # Desktop listing (limitat la 20 intrari)
        context["desktop"] = _desktop_listing(limit=20)

    except Exception as exc:
        context = {"preflight_error": str(exc)}

    # Limitat strict la 400 chars pentru a nu trunchia system prompt-ul
    return _safe_compact_json(context, limit=400)




