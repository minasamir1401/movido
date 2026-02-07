
import asyncio
import httpx

MIRRORS = [
    "https://q.larozavideo.net", 
    "https://larooza.mom", 
    "https://larooza.site", 
    "https://m.laroza-tv.net",
    "https://larooza.lol",
    "https://larooza.cfd",
    "https://larooza.video",
    "https://laroza.net",
    "https://laroza.one"
]

async def check_mirror(url):
    try:
        async with httpx.AsyncClient(verify=False, timeout=5.0) as client:
            resp = await client.get(url, follow_redirects=True)
            print(f"{url}: {resp.status_code}")
            if resp.status_code == 200 and "Video" in resp.text:
                return url
    except Exception as e:
        print(f"{url}: Failed ({e})")
    return None

async def main():
    print("Checking mirrors...")
    tasks = [check_mirror(url) for url in MIRRORS]
    results = await asyncio.gather(*tasks)
    working = [r for r in results if r]
    print(f"Working mirrors: {working}")

if __name__ == "__main__":
    asyncio.run(main())
