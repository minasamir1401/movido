import asyncio
import base64
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from scraper.animerco import animerco_scraper

async def test():
    # Test Episode 3
    url = "https://ww1.animerco.org/episodes/one-punch-man-%d8%a7%d9%84%d8%ad%d9%84%d9%82%d8%a9-3/"
    safe_id = base64.urlsafe_b64encode(url.encode()).decode()
    
    print(f"Testing Episode 3: {url}")
    print(f"Safe ID: {safe_id}\n")
    
    try:
        data = await animerco_scraper.fetch_episode(safe_id)
        
        print("=" * 60)
        print("EPISODE DATA:")
        print("=" * 60)
        print(f"Title: {data.get('title', 'N/A')}")
        print(f"Description: {data.get('description', 'N/A')[:100]}...")
        
        servers = data.get("servers", [])
        print(f"\n{'=' * 60}")
        print(f"SERVERS FOUND: {len(servers)}")
        print("=" * 60)
        
        if servers:
            for i, s in enumerate(servers, 1):
                print(f"{i}. {s['name']}")
                print(f"   URL: {s['url'][:80]}...")
                print(f"   Type: {s['type']}\n")
        else:
            print("⚠️  WARNING: No servers found!")
            
        downloads = data.get("downloads", [])
        print(f"\n{'=' * 60}")
        print(f"DOWNLOADS FOUND: {len(downloads)}")
        print("=" * 60)
        
        if downloads:
            for i, d in enumerate(downloads, 1):
                print(f"{i}. {d.get('server', 'Unknown')} - {d.get('quality', 'N/A')}")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
