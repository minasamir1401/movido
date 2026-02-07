
import asyncio
import logging
import sys
import os

# Add the project root to sys.path to import scraper
sys.path.append(os.path.join(os.getcwd()))

from scraper.mycima import scraper

async def test_arabseed_fetch():
    logging.basicConfig(level=logging.INFO)
    print("Testing ArabSeed Fetch Home...")
    try:
        items = await scraper.fetch_home(page=1)
        print(f"Fetched {len(items)} items.")
        if items:
            for item in items[:3]:
                print(f"- {item['title']} : {item['url']}")
        else:
            print("No items found. Checking HTML...")
            # We can't easily check HTML here without modifying the scraper but let's see
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_arabseed_fetch())
