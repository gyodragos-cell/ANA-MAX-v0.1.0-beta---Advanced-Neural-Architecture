"""
ANA MAX - world_model_tool.py
==============================
Embodied World Model — Simulare interna live a starii masinii.

Mentine un "model mental" actualizat in timp real:
- Procese active (PID, RAM, CPU)
- Porturi ascultate
- Fisiere modificate recent
- VRAM disponibil
- Tool-uri ANA active

Orice agent MCP poate apela 'world_model' si primeste instantaneu
harta completa a sistemului, fara query-uri suplimentare.

Actualizare: daemon thread la fiecare 5 secunde, zero-cost.
"""
from __future__ import annotations

import json
import logging
import os
import socket
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import psutil

from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus

logger = logging.getLogger("ANA.WorldModel")

# Starea globala (singleton) a modelului mental
_world_state: dict = {}
_state_lock = threading.Lock()
_daemon_running = False


def _update_world_state():
    """Actualizeaza starea lumii (ruleaza in daemon thread)."""
    global _world_state
    while True:
        try:
            # 1. Procese top RAM
            processes = []
            for p in psutil.process_iter(["pid", "name", "memory_info", "cpu_percent", "status"]):
                try:
                    mem_mb = p.info["memory_info"].rss / (1024 * 1024)
                    processes.append({
                        "pid": p.info["pid"],
                        "name": p.info["name"],
                        "ram_mb": round(mem_mb, 1),
                        "cpu_pct": p.info["cpu_percent"],
                        "status": p.info["status"],
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            processes.sort(key=lambda x: x["ram_mb"], reverse=True)

            # 2. Porturi ascultate
            listening_ports = []
            for conn in psutil.net_connections(kind="inet"):
                if conn.status == "LISTEN":
                    try:
                        proc_name = psutil.Process(conn.pid).name() if conn.pid else "unknown"
                    except Exception:
                        proc_name = "unknown"
                    listening_ports.append({
                        "port": conn.laddr.port,
                        "pid": conn.pid,
                        "process": proc_name,
                    })

            # 3. Memorie sistem
            vm = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            # 4. GPU VRAM (via nvidia-smi daca exista)
            vram_info = {"available": "N/A", "total": "N/A", "used": "N/A"}
            try:
                import subprocess
                result = subprocess.run(
                    ["nvidia-smi", "--query-gpu=memory.free,memory.total,memory.used",
                     "--format=csv,noheader,nounits"],
                    capture_output=True, text=True, timeout=2
                )
                if result.returncode == 0:
                    parts = result.stdout.strip().split(",")
                    if len(parts) == 3:
                        vram_info = {
                            "available_mb": int(parts[0].strip()),
                            "total_mb": int(parts[1].strip()),
                            "used_mb": int(parts[2].strip()),
                        }
            except Exception:
                pass

            # 5. Fisiere recent modificate in workspace ANA
            ana_root = Path(__file__).parent.parent
            recent_files = []
            cutoff = time.time() - 300  # ultimele 5 minute
            try:
                for f in ana_root.rglob("*.py"):
                    if "venv" in str(f) or "__pycache__" in str(f):
                        continue
                    if f.stat().st_mtime > cutoff:
                        recent_files.append({
                            "file": str(f.relative_to(ana_root)),
                            "modified": datetime.fromtimestamp(f.stat().st_mtime).strftime("%H:%M:%S"),
                        })
                recent_files.sort(key=lambda x: x["modified"], reverse=True)
            except Exception:
                pass

            new_state = {
                "timestamp": datetime.now().isoformat(),
                "system": {
                    "ram_total_gb": round(vm.total / 1e9, 1),
                    "ram_used_pct": vm.percent,
                    "ram_available_gb": round(vm.available / 1e9, 1),
                    "disk_used_pct": disk.percent,
                    "cpu_pct": psutil.cpu_percent(interval=None),
                },
                "gpu": vram_info,
                "top_processes": processes[:10],
                "listening_ports": listening_ports[:20],
                "recent_modified_files": recent_files[:10],
                "ana_server_alive": _check_ana_server(),
                "swarm_node_alive": _check_swarm_node(),
            }

            with _state_lock:
                _world_state = new_state

        except Exception as e:
            logger.debug(f"World model update error: {e}")

        time.sleep(5)


def _check_ana_server() -> bool:
    try:
        s = socket.create_connection(("127.0.0.1", 8765), timeout=0.5)
        s.close()
        return True
    except Exception:
        return False


def _check_swarm_node() -> bool:
    try:
        s = socket.create_connection(("127.0.0.1", 8766), timeout=0.5)
        s.close()
        return True
    except Exception:
        return False


def _start_world_model_daemon():
    global _daemon_running
    if not _daemon_running:
        _daemon_running = True
        t = threading.Thread(target=_update_world_state, daemon=True, name="WorldModelDaemon")
        t.start()
        logger.info("World Model Daemon pornit (refresh: 5s)")


# Porneste demonul la import
_start_world_model_daemon()


class WorldModelTool(Tool):
    """Returneaza modelul mental live al intregii masini."""

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="world_model",
            description=(
                "Returneaza harta mentala live a sistemului: procese active, porturi, "
                "VRAM disponibil, fisiere recent modificate si statusul serverelor ANA. "
                "Date pre-calculate, raspuns instant."
            ),
            parameters=[
                ToolParameter(
                    name="filter",
                    description="Filtreaza sectiunea dorita: 'system', 'gpu', 'processes', 'ports', 'files', 'servers', 'all'",
                    type="string",
                    required=False,
                ),
            ],
            category="system",
        )

    def execute(self, **kwargs: Any) -> ToolResult:
        with _state_lock:
            state = dict(_world_state)

        if not state:
            return ToolResult(
                status=ToolStatus.ERROR,
                error="World model inca se initializeaza (asteapta 5 secunde si incearca din nou)."
            )

        filter_key = kwargs.get("filter", "all")
        if filter_key == "all" or not filter_key:
            result_data = state
        elif filter_key == "processes":
            result_data = {"top_processes": state.get("top_processes", [])}
        elif filter_key == "ports":
            result_data = {"listening_ports": state.get("listening_ports", [])}
        elif filter_key == "files":
            result_data = {"recent_modified_files": state.get("recent_modified_files", [])}
        elif filter_key == "servers":
            result_data = {
                "ana_server_alive": state.get("ana_server_alive"),
                "swarm_node_alive": state.get("swarm_node_alive"),
            }
        elif filter_key in state:
            result_data = {filter_key: state[filter_key]}
        else:
            result_data = state

        return ToolResult(
            status=ToolStatus.SUCCESS,
            data=result_data,
            message=f"World Model snapshot @ {state.get('timestamp', 'N/A')}",
        )
