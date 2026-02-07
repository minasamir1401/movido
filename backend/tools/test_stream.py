import httpx
import logging
import asyncio
from zenrows import ZenRowsClient

ZENROWS_KEY = "928aad4cd57cfe96ca06ed080752734304acdac4"
from urllib.parse import quote

# http://s.showplustv.pro:80/live/784512589635/785412587453/46761.png
SOURCE_URL = "http://s.showplustv.pro:80/live/784512589635/785412587453/46761.png"
HAMOT_PROXY_URL = f"https://hamottv.rf.gd/?google_stream={quote(SOURCE_URL)}"

async def test_direct():
    pass # Skip direct for now

def test_zenrows():
    print(f"\nTesting ZenRows access to Hamot Proxy: {HAMOT_PROXY_URL}...")
    client = ZenRowsClient(ZENROWS_KEY)
    try:
        # We expect a redirect or the content
        resp = client.get(HAMOT_PROXY_URL)
        print(f"ZenRows Status: {resp.status_code}")
        print(f"ZenRows Headers: {resp.headers}")
        print(f"ZenRows Content Start: {resp.text[:200]}")
    except Exception as e:
        print(f"ZenRows failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_direct())
    test_zenrows()
