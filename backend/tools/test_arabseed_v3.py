
import httpx
import asyncio
from bs4 import BeautifulSoup
from urllib.parse import quote, unquote
import re

async def test_domain(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }
    print(f"Testing {url}...")
    try:
        async with httpx.AsyncClient(timeout=10, verify=False) as client:
            resp = await client.get(url, headers=headers)
            print(f"  Status: {resp.status_code}")
            if resp.status_code == 200:
                if "arabseed" in resp.text.lower() or "aseed" in resp.text.lower():
                    print(f"  ✅ SUCCESS: {url} looks like ArabSeed")
                    return True
    except Exception as e:
        print(f"  ❌ FAILED: {url} - {e}")
    return False

async def main():
    candidates = [
        "https://m2.arabseed.one",
        "https://www.arabseed.site",
        "https://arabseed.pw",
        "https://arabseed.one",
        "https://asd.homes"
    ]
    
    for c in candidates:
        if await test_domain(c):
            print(f"\nWINNER: {c}")
            # break # test all to be sure
            
    print("\nSearching for more...")
    search_query = "موقع عرب سيد الجديد"
    search_url = f"https://html.duckduckgo.com/html/?q={quote(search_query)}"
    try:
        async with httpx.AsyncClient(timeout=15, verify=False) as client:
            resp = await client.get(search_url)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            for link in soup.select('.result__a'):
                href = link.get('href')
                if 'uddg=' in href:
                    url = unquote(re.search(r'uddg=([^&]+)', href).group(1))
                    if 'arabseed' in url.lower():
                        await test_domain(url)
    except Exception as e:
        print(f"Search failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
