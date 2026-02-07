
import asyncio
import os
from bs4 import BeautifulSoup
from curl_cffi.requests import AsyncSession

async def inspect():
    url = "https://larooza.bond/video.php?vid=Yv7Y1Y4JE"
    # Also check play.php as that's often where the actual player is
    play_url = "https://larooza.bond/play.php?vid=Yv7Y1Y4JE"
    
    urls = [url, play_url]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://larooza.bond/",
    }

    async with AsyncSession(impersonate="chrome120", verify=False) as session:
        for u in urls:
            print(f"\n--- Fetching {u} ---")
            try:
                resp = await session.get(u, headers=headers)
                print(f"Status: {resp.status_code}")
                content = resp.text
                print(f"Length: {len(content)}")
                
                # Save for inspection
                filename = f"c:\\Users\\Mina\\Desktop\\lmina\\backend\\debug_{u.split('/')[-1].replace('?', '_')}.html"
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(content)
                print(f"Saved to {filename}")

                soup = BeautifulSoup(content, 'html.parser')
                
                # Check for servers
                servers = soup.select('[data-embed-url]')
                print(f"Found {len(servers)} servers via data-embed-url")
                for s in servers:
                    print(f" - {s.get_text(strip=True)}: {s.get('data-embed-url')}")
                    
                if not servers:
                    print("Trying alternative selectors...")
                    servers_legacy = soup.select('.server-item, .servers-list li, #watch-servers li')
                    print(f"Found {len(servers_legacy)} via legacy selectors")
                    for s in servers_legacy:
                        print(f" - L: {s.get_text(strip=True)}: {s.get('data-embed-url') or s.get('data-url')}")

            except Exception as e:
                print(f"Error fetching {u}: {e}")

if __name__ == "__main__":
    asyncio.run(inspect())
