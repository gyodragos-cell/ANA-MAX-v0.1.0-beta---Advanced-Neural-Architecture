import sys
import time
import os
import threading
sys.path.insert(0, "ANA_MAX")

from core.omnisense import start_omnisense, stop_omnisense, _omnisense_instance
from core.event_stream import event_stream

print("============================================================")
print(" Testare Omni-Sense Vision Agent (Proactive Background) ")
print("============================================================")

# Override alert cooldown for testing
start_omnisense()
_omnisense_instance._alert_cooldown = 1  # 1 second for test
_omnisense_instance._vision_interval = 2.0 # 2 seconds for test

print("[TEST] Agent started. Interval set to 2s.")

# Listen to SSE chat events
def listen_chat():
    try:
        def on_event(event):
            if event.get("type") == "conversation" and event.get("source") == "omni-sense":
                print(f"\n>>> [CHAT UI RECEIVED]: {event['data']['content']}\n")
        
        event_stream.subscribe(on_event)
        # Block until stopped
        while _omnisense_instance and _omnisense_instance._running_vision:
            time.sleep(1)
    except Exception as e:
        print(e)

t = threading.Thread(target=listen_chat, daemon=True)
t.start()

print("[TEST] Te rog sa deschizi un fisier cu textul 'Traceback (most recent call last)' pe ecran timp de 10 secunde.")
print("[TEST] Asteptam 15 secunde (Omni-Sense ruleaza in fundal)...")

try:
    time.sleep(15)
except KeyboardInterrupt:
    pass

stop_omnisense()
print("\n[TEST] GATA.")
