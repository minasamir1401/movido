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
    # The URL for Finding Her Edge Episode 7
    url = "https://asd.pics/%d9%85%d8%b3%d9%84%d8%b3%d9%84-finding-her-edge-%d8%a7%d9%84%d9%85%d9%88%d8%b3%d9%85-%d8%a7%d9%84%d8%a7%d9%88%d9%84-%d8%a7%d9%84%d8%ad%d9%84%d9%82%d8%a9-7-%d8%a7%d9%84%d8%b3%d8%a7%d8%a8%d8%b9%d8%a9/"
    
    # Safe ID for this URL
    safe_id = base64.urlsafe_b64encode(url.encode()).decode().strip('=')
    
    print(f"Extracting details for: {url}")
    print(f"Safe ID: {safe_id}")
    
    details = await scraper.fetch_details(safe_id)
    
    # Save to a file for review
    with open("series_extraction_result.json", "w", encoding="utf-8") as f:
        json.dump(details, f, indent=4, ensure_ascii=False)
    
    print("\nExtraction Complete!")
    print(f"Title: {details.get('title')}")
    print(f"Type: {details.get('type')}")
    print(f"Servers Found: {len(details.get('servers', []))}")
    print(f"Downloads Found: {len(details.get('download_links', []))}")
    
    for server in details.get('servers', []):
        print(f" - {server['name']}: {server['url']}")

if __name__ == "__main__":
    asyncio.run(test_extraction())
