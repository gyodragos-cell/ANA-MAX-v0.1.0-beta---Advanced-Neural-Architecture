import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        b = await p.chromium.launch(
            headless=True,
            args=["--disable-web-security"] # just in case
        )
        context = await b.new_context(permissions=['clipboard-read', 'clipboard-write'])
        page = await context.new_page()
        
        await page.goto('https://duck.ai', wait_until='networkidle')
        try:
            btn = page.locator('button:has-text("Continue"), button:has-text("Get Started"), button:has-text("I Agree")').first
            if await btn.count() > 0: await btn.click(timeout=2000)
        except: pass
        
        box = page.locator('textarea').last
        await box.wait_for(state='visible')
        prompt = 'Reply EXACTLY with: ```python\\nprint("PONG")\\n```'
        await box.type(prompt, delay=10)
        await box.press('Enter')
        
        print('[*] Waiting for Copy button to appear...')
        # Wait for the "Stop generating" to disappear first if needed, or wait for the new copy button
        # Actually, copy button might be present immediately but disabled, or only appears at the end.
        await page.wait_for_timeout(5000) # Give it 5s to finish
        
        copy_btn = page.locator('button[aria-label="Copy to clipboard"]').last
        await copy_btn.wait_for(state='visible', timeout=15000)
        await copy_btn.click()
        
        # Read clipboard
        text = await page.evaluate('navigator.clipboard.readText()')
        print('[+] CLIPBOARD:', text)
                
        await b.close()

asyncio.run(run())
