import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        b = await p.chromium.launch(headless=True)
        context = await b.new_context(permissions=['clipboard-read', 'clipboard-write'])
        page = await context.new_page()
        
        await page.goto('https://duck.ai', wait_until='networkidle')
        try:
            btn = page.locator('button:has-text("Continue"), button:has-text("Get Started"), button:has-text("I Agree")').first
            if await btn.count() > 0: await btn.click(timeout=2000)
        except: pass
        
        box = page.locator('textarea').last
        await box.wait_for(state='visible')
        
        await box.fill('Write a short python function that prints pong. Include markdown code block.')
        await box.press('Enter')
        
        print('[*] Waiting for networkidle...')
        # Wait for the network to be idle, which happens when SSE stops
        await page.wait_for_load_state('networkidle', timeout=60000)
        
        # Wait a bit just in case
        await page.wait_for_timeout(1000)
        
        # Get all text from DOM for debugging
        content = await page.evaluate('document.body.innerText')
        if 'def' not in content:
            print("[-] Wait, 'def' not in content! Output might have failed.")
            print(content[-500:])
            
        print('[*] Clicking copy button...')
        copy_btn = page.locator('button[aria-label="Copy to clipboard"]').last
        await copy_btn.click()
        
        text = await page.evaluate('navigator.clipboard.readText()')
        print('[+] CLIPBOARD:')
        print(text)
        await b.close()

asyncio.run(run())
