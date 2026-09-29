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
        
        # Get old text
        old_text = await page.evaluate('document.body.innerText')
        
        prompt = 'Write a 5-line poem about a duck.'
        await box.type(prompt, delay=10)
        await box.press('Enter')
        
        print('[*] Waiting for text to stabilize...')
        # Polling to wait for text to change and then stop changing
        last_text = ""
        stable_count = 0
        while True:
            await page.wait_for_timeout(1500)
            current_text = await page.evaluate('document.body.innerText')
            if current_text == last_text and current_text != old_text:
                stable_count += 1
                if stable_count >= 2: # 3 seconds stable
                    break
            else:
                stable_count = 0
            last_text = current_text
            
        print('[*] Generation finished!')
        
        # Diff the text
        # The new text is usually at the bottom, just before the footer.
        # But a simple string replace or split might work, or difflib.
        import difflib
        diff = difflib.ndiff(old_text.splitlines(), current_text.splitlines())
        added_lines = [line[2:] for line in diff if line.startswith('+ ')]
        
        print('[+] Added Lines:')
        for l in added_lines:
            if prompt not in l and 'Anonymized by DuckDuckGo' not in l and l.strip():
                print(l)
                
        await b.close()

asyncio.run(run())
