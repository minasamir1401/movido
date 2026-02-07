import asyncio
import base64
import logging
import re
import time
from typing import Any, Dict, List, Optional, Callable
from functools import wraps
from urllib.parse import quote, urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger("anime4up_scraper")

def retry(retries: int = 3, backoff: float = 1.0):
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exc = None
            for i in range(retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exc = e
                    wait = backoff * (2 ** i) + random.uniform(0, 1)
                    logger.warning(f"Retrying {func.__name__} in {wait:.2f}s (Attempt {i+1}/{retries}) due to: {e}")
                    await asyncio.sleep(wait)
            logger.error(f"Failed {func.__name__} after {retries} attempts.")
            raise last_exc
        return wrapper
    return decorator

class Anime4UpScraper:
    def __init__(self):
        self.blogspot_url = "https://anime4upnoads.blogspot.com"
        self.source_url = "https://4r.2qk9x7b.shop"
        self.session = httpx.AsyncClient(timeout=30.0, verify=False, follow_redirects=True)
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "ar,en-US;q=0.9,en;q=0.8",
            "Referer": "https://www.google.com/",
        }
        self._cache = {}
        self._cache_ttl = 3600
        self._semaphore = asyncio.Semaphore(10)
    
    def _is_safe_server_url(self, url: str) -> bool:
        """Check if a server URL is safe to use by filtering out known malicious domains."""
        unsafe_domains = [
            'larooza.homes',
            'gaza.20',
            'bit.ly',  # Often used for malicious redirects
            'tinyurl.com',
            'adf.ly',
            'bc.vc',
            'adfoc.us',
            'shorte.st',
            'ouo.io',
            'clicksfly.com',
            'katfile.com',  # Often problematic
            'pixeldrain.com',  # Sometimes abused
            'rockfile.co',  # Known for suspicious content
        ]
        
        for domain in unsafe_domains:
            if domain in url.lower():
                return False
        return True

    @retry(retries=3, backoff=0.5)
    async def _get_html(self, url: str) -> Optional[str]:
        """Unified HTML fetching with caching, semaphore, and retries."""
        async with self._semaphore:
            now = time.time()
            if url in self._cache:
                ts, data = self._cache[url]
                if now - ts < self._cache_ttl: return data
            
            resp = await self.session.get(url, headers=self.headers)
            if resp.status_code == 200:
                self._cache[url] = (now, resp.text)
                return resp.text
            elif resp.status_code in [404, 403]:
                return None
            else:
                resp.raise_for_status()
            return None

    def _normalize_id(self, url: str) -> str:
        if "blogspot.com" not in url:
            parsed = urlparse(url)
            if parsed.path:
                url = urljoin(self.source_url, parsed.path)
                if parsed.query: url += "?" + parsed.query
        return base64.urlsafe_b64encode(url.encode()).decode()

    def _extract_poster(self, node: BeautifulSoup) -> str:
        p_url = ""
        
        # Helper to check a node for common image attributes
        def get_img_attr(img_node):
            if not img_node: return ""
            # Check for data attributes first (usually contain actual high-res image in lazy loaders)
            return (img_node.get('data-image') or 
                    img_node.get('data-src') or 
                    img_node.get('data-original') or
                    img_node.get('data-lazy-src') or 
                    img_node.get('data-lzy-src') or 
                    img_node.get('data-lzy') or
                    img_node.get('src') or "")

        # 1. If node is itself an img
        if node.name == 'img':
            p_url = get_img_attr(node)
        
        # 2. Try common class-based img tags inside
        if not p_url:
            hq_img = node.select_one('.thumbnail.img-responsive, .anime-thumbnail img, .poster img, .image img, .hover img, img.img-responsive')
            if hq_img:
                p_url = get_img_attr(hq_img)

        # 3. Try any img inside node
        if not p_url:
            img = node.select_one('img')
            if img:
                p_url = get_img_attr(img)
                # If still empty or looks like a placeholder, try specifically data-lzy
                if (not p_url or "placeholder" in p_url or p_url.startswith('data:image')):
                    lzy = img.get('data-lzy')
                    if lzy and "http" in lzy: p_url = lzy

        # 4. Try background-image in child nodes OR node itself
        if not p_url or "placeholder" in p_url or p_url.startswith('data:image'):
            # Check node itself and descendants
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
            # Remove any unwanted characters and clean URL
            p_url = p_url.split('?')[0].split(' ')[0].strip()
            
            # Final check to avoid empty or placeholder strings
            if len(p_url) < 10 or "placeholder" in p_url:
                return ""
                
            return f"/proxy/image?url={quote(p_url)}"
        return ""

    def _extract_cards_source(self, container: BeautifulSoup) -> List[Dict[str, Any]]:
        items = []
        selectors = [
            '.hover.ehover6', 
            '.lucodeia-widget-item', 
            '.col-6.image', 
            '.pinned-card', 
            '.anime-card', 
            '.anime-item',
            'div.image',
            'a.overlay',
            '.anime-card-container'
        ]
        
        for selector in selectors:
            for card in container.select(selector):
                a = card.select_one('a.overlay, a.image') or (card if card.name == 'a' else card.find('a', href=True))
                if not a: continue
                
                url = urljoin(self.source_url, a['href'])
                title_node = card.select_one('h3, .title, .anime-title, .anime-card-title h3')
                badge_node = card.select_one('.badge.light-soft, .quality, .ep-num')
                
                title = a.get('aria-label') or a.get('title') or (title_node.get_text(strip=True) if title_node else "")
                if not title:
                     # Try finding text directly in h3
                     h3 = card.find('h3')
                     if h3: title = h3.get_text(strip=True)
                
                if not title:
                    title = card.get_text(strip=True).split('\n')[0]
                
                # Clean title
                title = title.replace("انمي", "").strip()

                if badge_node:
                    b_txt = badge_node.get_text(strip=True)
                    if b_txt and b_txt not in title:
                        title += f" {b_txt}"
                
                poster = self._extract_poster(card)

                if url and title and len(title) > 1:
                    items.append({
                        "id": self._normalize_id(url),
                        "title": title.strip(),
                        "poster": poster,
                        "type": "series"
                    })
        
        seen = set()
        unique_items = []
        for itm in items:
            if itm['id'] not in seen:
                unique_items.append(itm)
                seen.add(itm['id'])
        return unique_items

    async def fetch_home(self) -> Dict[str, List[Dict[str, Any]]]:
        sections = {}
        all_ids = set()

        def add_items(section_name: str, items: List[Dict[str, Any]]):
            if section_name not in sections:
                sections[section_name] = []
            for item in items:
                if item["id"] not in all_ids:
                    sections[section_name].append(item)
                    all_ids.add(item["id"])

        try:
            html = await self._get_html(self.source_url)
            if html:
                soup = BeautifulSoup(html, 'html.parser')
                # 1. Target main widgets which usually have a clear header and content
                # We exclude broad '.row' unless it has a direct widget header to avoid sucking in the whole page
                for widget in soup.select('.main-widget, .lucodeia-home-widget, .row.lucodeia-home-widget'):
                    header = widget.select_one('.main-didget-head h3, .widget-title, .section-title, h2')
                    if header:
                        sec_title = header.get_text(strip=True)
                        if sec_title and len(sec_title) < 50:
                            items = self._extract_cards_source(widget)
                            if items: add_items(sec_title, items)
                
                # 2. Add 'أخر الحلقات المضافة' specifically if not already in
                if not any("حلقات" in s for s in sections):
                    for widget in soup.select('.row'):
                        header = widget.select_one('h2, h3')
                        if header and "حلقات" in header.get_text():
                           items = self._extract_cards_source(widget)
                           if items: add_items(header.get_text(strip=True), items)

                # 3. Fallback for page-content areas
                if not sections:
                    for widget in soup.select('.page-content-container, .main-content'):
                        items = self._extract_cards_source(widget)
                        if items: add_items("المقترحات", items)
        except Exception as e:
            logger.error(f"Error fetch_home: {e}")
            
        return sections

    async def fetch_anime_list(self, page: int = 1) -> List[Dict[str, Any]]:
        url = f"{self.source_url}/%d9%82%d8%a7%d8%a6%d9%85%d8%a9-%d8%a7%d9%84%d8%a7%d9%86%d9%85%d9%8a/page/{page}/"
        html = await self._get_html(url)
        if not html: return []
        return self._extract_cards_source(BeautifulSoup(html, 'html.parser'))

    async def search(self, query: str) -> List[Dict[str, Any]]:
        url = f"{self.source_url}/?s={quote(query)}"
        html = await self._get_html(url)
        if not html: return []
        return self._extract_cards_source(BeautifulSoup(html, 'html.parser'))

    async def fetch_details(self, safe_id: str) -> Dict[str, Any]:
        try:
            url = base64.urlsafe_b64decode(safe_id).decode()
        except: return {}

        # URL normalization
        parsed = urlparse(url)
        if parsed.path:
            url = urljoin(self.source_url, parsed.path)
            if parsed.query: url += "?" + parsed.query
        
        if not url.startswith('http'): url = urljoin(self.source_url, url)

        html = await self._get_html(url)
        if not html: return {}
        
        soup = BeautifulSoup(html, 'html.parser')
        is_episode = "/episode/" in url
        
        details = {
            "id": safe_id, "title": "", "description": "", "poster": "", "type": "series",
            "meta": {}, "seasons": [], "episodes": [], "servers": [], "download_links": []
        }

        if is_episode:
            # Episode Page
            details["title"] = soup.select_one('.episode-title, h1').get_text(strip=True) if soup.select_one('.episode-title, h1') else "Episode"
            details["servers"] = self._extract_servers_source(soup)
            details["download_links"] = self._extract_downloads_source(soup)
            
            # Fetch parent anime for episodes list and poster
            anime_link = soup.select_one('.anime-page-link a, a[href*="/anime/"], .breadcrumb a[href*="/anime/"]')
            if anime_link:
                a_url = urljoin(self.source_url, anime_link['href'])
                a_html = await self._get_html(a_url)
                if a_html:
                    a_soup = BeautifulSoup(a_html, 'html.parser')
                    details["episodes"] = await self._get_all_episodes(a_soup, a_url)
                    details["description"] = a_soup.select_one('.anime-story').get_text(strip=True) if a_soup.select_one('.anime-story') else ""
                    details["poster"] = self._extract_poster(a_soup.select_one('.anime-thumbnail') or a_soup)
            
            if not details["episodes"]:
                details["episodes"] = await self._get_all_episodes(soup, url)
        else:
            # Anime Page
            details["title"] = soup.select_one('.anime-details-title, h1').get_text(strip=True) if soup.select_one('.anime-details-title, h1') else ""
            details["description"] = soup.select_one('.anime-story').get_text(strip=True) if soup.select_one('.anime-story') else ""
            details["poster"] = self._extract_poster(soup.select_one('.anime-thumbnail') or soup)
            
            details["episodes"] = await self._get_all_episodes(soup, url)
            if details["episodes"]:
                # Fetch first episode for servers/downloads
                first_ep = details["episodes"][0]
                ep_html = await self._get_html(first_ep["url"])
                if ep_html:
                    ep_soup = BeautifulSoup(ep_html, 'html.parser')
                    details["servers"] = self._extract_servers_source(ep_soup)
                    details["download_links"] = self._extract_downloads_source(ep_soup)
            
            # Fallback: If no servers found via episode, try finding them on the main page (common for movies)
            if not details["servers"]:
                 details["servers"] = self._extract_servers_source(soup)
                 if not details["download_links"]:
                     details["download_links"] = self._extract_downloads_source(soup)
        
        # Auto-detect Movie type
        if "movie" in details["title"].lower() or "فيلم" in details["title"] or "movie" in url.lower():
            details["type"] = "movie"
            # For movies, sometimes the episode list is just the movie itself.
            # We ensure we have servers from the 'episode' if it exists.
            if details["episodes"] and not details["servers"]:
                 # If we haven't fetched them yet
                 first_ep = details["episodes"][0]
                 ep_html = await self._get_html(first_ep["url"])
                 if ep_html:
                    ep_soup = BeautifulSoup(ep_html, 'html.parser')
                    details["servers"] = self._extract_servers_source(ep_soup)
                    if not details["download_links"]:
                        details["download_links"] = self._extract_downloads_source(ep_soup)

        return details

    async def _get_all_episodes(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, Any]]:
        all_episodes = self._extract_episodes_source(soup)
        seen_urls = {ep['url'] for ep in all_episodes}
        
        checked_pages = {base_url}
        current_soup = soup
        
        # Sequentially follow pagination links
        for _ in range(20): # Safety limit
            # Find next page link (e.g. <a class="page-numbers next"> or link to current+1)
            next_page = current_soup.select_one('a.page-numbers.next, a.next.page-numbers')
            if not next_page:
                current_active = current_soup.select_one('.page-numbers.current, span.current')
                if current_active:
                    try:
                        next_num = int(current_active.get_text(strip=True)) + 1
                        next_page = current_soup.find('a', class_='page-numbers', string=str(next_num)) or \
                                    current_soup.find('a', string=str(next_num))
                    except: pass
            
            if next_page and next_page.get('href'):
                page_url = urljoin(self.source_url, next_page['href'])
                if page_url in checked_pages: break
                checked_pages.add(page_url)
                
                html = await self._get_html(page_url)
                if not html: break
                
                current_soup = BeautifulSoup(html, 'html.parser')
                new_eps = self._extract_episodes_source(current_soup)
                if not new_eps: break
                
                added_any = False
                for ep in new_eps:
                    if ep['url'] not in seen_urls:
                        all_episodes.append(ep)
                        seen_urls.add(ep['url'])
                        added_any = True
                if not added_any: break
            else:
                break
        
        # Sort all episodes (descending by number)
        try:
            all_episodes.sort(key=lambda x: int(re.search(r'(\d+)', str(x["episode"])).group(1)) if re.search(r'(\d+)', str(x["episode"])) else 0, reverse=True)
        except: pass
        
        return all_episodes

    def _extract_episodes_source(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        episodes = []
        selectors = [
            'ul#ULEpisodesList li a', 
            '.all-episodes-list a', 
            'a.badge.light-soft',
            '.pinned-card a.image',
            '.episodes-list-content a.image',
            '.episodes-list-content .info a',
            '.episodes-card-container a'
        ]
        
        nodes = soup.select(', '.join(selectors))
        seen = set()
        for a in nodes:
            href = a.get('href')
            if not href or "/episode/" not in href: continue
            
            url = urljoin(self.source_url, href)
            if url in seen: continue
            seen.add(url)
            
            text = a.get_text(strip=True)
            title_attr = a.get('title') or ""
            search_text = text + " " + title_attr
            
            num_match = re.search(r'(\d+)', search_text)
            ep_num = num_match.group(1) if num_match else "0"
            
            episodes.append({
                "id": self._normalize_id(url),
                "title": text or f"الحلقة {ep_num}",
                "episode": ep_num, "url": url
            })
            
        return episodes

    def _extract_servers_source(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        servers = []
        selectors = [
            'ul#episode-servers li a',
            'ul#episode-servers li',
            'ul#episode-watch-list li', 
            'ul#show-tabs li',
            '.watch-servers ul li',
            '.episodes-card-container a[data-id]'
        ]
        
        for selector in selectors:
            for node in soup.select(selector):
                url = node.get('data-watch') or node.get('data-url') or node.get('href')
                name = node.get_text(strip=True)
                
                if not url and node.name == 'li':
                    a_tag = node.select_one('a')
                    if a_tag:
                         url = a_tag.get('data-watch') or a_tag.get('data-url') or a_tag.get('href')
                         name = a_tag.get_text(strip=True)

                if not name: name = f"Server {len(servers)+1}"
                
                # Handling iframes
                if (not url or url == "#" or "javascript" in url):
                     # Try finding script or raw iframe
                     pass

                if url and url != "#" and "javascript" not in url:
                    if url.startswith('//'): url = 'https:' + url
                    # Filter out problematic/malicious URLs
                    if self._is_safe_server_url(url) and url not in [s['url'] for s in servers]:
                        servers.append({"name": name.strip(), "url": url, "type": "iframe"})
        return servers

    def _extract_downloads_source(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        downloads = []
        
        # 1. Look for #download container
        download_container = soup.select_one('#download, .download-links, .download-list')
        if download_container:
            # Table rows
            for tr in download_container.select('tr'):
                 a = tr.select_one('a')
                 if a:
                     url = a.get('href')
                     qual = tr.select_one('.quality, .td-quality, .badge')
                     server = tr.select_one('.server, .td-server')
                     name = f"{server.get_text(strip=True) if server else ''} {qual.get_text(strip=True) if qual else ''}".strip()
                     if not name: name = a.get_text(strip=True)
                     if url and "javascript" not in url:
                        downloads.append({"quality": name, "url": urljoin(self.source_url, url)})
            
            if not downloads:
                # Direct links
                for a in download_container.select('a'):
                     url = a.get('href')
                     if url and "javascript" not in url:
                          downloads.append({"quality": a.get_text(strip=True), "url": urljoin(self.source_url, url)})

        # 2. General fallback
        if not downloads:
            table_rows = soup.select('.download-list table tr, .episodes-download table tr, table[role="table"] tr')
            for tr in table_rows:
                a = tr.select_one('a.btn, a[href*="/d/"], a[href*="mega"], a[href*="mp4upload"]')
                if not a: continue
                url = a.get('href')
                if url:
                    downloads.append({"quality": a.get_text(strip=True), "url": urljoin(self.source_url, url)})

        return downloads

    async def fetch_episode(self, safe_id: str) -> Dict[str, Any]:
        return await self.fetch_details(safe_id)

anime4up_scraper = Anime4UpScraper()
