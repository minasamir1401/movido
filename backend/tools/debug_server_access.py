
import asyncio
import httpx
from bs4 import BeautifulSoup
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("server_debug")

async def debug_servers():
    base_url = "https://larooza.bond/video.php?vid=Yv7Y1Y4JE"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://larooza.bond/",
    }

    print(f"Fetching source page: {base_url}")
    async with httpx.AsyncClient(verify=False, follow_redirects=True) as client:
        resp = await client.get(base_url, headers=headers)
        if resp.status_code != 200:
            print(f"Failed to fetch source page: {resp.status_code}")
            return

        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Extract servers like the engine does
        servers = []
        # 1. From data-embed-url
        for el in soup.select('[data-embed-url]'):
            servers.append({"name": el.get_text(strip=True), "url": el.get('data-embed-url')})
        
        # 2. From list items if not found
        if not servers:
            for li in soup.select('.server-item, .servers-list li, #watch-servers li'):
                url = li.get('data-embed-url') or li.get('data-url')
                if url:
                    servers.append({"name": li.get_text(strip=True), "url": url})

        print(f"\nFound {len(servers)} servers.")
        
        # Test specific problematic servers
        for server in servers:
            url = server['url']
            name = server['name']
            
            # Focus on OkPrime and Film77 (or others if needed)
            if "okprime" in url or "film77" in url or "ok.ru" in url:
                print(f"\nTesting Server: {name} => {url}")
                await test_server_access(client, url)

async def test_server_access(client, url):
    # Test cases
    scenarios = [
        {"name": "Ref: larooza", "headers": {"Referer": "https://larooza.bond/", "Origin": "https://larooza.bond"}},
        {"name": "Ref: self", "headers": {"Referer": url, "Origin": "/".join(url.split('/')[:3])}},
        {"name": "No Referer", "headers": {"Referer": "", "Origin": ""}},
        {"name": "Ref: Google", "headers": {"Referer": "https://www.google.com/"}},
    ]

    for scenario in scenarios:
        try:
            # Merge with default UA
            h = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
            }
            h.update(scenario['headers'])
            
            # Don't follow redirects automatically to see 302s
            resp = await client.get(url, headers=h, follow_redirects=False, timeout=10.0)
            
            status = resp.status_code
            redirect_to = resp.headers.get("location", "") if status in [301, 302, 303, 307] else ""
            content_len = len(resp.text)
            title = ""
            if status == 200:
                s = BeautifulSoup(resp.text, 'html.parser')
                title = s.title.string.strip() if s.title else "No Title"
            
            print(f"  [{scenario['name']}] Status: {status} | Loc: {redirect_to} | Len: {content_len} | Title: {title}")
            
        except Exception as e:
            print(f"  [{scenario['name']}] Error: {e}")

if __name__ == "__main__":
    asyncio.run(debug_servers())
