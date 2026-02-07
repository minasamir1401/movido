
import asyncio
from curl_cffi.requests import AsyncSession

async def check_servers():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://larooza.bond/",
        "Origin": "https://larooza.bond"
    }

    servers = [
        ("Server 1 (OkPrime)", "https://qq.okprime.site/embed-bp1jhrlx62c8.html"),
        ("Server 3 (Film77)", "https://rty1.film77.xyz/embed-nmb307o1jr2n.html"),
        ("Server 11 (Ok.ru)", "https://www.ok.ru/videoembed/11141472717390")
    ]

    async with AsyncSession(impersonate="chrome120", verify=False) as session:
        for name, url in servers:
            print(f"\nScanning {name}: {url}")
            try:
                resp = await session.get(url, headers=headers, allow_redirects=True)
                print(f"Status: {resp.status_code}")
                print(f"Final URL: {resp.url}")
                print(f"Content-Length: {len(resp.text)}")
                if resp.status_code == 200:
                    if "Video has not been found" in resp.text:
                        print("Result: ❌ Video Not Found message detected")
                    elif "Deleted" in resp.text:
                        print("Result: ❌ Video Deleted message detected")
                    else:
                        print("Result: ✅ Seems OK (Content returned)")
                        # Save small snippet
                        print(f"Snippet: {resp.text[:200]}")
                else:
                    print(f"Result: ❌ HTTP Error {resp.status_code}")
            except Exception as e:
                print(f"Result: ❌ Exception: {e}")

if __name__ == "__main__":
    asyncio.run(check_servers())
