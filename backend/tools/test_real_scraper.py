import asyncio
import base64
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from scraper.animerco import animerco_scraper

async def test():
    url = "https://ww1.animerco.org/episodes/one-punch-man-%d8%a7%d9%84%d8%ad%d9%84%d9%82%d8%a9-1/"
    safe_id = base64.urlsafe_b64encode(url.encode()).decode()
    
    print(f"Testing fetch_episode for URL: {url}")
    print(f"Safe ID: {safe_id}")
    
    try:
        data = await animerco_scraper.fetch_episode(safe_id)
        print("Successfully fetched data.")
        servers = data.get("servers", [])
        print(f"Found {len(servers)} servers.")
        for s in servers:
            print(f"- {s['name']}: {s['url']}")
            
        if not servers:
            print("WARNING: No servers found!")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test())
