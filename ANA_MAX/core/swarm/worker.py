import time
import uuid
import logging
import requests
from typing import List, Callable, Dict, Any

logger = logging.getLogger("ANA.SwarmWorker")

class SwarmWorker:
    def __init__(self, router_url: str = "http://localhost:8888", capabilities: List[str] = None):
        self.router_url = router_url
        self.node_id = f"node-{uuid.uuid4().hex[:8]}"
        self.capabilities = capabilities or ["vlm", "ocr", "heavy_rag"]
        self.handlers: Dict[str, Callable] = {}
        self.running = False
        
    def register_handler(self, task_type: str, handler: Callable):
        self.handlers[task_type] = handler
        if task_type not in self.capabilities:
            self.capabilities.append(task_type)
            
    def _register(self):
        try:
            res = requests.post(
                f"{self.router_url}/register", 
                json={"node_id": self.node_id, "capabilities": self.capabilities},
                timeout=5
            )
            res.raise_for_status()
            logger.info(f"Registered with Swarm Router as {self.node_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to register with router: {e}")
            return False

    def start(self):
        self.running = True
        
        while self.running and not self._register():
            logger.info("Retrying registration in 5 seconds...")
            time.sleep(5)
            
        while self.running:
            try:
                # Poll for tasks
                res = requests.get(f"{self.router_url}/task/poll/{self.node_id}", timeout=5)
                res.raise_for_status()
                data = res.json()
                
                if data.get("task_id"):
                    task_id = data["task_id"]
                    task_type = data["task_type"]
                    payload = data["payload"]
                    
                    logger.info(f"Received task {task_id} ({task_type})")
                    
                    if task_type in self.handlers:
                        try:
                            # Execute task
                            result = self.handlers[task_type](payload)
                            
                            # Submit result
                            requests.post(
                                f"{self.router_url}/task/result",
                                json={"task_id": task_id, "status": "completed", "result": result},
                                timeout=5
                            )
                            logger.info(f"Completed task {task_id}")
                        except Exception as e:
                            logger.error(f"Error processing task {task_id}: {e}")
                            requests.post(
                                f"{self.router_url}/task/result",
                                json={"task_id": task_id, "status": "failed", "result": str(e)},
                                timeout=5
                            )
                    else:
                        logger.error(f"No handler registered for task type {task_type}")
                else:
                    # No tasks, heartbeat and sleep
                    requests.post(f"{self.router_url}/heartbeat/{self.node_id}", timeout=2)
                    time.sleep(2)
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"Router connection error: {e}")
                time.sleep(5)
                
    def stop(self):
        self.running = False
        logger.info(f"Worker {self.node_id} stopping...")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Example usage:
    worker = SwarmWorker()
    
    def mock_vlm_handler(payload):
        logger.info("Processing mock VLM payload...")
        time.sleep(2)
        return {"intent": "testing_swarm", "error_visible": False, "details": "Mock analysis complete"}
        
    worker.register_handler("vlm", mock_vlm_handler)
    worker.start()
