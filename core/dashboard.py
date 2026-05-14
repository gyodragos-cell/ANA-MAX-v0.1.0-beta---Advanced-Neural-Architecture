import os
import json
import logging
from flask import Flask, render_template_string, jsonify
from pathlib import Path

# Configurare logging minimalist pentru dashboard
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ANA_WhiteHat_UI")

app = Flask(__name__)

# Template HTML minimalist cu Tailwind CSS
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="ro">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ANA White Hat v16 - Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        .status-pulse { animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite; }
    </style>
</head>
<body class="bg-gray-900 text-green-400 font-mono">
    <div class="container mx-auto p-6">
        <header class="flex justify-between items-center mb-10 border-b border-green-900 pb-4">
            <h1 class="text-3xl font-bold tracking-tighter">A.N.A. <span class="text-white">WHITE HAT</span> v16.0</h1>
            <div class="flex items-center space-x-2">
                <div class="w-3 h-3 bg-green-500 rounded-full status-pulse"></div>
                <span class="text-sm">SYSTEM ACTIVE</span>
            </div>
        </header>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
            <div class="bg-black border border-green-900 p-4 rounded shadow-lg">
                <h3 class="text-gray-500 text-xs uppercase mb-2">Evoluții Detectate</h3>
                <p id="evolution-count" class="text-4xl font-bold text-white">0</p>
            </div>
            <div class="bg-black border border-green-900 p-4 rounded shadow-lg">
                <h3 class="text-gray-500 text-xs uppercase mb-2">Dataset FT (JSONL)</h3>
                <p id="dataset-size" class="text-4xl font-bold text-white">0</p>
            </div>
            <div class="bg-black border border-green-900 p-4 rounded shadow-lg">
                <h3 class="text-gray-500 text-xs uppercase mb-2">Status Critical Thinking</h3>
                <p class="text-2xl font-bold text-green-500 italic">ARMED</p>
            </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div class="bg-black border border-green-900 p-4 rounded h-96 overflow-y-auto">
                <h3 class="text-white mb-4 border-b border-green-900 pb-2">Activitate Recenta (Ghost Logs)</h3>
                <div id="logs-container" class="space-y-2 text-xs">
                    <!-- Logs will be populated here -->
                </div>
            </div>
            <div class="bg-black border border-green-900 p-4 rounded h-96">
                <h3 class="text-white mb-4 border-b border-green-900 pb-2">Swarm Status</h3>
                <div class="space-y-4">
                    <div class="flex justify-between items-center bg-gray-800 p-2 rounded">
                        <span>Architect</span>
                        <span class="text-green-500 text-xs">[ONLINE]</span>
                    </div>
                    <div class="flex justify-between items-center bg-gray-800 p-2 rounded text-gray-500">
                        <span>Security Audit</span>
                        <span class="text-xs">[WAITING FOR TASK]</span>
                    </div>
                    <div class="flex justify-between items-center bg-gray-800 p-2 rounded text-gray-500">
                        <span>QA Engineer</span>
                        <span class="text-xs">[WAITING FOR TASK]</span>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        function updateStats() {
            fetch('/api/stats')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('evolution-count').innerText = data.evolution_count;
                    document.getElementById('dataset-size').innerText = data.dataset_size;
                    
                    const logsContainer = document.getElementById('logs-container');
                    logsContainer.innerHTML = '';
                    data.recent_logs.forEach(log => {
                        const div = document.createElement('div');
                        div.className = 'border-l-2 border-green-700 pl-2 mb-2';
                        div.innerHTML = `<span class="text-gray-600">[${log.time}]</span> <span class="text-yellow-600">${log.type}</span>: ${log.data}`;
                        logsContainer.appendChild(div);
                    });
                });
        }

        setInterval(updateStats, 5000);
        updateStats();
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(DASHBOARD_HTML)

@app.route('/api/stats')
def get_stats():
    # Simulăm citirea datelor din fișierele reale
    evolution_log = Path("logs/evolution.jsonl")
    dataset_file = Path("dataset/fine_tuning_v16.jsonl")
    
    evolution_count = 0
    recent_logs = []
    
    if evolution_log.exists():
        with open(evolution_log, "r", encoding="utf-8") as f:
            lines = f.readlines()
            evolution_count = len(lines)
            # Ultimele 10 log-uri
            for line in lines[-10:]:
                try:
                    ev = json.loads(line)
                    recent_logs.append({
                        "time": ev.get("timestamp", "").split("T")[1][:8],
                        "type": ev.get("type", "EVENT"),
                        "data": str(ev.get("data", ""))[:100]
                    })
                except: continue
    
    dataset_size = 0
    if dataset_file.exists():
        with open(dataset_file, "r", encoding="utf-8") as f:
            dataset_size = len(f.readlines())
            
    return jsonify({
        "evolution_count": evolution_count,
        "dataset_size": dataset_size,
        "recent_logs": recent_logs[::-1] # Cele mai noi primele
    })

def run_dashboard(port=5000):
    """Rulează serverul Dashboard fără să blocheze procesul principal."""
    # Dezactivăm output-ul Werkzeug pentru a nu polua terminalul de chat
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

if __name__ == "__main__":
    run_dashboard()
