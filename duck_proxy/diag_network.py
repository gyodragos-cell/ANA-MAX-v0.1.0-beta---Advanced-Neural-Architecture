import asyncio
from playwright.async_api import async_playwright
import time
import os

async def run():
    print("[*] Starting Deep Diagnostic...")
    profile_dir = r"C:\Users\billy\Desktop\ana-manus\.duck_profile"
    os.makedirs(profile_dir, exist_ok=True)
    
    async with async_playwright() as p:
        # HEADFUL to bypass bot detection
        browser = await p.chromium.launch_persistent_context(
            user_data_dir=profile_dir,
            channel="chrome",
            headless=False,
            args=["--disable-blink-features=AutomationControlled"]
        )
        page = browser.pages[0] if browser.pages else await browser.new_page()
        
        # Log all requests
        async def handle_request(request):
            if "duckchat" in request.url:
                print(f"[REQ] {request.method} {request.url}")
                # print(f"      Headers: {request.headers}")
        
        async def handle_response(response):
            if "duckchat" in response.url:
                print(f"[RES] {response.status} {response.url}")
                if response.status == 418:
                    print(f"[!!!] CHALLENGE DETECTED: {await response.text()}")
        
        page.on("request", handle_request)
        page.on("response", handle_response)
        
        print("[*] Navigating to duck.ai...")
        await page.goto("https://duck.ai")
        await page.wait_for_load_state("networkidle")
        
        print("[*] Searching for textarea...")
        # Try multiple selectors
        selectors = ["textarea", "[role='textbox']", "div[contenteditable='true']"]
        box = None
        for sel in selectors:
            try:
                box = page.locator(sel).last
                await box.wait_for(state="visible", timeout=5000)
                print(f"[+] Found box with: {sel}")
                break
            except:
                continue
        
        if box:
            print("[*] Typing PONG test...")
            await box.click()
            await box.type("reply with PONG and nothing else", delay=50)
            await box.press("Enter")
            
            print("[*] Waiting 15s for network activity...")
            await asyncio.sleep(15)
        else:
            print("[-] Textarea not found. Is there a CAPTCHA?")
            await asyncio.sleep(30) # Wait for manual inspection
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
