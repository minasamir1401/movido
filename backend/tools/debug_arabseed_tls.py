
from curl_cffi.requests import AsyncSession
import asyncio

async def test_fingerprint():
    url = "https://m.arabseed.show/"
    print(f"Testing {url} with curl_cffi...")
    async with AsyncSession(impersonate="chrome110") as s:
        try:
            resp = await s.get(url, timeout=15)
            print(f"Status: {resp.status_code}")
            print(f"Text Snippet: {resp.text[:500]}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_fingerprint())
