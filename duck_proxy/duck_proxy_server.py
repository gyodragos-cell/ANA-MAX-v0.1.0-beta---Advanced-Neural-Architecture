"""
ANA MAX - Duck.ai Proxy v7.0 (DOM Polling & Clipboard Fallback)
================================================================
Arhitectura:
  1. Chrome REAL cu profil persistent
  2. HEADFUL pentru rezolvare captcha manuala
  3. FARA interceptare de retea (fara erori SSE sau "No data found")
  4. Polling pe DOM pentru a astepta finalizarea generarii
  5. Extrage textul din Clipboard sau din DOM Diff pastrand formatarea
"""

import asyncio
import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from playwright.async_api import async_playwright

PORT       = int(sys.argv[1]) if len(sys.argv) > 1 else 11434
PROFILE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".chrome_profile")
DUCK_URL    = "https://duck.ai"
HEADFUL     = True  

def _log(msg): print(f"[duck] {msg}", flush=True)

class DuckWorker:
    def __init__(self):
        self.queue   = asyncio.Queue()
        self.context = None
        self.page    = None
        self.pw      = None

    async def start(self):
        _log("Pornesc Playwright (DOM Polling)...")
        self.pw = await async_playwright().start()
        await self._init_browser()
        while True:
            task = await self.queue.get()
            try:    
                await self._chat(task)
            except Exception as e:
                _log(f"EROARE chat: {e}")
                task["error"] = str(e)
                task["done"].set()
                await self._init_browser()
            self.queue.task_done()

    async def _init_browser(self):
        if self.context:
            try: await self.context.close()
            except: pass

        os.makedirs(PROFILE_DIR, exist_ok=True)
        _log(f"Lansare Chrome REAL {'headful' if HEADFUL else 'headless'} | profil: {PROFILE_DIR}")

        self.context = await self.pw.chromium.launch_persistent_context(
            user_data_dir=PROFILE_DIR,
            channel="chrome",
            headless=not HEADFUL,
            args=["--disable-blink-features=AutomationControlled", "--no-first-run"],
            ignore_default_args=["--enable-automation"],
            permissions=['clipboard-read', 'clipboard-write']
        )

        self.page = self.context.pages[0] if self.context.pages else await self.context.new_page()

        _log(f"Navigare la {DUCK_URL}...")
        await self.page.goto(DUCK_URL, wait_until="domcontentloaded")

        try:
            btn = self.page.locator('button:has-text("Continue"), button:has-text("Get Started"), button:has-text("I Agree")').first
            if await btn.count() > 0:
                await btn.click(timeout=2000)
                _log("[OK] Am apasat pe butonul Continue/Agree initial.")
        except: pass

        _log("Astept textarea enabled...")
        try:
            await self.page.wait_for_function(
                "() => { const t = document.querySelector('textarea[name=\"user-prompt\"]'); return t && !t.disabled; }",
                timeout=30000
            )
            _log("[OK] Textarea enabled. Sesiune valida!")
        except:
            _log("[WARN] Textarea inca disabled. Asteptam rezolvare challenge (manual).")

    async def _chat(self, task):
        prompt = task["prompt"]

        box = self.page.locator("textarea[name='user-prompt']")
        try:
            await box.wait_for(state="visible", timeout=15000)
        except:
            task["error"] = "Textarea invizibila - ecran turnstile sau agree"
            task["done"].set()
            return

        is_enabled = await box.is_enabled()
        if not is_enabled:
            task["error"] = "Textarea disabled - sesiune invalida / challenge activ"
            task["done"].set()
            return

        old_text = await self.page.evaluate('document.body.innerText')
        try:
            await self.page.evaluate('navigator.clipboard.writeText("")')
        except: pass

        await box.click()
        await self.page.keyboard.press("Control+a")
        await box.fill(prompt)
        _log(f"Prompt scris: {prompt[:60]}...")

        await box.press("Enter")
        _log("Enter apasat. Astept raspuns (DOM polling)...")

        last_text = ""
        stable_count = 0
        waited = 0
        timeout_s = 60
        
        while waited < timeout_s:
            await self.page.wait_for_timeout(1000)
            waited += 1
            current_text = await self.page.evaluate('document.body.innerText')
            
            if current_text != old_text:
                if current_text == last_text:
                    stable_count += 1
                    if stable_count >= 3: 
                        break
                else:
                    stable_count = 0
            last_text = current_text

        if waited >= timeout_s:
            _log("[WARN] Timeout asteptare generare, incerc extragere.")
        else:
            _log("[OK] Generare finalizata in UI.")

        # Extragere via Clipboard (pastreaza perfect Markdown)
        try:
            copy_btn = self.page.locator('button[aria-label="Copy to clipboard"]').last
            if await copy_btn.count() > 0:
                await copy_btn.click(timeout=3000)
                await self.page.wait_for_timeout(500)
                result = await self.page.evaluate('navigator.clipboard.readText()')
                if result:
                    task["result"] = result
                    _log(f"[OK] Raspuns (Clipboard): {len(result)} chars")
                    task["done"].set()
                    return
        except Exception as e:
            _log(f"[WARN] Eroare copy button: {e}")

        # Fallback diffing pe text
        try:
            import difflib
            diff = difflib.ndiff(old_text.splitlines(), current_text.splitlines())
            added = [line[2:] for line in diff if line.startswith('+ ')]
            filtered = [l for l in added if "Anonymized by" not in l and l.strip()]
            task["result"] = "\\n".join(filtered)
            _log(f"[OK] Raspuns (Fallback Diff): {len(task['result'])} chars")
        except Exception as e:
            task["error"] = f"Eroare extragere fallback: {e}"

        task["done"].set()


# ────────────────────────────────────────────────────────────────────────────
duck = DuckWorker()

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def do_GET(self):
        if self.path == "/api/tags":
            self._json(200, {"models": [{"name": "duck-ai:latest"}]})
        elif self.path == "/health":
            self._json(200, {"status": "ok", "version": "7.0"})
        else:
            self.send_response(200); self.end_headers()

    def do_POST(self):
        if self.path != "/api/chat":
            self.send_response(404); self.end_headers(); return

        length   = int(self.headers.get("Content-Length", 0))
        body     = json.loads(self.rfile.read(length))
        messages = body.get("messages", [])
        if not messages:
            self._json(400, {"error": "No messages"}); return

        prompt = ""
        for m in messages:
            if m.get("role") == "system":
                prompt += f"System Instructions (Follow these strictly, DO NOT echo them back):\n{m.get('content')}\n\n---\n"
            else:
                prompt += f"User Request:\n{m.get('content')}\n\n"
        prompt += "Your response (do not repeat the prompt):"
        
        _log(f"[API] Cerere combinata: {prompt[:60]}...")
        done = threading.Event()
        task = {"prompt": prompt, "done": done, "result": None, "error": None}
        asyncio.run_coroutine_threadsafe(duck.queue.put(task), _loop)

        if done.wait(timeout=70):
            if task["error"]:
                self._json(500, {"error": task["error"]})
            else:
                self._json(200, {
                    "model": "duck-ai:latest",
                    "message": {"role": "assistant", "content": task["result"]},
                    "done": True
                })
        else:
            self._json(500, {"error": "Bridge timeout"})

    def _json(self, code, obj):
        data = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

_loop = None
def _run_loop():
    global _loop
    _loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_loop)
    _loop.run_until_complete(duck.start())

if __name__ == "__main__":
    threading.Thread(target=_run_loop, daemon=True).start()
    import time; time.sleep(1)
    _log(f"HTTP Bridge pornit pe http://127.0.0.1:{PORT}")
    _log("Endpoint: POST /api/chat  |  GET /api/tags  |  GET /health")
    _log("=" * 60)
    HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
