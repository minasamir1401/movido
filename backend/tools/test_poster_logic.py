from bs4 import BeautifulSoup
from urllib.parse import quote, urljoin
import re

class MockScraper:
    def __init__(self):
        self.source_url = "https://4r.2qk9x7b.shop"

    def _extract_poster(self, node: BeautifulSoup) -> str:
        p_url = ""
        def get_img_attr(img_node):
            if not img_node: return ""
            return (img_node.get('data-image') or 
                    img_node.get('data-src') or 
                    img_node.get('data-lazy-src') or 
                    img_node.get('data-lzy-src') or 
                    img_node.get('src') or "")

        if node.name == 'img':
            p_url = get_img_attr(node)
        
        if not p_url:
            hq_img = node.select_one('.thumbnail.img-responsive, .anime-thumbnail img, .poster img, .image img, .hover img')
            if hq_img:
                p_url = get_img_attr(hq_img)

        if not p_url:
            img = node.select_one('img')
            if img:
                p_url = get_img_attr(img)
                if (not p_url or "placeholder" in p_url or p_url.startswith('data:image')) and img.get('data-lzy'):
                    lzy = img.get('data-lzy')
                    if lzy and "http" in lzy: p_url = lzy

        if not p_url or "placeholder" in p_url or p_url.startswith('data:image'):
            potential_bg_nodes = [node] + node.select('.image, .poster, .img, .thumbnail, .hover, a[style*="background-image"], div[style*="background-image"]')
            for s_node in potential_bg_nodes:
                if not s_node: continue
                style = s_node.get('style', '') or ""
                m = re.search(r'url\s*\(\s*["\']?(.*?)["\']?\s*\)', style)
                if m:
                    p_url = m.group(1)
                    if p_url and not ("placeholder" in p_url or p_url.startswith('data:image')):
                        break
            
        if p_url:
            if p_url.startswith('//'): p_url = 'https:' + p_url
            if p_url.startswith('/'): p_url = urljoin(self.source_url, p_url)
            p_url = p_url.split('?')[0].strip()
            p_url = p_url.split(' ')[0] 
            return f"/proxy/image?url={quote(p_url)}"
        return ""

html = """
<div class="anime-card-container">
<div class="anime-card-poster">
    <div class="hover ehover6">
        <img class="img-responsive imgInit"
             data-image="https://4t.m8r2f9a.shop/wp-content/uploads/2020/05/DFJ455SD4GF465DFG.png"
             alt="Naruto: Shippuuden" />
        <a href="https://4t.m8r2f9a.shop/anime/naruto-shippuuden/" class="overlay"></a>
    </div>
</div>
</div>
"""

scraper = MockScraper()
soup = BeautifulSoup(html, 'html.parser')
card = soup.select_one('.anime-card-container')
poster = scraper._extract_poster(card)
print(f"Extracted Poster: {poster}")
