import threading
import time
import requests
import json
import logging

from router import start_router, _nodes, _tasks
from worker import SwarmWorker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TestSwarm")

def test_swarm_integration():
    logger.info("1. Starting Swarm Router in background...")
    router_thread = threading.Thread(target=start_router, kwargs={"host": "127.0.0.1", "port": 8889}, daemon=True)
    router_thread.start()
    time.sleep(2) # wait for startup

    logger.info("2. Starting Swarm Worker in background...")
    worker = SwarmWorker(router_url="http://127.0.0.1:8889", capabilities=["vlm"])
    
    def mock_vlm(payload):
        logger.info(f"Worker processing VLM payload: {payload['prompt']}")
        return {"intent": "test_intent", "error_visible": True, "details": "Simulated error"}
        
    worker.register_handler("vlm", mock_vlm)
    
    worker_thread = threading.Thread(target=worker.start, daemon=True)
    worker_thread.start()
    time.sleep(2) # wait for registration
    
    logger.info("3. Verifying Node Registration...")
    assert len(_nodes) > 0, "No nodes registered!"
    logger.info("Node registered successfully.")
    
    logger.info("4. Submitting VLM Task to Router...")
    payload = {"image_b64": "fake_base64", "prompt": "What is this?"}
    res = requests.post("http://127.0.0.1:8889/task", json={"task_type": "vlm", "payload": payload})
    task_id = res.json()["task_id"]
    
    logger.info("5. Waiting for task completion...")
    for _ in range(5):
        status_res = requests.get(f"http://127.0.0.1:8889/task/status/{task_id}")
        data = status_res.json()
        if data["status"] == "completed":
            logger.info(f"Task completed successfully! Result: {data['result']}")
            assert data["result"]["intent"] == "test_intent"
            break
        time.sleep(1)
    else:
        assert False, "Task did not complete in time"
        
    worker.stop()
    logger.info("Swarm Integration Test Passed!")

if __name__ == "__main__":
    test_swarm_integration()
