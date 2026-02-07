import asyncio
import sys
import os
import httpx
import logging

# Setup path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

# Configure logging
logging.basicConfig(level=logging.INFO)

from scraper.matches import matches_scraper

async def verify():
    print("--- STARTING VERIFICATION ---")
    print("1. Fetching Channels...")
    
    # Force fetch
    channels = await matches_scraper.fetch_matches()
    
    if not channels:
        print("❌ Failed to fetch channels!")
        return
        
    print(f"✅ Successfully fetched {len(channels)} channels.")
    
    # Print categories (inferred from names)
    print("\n--- CHANNEL LIST ---")
    for ch in channels[:5]: # Show first 5
        print(f"- {ch['team_home']} | URL: {ch['url'][:50]}...")
    if len(channels) > 5:
        print(f"... and {len(channels)-5} more.")

    # Verify first stream
    if channels:
        first_url = channels[0]['url']
        # The URL in channel is the PROXIED url (http://localhost:8000...)
        # We want to test the REAL upstream source to verify connectivity
        # But we can't easily get it here without parsing. 
        # So we'll test the scraper's internal logic if possible, 
        # OR we just test the scraper result.
        
        # Let's try to extract the real URL from the proxy param for testing
        from urllib.parse import unquote
        if "?url=" in first_url:
            real_url = unquote(first_url.split("?url=")[1])
            print(f"\n2. Testing Real Stream Connectivity: {real_url}")
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer": "https://hamottv.rf.gd/",
                "Origin": "https://hamottv.rf.gd"
            }
            
            # Disable proxy envs for test
            os.environ.pop("HTTP_PROXY", None)
            os.environ.pop("HTTPS_PROXY", None)
            
            try:
                async with httpx.AsyncClient(verify=False, trust_env=False) as client:
                    resp = await client.get(real_url, headers=headers, timeout=10)
                    print(f"Status Code: {resp.status_code}")
                    if resp.status_code == 200:
                        print("✅ Stream is reachable!")
                    elif resp.status_code in [403, 401]:
                        print("⚠️ Stream returned 403/401 - Might need more headers or token.")
                    else:
                        print(f"❌ Stream returned {resp.status_code}")
            except Exception as e:
                print(f"❌ Connection Failed: {e}")

if __name__ == "__main__":
    asyncio.run(verify())
