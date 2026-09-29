import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto('https://duck.ai', wait_until='networkidle')
        try:
            agree = page.locator('button:has-text("Get Started")')
            if await agree.count(): await agree.first.click()
            agree2 = page.locator('button:has-text("I Agree")')
            if await agree2.count(): await agree2.first.click()
        except: pass
        
        box = page.locator('textarea').last
        await box.wait_for(state='visible')
        await box.type('Reply exactly: PONG123', delay=10)
        await box.press('Enter')
        await page.wait_for_timeout(5000)
        
        # Get all texts
        texts = await page.locator('p, [data-testid], article').all_inner_texts()
        print('TEXTS:')
        for i, t in enumerate(texts):
            if t.strip():
                print(f"[{i}] {t.strip()}")
        await browser.close()
asyncio.run(run())
