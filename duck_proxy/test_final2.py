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
        
        copy_selector = 'button[aria-label="Copy to clipboard"]'
        initial_copies = await page.locator(copy_selector).count()
        print(f'[*] Initial copy buttons: {initial_copies}')
        
        prompt = 'Write a short python function that prints pong. Include markdown code block.'
        await box.fill(prompt)
        await box.press('Enter')
        
        print(f'[*] Waiting for copy buttons to reach {initial_copies + 2}...')
        # Wait until the number of copy buttons increases by 2
        while True:
            await page.wait_for_timeout(1000)
            current_copies = await page.locator(copy_selector).count()
            if current_copies >= initial_copies + 2:
                break
                
        print(f'[*] Found {current_copies} buttons. Generation complete. Clicking last copy button...')
        copy_btn = page.locator(copy_selector).last
        await copy_btn.click()
        
        text = await page.evaluate('navigator.clipboard.readText()')
        print('[+] CLIPBOARD START')
        print(text)
        print('[+] CLIPBOARD END')
                
        await b.close()

asyncio.run(run())
