import asyncio
from playwright.async_api import async_playwright
import re

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
        
        await page.wait_for_load_state('networkidle', timeout=15000)
        content = await page.content()
        # Find all divs containing PONG
        matches = re.findall(r'<div[^>]*>([^<]*PONG[^<]*)</div>', content)
        print('MATCHES:', matches)
        if not matches:
            # Maybe it is inside a p tag or span
            matches = re.findall(r'<p[^>]*>([^<]*PONG[^<]*)</p>', content)
            print('P MATCHES:', matches)
            
        # Or just read all elements with class containing 'message' or similar
        elems = await page.locator('[class*="message"]').all_inner_texts()
        print('CLASSES MATCH:', elems)
        
        await browser.close()

asyncio.run(run())
