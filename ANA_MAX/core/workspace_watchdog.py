import os
import time
import logging
import threading
from typing import Set
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from core.event_stream import EventStream

logger = logging.getLogger(__name__)

class WorkspaceEventHandler(FileSystemEventHandler):
    def __init__(self, ignore_paths: Set[str], event_stream: EventStream):
        self.ignore_paths = ignore_paths
        self.event_stream = event_stream

    def _should_ignore(self, path: str) -> bool:
        normalized_path = os.path.normpath(path).lower()
        for ignored in self.ignore_paths:
            if ignored in normalized_path:
                return True
        return False

    def on_modified(self, event):
        if event.is_directory or self._should_ignore(event.src_path):
            return
        self._push("file_modified", event.src_path)

    def on_created(self, event):
        if event.is_directory or self._should_ignore(event.src_path):
            return
        self._push("file_created", event.src_path)

    def on_deleted(self, event):
        if event.is_directory or self._should_ignore(event.src_path):
            return
        self._push("file_deleted", event.src_path)
        
    def _push(self, action: str, path: str):
        try:
            self.event_stream.emit(
                event_type="system_state",
                source="watchdog",
                data={"action": action, "path": path}
            )
            logger.debug(f"[Watchdog] {action}: {path}")
        except Exception as e:
            logger.error(f"[Watchdog] Failed to push event: {e}")


class WorkspaceWatchdog:
    def __init__(self, watch_dir: str, event_stream: EventStream):
        self.watch_dir = watch_dir
        self.event_stream = event_stream
        self.observer = Observer()
        
        # Ignoram logurile si DB ca sa evitam bucla infinita
        self.ignore_paths = {
            os.path.normpath(".git").lower(),
            os.path.normpath("venv").lower(),
            os.path.normpath(".gemini").lower(),
            os.path.normpath("__pycache__").lower(),
            os.path.normpath("logs").lower(),
            os.path.normpath("events.db").lower(),
            os.path.normpath(".tmp").lower()
        }
        
        self.handler = WorkspaceEventHandler(self.ignore_paths, self.event_stream)
        self._running = False

    def start(self):
        if self._running:
            return
        logger.info(f"Pornire Watchdog pe: {self.watch_dir}")
        self.observer.schedule(self.handler, self.watch_dir, recursive=True)
        self.observer.start()
        self._running = True

    def stop(self):
        if not self._running:
            return
        self.observer.stop()
        self.observer.join()
        self._running = False
        logger.info("Watchdog oprit.")
