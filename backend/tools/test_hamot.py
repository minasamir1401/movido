import httpx
import asyncio
import logging
from bs4 import BeautifulSoup

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("hamot_test")

async def fetch_hamot():
    url = "https://hamottv.rf.gd/"
    logger.info(f"Fetching {url}...")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "ar,en-US;q=0.9,en;q=0.8",
        "Referer": "https://www.google.com/"
    }

    async with httpx.AsyncClient(timeout=30.0, verify=False, follow_redirects=True) as client:
        try:
            resp = await client.get(url, headers=headers)
            logger.info(f"Status Code: {resp.status_code}")
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                # Try to find matches
                # searching for common likely classes
                matches = soup.select('.match-container, .match-card, .event, .game')
                if not matches:
                    # simplistic fallback: look for divs with 2 team names?
                    logger.info("No obvious match classes found. Dumping general structure...")
                    for div in soup.find_all('div', class_=True)[:10]:
                        logger.info(f"Div classes: {div.get('class')}")
                else:
                    logger.info(f"Found {len(matches)} potential matches.")
                
                # Save to file for user/agent to inspect if needed
                with open("hamot_dump.html", "w", encoding="utf-8") as f:
                    f.write(resp.text)
                logger.info("Saved hamot_dump.html")
                
        except Exception as e:
            logger.error(f"Error fetching: {e}")

if __name__ == "__main__":
    asyncio.run(fetch_hamot())
