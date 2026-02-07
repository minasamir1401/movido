import asyncio
import json
import base64
from scraper.anime4up import anime4up_scraper

async def main():
    print("--- Testing Fetch Home ---")
    home = await anime4up_scraper.fetch_home()
    sections = list(home.keys())
    print(f"Sections found: {sections}")
    if sections:
        first_section = sections[0]
        items = home[first_section]
        print(f"Items in '{first_section}': {len(items)}")
        if items:
            print(f"Sample Item: {json.dumps(items[0], indent=2, ensure_ascii=False)}")

    print("\n--- Testing Fetch Details (Anime) ---")
    # Using a known slug if possible, or search first
    search_results = await anime4up_scraper.search("One Piece")
    if search_results:
        anime_id = search_results[0]['id']
        print(f"Fetching details for: {search_results[0]['title']} (ID: {anime_id})")
        details = await anime4up_scraper.fetch_details(anime_id)
        
        print(f"Title: {details.get('title')}")
        print(f"Poster: {details.get('poster')}")
        print(f"Episodes count: {len(details.get('episodes', []))}")
        
        if details.get('episodes'):
            ep_id = details['episodes'][0]['id']
            print(f"\n--- Testing Fetch Episode (Watch) ---")
            print(f"Fetching episode details for ID: {ep_id}")
            ep_details = await anime4up_scraper.fetch_details(ep_id)
            print(f"Episode Title: {ep_details.get('title')}")
            print(f"Servers count: {len(ep_details.get('servers', []))}")
            print(f"Downloads count: {len(ep_details.get('download_links', []))}")
            
            if ep_details.get('servers'):
                print(f"Sample Server: {ep_details['servers'][0]}")
            if ep_details.get('download_links'):
                print(f"Sample Download: {ep_details['download_links'][0]}")

if __name__ == "__main__":
    asyncio.run(main())
