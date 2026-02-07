
import httpx
import asyncio
from urllib.parse import quote

async def check_proxy_output():
    # The URL for Server 1
    target_url = "https://qq.okprime.site/embed-bp1jhrlx62c8.html"
    encoded_url = quote(target_url)
    proxy_endpoint = f"http://localhost:8000/proxy/player?url={encoded_url}"
    
    print(f"Requesting: {proxy_endpoint}")
    
    async with httpx.AsyncClient() as client:
        resp = await client.get(proxy_endpoint, follow_redirects=True)
        print(f"Status: {resp.status_code}")
        print("--- Headers ---")
        for k,v in resp.headers.items():
            print(f"{k}: {v}")
        
        print("\n--- Content Snippet (Head) ---")
        print(resp.text[:2000])
        
        print("\n--- Content Snippet (Tail) ---")
        print(resp.text[-500:])

if __name__ == "__main__":
    asyncio.run(check_proxy_output())
