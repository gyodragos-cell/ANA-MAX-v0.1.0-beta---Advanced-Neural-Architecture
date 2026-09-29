import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        await page.goto('https://duck.ai', wait_until='networkidle')
        
        try:
            agree_btn = page.locator('button:has-text("Get Started"), button:has-text("I Agree")').first
            if await agree_btn.count() > 0:
                await agree_btn.click(timeout=2000)
                await page.wait_for_timeout(1000)
        except Exception:
            pass
            
        box = page.locator('textarea').last
        await box.wait_for(state='visible')
        await box.type('Reply exactly: PONG', delay=10)
        await box.press('Enter')
        
        # In duck.ai, assistant messages usually have a specific class or ARIA role.
        # Let's wait for networkidle
        await page.wait_for_load_state('networkidle', timeout=15000)
        
        # Try to find all articles or divs that look like messages
        elements = await page.locator('article, [data-testid^="message"]').all_inner_texts()
        print("BUBBLES:")
        for idx, text in enumerate(elements):
            if "PONG" in text:
                print(f"[{idx}] {text}")
                
        await browser.close()

asyncio.run(run())
