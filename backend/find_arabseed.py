
import httpx
import asyncio
from bs4 import BeautifulSoup
from urllib.parse import quote, unquote
import re

async def find_real_arabseed():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }
    
    queries = [
        "رابط موقع عرب سيد",
        "arabseed official site",
        "موقع عرب سيد 2026"
    ]
    
    found_urls = []
    
    for q in queries:
        print(f"Searching for: {q}")
        search_url = f"https://html.duckduckgo.com/html/?q={quote(q)}"
        try:
            async with httpx.AsyncClient(timeout=15, verify=False) as client:
                resp = await client.get(search_url)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                for link in soup.select('.result__a'):
                    href = link.get('href')
                    if 'uddg=' in href:
                        url = unquote(re.search(r'uddg=([^&]+)', href).group(1))
                        if any(x in url.lower() for x in ["arab", "seed", "asd"]):
                            found_urls.append(url)
        except Exception as e:
            print(f"  Search failed: {e}")

    unique_urls = list(set(found_urls))
    print(f"\nFound {len(unique_urls)} candidate URLs:")
    for u in unique_urls:
        print(f" - {u}")
        
    for u in unique_urls:
        parsed = urlparse(u)
        domain = f"{parsed.scheme}://{parsed.netloc}"
        print(f"\nTesting domain: {domain}")
        try:
            async with httpx.AsyncClient(timeout=5, verify=False) as client:
                resp = await client.get(domain, headers=headers)
                print(f"  Status: {resp.status_code}")
                if resp.status_code == 200 and ("arabseed" in resp.text.lower() or "aseed" in resp.text.lower()):
                    if "movie__block" in resp.text or "recently" in resp.text or "category" in resp.text:
                        print(f"  ⭐ BINGO: {domain} looks like the actual site!")
        except:
            print(f"  Connection failed")

from urllib.parse import urlparse
if __name__ == "__main__":
    asyncio.run(find_real_arabseed())
