import asyncio
from playwright.async_api import async_playwright

JS_INTERCEPTOR = """
window._captured_sse = "";
window._sse_done = false;

// Hook Fetch
const originalFetch = window.fetch;
window.fetch = async function(...args) {
    const url = args[0] && typeof args[0] === 'string' ? args[0] : (args[0] && args[0].url ? args[0].url : "");
    const response = await originalFetch.apply(this, args);
    
    if (url.includes('/duckchat/v1/chat')) {
        const clone = response.clone();
        const reader = clone.body.getReader();
        const decoder = new TextDecoder("utf-8");
        window._captured_sse = "";
        window._sse_done = false;
        
        reader.read().then(function processText({ done, value }) {
            if (done) {
                window._sse_done = true;
                return;
            }
            const chunk = decoder.decode(value, {stream: true});
            // Parse SSE chunk
            const lines = chunk.split('\\n');
            for (let line of lines) {
                if (line.startsWith('data: ')) {
                    const d = line.substring(6);
                    if (d === '[DONE]') {
                        window._sse_done = true;
                    } else {
                        try {
                            const j = JSON.parse(d);
                            if (j.message) window._captured_sse += j.message;
                        } catch(e) {}
                    }
                }
            }
            return reader.read().then(processText);
        });
    }
    return response;
};
"""

async def run():
    async with async_playwright() as p:
        b = await p.chromium.launch(headless=True)
        page = await b.new_page()
        
        # Inject interceptor BEFORE page loads
        await page.add_init_script(JS_INTERCEPTOR)
        
        await page.goto('https://duck.ai', wait_until='networkidle')
        try:
            btn = page.locator('button:has-text("Continue"), button:has-text("Get Started"), button:has-text("I Agree")').first
            if await btn.count() > 0: await btn.click(timeout=2000)
        except: pass
        
        box = page.locator('textarea').last
        await box.wait_for(state='visible')
        await box.type('Reply exactly: PONG_MAGIC', delay=10)
        await box.press('Enter')
        
        print('[*] Waiting for SSE in JS...')
        try:
            await page.wait_for_function("() => window._sse_done === true", timeout=15000)
            sse_data = await page.evaluate("() => window._captured_sse")
            print('[+] SSE DATA RECEIVED (length):', len(sse_data))
            print('[+] DATA SNIPPET:', sse_data)
        except Exception as e:
            print('[-] Error waiting for SSE:', e)
            
        await b.close()

asyncio.run(run())
