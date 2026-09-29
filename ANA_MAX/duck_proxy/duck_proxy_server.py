import os
import sys
import json
import time
import requests
import urllib3
from http.server import BaseHTTPRequestHandler, HTTPServer

# Adauga path-ul corect pentru import-ul ANA modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.backend_manager import get_backend_manager, BackendType
from core.session_logger import log_action, log_result, log_error, log_next_step

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 11434

# Initializeaza Backend Manager
backend_manager = get_backend_manager()

# DurableStream static din exemplul functional
DURABLE_STREAM = {
    "messageId": "1f216817-bd2a-43c9-b824-ba74e28acc29",
    "conversationId": "0747eeb3-0f68-4ebe-a9f4-2ccaafa4e246",
    "publicKey": {
        "alg": "RSA-OAEP-256",
        "e": "AQAB",
        "ext": True,
        "key_ops": ["encrypt"],
        "kty": "RSA",
        "n": "pANL1PLHhmGepTU9B-E7ypklzrt5i6EAuE1YnDWjqPqsZm9pW4M62f4M_4sauzO-R3_kMhG1gQgTAKNsn_dSdsJxAdcXFGEs_87rzq2UXHm2Tpak0ag-PuDR0cuW95O4PHZFmoliYEALme6VSzyrc3gYbvz9s7u-Fl5jh9foXfJWWKp1yhv5MQJlgDR1Oy5LCqq686ToJsvjycDfJLbNP-hnFewjLgZda_Z-BQgDXOH7Z9IEsZvo-57Xo3aOsve5jzPIixKakCYqY2eE0td7CYrVMnLAVCn7KgEgsTMlvTBGH0CjT5OrEUbNvaCASrPMCNaIamRtbTwvOb6hZA8vsQ",
        "use": "enc"
    }
}

class FakeOllamaHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        if self.path == "/api/tags":
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {"models": [{"name": "duck-ai-model:latest"}]}
            self.wfile.write(json.dumps(response).encode())
        elif self.path == "/health":
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            status_report = backend_manager.get_status_report()
            self.wfile.write(json.dumps(status_report).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/api/chat":
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            req = json.loads(post_data)
            
            raw_messages = req.get("messages", [])
            messages = []
            system_prompt = ""
            for m in raw_messages:
                if m.get("role") == "system":
                    system_prompt += m.get("content", "") + "\n\n"
                else:
                    messages.append(m)
            
            if system_prompt and messages and messages[0].get("role") == "user":
                messages[0]["content"] = f"[{system_prompt.strip()}]\n\n{messages[0]['content']}"
            elif system_prompt:
                messages.insert(0, {"role": "user", "content": system_prompt.strip()})
            
            # Foloseste Backend Manager cu auto-fallback
            result = backend_manager.send_chat_request(messages)
            
            if result["success"]:
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                
                ollama_chunk = {
                    "model": "duck-ai-model:latest",
                    "message": {"role": "assistant", "content": result["content"]},
                    "done": True
                }
                self.wfile.write((json.dumps(ollama_chunk) + "\n").encode())
                print(f"[+] Response via {result['backend']} (quality: {result['quality_score']:.2f})")
            else:
                self.send_response(500)
                self.end_headers()
                error_response = {"error": result["error"], "backend": result["backend"]}
                self.wfile.write(json.dumps(error_response).encode())
                print(f"[-] All backends failed: {result['error']}")
        else:
            self.send_response(404)
            self.end_headers()

def run(server_class=HTTPServer, handler_class=FakeOllamaHandler, port=PORT):
    server_address = ('127.0.0.1', port)
    httpd = server_class(server_address, handler_class)
    print(f"[*] FAKE OLLAMA (Duck.ai Proxy) is running on http://127.0.0.1:{port}")
    print("[*] Using static headers from Charles Proxy (NO Playwright)")
    print("[*] Leave this console open.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    run()
