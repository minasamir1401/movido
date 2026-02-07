
import asyncio
import sys
import os
import json
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("verify_core")

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scraper.engine import scraper

async def main():
    print("🚀 Verifying Core Scraper Functionality...")
    
    # 1. Test Home Page (Basic Connectivity)
    print("\n1️⃣ Testing Fetch Home...")
    try:
        home_items = await scraper.fetch_home(page=1)
        print(f"✅ Fetch Home Success: Found {len(home_items)} items")
        if home_items:
            print(f"   Sample: {home_items[0]['title']}")
            
            # 2. Test Details Extraction (Deep Test)
            first_item = home_items[0]
            if 'id' in first_item:
                print(f"\n2️⃣ Testing Details for: {first_item['title']}")
                details = await scraper.fetch_details(first_item['id'])
                
                print(f"   Title: {details.get('title')}")
                print(f"   Type: {details.get('type')}")
                print(f"   Servers: {len(details.get('servers', []))}")
                print(f"   Episodes: {len(details.get('episodes', []))}")
                print(f"   Downloads: {len(details.get('download_links', []))}")
                
                if details.get('servers'):
                    print(f"   ✅ Servers found: {details['servers'][0]['name']}")
                else:
                    print("   ⚠️ No servers found (might be expected for this item)")
                    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
