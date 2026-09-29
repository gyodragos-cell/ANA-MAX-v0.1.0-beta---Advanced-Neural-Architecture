import threading
import uuid
import time
import logging
from typing import Any, Dict
from tools.base import registry
from tools.watchdog_bus import EventBus

logger = logging.getLogger(__name__)

class AsyncDispatcher:
    """Kernel asincron pentru rularea task-urilor (uneltelor) in background."""
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(AsyncDispatcher, cls).__new__(cls)
                cls._instance._init()
            return cls._instance

    def _init(self):
        self.active_tasks: Dict[str, Dict[str, Any]] = {}
        self.bus = EventBus()
        self.bus.start()

    def dispatch(self, tool_name: str, kwargs: Dict[str, Any], wait_ms: int = 0) -> Dict[str, Any]:
        """
        Dispatches a tool execution. If it finishes within wait_ms, returns result directly.
        Otherwise, returns a TaskID immediately and runs in background.
        """
        task_id = f"task-{uuid.uuid4().hex[:8]}"
        result_container = {"done": False, "result": None, "error": None}
        
        def _worker():
            start_time = time.time()
            try:
                logger.info(f"[ASYNC] Task {task_id} started: {tool_name}")
                self.bus.publish("AsyncDispatcher", "task_started", {"task_id": task_id, "tool": tool_name})
                
                # Execute tool
                res = registry.execute(tool_name, **kwargs)
                
                result_container["result"] = res
                result_container["done"] = True
                elapsed = time.time() - start_time
                
                payload = {
                    "task_id": task_id,
                    "tool": tool_name,
                    "success": res.is_success,
                    "data": res.data,
                    "elapsed_sec": round(elapsed, 2)
                }
                
                logger.info(f"[ASYNC] Task {task_id} completed in {elapsed:.2f}s")
                self.bus.publish("AsyncDispatcher", "task_completed", payload)
                
            except Exception as e:
                result_container["error"] = str(e)
                result_container["done"] = True
                logger.error(f"[ASYNC] Task {task_id} failed: {e}")
                self.bus.publish("AsyncDispatcher", "task_failed", {"task_id": task_id, "tool": tool_name, "error": str(e)})
            finally:
                if task_id in self.active_tasks:
                    del self.active_tasks[task_id]

        self.active_tasks[task_id] = {
            "tool": tool_name,
            "status": "running",
            "start_time": time.time()
        }
        
        t = threading.Thread(target=_worker, daemon=True)
        t.start()
        
        # Wait up to wait_ms
        if wait_ms > 0:
            t.join(timeout=wait_ms / 1000.0)
        
        if result_container["done"]:
            # Finished within wait time
            if result_container["error"]:
                raise RuntimeError(result_container["error"])
            return {"async": False, "result": result_container["result"]}
            
        return {
            "async": True, 
            "task_id": task_id, 
            "message": f"Task {tool_name} trimis in background. Vei fi notificat cand se termina (task_id: {task_id})."
        }

    def get_status(self, task_id: str) -> Dict[str, Any]:
        if task_id in self.active_tasks:
            return self.active_tasks[task_id]
        return {"status": "unknown_or_finished"}

    def spawn_worker(self, name: str, command: str) -> str:
        """
        Spawns a blind autonomous worker (subprocess) to execute a command without LLM overhead.
        """
        import subprocess
        task_id = f"worker-{uuid.uuid4().hex[:8]}"
        
        def _process_worker():
            start_time = time.time()
            try:
                self.bus.publish("Swarm", "worker_started", {"task_id": task_id, "name": name, "command": command})
                self.active_tasks[task_id] = {"name": name, "status": "running", "start_time": start_time}
                
                # Execute command
                proc = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                stdout, stderr = proc.communicate()
                
                elapsed = time.time() - start_time
                success = proc.returncode == 0
                
                payload = {
                    "task_id": task_id,
                    "name": name,
                    "success": success,
                    "stdout": stdout,
                    "stderr": stderr,
                    "elapsed_sec": round(elapsed, 2)
                }
                self.bus.publish("Swarm", "worker_completed", payload)
            except Exception as e:
                self.bus.publish("Swarm", "worker_failed", {"task_id": task_id, "name": name, "error": str(e)})
            finally:
                if task_id in self.active_tasks:
                    del self.active_tasks[task_id]

        t = threading.Thread(target=_process_worker, daemon=True)
        t.start()
        return task_id

    def kill_worker(self, task_id: str) -> bool:
        if task_id in self.active_tasks:
            # We can't cleanly kill the subprocess from here easily without storing the proc object.
            # For this MVP, we just mark it as killed.
            self.active_tasks[task_id]["status"] = "killed"
            self.bus.publish("Swarm", "worker_killed", {"task_id": task_id})
            del self.active_tasks[task_id]
            return True
        return False

def get_dispatcher():
    return AsyncDispatcher()
