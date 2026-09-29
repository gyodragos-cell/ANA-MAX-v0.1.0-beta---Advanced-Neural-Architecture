import asyncio
from playwright.async_api import async_playwright
import json

async def run():
    print("[*] Starting Playwright JS Bridge Test...")
    async with async_playwright() as p:
        # Use system Chrome
        browser = await p.chromium.launch(channel="chrome", headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        print("[*] Navigating to duck.ai...")
        await page.goto("https://duck.ai", wait_until="domcontentloaded")
        
        print("[*] Executing JS Fetch in page context...")
        # This JS code runs inside the real browser, bypassing most anti-bot
        js_code = """
        async () => {
            const r1 = await fetch("https://duck.ai/duckchat/v1/auth/token", {
                headers: {"x-vqd-accept": "1"}
            });
            const vqd = r1.headers.get("x-vqd-4");
            
            const r2 = await fetch("https://duck.ai/duckchat/v1/chat", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "x-vqd-4": vqd,
                    "accept": "text/event-stream"
                },
                body: JSON.stringify({
                    model: "gpt-4o-mini",
                    messages: [{role: "user", content: "reply with exactly the word PONG"}]
                })
            });
            const text = await r2.text();
            return {status: r2.status, vqd: vqd, text: text};
        }
        """
        try:
            res = await page.evaluate(js_code)
            print(f"[+] VQD Token: {res.get('vqd')}")
            print(f"[+] HTTP Status: {res.get('status')}")
            print(f"[+] Response: {res.get('text')[:200]}")
            
            if "PONG" in res.get('text', '').upper():
                print("\n[SUCCESS] JS Bridge approach works perfectly!")
            else:
                print("\n[FAILED] Response received but PONG not found.")
        except Exception as e:
            print(f"[-] JS Execution failed: {e}")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
