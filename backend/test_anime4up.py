import asyncio
import sys
from scraper.anime4up import anime4up_scraper

async def test():
    print("Testing Anime4Up Scraper...")
    
    # Test Home
    print("\n1. Testing Home...")
    home = await anime4up_scraper.fetch_home()
    if home:
        print(f"Found {len(home)} sections")
        for name, items in home.items():
            print(f" - Section '{name}': {len(items)} items")
            if items:
                print(f"   Sample Item: {items[0]['title']} | Poster: {items[0]['poster'][:50]}...")
    
    # Test Search
    print("\n2. Testing Search 'One Piece'...")
    results = await anime4up_scraper.search("One Piece")
    print(f"Found {len(results)} results")
    if results:
        print(f"Sample: {results[0]['title']} | ID: {results[0]['id'][:20]}...")

    # Test Details
    if results:
        print(f"\n3. Testing Details ({results[0]['title']})...")
        details = await anime4up_scraper.fetch_details(results[0]['id'])
        if details:
            print(f"Title: {details['title']}")
            print(f"Episodes: {len(details['episodes'])}")
            print(f"Poster: {details['poster'][:50]}...")
            if details['episodes']:
                print(f"Sample Ep: {details['episodes'][0]['title']} | ID: {details['episodes'][0]['id'][:20]}...")

    # Test Episode
    if details and details['episodes']:
        ep_id = details['episodes'][0]['id']
        print(f"\n4. Testing Episode ({details['episodes'][0]['title']})...")
        ep_details = await anime4up_scraper.fetch_details(ep_id)
        if ep_details:
            print(f"Title: {ep_details['title']}")
            print(f"Servers: {len(ep_details['servers'])}")
            print(f"Episodes List (remaining): {len(ep_details['episodes'])}")

if __name__ == "__main__":
    asyncio.run(test())
