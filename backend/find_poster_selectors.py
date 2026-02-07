import asyncio
from scraper.mycima import scraper
from bs4 import BeautifulSoup
from urllib.parse import urljoin

async def find_poster():
    url = 'https://a.asd.homes/%d9%81%d9%8a%d9%84%d9%85-%d8%a7%d9%84%d8%b3%d8%a7%d8%af%d8%a9-%d8%a7%d9%84%d8%a7%d9%81%d8%a7%d8%b6%d9%84-2025/'
    html = await scraper._get_html(url)
    if not html:
        print("Failed to fetch")
        return
    
    soup = BeautifulSoup(html, 'html.parser')
    
    # Common ArabSeed poster containers
    candidates = soup.select('.Poster img, .poster img, .movie-poster img, .post-thumbnail img, .image img, [style*="background-image"]')
    
    print("--- Found Images ---")
    for img in soup.find_all('img'):
        src = img.get('src') or img.get('data-src') or img.get('data-echo')
        cls = img.get('class')
        parent = img.parent.get('class')
        print(f"SRC: {src} | CLASS: {cls} | PARENT ClS: {parent}")

    print("\n--- Style-based images ---")
    for div in soup.find_all(attrs={"style": True}):
        if 'background-image' in div['style']:
            print(f"Style: {div['style']} | Class: {div.get('class')}")

if __name__ == "__main__":
    asyncio.run(find_poster())
