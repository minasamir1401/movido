import asyncio
import sys
import os
import base64
import json

# Add the backend path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scraper.animerco import AnimercoScraper

async def verify():
    print("Initializing Scraper...")
    scraper = AnimercoScraper()
    
    # Test One Punch Man Season 1 (which forwards to episodes)
    # The scraper logic now should:
    # 1. Fetch Season page
    # 2. Extract Episodes
    # 3. Auto-fetch servers for Episode 1
    
    target_url = "https://ww1.animerco.org/seasons/one-punch-man-season-1/"
    safe_id = base64.urlsafe_b64encode(target_url.encode()).decode()
    
    print(f"Fetching Details for: {target_url}")
    details = await scraper.fetch_details(safe_id)
    
    print(f"\n[Result] Title: {details.get('title')}")
    print(f"[Result] Episodes Found: {len(details.get('episodes', []))}")
    
    servers = details.get('servers', [])
    print(f"[Result] Servers Found (Auto-fetched): {len(servers)}")
    
    for s in servers:
        print(f" - [{s['type']}] {s['name']}: {s['url']}")

    if len(servers) > 0:
        print("\nSUCCESS: Servers are being extracted (either via AJAX or Fallback)!")
    else:
        print("\nFAILURE: Still no servers found.")

if __name__ == "__main__":
    asyncio.run(verify())
