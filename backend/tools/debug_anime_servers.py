import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import base64
from scraper.anime4up import anime4up_scraper

async def main():
    # ID for MF Ghost 3rd Season (Anime Page)
    safe_id = "aHR0cHM6Ly80ci4ycWs5eDdiLnNob3AvYW5pbWUvbWYtZ2hvc3QtM3JkLXNlYXNvbi8="
    print(f"Debug: Fetching details for Anime ID: {safe_id}")
    
    try:
        details = await anime4up_scraper.fetch_details(safe_id)
        
        print(f"Title: {details.get('title')}")
        print(f"Type: {details.get('type')}")
        
        episodes = details.get('episodes', [])
        print(f"Episodes Found: {len(episodes)}")
        if episodes:
            print(f"First Episode URL: {episodes[0]['url']}")
            
        servers = details.get('servers', [])
        print(f"Servers in Anime Details: {len(servers)}")
        for s in servers:
            try:
                print(f" - {s['name'].encode('utf-8', 'replace').decode()}: {s['url']}")
            except:
                print(f" - <name error>: {s['url']}")
                
        downloads = details.get('download_links', [])
        print(f"Downloads in Anime Details: {len(downloads)}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
