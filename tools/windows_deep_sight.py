"""
ANA MAX - Windows Deep Sight Tool v2 (God View)
================================================
Monitorizare profunda Windows: API calls, procese, fisiere, registrii, mouse, tastatura.
Foloseste Win32 API (ctypes), WMI, Frida pentru instrumentare dinamica.
"""

import os, sys, time, json, struct, logging, threading, queue, subprocess, re, sqlite3
from typing import Optional, List, Dict, Any
import ctypes
from ctypes import wintypes, Structure, POINTER, byref, create_unicode_buffer, windll
from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus

logger = logging.getLogger(__name__)

# --- Win32 API constants ---
PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010
TH32CS_SNAPPROCESS = 0x00000002
TH32CS_SNAPTHREAD = 0x00000004

# Winternl constants for process tree
PROCESS_BASIC_INFORMATION = 0

# (structurile nu sunt folosite - pastram process tree prin WMI)

class WindowsDeepSightTool(Tool):
    """God View: vede fiecare click, proces, fisier, API call pe Windows."""

    def __init__(self):
        self._event_queue = queue.Queue()
        self._monitor_threads = []
        self._stop_event = threading.Event()
        self._frida_session = None
        self._last_mouse_pos = None
        self._last_click_state = [False, False, False]  # left, right, middle
        self._last_key_state = {}
        self._frida_available = self._check_frida()
        # !!! _frida_admin si _frida_interceptor sunt setate in _check_frida() - nu le suprascrie aici !

        # Self-filter: nu inregistra evenimente proprii
        self._self_pid = os.getpid()
        self._skip_pids = {self._self_pid}

        # Dedup for window focus
        self._last_focus_hwnd = None
        self._last_focus_time = 0

        # Rate limiting for process events
        self._process_event_times = []

        # SSE subscribers: set de queue.Queue pentru streaming live
        self._subscribers = set()

        # Win32 API functions
        self._setup_win32_api()

        # SQLite persistence for events
        self._init_db()
        self._load_recent_events()

    def _init_db(self):
        """Initializeaza baza SQLite pentru persistarea evenimentelor."""
        db_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
        os.makedirs(db_dir, exist_ok=True)
        self._db_path = os.path.join(db_dir, "events.db")
        self._event_buffer = []
        self._db_lock = threading.Lock()
        try:
            conn = sqlite3.connect(self._db_path, timeout=5)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts REAL NOT NULL,
                    type TEXT NOT NULL,
                    payload TEXT NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_type ON events(type)")
            conn.commit()
            conn.close()
            # Background flusher
            t = threading.Thread(target=self._flush_events_loop, daemon=True)
            t.start()
        except Exception as e:
            logger.warning(f"SQLite init error (events not persisted): {e}")
            self._db_path = None

    def _flush_events_loop(self):
        """Flushes event buffer to SQLite every 5 seconds."""
        while not self._stop_event.is_set():
            time.sleep(5)
            self._flush_buffer()

    def _flush_buffer(self):
        if not self._db_path or not self._event_buffer:
            return
        with self._db_lock:
            batch = self._event_buffer[:]
            self._event_buffer = []
        if not batch:
            return
        try:
            conn = sqlite3.connect(self._db_path, timeout=5)
            conn.executemany(
                "INSERT INTO events (ts, type, payload) VALUES (?, ?, ?)",
                [(e.get("_ts", time.time()), e.get("type", "unknown"),
                  json.dumps(e, default=str)) for e in batch]
            )
            # Rotate: keep max 10000 newest
            conn.execute("DELETE FROM events WHERE id NOT IN (SELECT id FROM events ORDER BY id DESC LIMIT 10000)")
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning(f"SQLite flush error: {e}")

    def _load_recent_events(self):
        """Incarca ultimele 50 de evenimente din SQLite in coada."""
        if not self._db_path:
            return
        try:
            conn = sqlite3.connect(self._db_path, timeout=5)
            rows = conn.execute(
                "SELECT payload FROM events ORDER BY id DESC LIMIT 50"
            ).fetchall()
            conn.close()
            for (payload_str,) in reversed(rows):
                try:
                    ev = json.loads(payload_str)
                    self._event_queue.put(ev)
                except json.JSONDecodeError:
                    pass
            if rows:
                logger.info(f"Incarcate {len(rows)} evenimente din istoric")
        except Exception as e:
            logger.warning(f"SQLite load error: {e}")

    def _check_frida(self):
        try:
            import frida
            self._frida_available = True
            self._frida_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
            # Test if Interceptor.attach actually works on this Windows build
            self._frida_interceptor = False
            try:
                # Attach to our own process briefly to test Interceptor
                sess = frida.attach(os.getpid())
                js = """
                'use strict';
                var addr = Module.findExportByName('ntdll.dll', 'RtlAllocateHeap');
                if (addr) {
                    try {
                        Interceptor.attach(addr, {onEnter: function(a){}});
                        Interceptor.detachAll();
                        send({ok: true});
                    } catch(e) {
                        send({ok: false, error: e.toString()});
                    }
                } else {
                    send({ok: false, error: 'export not found'});
                }
                """
                script = sess.create_script(js)
                msgs = []
                def on_m(m, d):
                    if m.get("type") == "send": msgs.append(m["payload"])
                script.on("message", on_m)
                script.load()
                import time as _t
                _t.sleep(0.3)
                sess.detach()
                if msgs and msgs[0].get("ok"):
                    self._frida_interceptor = True
            except Exception:
                pass
            return True
        except ImportError:
            self._frida_admin = False
            self._frida_interceptor = False
            return False

    def _setup_win32_api(self):
        """Incarca functii Win32 API prin ctypes."""
        self.kernel32 = windll.kernel32
        self.user32 = windll.user32

        # Process enumeration
        self.CreateToolhelp32Snapshot = self.kernel32.CreateToolhelp32Snapshot
        self.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
        self.CreateToolhelp32Snapshot.restype = wintypes.HANDLE

        self.Process32FirstW = self.kernel32.Process32FirstW
        # self.Process32FirstW.argtypes = [wintypes.HANDLE, wintypes.POINTER]

    def get_definition(self):
        return ToolDefinition(
            name="windows_deep_sight",
            description="God View Windows: monitorizeaza click-uri, procese, API calls, fisiere, registrii in timp real.",
            parameters=[
                ToolParameter(name="operation", description="Operatia de executat", type="string", required=True,
                    choices=["start_god_view", "stop_god_view", "get_events", "process_tree",
                             "system_snapshot", "trace_process", "hook_process", "list_hooks",
                             "get_clicks", "get_processes", "window_tree", "frida_status",
                             "start_etw_monitor", "stop_etw_monitor", "etw_status"]),
                ToolParameter(name="target", description="Proces tinta (nume sau PID)", type="string", required=False),
                ToolParameter(name="script", description="Script JavaScript pentru Frida hook", type="string", required=False),
                ToolParameter(name="hook_functions", description="Functii de hook-at", type="string", required=False),
                ToolParameter(name="path", description="Calea de monitorizat fisiere", type="string", required=False),
                ToolParameter(name="duration", description="Durata monitorizarii (secunde)", type="integer", required=False),
            ],
            category="system_intelligence"
        )

    def execute(self, operation, target=None, script=None, hook_functions=None, path=None, duration=None, **kwargs):
        try:
            # Throttle windows_deep_sight
            now = time.time()
            if not hasattr(self, '_last_run_timestamps'):
                self._last_run_timestamps = {}
            interval = 300 # 5 minutes
            
            # Skip throttling for operations that are explicit user actions like stop or trace
            throttle_ops = ["start_god_view", "get_events", "start_etw_monitor"]
            if operation in throttle_ops:
                last_run = self._last_run_timestamps.get(operation, 0)
                if now - last_run < interval:
                    return ToolResult(status=ToolStatus.SUCCESS, message=f"Throttled: {operation} already executed recently.")
                self._last_run_timestamps[operation] = now
            if operation == "start_god_view": return self._start_god_view(path or os.getcwd())
            if operation == "stop_god_view": return self._stop_god_view()
            if operation == "get_events": return self._get_events()
            if operation == "process_tree": return self._process_tree(target)
            if operation == "system_snapshot": return self._system_snapshot()
            if operation == "trace_process": return self._trace_process(target)
            if operation == "hook_process": return self._hook_process(target, script, hook_functions)
            if operation == "list_hooks": return self._list_hooks()
            if operation == "get_clicks": return self._get_clicks()
            if operation == "get_processes": return self._get_processes()
            if operation == "window_tree": return self._window_tree()
            if operation == "frida_status": return self._frida_status()
            if operation == "start_etw_monitor": return self._start_etw_monitor()
            if operation == "stop_etw_monitor": return self._stop_etw_monitor()
            if operation == "etw_status": return self._etw_status()
            return ToolResult(status=ToolStatus.ERROR, error=f"Operatie necunoscuta: {operation}")
        except Exception as e:
            logger.error(f"DeepSight error: {e}")
            return ToolResult(status=ToolStatus.ERROR, error=str(e))

    # ============ GOD VIEW ENGINE ============

    def _start_god_view(self, path):
        if self._stop_event.is_set():
            self._stop_event = threading.Event()

        # Thread 1: Mouse tracker (Win32 API)
        t1 = threading.Thread(target=self._mouse_tracker_loop, daemon=True)
        t1.start()
        self._monitor_threads.append(t1)

        # Thread 2: File watcher (PowerShell)
        t2 = threading.Thread(target=self._file_watcher_loop, args=(path,), daemon=True)
        t2.start()
        self._monitor_threads.append(t2)

        # Thread 3: Process watcher (WMI)
        t3 = threading.Thread(target=self._process_watcher_loop, daemon=True)
        t3.start()
        self._monitor_threads.append(t3)

        # Thread 4: Window focus tracker
        t4 = threading.Thread(target=self._window_focus_loop, daemon=True)
        t4.start()
        self._monitor_threads.append(t4)

        return ToolResult(status=ToolStatus.SUCCESS,
            message=f"God View activat: mouse, fisiere, procese, ferestre. Monitorizam {path}")

    def _stop_god_view(self):
        self._stop_event.set()
        for t in self._monitor_threads:
            if t.is_alive(): t.join(timeout=2)
        self._monitor_threads = []
        self._event_queue.queue.clear()
        if self._frida_session:
            try: self._frida_session.detach()
            except Exception: pass
            self._frida_session = None
        return ToolResult(status=ToolStatus.SUCCESS, message="God View dezactivat.")

    def subscribe_events(self):
        """Creeaza un subscriber queue pentru SSE streaming."""
        q = queue.Queue(maxsize=2000)
        self._subscribers.add(q)
        return q

    def unsubscribe_events(self, q):
        """Elimina un subscriber."""
        self._subscribers.discard(q)

    def _push_event(self, event):
        """Adauga eveniment in coada, notifica subscriberii, persista in SQLite."""
        now = time.time()
        event["_ts"] = now
        self._event_queue.put(event)

        # Buffer for SQLite flush
        if hasattr(self, '_db_lock'):
            with self._db_lock:
                if hasattr(self, '_event_buffer'):
                    self._event_buffer.append(event)

        dead = []
        for q in self._subscribers:
            try:
                q.put_nowait(event)
            except queue.Full:
                dead.append(q)
        for q in dead:
            self._subscribers.discard(q)
        # Rate limiter cleanup
        self._process_event_times = [t for t in self._process_event_times if now - (t if isinstance(t, (int, float)) else t.get("time", 0)) < 1.0]

    def _rate_limited(self, event_type):
        """Verifica daca am depasit limita de evenimente/secunda."""
        now = time.time()
        self._process_event_times = [t for t in self._process_event_times if now - (t if isinstance(t, (int, float)) else t.get("time", 0)) < 1.0]
        # Per type limit: max 20 events/sec per type
        type_count = sum(1 for t in self._process_event_times if t.get("type") == event_type)
        if type_count > 20:
            return True
        self._process_event_times.append({"time": now, "type": event_type})
        return False

    def _get_events(self):
        events = []
        while not self._event_queue.empty():
            try:
                events.append(self._event_queue.get_nowait())
            except queue.Empty:
                break
        return ToolResult(status=ToolStatus.SUCCESS,
            data={"events": events, "count": len(events)},
            message=f"{len(events)} evenimente noi")

    # ============ MOUSE TRACKER (Win32 API) ============

    def _mouse_tracker_loop(self):
        """Tracking mouse pozitie si click-uri via GetCursorPos + GetAsyncKeyState."""
        user32 = windll.user32
        while not self._stop_event.is_set():
            try:
                # Get cursor position
                point = wintypes.POINT()
                user32.GetCursorPos(byref(point))
                current_pos = (point.x, point.y)

                if current_pos != self._last_mouse_pos:
                    self._last_mouse_pos = current_pos

                # Detect clicks via GetAsyncKeyState
                click_states = [
                    ("left", 0x01),
                    ("right", 0x02),
                    ("middle", 0x04),
                ]
                for i, (name, vk) in enumerate(click_states):
                    state = user32.GetAsyncKeyState(vk) & 0x8000 != 0
                    if state and not self._last_click_state[i]:
                        self._push_event({
                            "type": "click",
                            "button": name,
                            "x": point.x,
                            "y": point.y,
                            "time": time.strftime("%H:%M:%S"),
                            "target_window": self._get_window_at(point.x, point.y)
                        })
                    self._last_click_state[i] = state

                time.sleep(0.05)
            except Exception:
                time.sleep(0.1)

    def _get_window_at(self, x, y):
        """Returneaza titlul ferestrei sub cursor."""
        user32 = windll.user32
        hwnd = user32.WindowFromPoint(wintypes.POINT(x, y))
        if hwnd:
            length = user32.GetWindowTextLengthW(hwnd) + 1
            buffer = create_unicode_buffer(length)
            user32.GetWindowTextW(hwnd, buffer, length)
            return buffer.value
        return "unknown"

    # ============ FILE WATCHER (PowerShell) ============

    def _file_watcher_loop(self, path):
        """Monitorizeaza fisiere via PowerShell FileSystemWatcher."""
        ps_script = f'''
        $path = "{path}"
        $watcher = New-Object System.IO.FileSystemWatcher
        $watcher.Path = $path
        $watcher.IncludeSubdirectories = $true
        $watcher.EnableRaisingEvents = $true
        Register-ObjectEvent $watcher "Changed" -Action {{
            $time = Get-Date -Format "HH:mm:ss"
            Write-Host "EVENT|FILE|$time|MODIFY|$($Event.SourceEventArgs.FullPath)"
        }} | Out-Null
        Register-ObjectEvent $watcher "Created" -Action {{
            $time = Get-Date -Format "HH:mm:ss"
            Write-Host "EVENT|FILE|$time|CREATE|$($Event.SourceEventArgs.FullPath)"
        }} | Out-Null
        Register-ObjectEvent $watcher "Deleted" -Action {{
            $time = Get-Date -Format "HH:mm:ss"
            Write-Host "EVENT|FILE|$time|DELETE|$($Event.SourceEventArgs.FullPath)"
        }} | Out-Null
        Register-ObjectEvent $watcher "Renamed" -Action {{
            $time = Get-Date -Format "HH:mm:ss"
            Write-Host "EVENT|FILE|$time|RENAME|$($Event.SourceEventArgs.FullPath) -> $($Event.SourceEventArgs.Name)"
        }} | Out-Null
        while ($true) {{ Start-Sleep -Seconds 1 }}
        '''
        process = subprocess.Popen(
            ["powershell", "-NoProfile", "-Command", ps_script],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        try:
            for line in iter(process.stdout.readline, ''):
                if self._stop_event.is_set():
                    process.terminate()
                    break
                if line.startswith("EVENT|"):
                    parts = line.strip().split("|")
                    if len(parts) >= 4:
                        self._push_event({
                            "type": "file",
                            "action": parts[3],
                            "path": parts[4] if len(parts) > 4 else "",
                            "time": parts[2]
                        })
        finally:
            process.terminate()

    # ============ PROCESS WATCHER (WMI) ============

    def _process_watcher_loop(self):
        """Monitorizeaza procese noi prin psutil polling."""
        import psutil
        known_pids = set(psutil.pids())
        processes = {}
        for p in psutil.process_iter(['pid', 'name', 'ppid', 'cmdline']):
            processes[p.info['pid']] = p.info

        while not self._stop_event.is_set():
            try:
                current_pids = set(psutil.pids())
                
                # Detect new processes
                new_pids = current_pids - known_pids - self._skip_pids
                if new_pids:
                    # Update processes cache
                    for pid in new_pids:
                        try:
                            p = psutil.Process(pid)
                            pinfo = p.as_dict(attrs=['pid', 'name', 'ppid', 'cmdline'])
                            processes[pid] = pinfo
                            name = pinfo.get("name", "unknown")
                            ppid = pinfo.get("ppid", 0)
                            cmdline = pinfo.get("cmdline")
                            cmd = " ".join(cmdline)[:200] if cmdline else ""
                            
                            parent_name = ""
                            if ppid and ppid in processes:
                                parent_name = processes[ppid].get('name', '')
                                    
                            if ppid == self._self_pid or ppid in self._skip_pids:
                                self._skip_pids.add(pid)
                                continue
                                
                            if self._rate_limited("process_start"):
                                continue
                                
                            self._push_event({
                                "type": "process_start",
                                "pid": pid,
                                "name": name,
                                "parent_pid": ppid,
                                "parent_name": parent_name,
                                "command": cmd,
                                "time": time.strftime("%H:%M:%S")
                            })
                            logger.debug(f"PROC START: {name} (PID: {pid}) parinte: {parent_name} ({ppid})")
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass

                # Detect terminated processes
                terminated_pids = known_pids - current_pids
                for pid in terminated_pids:
                    processes.pop(pid, None)
                    if pid in self._skip_pids:
                        continue
                    if self._rate_limited("process_end"):
                        continue
                    self._push_event({
                        "type": "process_end",
                        "pid": pid,
                        "time": time.strftime("%H:%M:%S")
                    })

                known_pids = current_pids
                time.sleep(2)
            except Exception as e:
                logger.warning(f"Process watcher error: {e}")
                time.sleep(5)

    # ============ WINDOW FOCUS TRACKER ============

    def _window_focus_loop(self):
        """Tracking fereastra activa (foreground)."""
        user32 = windll.user32
        kernel32 = windll.kernel32
        last_foreground = None
        while not self._stop_event.is_set():
            try:
                hwnd = user32.GetForegroundWindow()
                now = time.time()
                if hwnd == self._last_focus_hwnd and now - self._last_focus_time < 1.0:
                    time.sleep(0.3)
                    continue
                self._last_focus_hwnd = hwnd
                self._last_focus_time = now

                length = user32.GetWindowTextLengthW(hwnd) + 1
                buffer = create_unicode_buffer(length)
                user32.GetWindowTextW(hwnd, buffer, length)
                title = buffer.value

                # Get PID
                pid = wintypes.DWORD()
                user32.GetWindowThreadProcessId(hwnd, byref(pid))

                # Get executable name
                exe_name = ""
                if pid.value:
                    handle = kernel32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ,
                                                   False, pid.value)
                    if handle:
                        exe_buf = create_unicode_buffer(260)
                        size = wintypes.DWORD(260)
                        kernel32.QueryFullProcessImageNameW(handle, 0, exe_buf, byref(size))
                        exe_name = os.path.basename(exe_buf.value) if exe_buf.value else ""
                        kernel32.CloseHandle(handle)

                self._push_event({
                    "type": "window_focus",
                    "title": title,
                    "pid": pid.value,
                    "exe": exe_name,
                    "time": time.strftime("%H:%M:%S")
                })
                last_foreground = title
                time.sleep(0.3)
            except Exception:
                time.sleep(1)

    # ============ PROCESS TREE ============

    def _process_tree(self, target=None):
        """Arborele proceselor (parent-child relationships)."""
        import psutil
        try:
            procs = []
            for p in psutil.process_iter(['pid', 'name', 'ppid', 'cmdline', 'num_threads']):
                try:
                    info = p.info
                    procs.append(info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            proc_map = {p['pid']: p for p in procs}
            tree = []
            seen = set()

            def build_node(pid, depth=0):
                if pid in seen or depth > 10:
                    return None
                seen.add(pid)
                p = proc_map.get(pid)
                if not p:
                    return None
                children = []
                for other_pid, other in proc_map.items():
                    if other.get('ppid') == pid:
                        child = build_node(other_pid, depth + 1)
                        if child:
                            children.append(child)
                cmdline = p.get('cmdline')
                return {
                    "pid": pid,
                    "name": p.get("name", "?"),
                    "command": (" ".join(cmdline) if cmdline else "")[:120],
                    "threads": p.get("num_threads", 0),
                    "children": children
                }

            # Root processes (no parent or parent not found)
            for p in procs:
                pid = p.get('pid')
                if pid and p.get('ppid') not in proc_map:
                    node = build_node(pid)
                    if node:
                        tree.append(node)

            # Filter if target specified
            if target:
                target_lower = target.lower()
                def find_in_children(node, search):
                    if search in node["name"].lower():
                        return True
                    for c in node.get("children", []):
                        if find_in_children(c, search):
                            return True
                    return False
                tree = [n for n in tree if find_in_children(n, target_lower)]

            return ToolResult(status=ToolStatus.SUCCESS,
                data={"processes": tree, "count": len(tree)},
                message=f"Arbore procese: {len(tree)} radacini")
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=f"Process tree error: {e}")

    # ============ SYSTEM SNAPSHOT ============

    def _system_snapshot(self):
        """Snapshot complet: procese, handles, memorie, retea."""
        user32 = windll.user32
        kernel32 = windll.kernel32

        # Screen dimensions
        screen_w = user32.GetSystemMetrics(0)
        screen_h = user32.GetSystemMetrics(1)

        # Cursor position
        point = wintypes.POINT()
        user32.GetCursorPos(byref(point))

        # Foreground window
        hwnd = user32.GetForegroundWindow()
        title_buf = create_unicode_buffer(512)
        user32.GetWindowTextW(hwnd, title_buf, 512)
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, byref(pid))

        # Top processes by CPU
        import psutil
        top_procs = []
        try:
            procs = []
            count = 0
            for p in psutil.process_iter(['pid', 'name', 'memory_info', 'num_threads']):
                if count > 200:  # Limit to avoid timeout
                    break
                try:
                    p.cpu_percent(interval=None) # start measure
                    procs.append(p)
                    count += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            time.sleep(0.1)
            proc_stats = []
            for p in procs[:100]:  # Process max 100
                try:
                    cpu = p.cpu_percent(interval=None)
                    info = p.info
                    mem = info.get('memory_info')
                    mem_mb = round(mem.rss / (1024*1024), 1) if mem else 0
                    proc_stats.append({
                        "name": info.get("name", "?"),
                        "pid": info.get("pid", 0),
                        "cpu": cpu,
                        "memory_mb": mem_mb,
                        "threads": info.get("num_threads", 0)
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied, AttributeError):
                    pass
            
            proc_stats.sort(key=lambda x: x["cpu"], reverse=True)
            top_procs = proc_stats[:10]
        except Exception as e:
            logger.warning(f"Process snapshot error: {e}")
            pass

        # Active windows
        windows = []
        def enum_windows_proc(hwnd, lparam):
            if user32.IsWindowVisible(hwnd) and user32.GetWindowTextLengthW(hwnd) > 0:
                buf = create_unicode_buffer(512)
                user32.GetWindowTextW(hwnd, buf, 512)
                pid = wintypes.DWORD()
                user32.GetWindowThreadProcessId(hwnd, byref(pid))
                rect = wintypes.RECT()
                user32.GetWindowRect(hwnd, byref(rect))
                windows.append({
                    "title": buf.value,
                    "pid": pid.value,
                    "x": rect.left, "y": rect.top,
                    "w": rect.right - rect.left,
                    "h": rect.bottom - rect.top
                })
            return True
        WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        user32.EnumWindows(WNDENUMPROC(enum_windows_proc), 0)

        return ToolResult(status=ToolStatus.SUCCESS, data={
            "screen": f"{screen_w}x{screen_h}",
            "cursor": {"x": point.x, "y": point.y},
            "foreground_window": {
                "title": title_buf.value,
                "pid": pid.value
            },
            "top_processes": top_procs[:5],
            "visible_windows": len(windows),
            "windows_sample": [w for w in windows[:15] if w["title"].strip()]
        }, message=f"Snapshot: {len(top_procs)} procese, {len(windows)} ferestre")

    # ============ ETW MONITOR (Alternative to Frida Interceptor) ============

    def _etw_monitor_loop(self):
        """PowerShell WMI event-based monitoring for instant process notifications + registry changes."""
        self._etw_stop = threading.Event()
        threads = []

        # Thread 1: WMI process creation events (instant, no polling)
        t1 = threading.Thread(target=self._etw_process_events, daemon=True)
        t1.start()
        threads.append(t1)

        # Thread 2: Registry key change monitor
        t2 = threading.Thread(target=self._etw_registry_monitor, daemon=True)
        t2.start()
        threads.append(t2)

        # Thread 3: Security log process audits (Event ID 4688)
        t3 = threading.Thread(target=self._etw_security_audit, daemon=True)
        t3.start()
        threads.append(t3)

        # Wait until stop
        self._etw_stop.wait()
        for t in threads:
            t.join(timeout=2)
        return ToolResult(status=ToolStatus.SUCCESS, message="ETW monitor oprit.")

    def _etw_process_events(self):
        """Monitorizeaza procese in timp real via WMI __InstanceCreationEvent (instant, nu polling 2s)."""
        ps_script = r'''
        $query = "SELECT * FROM __InstanceCreationEvent WITHIN 1 WHERE TargetInstance ISA 'Win32_Process'"
        Register-CimIndicationEvent -Query $query -Action {
            $p = $Event.SourceEventArgs.NewEvent.TargetInstance
            $t = Get-Date -Format "HH:mm:ss"
            $o = @{type="process_start"; pid=[int]$p.ProcessId; name=$p.Name; ppid=[int]$p.ParentProcessId; cmd=($p.CommandLine -replace '"','\"'); time=$t}
            Write-Host "ETW|$($o | ConvertTo-Json -Compress)"
        } | Out-Null
        $queryDel = "SELECT * FROM __InstanceDeletionEvent WITHIN 1 WHERE TargetInstance ISA 'Win32_Process'"
        Register-CimIndicationEvent -Query $queryDel -Action {
            $p = $Event.SourceEventArgs.NewEvent.TargetInstance
            $t = Get-Date -Format "HH:mm:ss"
            $o = @{type="process_end"; pid=[int]$p.ProcessId; name=$p.Name; time=$t}
            Write-Host "ETW|$($o | ConvertTo-Json -Compress)"
        } | Out-Null
        while ($true) { Wait-Event -Timeout 1 | Out-Null; if ([Console]::KeyAvailable) { break } }
        '''
        process = subprocess.Popen(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        try:
            for line in iter(process.stdout.readline, ''):
                if getattr(self, '_etw_stop', None) and self._etw_stop.is_set():
                    process.terminate()
                    break
                if line.startswith("ETW|"):
                    try:
                        payload = json.loads(line[4:])
                        if payload.get("pid") in self._skip_pids:
                            continue
                        ppid = payload.get("ppid", 0)
                        # Skip if parent is our PID or already skipped (grandchildren)
                        if ppid == self._self_pid or ppid in self._skip_pids:
                            self._skip_pids.add(payload.get("pid"))
                            continue
                        if self._rate_limited(payload.get("type", "etw")):
                            continue
                        self._push_event(payload)
                        logger.debug(f"ETW {payload.get('type','?')}: {payload.get('name','?')} (PID: {payload.get('pid')})")
                    except (json.JSONDecodeError, KeyError):
                        pass
        finally:
            try: process.terminate()
            except Exception as e: pass

    def _etw_registry_monitor(self):
        """Monitorizeaza modificari in registry chei critice."""
        # Monitorizam chei de registry frecvent modificate
        reg_keys = [
            r"HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run",
            r"HKLM:\SYSTEM\CurrentControlSet\Services",
            r"HKCU:\Software\Microsoft\Windows\CurrentVersion\Run",
        ]
        known_values = {}
        for key in reg_keys:
            try:
                result = subprocess.run(
                    ["powershell", "-NoProfile", "-Command",
                     f"Get-ItemProperty -Path '{key}' -ErrorAction SilentlyContinue | ConvertTo-Json -Compress"],
                    capture_output=True, text=True, timeout=5,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                if result.returncode == 0 and result.stdout.strip():
                    known_values[key] = result.stdout.strip()
            except Exception as e:
                known_values[key] = ""

        while not (getattr(self, '_etw_stop', None) and self._etw_stop.is_set()):
            try:
                for key in reg_keys:
                    result = subprocess.run(
                        ["powershell", "-NoProfile", "-Command",
                         f"Get-ItemProperty -Path '{key}' -ErrorAction SilentlyContinue | ConvertTo-Json -Compress"],
                        capture_output=True, text=True, timeout=5,
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
                    current = result.stdout.strip() if result.returncode == 0 else ""
                    if current and current != known_values.get(key, ""):
                        if self._rate_limited("registry_change"):
                            continue
                        self._push_event({
                            "type": "registry_change",
                            "key": key,
                            "time": time.strftime("%H:%M:%S")
                        })
                        logger.debug(f"REGISTRY CHANGE: {key}")
                        known_values[key] = current
                time.sleep(3)
            except Exception as e:
                logger.warning(f"Registry monitor error: {e}")
                time.sleep(10)

    def _etw_security_audit(self):
        """Citeste evenimente de securitate recente (Event ID 4688 = process creation) via Get-WinEvent."""
        last_seen = time.time() - 5  # Ignore events older than 5 seconds at start
        if not hasattr(self, '_last_audit_time'):
            self._last_audit_time = (time.time() - 5)  # start 5s ago
        poll_interval = 3
        while not (getattr(self, '_etw_stop', None) and self._etw_stop.is_set()):
            try:
                # Use cursor-based query — ask for events after last seen time
                from_dt = time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(self._last_audit_time))
                cmd = (
                    "$from = '{0}'; "
                    "Get-WinEvent -FilterHashtable @{{LogName='Security';Id=4688;StartTime=$from}} -MaxEvents 10 -ErrorAction SilentlyContinue | "
                    "ForEach-Object {{ $xml = [xml]$_.ToXml(); $p = $xml.Event.EventData.Data; "
                    "@{{type='audit_process'; pid=[int]($p | ?{{$_.Name -eq 'NewProcessId'}}).'#text'; "
                    "name=($p | ?{{$_.Name -eq 'NewProcessName'}}).'#text'; "
                    "ppid=[int]($p | ?{{$_.Name -eq 'CreatorProcessId'}}).'#text'; "
                    "time=($_.TimeCreated.ToString('HH:mm:ss')); "
                    "ts=($_.TimeCreated.ToString('yyyy-MM-ddTHH:mm:ss')); "
                    "cmd=($p | ?{{$_.Name -eq 'CommandLine'}}).'#text'}}}} | ConvertTo-Json -Compress"
                ).format(from_dt)
                result = subprocess.run(
                    ["powershell", "-NoProfile", "-Command", cmd],
                    capture_output=True, text=True, timeout=10,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                if result.returncode == 0 and result.stdout.strip():
                    try:
                        data = json.loads(result.stdout)
                        events = data if isinstance(data, list) else [data]
                        max_ts = self._last_audit_time
                        for ev in events:
                            if ev and ev.get("pid") and ev.get("pid") not in self._skip_pids:
                                if self._rate_limited("audit_process"):
                                    continue
                                # Update cursor to latest timestamp seen
                                if ev.get("ts"):
                                    try:
                                        ev_t = time.mktime(time.strptime(ev["ts"], "%Y-%m-%dT%H:%M:%S"))
                                        if ev_t > max_ts:
                                            max_ts = ev_t
                                    except (ValueError, OSError):
                                        pass
                                self._push_event(ev)
                        if max_ts > self._last_audit_time:
                            self._last_audit_time = max_ts
                    except (json.JSONDecodeError, TypeError):
                        pass
                time.sleep(poll_interval)
            except Exception as e:
                logger.warning(f"Security audit error: {e}")
                time.sleep(10)

    # ============ FRIDA STATUS ============

    def _frida_status(self):
        """Raport complet despre starea Frida."""
        if getattr(self, "_frida_ready_reported", False):
            return ToolResult(status=ToolStatus.SUCCESS, data={"frida_available": True}, message="Frida: ready (cached)")
        
        is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0

        win_ver = f"{sys.getwindowsversion().major}.{sys.getwindowsversion().minor} (build {sys.getwindowsversion().build})"
        
        self._frida_ready_reported = True
        return ToolResult(status=ToolStatus.SUCCESS, data={
            "frida_available": getattr(self, "_frida_available", False),
            "frida_admin": getattr(self, "_frida_admin", False),
            "frida_interceptor": getattr(self, "_frida_interceptor", False),
            "is_admin": is_admin,
            "windows_version": win_ver,
            "note": "Interceptor nu functioneaza pe build-uri Windows >= 26200 cu Frida 17.x. "
                    "Foloseste ETW sau PyWin32 ca alternativa pentru API hooking."
        }, message=f"Frida: available={getattr(self,'_frida_available',False)}, "
                   f"admin={getattr(self,'_frida_admin',False)}, "
                   f"interceptor={getattr(self,'_frida_interceptor',False)}")

    # ============ ETW CONTROL METHODS ============

    def _start_etw_monitor(self):
        """Porneste ETW monitoring (WMI events + registry + security audit)."""
        if hasattr(self, '_etw_stop') and self._etw_stop and not self._etw_stop.is_set():
            return ToolResult(status=ToolStatus.ERROR, error="ETW monitor este deja activ.")
        t = threading.Thread(target=self._etw_monitor_loop, daemon=True)
        t.start()
        self._monitor_threads.append(t)
        return ToolResult(status=ToolStatus.SUCCESS,
            message="ETW monitor activ: process events (WMI), registry changes, security audit (4688).")

    def _stop_etw_monitor(self):
        """Opreste ETW monitoring."""
        if hasattr(self, '_etw_stop') and self._etw_stop:
            self._etw_stop.set()
        return ToolResult(status=ToolStatus.SUCCESS, message="ETW monitor oprit.")

    def _etw_status(self):
        """Status ETW monitor."""
        active = hasattr(self, '_etw_stop') and self._etw_stop and not self._etw_stop.is_set()
        return ToolResult(status=ToolStatus.SUCCESS, data={
            "etw_active": active,
            "frida_interceptor": getattr(self, "_frida_interceptor", False),
            "note": "ETW functioneaza pe orice Windows build, fara admin. "
                    "Inlocuieste Frida Interceptor pentru monitorizare procese/registry."
        }, message=f"ETW monitor: {'ACTIV' if active else 'INACTIV'}. "
                   f"Interceptor Frida: {getattr(self, '_frida_interceptor', False)}")

    # ============ TRACE PROCESS ============

    def _trace_process(self, target):
        if not target:
            return ToolResult(status=ToolStatus.ERROR, error="Target process name required")

        import psutil
        process_info = []
        parent_info = []
        target_lower = target.lower()
        if target_lower.endswith('.exe'):
            target_lower = target_lower[:-4]
            
        for p in psutil.process_iter(['pid', 'name', 'ppid', 'cmdline', 'memory_info', 'num_threads', 'username']):
            try:
                name = p.info.get('name', '').lower()
                if name == target_lower or name == f"{target_lower}.exe" or str(p.info.get('pid')) == target:
                    process_info.append(p.info)
                    ppid = p.info.get('ppid')
                    if ppid:
                        try:
                            parent = psutil.Process(ppid).as_dict(['pid', 'name', 'cmdline'])
                            parent_info.append({"process": p.info.get('pid'), "parent": parent})
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
                
        trace_data = {"process_info": process_info, "parent_info": parent_info}

        # If Frida available, try to hook
        if self._frida_available:
            try:
                import frida
                session = frida.attach(target)
                if session:
                    script = session.create_script("""
                    'use strict';
                    rpc.exports = {
                        listThreads() {
                            return Process.enumerateThreads().map(t => ({id: t.id, state: t.state}));
                        },
                        listModules() {
                            return Process.enumerateModules().map(m => ({name: m.name, base: m.base.toString(), size: m.size}));
                        }
                    };
                    """)
                    script.load()
                    trace_data["frida"] = {
                        "threads": script.exports.list_threads(),
                        "modules": script.exports.list_modules()
                    }
                    session.detach()
            except Exception as e:
                trace_data["frida_error"] = str(e)

        return ToolResult(status=ToolStatus.SUCCESS,
            data=trace_data,
            message=f"Trace complet pe procesul: {target}")

    # ============ FRIDA HOOK ============

    def _hook_process(self, target, script=None, hook_functions=None):
        if not self._frida_available:
            return ToolResult(status=ToolStatus.ERROR,
                error="Frida nu e instalat. Ruleaza: pip install frida frida-tools")

        if not target:
            return ToolResult(status=ToolStatus.ERROR, error="Target process required")

        if not self._frida_admin:
            return ToolResult(status=ToolStatus.ERROR,
                error="Frida Interceptor necesita administrator. Ruleaza terminalul ca Administrator.")
        if not getattr(self, "_frida_interceptor", False):
            return ToolResult(status=ToolStatus.ERROR,
                error="Frida Interceptor nu este disponibil pe acest Windows build. "
                      "Windows build 26200+ nu este suportat de Frida 17.x pentru Interceptor.attach. "
                      "Foloseste trace_process (fara Interceptor) sau ETW monitoring.")

        import frida

        default_script = '''
        'use strict';
        var hooks = [];

        function logCall(name, args) {
            console.log(JSON.stringify({
                type: 'api_call',
                function: name,
                pid: Process.id,
                time: new Date().toISOString(),
                args: Array.prototype.slice.call(args, 0, 5).map(function(a) {
                    try { return a.toString(); } catch(e) { return '?'; }
                })
            }));
        }

        // Hook CreateFileW
        var CreateFileW = Module.findExportByName('kernel32.dll', 'CreateFileW');
        if (CreateFileW) {
            Interceptor.attach(CreateFileW, {
                onEnter: function(args) {
                    var path = Memory.readUtf16String(args[0]);
                    logCall('CreateFileW', [path]);
                }
            });
            hooks.push('CreateFileW');
        }

        // Hook ReadFile
        var ReadFile = Module.findExportByName('kernel32.dll', 'ReadFile');
        if (ReadFile) {
            Interceptor.attach(ReadFile, {
                onEnter: function(args) {
                    var hFile = args[0];
                    var nBytes = args[2].toInt32();
                    if (nBytes > 0 && nBytes < 1000000) {
                        logCall('ReadFile', [hFile, nBytes + ' bytes']);
                    }
                }
            });
            hooks.push('ReadFile');
        }

        // Hook WriteFile
        var WriteFile = Module.findExportByName('kernel32.dll', 'WriteFile');
        if (WriteFile) {
            Interceptor.attach(WriteFile, {
                onEnter: function(args) {
                    var hFile = args[0];
                    var nBytes = args[2].toInt32();
                    if (nBytes > 0 && nBytes < 1000000) {
                        logCall('WriteFile', [hFile, nBytes + ' bytes']);
                    }
                }
            });
            hooks.push('WriteFile');
        }

        // Hook RegOpenKeyExW
        var RegOpenKeyExW = Module.findExportByName('advapi32.dll', 'RegOpenKeyExW');
        if (RegOpenKeyExW) {
            Interceptor.attach(RegOpenKeyExW, {
                onEnter: function(args) {
                    var path = Memory.readUtf16String(args[1]);
                    logCall('RegOpenKeyExW', [path]);
                }
            });
            hooks.push('RegOpenKeyExW');
        }

        // Hook CreateProcessW
        var CreateProcessW = Module.findExportByName('kernel32.dll', 'CreateProcessW');
        if (CreateProcessW) {
            Interceptor.attach(CreateProcessW, {
                onEnter: function(args) {
                    var cmd = Memory.readUtf16String(args[1]);
                    logCall('CreateProcessW', [cmd]);
                }
            });
            hooks.push('CreateProcessW');
        }

        console.log(JSON.stringify({type: 'hooks_loaded', functions: hooks}));
        '''

        js_code = script or default_script

        try:
            # Attach to process
            session = frida.attach(target)
            script = session.create_script(js_code)
            output = []

            def on_message(message, data):
                if message.get("type") == "send":
                    try:
                        payload = json.loads(message["payload"])
                        output.append(payload)
                        self._event_queue.put(payload)
                    except Exception as e:
                        output.append({"raw": message["payload"]})

            script.on("message", on_message)
            script.load()

            # Keep session in a thread for monitoring
            def monitor_thread():
                import time as _time
                _time.sleep(30)  # Monitor for 30 seconds
                try:
                    session.detach()
                except Exception as e:
                    pass

            t = threading.Thread(target=monitor_thread, daemon=True)
            t.start()

            return ToolResult(status=ToolStatus.SUCCESS, data={
                "target": target,
                "hooks": self._frida_hooks_summary(js_code),
                "initial_events": output[:20],
                "session_active": True
            }, message=f"Frida hook activ pe {target}. Hook-uri: {len(output)} evenimente initiale")

        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR,
                error=f"Frida hook error: {e}")

    def _frida_hooks_summary(self, js_code):
        """Extrage numele functiilor hook-uite din script."""
        hooks = re.findall(r"Module\.findExportByName\('([^']+)',\s*'([^']+)'\)", js_code)
        return [f"{mod}!{func}" for mod, func in hooks] if hooks else ["custom script"]

    def _list_hooks(self):
        if self._frida_session:
            return ToolResult(status=ToolStatus.SUCCESS,
                data={"active": True, "session": str(self._frida_session)},
                message="Sesiune Frida activa")
        return ToolResult(status=ToolStatus.SUCCESS,
            data={"active": False}, message="Nicio sesiune Frida activa")

    # ============ GET CLICKS ============

    def _get_clicks(self):
        """Returneaza click-urile recente din coada."""
        clicks = []
        user32 = windll.user32
        point = wintypes.POINT()
        user32.GetCursorPos(byref(point))

        # Get window under cursor
        hwnd = user32.WindowFromPoint(point)
        title_buf = create_unicode_buffer(512)
        if hwnd:
            user32.GetWindowTextW(hwnd, title_buf, 512)

        return ToolResult(status=ToolStatus.SUCCESS, data={
            "current_position": {"x": point.x, "y": point.y},
            "window_under_cursor": title_buf.value,
            "recent_clicks": list(self._event_queue.queue)[-20:] if not self._event_queue.empty() else []
        }, message=f"Cursor la ({point.x}, {point.y}) sub '{title_buf.value}'")

    # ============ GET PROCESSES ============

    def _get_processes(self):
        """Listeaza procesele active cu detalii."""
        import psutil
        try:
            unique = []
            seen = set()
            for p in psutil.process_iter(['pid', 'name', 'ppid', 'memory_info', 'num_threads', 'exe']):
                try:
                    info = p.info
                    pid = info.get('pid')
                    if pid and pid not in seen:
                        seen.add(pid)
                        mem = info.get('memory_info')
                        unique.append({
                            "pid": pid,
                            "name": info.get("name", "?"),
                            "ppid": info.get("ppid", 0),
                            "memory_mb": round(mem.rss / (1024*1024), 1) if mem else 0,
                            "threads": info.get("num_threads", 0),
                            "path": (info.get("exe") or "")[:100]
                        })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            return ToolResult(status=ToolStatus.SUCCESS,
                data={"processes": unique, "count": len(unique)},
                message=f"{len(unique)} procese active")
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=f"Process list error: {e}")

    # ============ WINDOW TREE ============

    def _window_tree(self):
        """Listeaza ierarhia ferestrelor vizibile."""
        user32 = windll.user32
        windows = []

        def enum_proc(hwnd, lparam):
            if user32.IsWindowVisible(hwnd):
                buf = create_unicode_buffer(512)
                length = user32.GetWindowTextW(hwnd, buf, 512)
                if length > 0:
                    pid = wintypes.DWORD()
                    user32.GetWindowThreadProcessId(hwnd, byref(pid))
                    rect = wintypes.RECT()
                    user32.GetWindowRect(hwnd, byref(rect))
                    windows.append({
                        "title": buf.value,
                        "pid": pid.value,
                        "x": rect.left, "y": rect.top,
                        "w": rect.right - rect.left,
                        "h": rect.bottom - rect.top
                    })
            return True

        WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        user32.EnumWindows(WNDENUMPROC(enum_proc), 0)

        return ToolResult(status=ToolStatus.SUCCESS,
            data={"windows": windows[:30], "count": len(windows)},
            message=f"{len(windows)} ferestre vizibile")
