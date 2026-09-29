"""
Test pentru BackgroundWatcher (Faza 1)
"""
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "ANA_MAX"))

from bridge.background_watcher import BackgroundWatcher

def main():
    print("=" * 60)
    print(" OS-27 Background Watcher Test (Phase 1)")
    print("=" * 60)

    watcher = BackgroundWatcher(poll_interval=2.0, rag_enabled=False)
    watcher.start()

    print("\n[*] Watcher activ. Copiaza ceva in clipboard sau schimba fereastra.")
    print("[*] Asteptam 10 secunde...\n")

    time.sleep(10)

    print("\n[STATUS]")
    print(watcher.get_status())

    print("\n[EVENTS]")
    events = watcher.get_events()
    if events:
        for e in events:
            print(f"  [{e['timestamp']}] {e['type']}: {str(e['data'])[:120]}")
    else:
        print("  Niciun eveniment detectat.")

    watcher.stop()

if __name__ == "__main__":
    main()
