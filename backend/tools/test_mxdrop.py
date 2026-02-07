
import asyncio
import re
import httpx
from urllib.parse import urljoin, quote
import sys

async def test_mxdrop():
    url = "https://mxdrop.to/e/7kp4rlz7ip14pv"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://larooza.homes/",
    }
    
    print(f"Testing MXDrop Extraction for: {url}")
    async with httpx.AsyncClient(timeout=30.0, verify=False, follow_redirects=True) as client:
        resp = await client.get(url, headers=headers)
        if resp.status_code != 200:
            print(f"Failed to fetch page: {resp.status_code}")
            return
            
        html = resp.text
        # Look for file:
        match = re.search(r'file:\s*["\'](https://[^"\']+\.mp4[^"\']*)["\']', html)
        if match:
             print(f"Found MP4 (file:): {match.group(1)}")
        else:
             print("Could not find MP4 with 'file:' pattern")
             # Try generic src link
             match = re.search(r'["\']?(?:file|src|url)["\']?\s*[:=]\s*["\'](https://[^"\']+\.mp4[^"\']*)["\']', html)
             if match:
                 print(f"Found MP4 (generic): {match.group(1)}")
             else:
                 print("Total Failure. Dumping first 1000 chars of HTML:")
                 print(html[:1000])

if __name__ == "__main__":
    asyncio.run(test_mxdrop())
