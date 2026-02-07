"""
Test script to verify all fixes:
1. Episode extraction (should show 3 episodes, not 9)
2. Server extraction
"""
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scraper.engine import scraper

async def test_episode_extraction():
    print("=" * 60)
    print("TEST 1: Episode Extraction")
    print("=" * 60)
    
    url = "https://larooza.bond/video.php?vid=012bf4d43"
    details = await scraper.fetch_details(url)
    
    print(f"Title: {details.get('title')}")
    print(f"Type: {details.get('type')}")
    print(f"\nEpisodes found: {len(details.get('episodes', []))}")
    
    for ep in details.get('episodes', []):
        print(f"  - Episode {ep['episode']}: {ep['title']}")
    
    print(f"\nServers found: {len(details.get('servers', []))}")
    for srv in details.get('servers', []):
        print(f"  - {srv['name']}: {srv['url'][:50]}...")
    
    return details

async def main():
    print("\n🧪 MOVIDO Backend Test Suite\n")
    
    # Test episode and server extraction
    details = await test_episode_extraction()
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Episodes: {'✅ PASS' if len(details.get('episodes', [])) == 3 else '❌ FAIL'} ({len(details.get('episodes', []))} found)")
    print(f"Servers: {'✅ PASS' if len(details.get('servers', [])) > 0 else '❌ FAIL'} ({len(details.get('servers', []))} found)")

if __name__ == "__main__":
    asyncio.run(main())
