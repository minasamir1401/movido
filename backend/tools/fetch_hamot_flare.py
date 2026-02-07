import httpx
import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("hamot_flare")

async def fetch_via_flaresolverr():
    flaresolverr_url = "http://localhost:8191/v1"
    target_url = "https://hamottv.rf.gd/"
    
    payload = {
        "cmd": "request.get",
        "url": target_url,
        "maxTimeout": 60000
    }
    
    logger.info(f"Requesting {target_url} via FlareSolverr...")
    async with httpx.AsyncClient(timeout=90.0) as client:
        try:
            resp = await client.post(flaresolverr_url, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('status') == 'ok':
                    html = data.get('solution', {}).get('response', '')
                    logger.info("Success! Saving html...")
                    with open("hamot_flare_dump.html", "w", encoding="utf-8") as f:
                        f.write(html)
                else:
                    logger.error(f"FlareSolverr returned status: {data.get('status')} - {data}")
            else:
                logger.error(f"FlareSolverr HTTP error: {resp.status_code}")
        except Exception as e:
            logger.error(f"Connection error: {e}")

if __name__ == "__main__":
    asyncio.run(fetch_via_flaresolverr())
