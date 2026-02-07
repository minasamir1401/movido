import asyncio
import json
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        print("Navigating to https://hamottv.rf.gd/ to bypass challenge...")
        await page.goto("https://hamottv.rf.gd/", timeout=60000)
        
        try:
            # Wait for content or specific element that indicates site is loaded
            await page.wait_for_selector('header', timeout=30000)
        except:
            print("Timeout waiting for header, but continuing...")

        print("Fetching API data via page context...")
        # Execute fetch in the browser context to get the JSON data
        data = await page.evaluate('''async () => {
            const response = await fetch('?sys_load_api=1');
            return await response.json();
        }''')
        
        output_file = "backend/hamot_servers.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
        print(f"Successfully extracted server data to {output_file}")
        
        # Calculate summary
        total_channels = 0
        for category, channels in data.items():
            count = len(channels)
            total_channels += count
            print(f"Category: {category} - {count} channels")
            
        print(f"Total Channels Extracted: {total_channels}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
