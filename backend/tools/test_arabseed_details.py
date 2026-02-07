
import asyncio
from scraper.mycima import scraper
import logging

logging.basicConfig(level=logging.INFO)

async def main():
    print("Testing MyCima/ArabSeed scraper fetch_details...")
    
    # The safe_id from the test
    safe_id = "aHR0cHM6Ly9hLmFzZC5ob21lcy8lZDklODElZDklOGElZDklODQlZDklODUtc2VsZi1oZWxwLTIwMjUtJWQ5JTg1JWQ4JWFhJWQ4JWIxJWQ4JWFjJWQ5JTg1Lw"
    
    try:
        details = await scraper.fetch_details(safe_id)
        print(f"\n✅ Details fetched successfully!")
        print(f"Title: {details.get('title')}")
        print(f"Type: {details.get('type')}")
        print(f"Servers: {len(details.get('servers', []))} servers found")
        print(f"Downloads: {len(details.get('download_links', []))} download links found")
        print(f"Episodes: {len(details.get('episodes', []))} episodes found")
        
        if details.get('servers'):
            print("\nServers:")
            for server in details.get('servers', [])[:3]:
                print(f"  - {server.get('name')}: {server.get('url')[:50]}...")
                
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
