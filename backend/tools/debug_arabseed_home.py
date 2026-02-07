
import httpx
import asyncio
from bs4 import BeautifulSoup

async def check_arabseed_home():
    base_url = "https://m2.arabseed.one"
    url = f"{base_url}/recently/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }
    
    print(f"Fetching {url}...")
    try:
        async with httpx.AsyncClient(timeout=15, verify=False) as client:
            resp = await client.get(url, headers=headers)
            print(f"Status: {resp.status_code}")
            if resp.status_code != 200:
                print("Fallback to home page...")
                resp = await client.get(base_url, headers=headers)
                print(f"Home Status: {resp.status_code}")
            
            soup = BeautifulSoup(resp.text, 'html.parser')
            # The current scraper looks for a.movie__block
            items = soup.select('a.movie__block')
            print(f"Found {len(items)} items using 'a.movie__block'")
            
            if len(items) == 0:
                print("Scanning all <a> tags for possible items...")
                # Search for alternate selectors
                for tag in soup.find_all('a', limit=100):
                    if tag.get('href') and 'video/' in tag.get('href', ''):
                        print(f"Candidate: {tag.get('href')} - {tag.get_text(strip=True)}")
                
                # Check for common container classes
                for div in soup.find_all('div', class_=True, limit=50):
                    if any(x in div.get('class') for x in ['item', 'movie', 'post', 'video']):
                        print(f"Div candidate: {div.get('class')}")
            else:
                for item in items[:5]:
                    print(f"Item: {item.get('title') or item.get_text(strip=True)} -> {item.get('href')}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_arabseed_home())
