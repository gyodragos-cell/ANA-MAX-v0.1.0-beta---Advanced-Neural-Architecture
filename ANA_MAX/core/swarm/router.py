import time
import uuid
import logging
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel

logger = logging.getLogger("ANA.SwarmRouter")

app = FastAPI(title="ANA Local Swarm Router")

# In-memory node registry
# key: node_id -> dict: {"status": "idle"|"busy", "capabilities": [...], "last_seen": float}
_nodes: Dict[str, Dict[str, Any]] = {}

# In-memory task queue
# key: task_id -> dict: {"status": "pending"|"processing"|"completed"|"failed", "payload": Any, "result": Any}
_tasks: Dict[str, Dict[str, Any]] = {}

class NodeRegistration(BaseModel):
    node_id: str
    capabilities: list[str]

class TaskRequest(BaseModel):
    task_type: str
    payload: Any

@app.post("/register")
async def register_node(req: NodeRegistration):
    _nodes[req.node_id] = {
        "status": "idle",
        "capabilities": req.capabilities,
        "last_seen": time.time()
    }
    logger.info(f"Node registered: {req.node_id} with caps {req.capabilities}")
    return {"status": "ok"}

@app.post("/heartbeat/{node_id}")
async def heartbeat(node_id: str):
    if node_id in _nodes:
        _nodes[node_id]["last_seen"] = time.time()
        return {"status": "ok"}
    raise HTTPException(status_code=404, detail="Node not found")

@app.post("/task")
async def submit_task(req: TaskRequest):
    task_id = str(uuid.uuid4())
    _tasks[task_id] = {
        "task_type": req.task_type,
        "payload": req.payload,
        "status": "pending",
        "result": None
    }
    logger.info(f"Task {task_id} ({req.task_type}) queued.")
    return {"task_id": task_id}

@app.get("/task/poll/{node_id}")
async def poll_tasks(node_id: str):
    if node_id not in _nodes:
        raise HTTPException(status_code=404, detail="Node not registered")
    
    _nodes[node_id]["last_seen"] = time.time()
    node_caps = _nodes[node_id]["capabilities"]

    # Find pending task that matches capabilities
    for tid, tdata in _tasks.items():
        if tdata["status"] == "pending" and tdata["task_type"] in node_caps:
            tdata["status"] = "processing"
            tdata["assigned_node"] = node_id
            _nodes[node_id]["status"] = "busy"
            logger.info(f"Assigned task {tid} to node {node_id}")
            return {"task_id": tid, "task_type": tdata["task_type"], "payload": tdata["payload"]}
    
    return {"task_id": None}

class TaskResult(BaseModel):
    task_id: str
    status: str
    result: Any

@app.post("/task/result")
async def submit_result(res: TaskResult):
    if res.task_id not in _tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    tdata = _tasks[res.task_id]
    tdata["status"] = res.status
    tdata["result"] = res.result
    
    node_id = tdata.get("assigned_node")
    if node_id and node_id in _nodes:
        _nodes[node_id]["status"] = "idle"
        
    logger.info(f"Task {res.task_id} completed with status {res.status}")
    return {"status": "ok"}

@app.get("/task/status/{task_id}")
async def get_task_status(task_id: str):
    if task_id not in _tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    tdata = _tasks[task_id]
    return {"task_id": task_id, "status": tdata["status"], "result": tdata["result"]}

def start_router(host="0.0.0.0", port=8888):
    import uvicorn
    logger.info(f"Starting Swarm Router on {host}:{port}")
    uvicorn.run(app, host=host, port=port)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    start_router()
