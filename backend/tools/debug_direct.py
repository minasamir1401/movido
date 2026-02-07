
import asyncio
import base64
import sys
import os
import re

# Add backend to sys.path
sys.path.append(os.getcwd())

from backend.scraper.engine import scraper as larooza_scraper

async def debug_direct():
    test_urls = [
        "https://mxdrop.to/e/7kp4rlz7ip14pv",
        "https://vidspeed.org/embed-3qwr1a0iitb9.html",
        "https://vidmoly.net/embed-r3jhudzh1w51.html"
    ]
    
    for url in test_urls:
        print(f"\n--- Testing {url} ---")
        direct = await larooza_scraper._extract_direct_url(url)
        if direct:
            print(f"SUCCESS: {direct}")
        else:
            print("FAILED to extract direct URL")
            # Let's try to see if we can get HTML at all
            headers = larooza_scraper.headers.copy()
            headers["Referer"] = url
            html = await larooza_scraper._get_html(url, headers=headers)
            if html:
                print(f"HTML Length: {len(html)}")
                # Show snippets around patterns
                for pattern in [r'file:', r'src:', r'file\s*:', r'source']:
                    match = re.search(pattern, html, re.IGNORECASE)
                    if match:
                        start = max(0, match.start() - 50)
                        end = min(len(html), match.end() + 200)
                        print(f"Snippet for '{pattern}':\n{html[start:end]}\n")
            else:
                print("Could not fetch HTML at all")

if __name__ == "__main__":
    asyncio.run(debug_direct())
