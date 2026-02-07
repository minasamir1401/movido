import asyncio
import logging
from scraper.engine import scraper
from scraper.anime4up import anime4up_scraper

logging.basicConfig(level=logging.INFO)

async def debug_endpoint_logic():
    q = "Darwin Jihen"
    print(f"Debugging endpoint logic for: {q}")
    
    # 1. General search
    items = await scraper.search(q) or []
    print(f"General results: {len(items)}")
    
    # 2. Anime search
    anime_items = await anime4up_scraper.search(q) or []
    print(f"Anime results: {len(anime_items)}")
    for itm in anime_items:
        print(f"Item keys: {list(itm.keys())}")
        print(f"Item: {itm}")

if __name__ == "__main__":
    asyncio.run(debug_endpoint_logic())
