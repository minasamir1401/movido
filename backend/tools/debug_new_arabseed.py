
import httpx
import asyncio
from bs4 import BeautifulSoup

async def check_new_arabseed():
    url = "https://m.arabseed.show/recently/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }
    
    print(f"Fetching {url}...")
    try:
        async with httpx.AsyncClient(timeout=15, verify=False) as client:
            resp = await client.get(url, headers=headers)
            print(f"Status: {resp.status_code}")
            
            soup = BeautifulSoup(resp.text, 'html.parser')
            # Check for a.movie__block
            items = soup.select('a.movie__block')
            print(f"Found {len(items)} items using 'a.movie__block'")
            
            if len(items) > 0:
                for item in items[:5]:
                    print(f"Item: {item.get('title') or item.get_text(strip=True)} -> {item.get('href')}")
            else:
                print("Snippet of HTML:")
                print(resp.text[:1000])

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_new_arabseed())
