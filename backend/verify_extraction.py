
import asyncio
import base64
import sys
from scraper.anime4up import anime4up_scraper

# Set encoding to utf-8 for Windows console
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())

async def test_and_report():
    print("--- Starting Extraction Test for Anime4Up ---")
    
    # 1. Fetch Home
    print("\n[Step 1] Fetching Home Content...")
    home = await anime4up_scraper.fetch_home()
    
    first_item = None
    for section_name, items in home.items():
        print(f"Found Section: {section_name} ({len(items)} items)")
        if not first_item and items:
            first_item = items[0]
            
    if not first_item:
        print("Error: No items found on home page!")
        return

    # 2. Fetch Details
    print(f"\n[Step 2] Fetching Details for: {first_item['title']}...")
    print(f"ID: {first_item['id']}")
    
    details = await anime4up_scraper.fetch_details(first_item['id'])
    
    print(f"Title: {details.get('title')}")
    print(f"Description: {details.get('description')[:100]}...")
    print(f"Total Episodes Found: {len(details.get('episodes', []))}")
    print(f"Initial Servers Found: {len(details.get('servers', []))}")
    
    # 3. Fetch Specific Episode if possible
    if details.get('episodes'):
        target_ep = details['episodes'][0]
        print(f"\n[Step 3] Fetching Episode: {target_ep['title']}...")
        ep_data = await anime4up_scraper.fetch_episode(target_ep['id'])
        
        print(f"Servers for this episode: {len(ep_data.get('servers', []))}")
        for i, s in enumerate(ep_data.get('servers', [])[:3]):
            print(f"  - Server {i+1}: {s['name']} -> {s['url'][:50]}...")
            
        print(f"Download links: {len(ep_data.get('download_links', []))}")
        for i, d in enumerate(ep_data.get('download_links', [])[:3]):
            print(f"  - Download {i+1}: {d['quality']} -> {d['url'][:50]}...")
    else:
        # If it's a direct episode from Blogspot
        print(f"\n[Step 3] Extraction from direct link...")
        print(f"Servers: {len(details.get('servers', []))}")
        for i, s in enumerate(details.get('servers', [])[:3]):
            print(f"  - Server {i+1}: {s['name']} -> {s['url'][:50]}...")

if __name__ == "__main__":
    asyncio.run(test_and_report())
