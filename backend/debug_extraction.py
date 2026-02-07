
import asyncio
import base64
import sys
from scraper.anime4up import anime4up_scraper
from bs4 import BeautifulSoup

# Set encoding to utf-8 for Windows console
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())

async def debug_direct():
    url = "https://anime4upnoads.blogspot.com/2020/08/kuroko-no-basket-3rd-season-11.html"
    print(f"DEBUG: Fetching HTML for {url}")
    html = await anime4up_scraper._get_html(url)
    if not html:
        print("DEBUG: No HTML returned!")
        return
    
    soup = BeautifulSoup(html, 'html.parser')
    iframe = soup.select_one('.post-body iframe[src*="anime4up"], .post-body iframe[src*="2qk9x7b"]')
    print(f"DEBUG: Iframe found: {iframe is not None}")
    if iframe:
        print(f"DEBUG: Iframe SRC: {iframe.get('src')}")
        src = iframe.get('src')
        # Simulate the normalization in fetch_details
        if src.startswith('/'):
            src = "https://4r.2qk9x7b.shop" + src
        elif "://" not in src:
            src = "https://" + src
        print(f"DEBUG: Normalized SRC: {src}")
        
        # Test fetching the normalized SRC
        print(f"DEBUG: Fetching Source HTML...")
        s_html = await anime4up_scraper._get_html(src)
        if s_html:
            s_soup = BeautifulSoup(s_html, 'html.parser')
            servers = anime4up_scraper._extract_servers_source(s_soup)
            print(f"DEBUG: Servers extracted: {len(servers)}")
            for s in servers:
                print(f"  - {s['name']}: {s['url']}")
        else:
            print("DEBUG: Failed to fetch Source HTML!")

if __name__ == "__main__":
    asyncio.run(debug_direct())
