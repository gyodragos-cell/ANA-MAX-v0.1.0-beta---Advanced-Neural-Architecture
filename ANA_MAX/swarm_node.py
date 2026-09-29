"""
ANA MAX - Local Swarm Node (P2P Worker)
=======================================
Ruleaza acest script pe orice PC/Dispozitiv din retea pentru a-l transforma intr-un nod de procesare.
Orchestratorul (laptopul principal) va trimite task-uri grele (comenzi, tool-uri, inferente) catre acest nod.
"""

import sys
import os
import uuid
import time
import threading
import subprocess
from flask import Flask, request, jsonify
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] Node: %(message)s")

# Simple in-memory job store
jobs = {}

@app.route('/ping', methods=['GET'])
def ping():
    return jsonify({
        "status": "online",
        "node_id": "swarm_node_" + os.environ.get("COMPUTERNAME", "unknown"),
        "capabilities": ["shell", "python"]
    })

def run_job_background(job_id, command):
    jobs[job_id]["status"] = "running"
    jobs[job_id]["start_time"] = time.time()
    
    try:
        proc = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, stderr = proc.communicate()
        
        jobs[job_id]["status"] = "completed" if proc.returncode == 0 else "failed"
        jobs[job_id]["stdout"] = stdout
        jobs[job_id]["stderr"] = stderr
        jobs[job_id]["exit_code"] = proc.returncode
    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)
        
    jobs[job_id]["end_time"] = time.time()
    logging.info(f"Job {job_id} finished with status: {jobs[job_id]['status']}")

@app.route('/jobs', methods=['POST'])
def submit_job():
    data = request.json
    if not data or "command" not in data:
        return jsonify({"error": "Missing 'command' in payload"}), 400
        
    job_id = f"job-{uuid.uuid4().hex[:8]}"
    command = data["command"]
    
    jobs[job_id] = {
        "id": job_id,
        "command": command,
        "status": "pending",
        "stdout": None,
        "stderr": None,
        "error": None
    }
    
    t = threading.Thread(target=run_job_background, args=(job_id, command), daemon=True)
    t.start()
    
    logging.info(f"Accepted job {job_id}: {command}")
    return jsonify({"job_id": job_id, "status": "pending"}), 202

@app.route('/jobs/<job_id>', methods=['GET'])
def get_job(job_id):
    if job_id not in jobs:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(jobs[job_id])

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description="ANA MAX Swarm Node")
    parser.add_argument("--port", type=int, default=8766, help="Port to listen on")
    args = parser.parse_args()
    
    logging.info(f"Starting Swarm Node on port {args.port}...")
    app.run(host="0.0.0.0", port=args.port, threaded=True)
