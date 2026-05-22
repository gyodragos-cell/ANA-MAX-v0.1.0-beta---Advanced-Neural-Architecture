"""
ANA MAX Launcher — Pornire sigura cu verificare integritate si auto-recovery.
Ruleaza: python launcher.py [--port 8765] [--host 127.0.0.1] [--admin]
"""

import sys, os, json, time, subprocess, signal, socket, tempfile, shutil
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).parent.resolve()
LOG_DIR = BASE_DIR / "logs"
PORT = 8765
HOST = "127.0.0.1"
SERVER_SCRIPT = BASE_DIR / "main.py"
VENV_PYTHON = BASE_DIR / "venv" / "Scripts" / "python.exe"
HEALTH_TIMEOUT = 15
MAX_RETRIES = 2
STATE_FILE = BASE_DIR / ".launcher_state.json"

REQUIRED_FILES = [
    "main.py",
    "tools/base.py",
    "tools/windows_deep_sight.py",
]

REQUIRED_DIRS = [
    "tools",
    "logs",
    "data",
]


def _log(msg: str):
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")


def _check_files() -> list[str]:
    missing = []
    for f in REQUIRED_FILES:
        if not (BASE_DIR / f).exists():
            missing.append(f)
    for d in REQUIRED_DIRS:
        if not (BASE_DIR / d).is_dir():
            missing.append(d)
    return missing


def _try_python() -> Optional[Path]:
    for exe in [VENV_PYTHON, Path("python.exe"), Path("python3.exe")]:
        if exe.exists():
            try:
                r = subprocess.run([str(exe), "--version"], capture_output=True, text=True, timeout=5)
                if r.returncode == 0:
                    return exe
            except Exception:
                continue
    return None


def _port_free(port: int) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(2)
            return s.connect_ex((HOST, port)) != 0
    except Exception as e:
        return True


def _kill_port(port: int):
    # First try: normal kill (works for non-elevated processes)
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | "
             f"ForEach-Object {{ Stop-Process -Id $_.OwningProcess -Force }}" ],
            capture_output=True, text=True, timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        time.sleep(2)
    except Exception as e:
        pass

    # If still occupied, try elevated kill (UAC prompt)
    if not _port_free(port):
        try:
            subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 f"$p = Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue; "
                 f"if ($p) {{ Start-Process taskkill -ArgumentList '/F','/PID',$p.OwningProcess -Verb RunAs -Wait }}" ],
                capture_output=True, text=True, timeout=30,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            time.sleep(3)
        except Exception as e:
            pass


def _mcp_tools_list(timeout: int = HEALTH_TIMEOUT) -> Optional[list[dict]]:
    import urllib.request
    payload = json.dumps({
        "jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}
    }).encode()
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            req = urllib.request.Request(
                f"http://{HOST}:{PORT}/mcp",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read())
                tools = data.get("result", {}).get("tools")
                if isinstance(tools, list):
                    return tools
        except Exception:
            time.sleep(1)
    return None


def _health_check(timeout: int = HEALTH_TIMEOUT) -> bool:
    return _mcp_tools_list(timeout=timeout) is not None


def _tool_count(timeout: int = 3) -> Optional[int]:
    tools = _mcp_tools_list(timeout=timeout)
    if tools is None:
        return None
    return len(tools)


def _load_state() -> dict:
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except Exception as e:
        pass
    return {"boot_count": 0, "last_ok": None, "retries": 0}


def _save_state(state: dict):
    try:
        STATE_FILE.write_text(json.dumps(state, indent=2))
    except Exception as e:
        pass


def start_server(python_exe: Path, port: int = PORT, host: str = HOST,
                 admin: bool = False) -> Optional[subprocess.Popen]:
    cmd = [str(python_exe), str(SERVER_SCRIPT), "--port", str(port), "--host", host]
    if admin:
        import ctypes
        if ctypes.windll.shell32.IsUserAnAdmin():
            _log("Deja admin. Pornire directa.")
            return subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW, cwd=str(BASE_DIR)
            )
        _log("Lansez fereastra UAC... Accepta dialogul pentru a continua.")
        ps_admin = (
            f'Start-Process -FilePath "{python_exe}" '
            f'-ArgumentList \'{SERVER_SCRIPT} --port {port} --host {host}\' '
            f'-Verb RunAs -WindowStyle Normal -PassThru'
        )
        proc = subprocess.Popen(
            ["powershell", "-NoProfile", "-Command", ps_admin],
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        return proc

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW,
        cwd=str(BASE_DIR)
    )
    return proc


def main():
    port = PORT
    host = HOST
    admin = False

    import ctypes

    for arg in sys.argv[1:]:
        if arg == "--admin":
            admin = True
        elif arg.startswith("--port="):
            port = int(arg.split("=")[1])
        elif arg.startswith("--host="):
            host = arg.split("=")[1]

    _log("=== ANA MAX Launcher ===")
    state = _load_state()
    state["boot_count"] = state.get("boot_count", 0) + 1
    _save_state(state)

    # Step 1: Verifica fisiere si creeaza directoare lipsa
    _log("Verific fisiere...")
    for d in REQUIRED_DIRS:
        (BASE_DIR / d).mkdir(parents=True, exist_ok=True)
    missing = _check_files()
    if missing:
        for f in missing:
            _log(f"  LIPSESTE: {f}")
        _log("EROARE: Fisiere lipsa. Nu pot porni.")
        sys.exit(1)
    _log("  OK")

    # Step 2: Gaseste Python
    _log("Caut Python...")
    python_exe = _try_python()
    if not python_exe:
        _log("EROARE: Nu gasesc Python (nici venv, nici system).")
        sys.exit(1)
    _log(f"  {python_exe}")

    # Step 3: Verifica port
    if not _port_free(port):
        _log(f"Port {port} e ocupat. Incerc sa eliberez...")
        _kill_port(port)
        if not _port_free(port):
            # Maybe it's our own server (elevated from UAC)?
            _log("Port ocupat. Verific daca e un server ANA MAX functional...")
            if _health_check(timeout=5):
                _log(f"Server ANA MAX deja activ la http://{host}:{port}")
                count = _tool_count()
                if count is not None:
                    _log(f"  Tool-uri disponibile: {count}")
                sys.exit(0)
            # Not our server, give up
            _log(f"Port {port} e ocupat de alt proces si nu poate fi oprit (posibil system/elevated).")
            _log("Ruleaza ca ADMINISTRATOR: taskkill /F /PID (gaseste PID cu: netstat -ano | findstr :8765)")
            sys.exit(1)
    _log(f"  Port {port} liber")

    # Step 4: Porneste serverul
    retries = state.get("retries", 0)
    attempt = 0
    while attempt <= MAX_RETRIES:
        attempt += 1
        _log(f"Pornire server (incercarea {attempt}/{MAX_RETRIES + 1})...")
        proc = start_server(python_exe, port, host, admin)
        if not proc:
            _log("EROARE: Nu am putut lansa procesul.")
            sys.exit(1)

        _log(f"  PID: {proc.pid}")

        if admin and not ctypes.windll.shell32.IsUserAnAdmin():
            # Admin mode via UAC: user must accept the dialog manually
            _log("  Astept acceptarea dialogului UAC (max 60s)...")
            if _health_check(timeout=60):
                _log("Server pornit cu succes (UAC elevation)! Health-check: OK")
            else:
                _log("  Serverul nu a pornit. Ruleaza manual ca Administrator:")
                _log(f"    {python_exe} {SERVER_SCRIPT} --port {port}")
                sys.exit(1)
            state["last_ok"] = time.time()
            state["retries"] = 0
            _save_state(state)
            _log(f"\n  ANA MAX ruleaza la http://{host}:{port} (ADMIN)")
            return

        if _health_check(timeout=HEALTH_TIMEOUT):
            _log("Server pornit cu succes! Health-check: OK")
            state["last_ok"] = time.time()
            state["retries"] = 0
            _save_state(state)

            _log(f"\n  ANA MAX ruleaza la http://{host}:{port}")
            count = _tool_count()
            if count is not None:
                _log(f"  Tool-uri disponibile: {count}")
            else:
                _log("  Tool-uri disponibile: health-check OK, count unavailable")
            return

        _log(f"  Serverul nu raspunde. Incerc din nou...")
        _kill_port(port)
        time.sleep(3)

    # All retries exhausted
    _log("\nEROARE: Serverul nu poate porni dupa " + str(MAX_RETRIES + 1) + " incercari.")
    state["retries"] = state.get("retries", 0) + 1
    _save_state(state)
    _log("\nVerifica:")
    _log("  1. Logs: type logs\\ana_max.log")
    _log("  2. Port: netstat -ano | findstr :" + str(port))
    _log("  3. Ruleaza manual: venv\\Scripts\\python main.py --port " + str(port))
    sys.exit(1)


if __name__ == "__main__":
    main()
