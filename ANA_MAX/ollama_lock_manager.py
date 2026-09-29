#!/usr/bin/env python3
"""
Ollama Lock Manager - Previne pornirea multipla a Ollama local
Protejeaza GPU impotriva supraincalzirii prin prevenirea instantelor multiple
"""

import os
import sys
import time
import psutil
import requests
from pathlib import Path
from datetime import datetime

# Constants
OLLAMA_HOST = "127.0.0.1"
OLLAMA_PORT = 11434
OLLAMA_URL = f"http://{OLLAMA_HOST}:{OLLAMA_PORT}"
LOCK_FILE = Path(__file__).parent / ".ollama_session.lock"
OLLAMA_PROCESS_NAME = "ollama"

def check_ollama_running():
    """Verifica daca Ollama ruleaza deja"""
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=2)
        return response.status_code == 200
    except Exception:
        return False

def check_ollama_process():
    """Verifica daca procesul ollama.exe ruleaza"""
    for proc in psutil.process_iter(['name', 'pid', 'cmdline']):
        try:
            if OLLAMA_PROCESS_NAME in proc.info['name'].lower():
                return True, proc.info['pid'], proc.info['cmdline']
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return False, None, None

def create_lock_file():
    """Creeaza lock file cu informatii despre sesiune"""
    try:
        is_running, pid, cmdline = check_ollama_process()
        
        lock_info = {
            "created_at": datetime.now().isoformat(),
            "ollama_running": is_running,
            "pid": pid,
            "cmdline": cmdline,
            "host": OLLAMA_HOST,
            "port": OLLAMA_PORT
        }
        
        import json
        LOCK_FILE.write_text(json.dumps(lock_info, indent=2), encoding='utf-8')
        print(f"[OLLAMA LOCK] Lock file created: {LOCK_FILE}")
        return True
    except Exception as e:
        print(f"[OLLAMA LOCK] Failed to create lock file: {e}")
        return False

def check_lock_file():
    """Verifica daca exista lock file valid"""
    if not LOCK_FILE.exists():
        return False, None
    
    try:
        import json
        lock_data = json.loads(LOCK_FILE.read_text(encoding='utf-8'))
        
        # Verifica daca procesul din lock mai ruleaza
        if lock_data.get("pid"):
            try:
                proc = psutil.Process(lock_data["pid"])
                if proc.is_running():
                    return True, lock_data
            except psutil.NoSuchProcess:
                # Procesul nu mai exista, lock invalid
                print(f"[OLLAMA LOCK] Stale lock file detected (PID {lock_data['pid']} not running)")
                LOCK_FILE.unlink()
                return False, None
        
        # Verifica daca Ollama raspunde
        if check_ollama_running():
            return True, lock_data
        
        # Ollama nu raspunde, lock invalid
        print("[OLLAMA LOCK] Ollama not responding, removing stale lock")
        LOCK_FILE.unlink()
        return False, None
        
    except Exception as e:
        print(f"[OLLAMA LOCK] Error checking lock file: {e}")
        return False, None

def remove_lock_file():
    """Sterge lock file"""
    try:
        if LOCK_FILE.exists():
            LOCK_FILE.unlink()
            print(f"[OLLAMA LOCK] Lock file removed: {LOCK_FILE}")
            return True
        return False
    except Exception as e:
        print(f"[OLLAMA LOCK] Failed to remove lock file: {e}")
        return False

def acquire_lock():
    """Incearca sa obtina lock pentru sesiune Ollama"""
    has_lock, lock_data = check_lock_file()
    
    if has_lock:
        print(f"[OLLAMA LOCK] Lock already exists!")
        print(f"[OLLAMA LOCK] Created: {lock_data.get('created_at')}")
        print(f"[OLLAMA LOCK] PID: {lock_data.get('pid')}")
        
        # Verifica daca Ollama ruleaza efectiv
        if check_ollama_running():
            print("[OLLAMA LOCK] Ollama is already running - BLOCKING duplicate start")
            print("[OLLAMA LOCK] To restart: 1. Stop current session 2. Lock will auto-release")
            return False
        else:
            print("[OLLAMA LOCK] Ollama not running despite lock - cleaning up")
            remove_lock_file()
            return acquire_lock()  # Retry
    
    # Creeaza lock nou
    if create_lock_file():
        print("[OLLAMA LOCK] Lock acquired successfully")
        return True
    return False

def release_lock():
    """Elibereaza lock la inchiderea sesiuni"""
    if remove_lock_file():
        print("[OLLAMA LOCK] Lock released successfully")
        return True
    return False

def force_cleanup():
    """Fortare cleanup lock si procese Ollama zombie"""
    print("[OLLAMA LOCK] Force cleanup initiated")
    
    # Sterge lock file
    remove_lock_file()
    
    # Omoara TOATE procesele Ollama si llama-server zombie
    for proc in psutil.process_iter(['name', 'pid']):
        try:
            name = proc.info['name'].lower()
            if "ollama" in name or "llama-server" in name:
                pid = proc.info['pid']
                p = psutil.Process(pid)
                p.terminate()
                time.sleep(0.5)
                if p.is_running():
                    p.kill()
                print(f"[OLLAMA LOCK] Killed process: {name} (PID {pid})")
        except (psutil.NoSuchProcess, psutil.AccessDenied, Exception):
            continue
    
    print("[OLLAMA LOCK] Force cleanup complete")

def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python ollama_lock_manager.py <command>")
        print("Commands: acquire, release, check, force-cleanup")
        return 1
    
    command = sys.argv[1].lower()
    
    if command == "acquire":
        success = acquire_lock()
        return 0 if success else 1
    elif command == "release":
        success = release_lock()
        return 0 if success else 1
    elif command == "check":
        has_lock, lock_data = check_lock_file()
        if has_lock:
            print(f"[OLLAMA LOCK] Active lock found: {lock_data}")
            return 0
        else:
            print("[OLLAMA LOCK] No active lock")
            return 1
    elif command == "force-cleanup":
        force_cleanup()
        return 0
    else:
        print(f"Unknown command: {command}")
        return 1

if __name__ == "__main__":
    sys.exit(main())