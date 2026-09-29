"""Test focalizat: verifica DOAR BrowserWorker (arhitectura thread-safe),
fara server HTTP complet. E mult mai rapid si confirma ca refactor-ul
cu worker-thread rezolva eroarea de thread-affinity."""
import sys, time, os
sys.path.insert(0, r"C:\Users\billy\Desktop\ana-manus\ANA_MAX\duck_proxy")
import duck_proxy_server as dp

def main():
    print("[*] (Re)cresez worker...")
    w = dp.BrowserWorker(dp._PROFILE_DIR)
    w.start()
    w.start_browser()
    print("[*] Astept pornirea browserului (max 45s)...")
    if not w.wait_ready(timeout=45):
        print("[-] Worker nu s-a putut initializa la timp.")
        return
    print("[+] Worker gata. Trimit un prompt de test...")
    t0 = time.time()
    answer, err = w.chat("reply with exactly the word PONG and nothing else", timeout=120)
    dt = time.time() - t0
    print(f"\n=== REZULTAT ({dt:.1f}s) ===")
    if err:
        print("[-] EROARE:", err)
        print("\n[!] Daca eroarea e legata de thread-affinity -> refactor incorect.")
        print("[!] Daca e 418/CAPTCHA -> problema de sesiune (nu de cod).")
    elif answer:
        print("RASPUNS:", repr(answer[:300]))
        if "PONG" in answer.upper():
            print("\n[+] WORKER THREAD-SAFE FUNCTIONAL: arhitectura refactorizata e corecta.")
        else:
            print("\n[~] Raspuns primit (worker merge), fara PONG exact.")
    else:
        print("[-] Niciun raspuns si nicio eroare (timeout).")
    # cleanup
    try:
        w._close_context()
        if w._pw:
            w._pw.stop()
    except Exception:
        pass

if __name__ == "__main__":
    main()
