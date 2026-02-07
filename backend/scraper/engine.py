import asyncio
import base64
import hashlib
import logging
import os
import random
import re
import time
from typing import Any, Dict, List, Optional, Callable
from functools import wraps
from urllib.parse import quote, urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
try:
    from curl_cffi.requests import AsyncSession
    HAS_CURL_CFFI = True
except ImportError:
    HAS_CURL_CFFI = False

# Optional dependencies for bypasses
try:
    import undetected_chromedriver as uc
    HAS_SELENIUM = True
except ImportError:
    HAS_SELENIUM = False

logger = logging.getLogger("scraper")

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

class ScraperConfig:
    MIRRORS = [
        "https://q.larozavideo.net", 
        "https://larooza.mom", 
        "https://larooza.site", 
        "https://m.laroza-tv.net",
        "https://larooza.lol",
        "https://larooza.cfd",
        "https://larooza.video"
    ]
    DEFAULT_BASE_URL = "https://larooza.cfd"
    CATEGORY_KEYWORDS = {
        "arabic-movies": ["أفلام عربية", "افلام عربية", "افلام عربي", "arabic-movies33"],
        "english-movies": ["افلام اجنبية", "أفلام أجنبية", "افلام اجنبي", "أجنبي", "all_movies_13"],
        "indian-movies": ["افلام هندي", "أفلام هندية", "هندي", "indian-movies9"],
        "anime-movies": ["افلام انمي", "أفلام أنمي", "انمي", "anime-movies-7"],
        "dubbed-movies": ["افلام مدبلجة", "أفلام مدبلجة", "مدبلج", "7-aflammdblgh"],
        "turkish-movies": ["افلام تركية", "أفلام تركية", "8-aflam3isk"],
        "turkish-series": ["مسلسلات تركية", "تركي", "turkish-3isk-seriess47"],
        "arabic-series": ["مسلسلات عربية", "عربي", "arabic-series46"],
        "english-series": ["مسلسلات اجنبية", "أجنبي", "english-series10"],
        "indian-series": ["مسلسلات هندية", "هندي", "11indian-series"],
        "ramadan-2025": ["رمضان 2025", "13-ramadan-2025"],
        "ramadan-2024": ["رمضان 2024", "28-ramadan-2024"],
        "ramadan-2023": ["رمضان 2023", "10-ramadan-2023"],
        "asian-movies": ["آسيوي", "اسيوي", "آسيوية", "6-asian-movies"],
        "asian-series": ["مسلسلات اسياوية", "6-asya"],
        "tv-programs": ["برامج تلفزيون", "برامج", "tv-programs12"],
        "plays": ["مسرحيات", "مسرحية", "masrh-5"],
        "anime-series": ["مسلسلات انمي", "كرتون", "6-anime-series"],
    }
    
class LaroozaScraper:
    """
    Refactored Larooza Scraper following Clean Code and SOLID principles.
    """
    def __init__(self):
        self.base_url = ScraperConfig.DEFAULT_BASE_URL
        if HAS_CURL_CFFI:
            self.session = AsyncSession(impersonate="chrome120", timeout=30, verify=False)
        else:
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
        self._category_map = {}
        self._discovery_lock = asyncio.Lock()
        self._last_discovery = 0

    @retry(retries=3, backoff=0.5)
    async def _get_html(self, url: str) -> Optional[str]:
        """Unified HTML fetching with caching, semaphore protection, and retries."""
        async with self._semaphore:
            now = time.time()
            if url in self._cache:
                ts, data = self._cache[url]
                if now - ts < self._cache_ttl:
                    return data

            if HAS_CURL_CFFI:
                resp = await self.session.get(url, headers=self.headers)
            else:
                resp = await self.session.get(url, headers=self.headers)
            
            if resp.status_code == 200:
                self._cache[url] = (now, resp.text)
                return resp.text
            elif resp.status_code in [404, 403]:
                # Don't retry permanent errors
                return None
            else:
                if hasattr(resp, 'raise_for_status'):
                    resp.raise_for_status()
                else:
                    raise Exception(f"HTTP Error {resp.status_code}")
            return None

    def _extract_items(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, Any]]:
        """Cleanly extraction of content items from page soup."""
        items = []
        containers = soup.select('.thumbnail, .pm-li-video, .video-block, .movie-item')
        
        for tag in containers:
            link_node = tag.find('a', href=True)
            if not link_node: continue
            
            href = link_node['href']
            full_url = urljoin(base_url, href)
            title = link_node.get('title') or tag.get_text(strip=True)
            
            # Image extraction with fallbacks
            img_node = tag.find('img')
            img_url = ""
            if img_node:
                img_url = img_node.get('data-echo') or img_node.get('src')
            
            items.append({
                "id": base64.urlsafe_b64encode(full_url.encode()).decode(),
                "title": self._clean_title(title),
                "poster": f"/proxy/image?url={quote(urljoin(base_url, img_url))}" if img_url else "",
                "type": "series" if "حلقة" in title or "مسلسل" in title else "movie"
            })
        return items

    def _clean_title(self, title: str) -> str:
        """Removes noise and garbage characters from titles."""
        noise = ["مشاهدة", "فيلم", "كامل", "مترجم", "اون لاين", "HD", "تحميل", "بجودة", "عالية", "", "اضغط هنا"]
        for n in noise:
            title = title.replace(n, "").strip()
        # Remove extra whitespace and leading/trailing dashes
        title = re.sub(r'\s+', ' ', title)
        return re.sub(r'\d{4}', '', title).strip("- ")

    async def fetch_home(self, page: int = 1) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/newvideos1.php?page={page}"
        html = await self._get_html(url)
        return self._extract_items(BeautifulSoup(html, 'html.parser'), url) if html else []

    async def search(self, query: str) -> List[Dict[str, Any]]:
        # Modified to use the correct keywords parameter
        url = f"{self.base_url}/search.php?keywords={quote(query)}"
        html = await self._get_html(url)
        # Search page uses the same container structure as Home
        return self._extract_items(BeautifulSoup(html, 'html.parser'), url) if html else []

    async def fetch_category(self, cat_id: str, page: int = 1) -> List[Dict[str, Any]]:
        # Resolve actual cat ID from keywords if possible
        actual_id = cat_id
        for key, aliases in ScraperConfig.CATEGORY_KEYWORDS.items():
            if cat_id == key:
                # The last item in aliases is the site ID
                actual_id = aliases[-1]
                break
        
        url = f"{self.base_url}/category.php?cat={actual_id}&page={page}"
        html = await self._get_html(url)
        return self._extract_items(BeautifulSoup(html, 'html.parser'), url) if html else []

    async def fetch_details(self, safe_id: str) -> Dict[str, Any]:
        """Detailed content extraction with server and download link resolution."""
        try:
            url = base64.urlsafe_b64decode(safe_id).decode()
        except Exception: return {}

        html = await self._get_html(url)
        if not html: return {}

        soup = BeautifulSoup(html, 'html.parser')
        title = soup.find('h1').get_text(strip=True) if soup.find('h1') else "Unknown"
        
        details = {
            "id": safe_id,
            "title": title,
            "description": self._extract_description(soup),
            "poster": self._extract_poster(soup, url),
            "type": "series" if "حلقة" in title else "movie",
            "servers": [],
            "download_links": await self._extract_downloads(url),
            "episodes": [],
        }

        # Try to extract servers from current page
        details["servers"] = self._extract_servers(soup, html)
        
        # Always try to check play.php if no servers or to get more (some mirrors hide servers in play.php)
        if not details["servers"] or len(details["servers"]) < 2:
            play_url = url.replace('video.php', 'play.php').replace('watch.php', 'play.php')
            if 'play.php' in play_url and play_url != url:
                play_html = await self._get_html(play_url)
                if play_html:
                    play_soup = BeautifulSoup(play_html, 'html.parser')
                    extra_servers = self._extract_servers(play_soup, play_html)
                    # Merge servers
                    seen_urls = {s['url'] for s in details["servers"]}
                    for s in extra_servers:
                        if s['url'] not in seen_urls:
                            details["servers"].append(s)
                            seen_urls.add(s['url'])
        
        if details["type"] == "series":
            details["episodes"] = await self._extract_series_episodes(soup, title, url)
            
        return details

    def _extract_description(self, soup: BeautifulSoup) -> str:
        desc_node = soup.select_one('.story, .desc, .entry-content')
        return desc_node.get_text(strip=True) if desc_node else ""

    def _extract_poster(self, soup: BeautifulSoup, base_url: str) -> str:
        img_node = soup.select_one('.poster img, .movie-poster img')
        if img_node:
            poster_url = img_node.get('src') or img_node.get('data-src')
            return f"/proxy/image?url={quote(urljoin(base_url, poster_url))}"
        return ""

    async def _extract_series_episodes(self, soup: BeautifulSoup, title: str, base_url: str) -> List[Dict]:
        """Extracts episodes from the series page without duplicates."""
        episodes = []
        seen_ids = set()
        
        # 1. Look for episode lists
        containers = soup.select('.EpisodesList a, .episodes-list a, .series-episodes a, .Episode--List a, #episodes a, .episode-item a')
        
        # 2. Fallback search for links containing "حلقة"
        if not containers:
            containers = [a for a in soup.find_all('a', href=True) if "حلقة" in a.get_text()]

        for a in containers:
            href = a.get('href')
            if not href or 'video.php' not in href: continue
            
            full_url = urljoin(base_url, href).split('&')[0] # Basic normalization
            ep_text = a.get_text(strip=True)
            
            # Skip "Next/Prev" links if they don't look like specific episode items
            if "التالية" in ep_text or "السابقة" in ep_text:
                if not any(cls in (a.get('class') or []) for cls in ['EpisodesList', 'episodes-list']):
                    continue

            ep_id = base64.urlsafe_b64encode(full_url.encode()).decode()
            if ep_id in seen_ids: continue
            
            # Extract episode number
            match = re.search(r'(\d+)', ep_text)
            ep_num = int(match.group(1)) if match else 0
            
            episodes.append({
                "id": ep_id,
                "title": self._clean_title(ep_text),
                "episode": ep_num,
                "url": full_url
            })
            seen_ids.add(ep_id)
            
        return sorted(episodes, key=lambda x: x['episode'])

    def _extract_servers(self, soup: BeautifulSoup, html: str) -> List[Dict[str, str]]:
        """Handles both static and dynamic server extraction."""
        servers = []
        seen_urls = set()

        # 1. Target the identified .WatchList li structure
        for li in soup.select('ul.WatchList li[data-embed-url]'):
            url = li.get('data-embed-url')
            # Look for name in strong tag or use current index
            name_node = li.select_one('strong')
            name = name_node.get_text(strip=True) if name_node else li.get_text(strip=True)
            if not name or name == "":
                name = f"سيرفر {len(servers) + 1}"
            
            if url and url not in seen_urls:
                servers.append({"name": name, "url": url, "type": "iframe"})
                seen_urls.add(url)
        
        # 2. Fallback for other mirrors or container types
        if not servers:
            selectors = [
                '.server-item', '.servers-list li', 
                '#watch-servers li', '.EpisodesLinks li', '.play-list li'
            ]
            for selector in selectors:
                for li in soup.select(selector):
                    url = li.get('data-embed-url') or li.get('data-url') or li.get('data-link') or li.get('data-href')
                    name = li.get_text(strip=True) or f"سيرفر {len(servers) + 1}"
                    if url and url not in seen_urls:
                        servers.append({"name": name, "url": url, "type": "iframe"})
                        seen_urls.add(url)
        
        # 3. Last fallback: direct iframe extraction (excluding ads)
        if not servers:
            for iframe in soup.select('iframe[src*="http"]'):
                src = iframe.get('src')
                if src and not any(x in src for x in ['facebook', 'google', 'twitter', 'adnxs', 'ads', 'analytics']):
                    label = f"سيرفر مباشر {len(servers) + 1}"
                    if src not in seen_urls:
                        servers.append({"name": label, "url": src, "type": "iframe"})
                        seen_urls.add(src)

        return servers

    async def _extract_downloads(self, url: str) -> List[Dict[str, str]]:
        dl_urls = [url.replace('video.php', 'download.php'), url.replace('play.php', 'download.php')]
        links = []
        seen_urls = set()

        for dl_url in dl_urls:
            html = await self._get_html(dl_url)
            if not html: continue
            
            soup = BeautifulSoup(html, 'html.parser')
            for a in soup.select('a[href*="http"]'):
                href = a.get('href')
                text = a.get_text(strip=True)
                
                # Check for download indicators
                is_dl = any(q in text.lower() or q in href.lower() for q in ['download', 'تحميل', '720', '1080', '480', 'mp4', 'mkv'])
                if is_dl and href not in seen_urls and 'larooza' not in href:
                    clean_label = self._clean_title(text).replace("اضغط هنا للتحميل", "").strip()
                    links.append({"quality": clean_label or urlparse(href).netloc, "url": href})
                    seen_urls.add(href)
            if links: break
        return links

scraper = LaroozaScraper()
