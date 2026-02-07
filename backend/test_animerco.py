
import asyncio
from scraper.animerco import animerco_scraper
import json
import base64

async def test():
    print("Fetching Home...")
    home = await animerco_scraper.fetch_home()
    print(f"Home Keys: {list(home.keys())}")
    
    first_item = None
    for section, items in home.items():
        if items:
            first_item = items[0]
            break
            
    if first_item:
        print(f"\nFetching Details for: {first_item['title']}")
        details = await animerco_scraper.fetch_details(first_item['id'])
        print(f"Details: {details.keys()}")
        print(f"Seasons: {len(details.get('seasons', []))}")
        print(f"Episodes: {len(details.get('episodes', []))}")
        
        if details.get('episodes'):
            first_ep = details['episodes'][0]
            print(f"\nFetching Episode: {first_ep['title']}")
            ep_details = await animerco_scraper.fetch_episode(first_ep['id'])
            print(f"Episode Title: {ep_details.get('title')}")
            print(f"Servers Count: {len(ep_details.get('servers', []))}")
            print(f"Download Links Count: {len(ep_details.get('download_links', []))}")
            if ep_details.get('servers'):
                print(f"Sample Server: {ep_details['servers'][0]}")
            if ep_details.get('download_links'):
                print(f"Sample Download: {ep_details['download_links'][0]}")

if __name__ == "__main__":
    asyncio.run(test())
