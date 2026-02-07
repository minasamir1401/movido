import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import base64
from scraper.anime4up import anime4up_scraper

async def main():
    safe_id = "aHR0cHM6Ly80ci4ycWs5eDdiLnNob3AvYW5pbWUvbWYtZ2hvc3QtM3JkLXNlYXNvbi8="
    print(f"Testing ID: {safe_id}")
    
    try:
        url = base64.urlsafe_b64decode(safe_id).decode()
        print(f"Decoded URL: {url}")
        
        details = await anime4up_scraper.fetch_details(safe_id)
        print(f"Title: {details.get('title')}")
        print(f"Episodes: {len(details.get('episodes', []))}")
        
        if details.get('episodes'):
            first_ep = details['episodes'][0]
            try:
                print(f"First Ep: {first_ep['title'].encode('utf-8', 'replace').decode()} ({first_ep['url']})")
            except:
                print("First Ep: <error>")
            
            # Fetch episode details
            ep_details = await anime4up_scraper.fetch_episode(first_ep['id'])
            print(f"Servers: {len(ep_details.get('servers', []))}")
            for s in ep_details.get('servers', []):
                try:
                    print(f" - {s['name'].encode('utf-8', 'replace').decode()}: {s['url']}")
                except:
                    print(f" - <name error>: {s['url']}")
                
            print(f"Downloads: {len(ep_details.get('download_links', []))}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
