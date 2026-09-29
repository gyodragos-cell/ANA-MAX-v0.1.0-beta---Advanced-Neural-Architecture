import asyncio
import json
import uuid
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
from playwright.async_api import async_playwright

PORT = 11434
DUCK_URL = "https://duck.ai"

def _log(msg):
    print(f"[duck_pw_api] {msg}", flush=True)

class DuckAPI:
    def __init__(self):
        self.queue = asyncio.Queue()
        self.browser = None
        self.page = None
        self.pw = None

    async def start(self):
        _log("Pornesc Playwright API Headless...")
        self.pw = await async_playwright().start()
        self.browser = await self.pw.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"]
        )
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()
        
        _log(f"Navigare la {DUCK_URL} pentru bypass anti-bot...")
        await self.page.goto(DUCK_URL, wait_until="domcontentloaded")
        _log("Sistem pregatit! Astept cereri.")
        
        while True:
            task = await self.queue.get()
            try:
                await self._process_chat(task)
            except Exception as e:
                _log(f"Eroare chat: {e}")
                task["error"] = str(e)
                task["done"].set()
            self.queue.task_done()

    async def _process_chat(self, task):
        prompt = task["prompt"]
        _log(f"Cer VQD token pentru request...")
        
        token_res = await self.context.request.get(
            "https://duck.ai/duckchat/v1/auth/token",
            headers={"x-vqd-accept": "1"}
        )
        
        if not token_res.ok:
            task["error"] = f"VQD fail: {token_res.status}"
            task["done"].set()
            return
            
        headers = token_res.headers
        vqd_token = headers.get("x-vqd-4") or headers.get("x-vqd-3")
        
        if not vqd_token:
            task["error"] = "Nu am gasit x-vqd-4 in header."
            task["done"].set()
            return

        _log("Trimit chat request cu VQD...")
        payload = {
            "model": "gpt-5.4-nano",
            "metadata": {"toolChoice": {"NewsSearch": False, "VideosSearch": False, "LocalSearch": False, "WeatherForecast": False}},
            "messages": [{"role": "user", "content": prompt}],
            "canUseTools": True,
            "reasoningEffort": "none",
            "durableStream": {
                "messageId": str(uuid.uuid4()),
                "conversationId": str(uuid.uuid4()),
                "publicKey": {
                    "alg": "RSA-OAEP-256", "e": "AQAB", "ext": True, "key_ops": ["encrypt"], "kty": "RSA",
                    "n": "pANL1PLHhmGepTU9B-E7ypklzrt5i6EAuE1YnDWjqPqsZm9pW4M62f4M_4sauzO-R3_kMhG1gQgTAKNsn_dSdsJxAdcXFGEs_87rzq2UXHm2Tpak0ag-PuDR0cuW95O4PHZFmoliYEALme6VSzyrc3gYbvz9s7u-Fl5jh9foXfJWWKp1yhv5MQJlgDR1Oy5LCqq686ToJsvjycDfJLbNP-hnFewjLgZda_Z-BQgDXOH7Z9IEsZvo-57Xo3aOsve5jzPIixKakCYqY2eE0td7CYrVMnLAVCn7KgEgsTMlvTBGH0CjT5OrEUbNvaCASrPMCNaIamRtbTwvOb6hZA8vsQ",
                    "use": "enc"
                }
            }
        }
        
        chat_res = await self.context.request.post(
            "https://duck.ai/duckchat/v1/chat",
            headers={
                "x-vqd-4": vqd_token,
                "Accept": "text/event-stream"
            },
            data=payload
        )
        
        if not chat_res.ok:
            task["error"] = f"Chat fail: {chat_res.status}"
            task["done"].set()
            return
            
        sse_text = await chat_res.text()
        
        # Parsam SSE
        lines = []
        for line in sse_text.splitlines():
            if line.startswith("data: "):
                d = line[6:]
                if d == "[DONE]": continue
                try:
                    j = json.loads(d)
                    if "message" in j:
                        lines.append(j["message"])
                except: pass
                
        task["result"] = "".join(lines)
        _log(f"Raspuns parsat ok, lungime {len(task['result'])}")
        task["done"].set()

api = DuckAPI()

class BridgeHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args): pass
    
    def do_GET(self):
        if self.path == "/api/tags":
            self._json(200, {"models": [{"name": "duck-ai-model:latest"}]})
        else:
            self.send_response(200); self.end_headers()

    def do_POST(self):
        if self.path == "/api/chat":
            length = int(self.headers.get("Content-Length", 0))
            data = json.loads(self.rfile.read(length))
            messages = data.get("messages", [])
            if not messages: return self._json(400, {"error": "No messages"})
            
            prompt = messages[-1]["content"]
            done = threading.Event()
            task = {"prompt": prompt, "done": done, "result": None, "error": None}
            
            asyncio.run_coroutine_threadsafe(api.queue.put(task), main_loop)
            
            if done.wait(timeout=90):
                if task["error"]:
                    self._json(500, {"error": task["error"]})
                else:
                    self._json(200, {
                        "model": "duck-ai-model:latest",
                        "message": {"role": "assistant", "content": task["result"]},
                        "done": True
                    })
            else:
                self._json(500, {"error": "Timeout"})

    def _json(self, status, obj):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(obj).encode())

main_loop = None
def start_async_loop():
    global main_loop
    main_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(main_loop)
    main_loop.run_until_complete(api.start())

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else PORT
    threading.Thread(target=start_async_loop, daemon=True).start()
    _log(f"Server OLLAMA API Duck.ai pe portul {port}")
    HTTPServer(("127.0.0.1", port), BridgeHandler).serve_forever()
