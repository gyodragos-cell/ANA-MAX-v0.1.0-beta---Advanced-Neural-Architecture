import os
import time
import logging
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

class WorkspaceEventHandler(FileSystemEventHandler):
    def __init__(self, log_file: Path):
        self.log_file = log_file
        self.ignore_patterns = ['.git', 'venv', '__pycache__', 'logs', '.ana_running']

    def _should_ignore(self, path: str) -> bool:
        for p in self.ignore_patterns:
            if p in path:
                return True
        return False

    def _log_event(self, event_type: str, path: str):
        if self._should_ignore(path):
            return
        
        # Ensure log directory exists
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        msg = f"[{timestamp}] EVENT: {event_type} -> {path}\n"
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(msg)
            logging.info(f"FS Event logged: {event_type} - {path}")
        except Exception as e:
            logging.error(f"Failed to log fs event: {e}")

    def on_modified(self, event):
        if not event.is_directory:
            self._log_event("MODIFIED", event.src_path)

    def on_created(self, event):
        if not event.is_directory:
            self._log_event("CREATED", event.src_path)

    def on_deleted(self, event):
        if not event.is_directory:
            self._log_event("DELETED", event.src_path)

def start_watchdog(workspace_path: str, log_file_path: str):
    event_handler = WorkspaceEventHandler(Path(log_file_path))
    observer = Observer()
    observer.schedule(event_handler, workspace_path, recursive=True)
    observer.start()
    logging.info(f"Watchdog started monitoring: {workspace_path}")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        logging.info("Watchdog stopped.")
    observer.join()

if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parents[3] # ANA_MAX is parents[2], workspace is parents[3]
    ana_max_dir = base_dir / "ANA_MAX"
    log_file = ana_max_dir / "logs" / "fs_events.log"
    
    start_watchdog(str(base_dir), str(log_file))
