import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        b = await p.chromium.launch(headless=True)
        page = await b.new_page()
        await page.goto('https://duck.ai', wait_until='networkidle')
        try:
            btn = page.locator('button:has-text("Get Started"), button:has-text("I Agree")').first
            if await btn.count() > 0: await btn.click(timeout=2000)
        except: pass
        box = page.locator('textarea').last
        await box.wait_for(state='visible')
        await box.type('Reply exactly: PONG_TEST_MAGIC_WORD', delay=10)
        await box.press('Enter')
        await page.wait_for_timeout(5000)
        html = await page.content()
        with open('dom.html', 'w', encoding='utf-8') as f:
            f.write(html)
        await b.close()
asyncio.run(run())
