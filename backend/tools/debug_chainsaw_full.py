import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import base64
import json
from scraper.anime4up import anime4up_scraper

async def main():
    # Chainsaw Man Movie ID
    safe_id = "aHR0cHM6Ly80ci4ycWs5eDdiLnNob3AvYW5pbWUvY2hhaW5zYXctbWFuLW1vdmllLXJlemUtaGVuLw=="
    print(f"Debug: Fetching details for Anime ID: {safe_id}")
    
    try:
        details = await anime4up_scraper.fetch_details(safe_id)
        
        print(f"Title: {details['title']}")
        print(f"Type: {details['type']}")
        print(f"Episodes Count: {len(details['episodes'])}")
        
        if details['episodes']:
            try:
                print(f"First Episode Title: {details['episodes'][0]['title'].encode('utf-8', 'replace').decode()}")
            except:
                print("First Episode Title: <error>")
            print(f"First Episode URL: {details['episodes'][0]['url']}")
            
        print(f"Servers Count: {len(details['servers'])}")
        for s in details['servers']:
             try:
                print(f" - {s['name'].encode('utf-8', 'replace').decode()}: {s['url']}")
             except: pass
             
        print(f"Downloads Count: {len(details['download_links'])}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
