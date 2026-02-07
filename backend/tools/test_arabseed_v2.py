
import httpx
import asyncio
from bs4 import BeautifulSoup
from urllib.parse import quote

async def test_arabseed():
    url = "https://m2.arabseed.one"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }
    
    print(f"Testing {url}...")
    try:
        async with httpx.AsyncClient(timeout=10, verify=False) as client:
            resp = await client.get(url, headers=headers)
            print(f"Status: {resp.status_code}")
            if resp.status_code == 200:
                print("Content length:", len(resp.text))
                print("Snippet:", resp.text[:500])
                return
            else:
                print(f"Error status: {resp.status_code}")
    except Exception as e:
        print(f"Connection failed: {e}")

    print("\nTrying to find new domain via search...")
    search_query = "عرب سيد الأصلي"
    search_url = f"https://html.duckduckgo.com/html/?q={quote(search_query)}"
    try:
        async with httpx.AsyncClient(timeout=15, verify=False) as client:
            resp = await client.get(search_url, headers=headers)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            results = soup.select('.result__a')
            for link in results[:5]:
                print(f"Found: {link.get('href')} - {link.get_text(strip=True)}")
    except Exception as e:
        print(f"Search failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_arabseed())
