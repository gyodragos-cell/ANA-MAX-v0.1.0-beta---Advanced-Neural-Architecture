import time
import threading
from collections import deque
from typing import List, Dict, Any
from tools.watchdog_bus import bus
import logging

logger = logging.getLogger(__name__)

class ReflexCore:
    """
    Short-term memory buffer for system reflexes.
    Provides immediate context of what happened recently in the OS.
    """
    def __init__(self, max_events: int = 100, max_age_seconds: int = 15):
        self._buffer = deque(maxlen=max_events)
        self._max_age = max_age_seconds
        self._lock = threading.Lock()
        
    def _on_event(self, event: Dict[str, Any]):
        """Callback for watchdog bus events."""
        with self._lock:
            # Inject a raw timestamp for internal age tracking
            event['_ts'] = time.time()
            self._buffer.append(event)
            
            # Allow the dispatcher to process it immediately
            from tools.reflex_dispatcher import dispatcher
            dispatcher.process_event(event)

    def start(self):
        """Subscribes to the event bus."""
        bus.subscribe(self._on_event)
        
    def get_recent_reflexes(self) -> List[Dict[str, Any]]:
        """
        Returns events that occurred within the max_age_seconds window.
        Called by Ollama Backend to gain immediate situational awareness.
        """
        current_time = time.time()
        recent = []
        with self._lock:
            for event in self._buffer:
                if current_time - event.get('_ts', 0) <= self._max_age:
                    # Strip internal timestamp before returning
                    clean_event = {k: v for k, v in event.items() if k != '_ts'}
                    recent.append(clean_event)
        return recent

# Global instance for the reflex pipeline
reflex_engine = ReflexCore()

if __name__ == '__main__':
    bus.start()
    reflex_engine.start()
    print("Reflex Core is listening. Send events to watchdog_bus to test.")
    time.sleep(60)
