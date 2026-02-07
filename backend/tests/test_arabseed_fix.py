import asyncio
import base64
import sys
import os

# Add the backend and scraper directories to the path
sys.path.append(os.path.abspath(os.path.join(os.getcwd())))
sys.path.append(os.path.abspath(os.path.join(os.getcwd(), 'backend')))

from backend.scraper.mycima import scraper

async def test_arabseed_fix():
    # URL provided by user
    url = "https://a.asd.homes/%d8%a8%d8%b1%d9%86%d8%a7%d9%85%d8%ac-%d8%b5%d8%a7%d8%ad%d8%a8%d8%a9-%d8%a7%d9%84%d8%b3%d8%b9%d8%a7%d8%af%d8%a9-2026-%d8%ad%d9%84%d9%82%d8%a9-%d9%87%d9%8a%d8%b1%d9%88-%d9%85%d8%b5%d8%b7%d9%81%d9%8a/"
    safe_id = base64.urlsafe_b64encode(url.encode()).decode().strip('=')
    
    print(f"Testing URL: {url}")
    print(f"Safe ID: {safe_id}")
    
    try:
        details = await scraper.fetch_details(safe_id)
        
        print("\n--- Results ---")
        print(f"Title: {details.get('title')}")
        print(f"Type: {details.get('type')}")
        print(f"Servers found: {len(details.get('servers', []))}")
        
        for idx, server in enumerate(details.get('servers', [])):
            print(f"{idx+1}. {server['name']}: {server['url'][:100]}...")
            
        if not details.get('servers'):
            print("❌ No servers found!")
        else:
            print("✅ Servers extracted successfully.")
            
    except Exception as e:
        print(f"❌ Error during test: {e}")

if __name__ == "__main__":
    asyncio.run(test_arabseed_fix())
