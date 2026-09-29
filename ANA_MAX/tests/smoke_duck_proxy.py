"""
ANA MAX - Smoke Test: Duck Proxy Server  v2.1
=============================================
Porneste duck_proxy_server.py pe un port de test (11458),
verifica /api/tags, asteapta initializarea Chrome, trimite
un prompt PONG si verifica raspunsul.

Rulare:
    python ANA_MAX\\tests\\smoke_duck_proxy.py

Nota: Necesita Chrome real instalat si conexiune la duck.ai.
      Prima rulare poate cere rezolvarea manuala a unui CAPTCHA.
"""
import time, json, sys, urllib.request, subprocess, os

PY = r"C:\Users\billy\Desktop\ana-manus\ANA_MAX\venv\Scripts\python.exe"
SCRIPT = r"C:\Users\billy\Desktop\ana-manus\ANA_MAX\duck_proxy\duck_proxy_server.py"
PORT = 11458  # port de test (diferit de 11434 productie)
LOG_FILE = r"C:\Users\billy\Desktop\ana-manus\ANA_MAX\duck_proxy\smoke_test.log"

def post_chat(content, timeout=180):
    payload = json.dumps({
        "model": "duck-ai-model",
        "messages": [{"role": "user", "content": content}],
    }).encode("utf-8")
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}/api/chat",
                                 data=payload,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))

def get_tags():
    with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/api/tags", timeout=10) as r:
        return json.loads(r.read().decode("utf-8"))

def read_log(n=20):
    """Citeste ultimele n linii din log."""
    try:
        with open(LOG_FILE, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
            return "".join(lines[-n:])
    except Exception:
        return "(no log yet)"

def main():
    # Curatam log vechi
    if os.path.exists(LOG_FILE):
        os.remove(LOG_FILE)

    print(f"[*] Start server pe portul {PORT}... (log: {LOG_FILE})")
    # Redirectam stdout+stderr catre fisier (NU PIPE, ca sa citim in timp real)
    log_fh = open(LOG_FILE, "w", encoding="utf-8", buffering=1)
    proc = subprocess.Popen(
        [PY, SCRIPT, str(PORT)],
        stdout=log_fh, stderr=log_fh,
        text=True, encoding="utf-8", errors="replace",
    )
    log_fh.close()  # subprocess detine fd-ul acum

    try:
        # Asteptam server HTTP
        print("[*] Astept server HTTP...", flush=True)
        for i in range(20):
            try:
                t = get_tags()
                print(f"[+] /api/tags OK: {t}", flush=True)
                break
            except Exception:
                time.sleep(2)
        else:
            print("[-] /api/tags nu raspunde. Server blocat?", flush=True)
            print(read_log(30))
            return

        # Asteptam initializarea browser (worker thread)
        print("[*] Astept initializare Chrome + duck.ai (max 45s)...", flush=True)
        for i in range(30):
            time.sleep(1.5)
            log = read_log(5)
            if "Browser gata" in log or "Browserul Chrome" in log:
                print(f"[+] Browser init: {log.strip()}", flush=True)
                break
        else:
            print("[~] Timeout asteptare browser. Log:", flush=True)
            print(read_log(15))
            print("[*] Continui cu request oricum...", flush=True)

        # Trimitem request PONG
        print("[*] Trimit /api/chat PONG...", flush=True)
        t0 = time.time()
        try:
            res = post_chat("reply with exactly the word PONG and nothing else", timeout=150)
            dt = time.time() - t0
            answer = res.get("message", {}).get("content", "")
            print(f"[+] Raspuns in {dt:.1f}s ({len(answer)} chars):", flush=True)
            print(f"    {repr(answer[:400])}", flush=True)
            if "PONG" in answer.upper():
                print("\n[+] SMOKE TEST PASSED", flush=True)
            else:
                print("\n[~] Raspuns primit dar nu contine PONG. Verifica.", flush=True)
        except Exception as e:
            dt = time.time() - t0
            print(f"[-] Request esuat dupa {dt:.1f}s: {e}", flush=True)

        # Afisam log complet
        print("\n=== LOG SERVER (complet) ===", flush=True)
        print(read_log(40), flush=True)

    finally:
        print("[*] Opresc serverul...", flush=True)
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except Exception:
            proc.kill()

if __name__ == "__main__":
    main()
