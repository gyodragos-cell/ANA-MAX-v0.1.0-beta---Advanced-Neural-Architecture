"""
HTTP Proxy pentru Gemini Grounding
===================================
Interceptează cererile HTTP de la Gemini și le trimite către ANA MAX MCP
"""
from flask import Flask, request, jsonify
import requests
import json

app = Flask(__name__)

# ANA MAX MCP endpoint
ANA_MAX_URL = "http://127.0.0.1:8766/mcp"

@app.route('/', methods=['POST'])
def proxy_to_ana():
    """Proxează cererile către ANA MAX"""
    try:
        # Obține cererea de la Gemini
        data = request.json
        
        # Extrage tool și arguments
        tool_name = data.get('tool', '')
        arguments = data.get('arguments', {})
        
        # Construiește cerere MCP JSON-RPC
        mcp_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        
        # Trimite către ANA MAX
        response = requests.post(ANA_MAX_URL, json=mcp_request, timeout=30)
        
        # Returnează rezultatul către Gemini
        return jsonify(response.json())
        
    except Exception as e:
        return jsonify({
            "error": str(e),
            "success": False
        }), 500

@app.route('/health', methods=['GET'])
def health():
    """Health check"""
    return jsonify({
        "status": "ok",
        "proxy": "gemini-proxy",
        "ana_max": ANA_MAX_URL
    })

if __name__ == '__main__':
    print("Gemini Proxy Running on http://127.0.0.1:8767")
    print("Proxying to ANA MAX: http://127.0.0.1:8766/mcp")
    app.run(host='127.0.0.1', port=8767, debug=False)
