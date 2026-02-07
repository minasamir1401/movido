
import asyncio
import base64
import sys
import os

# Add the backend and scraper directories to the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../scraper")))

from animerco import animerco_scraper

async def test():
    # Test One Punch Man details
    # URL: https://ww1.animerco.org/animes/one-punch-man/
    url = "https://ww1.animerco.org/animes/one-punch-man/"
    safe_id = base64.urlsafe_b64encode(url.encode()).decode()
    
    print(f"Fetching details for {url}...")
    details = await animerco_scraper.fetch_details(safe_id)
    
    print(f"Title: {details.get('title')}")
    print(f"Poster: {details.get('poster')}")
    print(f"Episodes count: {len(details.get('episodes', []))}")
    if details.get('episodes'):
        print(f"First Episode ID: {details['episodes'][0]['id']}")
        
        # Test first episode servers
        print(f"\nFetching episode details for {details['episodes'][0]['title']}...")
        ep_details = await animerco_scraper.fetch_details(details['episodes'][0]['id'])
        print(f"Servers found: {len(ep_details.get('servers', []))}")
        for s in ep_details.get('servers', []):
            print(f"- {s['name']}: {s['url'][:60]}...")
            
        print(f"Downloads found: {len(ep_details.get('download_links', []))}")
        for d in ep_details.get('download_links', []):
            print(f"- {d['quality']}: {d['url']}")

if __name__ == "__main__":
    asyncio.run(test())
