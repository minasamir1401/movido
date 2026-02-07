import asyncio
import json
import base64
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from scraper.mycima import MyCimaScraper

async def test_extraction():
    scraper = MyCimaScraper()
    # The URL provided by user
    url = "https://asd.pics/%d9%81%d9%8a%d9%84%d9%85-the-wrecking-crew-2026-%d9%85%d8%aa%d8%b1%d8%ac%d9%85/"
    
    # Safe ID for this URL
    safe_id = base64.urlsafe_b64encode(url.encode()).decode().strip('=')
    
    print(f"Extracting details for: {url}")
    print(f"Safe ID: {safe_id}")
    
    details = await scraper.fetch_details(safe_id)
    
    # Save to a file for review
    with open("extraction_result.json", "w", encoding="utf-8") as f:
        json.dump(details, f, indent=4, ensure_ascii=False)
    
    print("\nExtraction Complete!")
    print(f"Title: {details.get('title')}")
    print(f"Servers Found: {len(details.get('servers', []))}")
    print(f"Downloads Found: {len(details.get('download_links', []))}")
    
    for server in details.get('servers', []):
        print(f" - {server['name']}: {server['url']}")

if __name__ == "__main__":
    asyncio.run(test_extraction())
