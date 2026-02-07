
import asyncio
from scraper.engine import scraper
import logging

# Configure logging to see scraper output
logging.basicConfig(level=logging.INFO)

async def main():
    print("Testing Larooza Scraper Home Page fetch...")
    try:
        items = await scraper.fetch_home(page=1)
        print(f"Found {len(items)} items.")
        if items:
            print("First item:", items[0])
        else:
            print("No items found. Possible scraper issue.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
