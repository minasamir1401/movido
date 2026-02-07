
import asyncio
import aiohttp
import base64
import json
import sys

# URL specific to the user's issue (Episode 3)
# Based on HTML dump: value="video.php?vid=YNDoUFGYh"
TARGET_URL = "https://larooza.top/video.php?vid=YNDoUFGYh"

async def test_api():
    # 1. Generate safe_id
    safe_id = base64.urlsafe_b64encode(TARGET_URL.encode()).decode().strip("=")
    print(f"Target URL: {TARGET_URL}")
    print(f"Safe ID: {safe_id}")
    
    api_url = f"http://localhost:8000/api/v1/movies/details/{safe_id}?refresh=true"
    print(f"Calling API: {api_url}")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url) as resp:
                print(f"Status: {resp.status}")
                if resp.status == 200:
                    data = await resp.json()
                    
                    # 2. Inspect Servers
                    servers = data.get("servers", [])
                    print(f"Servers count in API response: {len(servers)}")
                    
                    if servers:
                        print("Servers found:")
                        for s in servers:
                            print(f" - {s.get('name')}: {s.get('url')}")
                    else:
                        print("WARNING: Servers list is empty!")
                        
                    # 3. Inspect Episodes
                    episodes = data.get("episodes", [])
                    print(f"Episodes count: {len(episodes)}")
                    
                    # 4. Check Source
                    print(f"Source: {data.get('_source')}")
                    
                else:
                    print(f"Error Response: {await resp.text()}")
    except Exception as e:
        print(f"Request failed: {e}")
        print("Is the backend server running properly on port 8000?")

if __name__ == "__main__":
    if sys.platform.startswith('win'):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(test_api())
