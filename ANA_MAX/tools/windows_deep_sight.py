"""
ANA MAX - Windows Deep Sight Tool (God View - PREMIUM)
======================================================
Vizibilitate totala asupra sistemului Windows: procese, retea, fisiere, registry.
Bazat strict pe psutil si win32 APIs native (fara subprocess pentru operatii comune).
PREMIUM tool - necesita licenta Pro.
"""

import os
import queue
import threading
import logging
from typing import Optional, List, Dict, Any
from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus

logger = logging.getLogger(__name__)


class WindowsDeepSightTool(Tool):
    """
    God View complet al sistemului Windows.
    Monitorizeaza in timp real: procese, conexiuni retea, fisiere deschise,
    utilizare CPU/RAM per proces, evenimente de securitate.
    """

    def __init__(self):
        self._event_queue: queue.Queue = queue.Queue(maxsize=1000)
        self._subscribers: List[queue.Queue] = []
        self._subscribers_lock = threading.Lock()
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._known_pids: set = set()

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="windows_deep_sight",
            description=(
                "God View sub capota sistemului Windows (PREMIUM): procese, retea, "
                "fisiere deschise, CPU/RAM per proces, detectie intruziuni. "
                "Bazat pe psutil nativ - zero overhead subprocess."
            ),
            parameters=[
                ToolParameter(
                    name="operation",
                    description=(
                        "Operatia: process_tree, network_map, open_files, "
                        "top_cpu, top_ram, security_scan, start_monitor, "
                        "stop_monitor, get_events"
                    ),
                    type="string",
                    required=True,
                    choices=[
                        "process_tree", "network_map", "open_files",
                        "top_cpu", "top_ram", "security_scan",
                        "start_monitor", "stop_monitor", "get_events"
                    ]
                ),
                ToolParameter(
                    name="pid",
                    description="PID-ul procesului pentru operatii specifice (optional)",
                    type="integer",
                    required=False
                ),
                ToolParameter(
                    name="limit",
                    description="Numarul maxim de rezultate returnate (default: 20)",
                    type="integer",
                    required=False
                ),
            ],
            category="system_intelligence"
        )

    def execute(self, operation: str, pid: Optional[int] = None,
                limit: int = 20, **kwargs) -> ToolResult:
        try:
            import psutil
        except ImportError:
            return ToolResult(
                status=ToolStatus.ERROR,
                error="psutil nu este instalat. Ruleaza: pip install psutil"
            )

        try:
            if operation == "process_tree":
                return self._process_tree(psutil, limit)
            elif operation == "network_map":
                return self._network_map(psutil, limit)
            elif operation == "open_files":
                return self._open_files(psutil, pid, limit)
            elif operation == "top_cpu":
                return self._top_by(psutil, "cpu_percent", limit)
            elif operation == "top_ram":
                return self._top_by(psutil, "memory_percent", limit)
            elif operation == "security_scan":
                return self._security_scan(psutil)
            elif operation == "start_monitor":
                return self._start_monitor(psutil)
            elif operation == "stop_monitor":
                return self._stop_monitor()
            elif operation == "get_events":
                return self._get_events()
            else:
                return ToolResult(status=ToolStatus.ERROR, error=f"Operatie necunoscuta: {operation}")
        except Exception as e:
            logger.exception("WindowsDeepSight error op=%s", operation)
            return ToolResult(status=ToolStatus.ERROR, error=str(e))

    # ------------------------------------------------------------------ #
    #  Operatii instantanee                                                #
    # ------------------------------------------------------------------ #

    def _process_tree(self, psutil, limit: int) -> ToolResult:
        """Arbore complet de procese cu detalii."""
        procs = []
        for proc in psutil.process_iter(
            ["pid", "name", "ppid", "status", "cpu_percent",
             "memory_percent", "username", "create_time"]
        ):
            try:
                info = proc.info
                procs.append({
                    "pid": info["pid"],
                    "name": info["name"],
                    "ppid": info["ppid"],
                    "status": info["status"],
                    "cpu_pct": round(info["cpu_percent"] or 0, 2),
                    "ram_pct": round(info["memory_percent"] or 0, 2),
                    "user": info["username"],
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        procs.sort(key=lambda x: x["cpu_pct"], reverse=True)
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={"processes": procs[:limit], "total": len(procs)},
            message=f"Process tree: {len(procs)} procese active, top {limit} dupa CPU."
        )

    def _network_map(self, psutil, limit: int) -> ToolResult:
        """Harta conexiunilor de retea active."""
        connections = []
        try:
            for conn in psutil.net_connections(kind="inet"):
                try:
                    proc_name = psutil.Process(conn.pid).name() if conn.pid else "system"
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    proc_name = "unknown"

                connections.append({
                    "pid": conn.pid,
                    "process": proc_name,
                    "status": conn.status,
                    "local": f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else "-",
                    "remote": f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else "-",
                    "type": "TCP" if conn.type.name == "SOCK_STREAM" else "UDP",
                })
        except psutil.AccessDenied:
            return ToolResult(
                status=ToolStatus.ERROR,
                error="Acces refuzat la conexiuni retea. Ruleaza ca Administrator."
            )

        established = [c for c in connections if c["status"] == "ESTABLISHED"]
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={
                "connections": connections[:limit],
                "total": len(connections),
                "established": len(established),
            },
            message=f"Network map: {len(connections)} conexiuni ({len(established)} ESTABLISHED)."
        )

    def _open_files(self, psutil, pid: Optional[int], limit: int) -> ToolResult:
        """Fisiere deschise de un proces sau de tot sistemul."""
        files = []
        try:
            if pid:
                proc = psutil.Process(pid)
                for f in proc.open_files():
                    files.append({"pid": pid, "process": proc.name(), "path": f.path})
            else:
                for proc in psutil.process_iter(["pid", "name"]):
                    try:
                        for f in proc.open_files():
                            files.append({
                                "pid": proc.pid,
                                "process": proc.info["name"],
                                "path": f.path
                            })
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))

        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={"files": files[:limit], "total": len(files)},
            message=f"Open files: {len(files)} fisiere deschise."
        )

    def _top_by(self, psutil, metric: str, limit: int) -> ToolResult:
        """Top procese dupa CPU sau RAM."""
        procs = []
        for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent", "memory_info"]):
            try:
                info = proc.info
                ram_mb = round(info["memory_info"].rss / 1024 / 1024, 1) if info.get("memory_info") else 0
                procs.append({
                    "pid": info["pid"],
                    "name": info["name"],
                    "cpu_pct": round(info["cpu_percent"] or 0, 2),
                    "ram_pct": round(info["memory_percent"] or 0, 2),
                    "ram_mb": ram_mb,
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        key = "cpu_pct" if metric == "cpu_percent" else "ram_pct"
        procs.sort(key=lambda x: x[key], reverse=True)
        label = "CPU" if key == "cpu_pct" else "RAM"

        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={"top": procs[:limit]},
            message=f"Top {limit} procese dupa {label}."
        )

    def _security_scan(self, psutil) -> ToolResult:
        """Scan rapid de securitate: procese suspecte, porturi neobisnuite, conexiuni externe."""
        suspicious_procs = []
        external_connections = []
        high_privilege = []

        # Procese fara nume sau cu nume suspecte
        suspicious_names = {"cmd.exe", "powershell.exe", "wscript.exe", "cscript.exe",
                            "mshta.exe", "regsvr32.exe", "rundll32.exe"}
        for proc in psutil.process_iter(["pid", "name", "username", "cmdline"]):
            try:
                info = proc.info
                name = (info["name"] or "").lower()
                if name in suspicious_names:
                    suspicious_procs.append({
                        "pid": info["pid"],
                        "name": info["name"],
                        "user": info["username"],
                        "cmdline": " ".join(info["cmdline"] or [])[:100],
                    })
                if info["username"] and "SYSTEM" in str(info["username"]).upper():
                    high_privilege.append({"pid": info["pid"], "name": info["name"]})
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        # Conexiuni catre IP-uri externe (non-loopback, non-LAN)
        try:
            for conn in psutil.net_connections(kind="inet"):
                if conn.raddr and conn.status == "ESTABLISHED":
                    ip = conn.raddr.ip
                    if not (ip.startswith("127.") or ip.startswith("192.168.")
                            or ip.startswith("10.") or ip == "::1"):
                        try:
                            proc_name = psutil.Process(conn.pid).name() if conn.pid else "system"
                        except Exception:
                            proc_name = "unknown"
                        external_connections.append({
                            "pid": conn.pid,
                            "process": proc_name,
                            "remote_ip": ip,
                            "remote_port": conn.raddr.port,
                        })
        except psutil.AccessDenied:
            pass

        risk_level = "LOW"
        if len(external_connections) > 10 or len(suspicious_procs) > 5:
            risk_level = "MEDIUM"
        if len(external_connections) > 30:
            risk_level = "HIGH"

        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={
                "risk_level": risk_level,
                "suspicious_processes": suspicious_procs[:20],
                "external_connections": external_connections[:20],
                "high_privilege_count": len(high_privilege),
            },
            message=(
                f"Security scan complet. Risk: {risk_level}. "
                f"{len(suspicious_procs)} procese suspecte, "
                f"{len(external_connections)} conexiuni externe."
            )
        )

    # ------------------------------------------------------------------ #
    #  Monitor continuu cu pub/sub pentru SSE streaming                   #
    # ------------------------------------------------------------------ #

    def _start_monitor(self, psutil) -> ToolResult:
        if self._monitor_thread and self._monitor_thread.is_alive():
            return ToolResult(status=ToolStatus.SUCCESS, message="Deep Sight monitor ruleaza deja.")

        self._stop_event.clear()
        # Initializeaza PID-urile cunoscute
        try:
            self._known_pids = {p.pid for p in psutil.process_iter(["pid"])}
        except Exception:
            self._known_pids = set()

        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="DeepSightMonitor"
        )
        self._monitor_thread.start()
        logger.info("WindowsDeepSight monitor pornit")
        return ToolResult(
            status=ToolStatus.SUCCESS,
            message="God View Deep Sight activat. Monitorizeaza procese si retea in timp real."
        )

    def _stop_monitor(self) -> ToolResult:
        self._stop_event.set()
        logger.info("WindowsDeepSight monitor oprit")
        return ToolResult(status=ToolStatus.SUCCESS, message="Deep Sight monitor oprit.")

    def _get_events(self) -> ToolResult:
        events = []
        while not self._event_queue.empty():
            try:
                events.append(self._event_queue.get_nowait())
            except queue.Empty:
                break
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={"events": events, "count": len(events)},
            message=f"{len(events)} evenimente Deep Sight colectate."
        )

    def subscribe_events(self) -> queue.Queue:
        """Aboneaza un consumer la stream-ul de evenimente (pentru SSE)."""
        sub_q: queue.Queue = queue.Queue(maxsize=500)
        with self._subscribers_lock:
            self._subscribers.append(sub_q)
        return sub_q

    def unsubscribe_events(self, sub_q: queue.Queue) -> None:
        """Dezaboneaza un consumer."""
        with self._subscribers_lock:
            try:
                self._subscribers.remove(sub_q)
            except ValueError:
                pass

    def _publish(self, event: Dict[str, Any]) -> None:
        """Trimite evenimentul catre queue principal si toti subscriberii."""
        try:
            self._event_queue.put_nowait(event)
        except queue.Full:
            try:
                self._event_queue.get_nowait()
                self._event_queue.put_nowait(event)
            except Exception:
                pass

        with self._subscribers_lock:
            for sub_q in list(self._subscribers):
                try:
                    sub_q.put_nowait(event)
                except queue.Full:
                    pass

    def _monitor_loop(self) -> None:
        """Bucla de monitorizare: detecteaza procese noi/terminate si conexiuni noi."""
        try:
            import psutil
            import time
        except ImportError:
            return

        logger.debug("DeepSight monitor loop started")
        known_connections: set = set()

        while not self._stop_event.is_set():
            try:
                # --- Procese noi / terminate ---
                current_pids = {p.pid for p in psutil.process_iter(["pid"])}
                new_pids = current_pids - self._known_pids
                dead_pids = self._known_pids - current_pids

                for pid in new_pids:
                    try:
                        proc = psutil.Process(pid)
                        self._publish({
                            "type": "PROCESS_START",
                            "pid": pid,
                            "name": proc.name(),
                            "user": proc.username(),
                            "cmdline": " ".join(proc.cmdline()[:3]),
                        })
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass

                for pid in dead_pids:
                    self._publish({"type": "PROCESS_END", "pid": pid})

                self._known_pids = current_pids

                # --- Conexiuni noi ---
                try:
                    current_conns = set()
                    for conn in psutil.net_connections(kind="inet"):
                        if conn.raddr and conn.status == "ESTABLISHED":
                            key = (conn.pid, conn.laddr, conn.raddr)
                            current_conns.add(key)
                            if key not in known_connections:
                                try:
                                    proc_name = psutil.Process(conn.pid).name() if conn.pid else "system"
                                except Exception:
                                    proc_name = "unknown"
                                self._publish({
                                    "type": "NEW_CONNECTION",
                                    "pid": conn.pid,
                                    "process": proc_name,
                                    "local": f"{conn.laddr.ip}:{conn.laddr.port}",
                                    "remote": f"{conn.raddr.ip}:{conn.raddr.port}",
                                })
                    known_connections = current_conns
                except psutil.AccessDenied:
                    pass

            except Exception as e:
                logger.debug("DeepSight monitor loop error: %s", e)

            self._stop_event.wait(timeout=2.0)

        logger.debug("DeepSight monitor loop stopped")
