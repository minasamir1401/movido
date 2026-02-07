import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        print("Navigating to https://hamottv.rf.gd/ ...")
        await page.goto("https://hamottv.rf.gd/", timeout=60000)
        
        # Wait for some content to ensure challenge is passed. 
        # We'll wait for network idle or a specific timeout
        print("Waiting for page to load...")
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(5) # Extra wait for JS execution
        
        content = await page.content()
        with open("backend/hamot_dump.html", "w", encoding="utf-8") as f:
            f.write(content)
            
        print("HTML dumped to backend/hamot_dump.html")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
