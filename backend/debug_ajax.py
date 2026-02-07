import asyncio
import httpx
try:
    from curl_cffi.requests import AsyncSession
    HAS_CURL_CFFI = True
except ImportError:
    HAS_CURL_CFFI = False

async def debug_ajax():
    base_url = "https://asd.pics"
    post_id = "832310"
    token = "a2e742cdeb" # From subagent
    quality = "1080"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Referer": f"{base_url}/%d9%81%d9%8a%d9%84%d9%85-the-wrecking-crew-2026/watch/"
    }
    
    data = {
        "post_id": post_id,
        "quality": quality,
        "csrf_token": token
    }
    
    print(f"Testing AJAX with post_id={post_id}, quality={quality}, token={token}")
    
    if HAS_CURL_CFFI:
        async with AsyncSession(impersonate="chrome120") as s:
            # Need to visit the home page first to get cookies maybe?
            await s.get(base_url, headers={"User-Agent": headers["User-Agent"]})
            resp = await s.post(f"{base_url}/get__quality__servers/", data=data, headers=headers)
            print(f"Status: {resp.status_code}")
            print(f"Response: {resp.text[:500]}")
    else:
        async with httpx.AsyncClient() as s:
            resp = await s.post(f"{base_url}/get__quality__servers/", data=data, headers=headers)
            print(f"Status: {resp.status_code}")
            print(f"Response: {resp.text[:500]}")

if __name__ == "__main__":
    asyncio.run(debug_ajax())
