
import asyncio
import sys
import os

# Add the project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scraper.engine import scraper

async def test_larooza():
    print("Testing Larooza Scraper...")
    try:
        print(f"Base URL: {scraper.base_url}")
        items = await scraper.fetch_home(page=1)
        print(f"Successfully fetched {len(items)} items from home page.")
        
        if items:
            print("\nFirst 3 items:")
            for item in items[:3]:
                print(f"- {item['title']} (ID: {item['id']})")
            
            # Test details for the first item
            first_id = items[0]['id']
            print(f"\nTesting details for ID: {first_id}...")
            details = await scraper.fetch_details(first_id)
            print(f"Title: {details.get('title')}")
            print(f"Servers found: {len(details.get('servers', []))}")
            for server in details.get('servers', [])[:3]:
                print(f"  * {server['name']}: {server['url'][:50]}...")
        else:
            print("No items found. Scraper might be failing.")
            
    except Exception as e:
        print(f"Error during test: {e}")

if __name__ == "__main__":
    asyncio.run(test_larooza())
