import httpx
import asyncio

async def fetch():
    url = "https://hamottv.rf.gd/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    async with httpx.AsyncClient(verify=False, follow_redirects=True, timeout=30.0) as client:
        try:
            resp = await client.get(url, headers=headers)
            print(resp.text)
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(fetch())
