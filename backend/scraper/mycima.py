import asyncio
import base64
import logging
import re
import time
from typing import Any, Dict, List, Optional, Callable
from functools import wraps
from urllib.parse import quote, urljoin, urlparse, unquote

import httpx
from bs4 import BeautifulSoup

try:
    from curl_cffi.requests import AsyncSession
    HAS_CURL_CFFI = True
except ImportError:
    HAS_CURL_CFFI = False

logger = logging.getLogger("arabseed_scraper")

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
                    wait = backoff * (2 ** i)
                    logger.warning(f"Retrying {func.__name__} in {wait:.2f}s (Attempt {i+1}/{retries}) due to: {e}")
                    await asyncio.sleep(wait)
            logger.error(f"Failed {func.__name__} after {retries} attempts.")
            raise last_exc
        return wrapper
    return decorator

class MyCimaScraper:
    """
    Scraper for ArabSeed (a.asd.homes) 
    Replacing MyCima as requested by user.
    """
    def __init__(self):
        self.base_url = "https://a.asd.homes" 
        
        if HAS_CURL_CFFI:
            self.session = AsyncSession(impersonate="chrome120", timeout=10, verify=False)
        else:
            self.session = httpx.AsyncClient(timeout=10.0, verify=False, follow_redirects=True)

        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "ar,en-US;q=0.9,en;q=0.8",
            "Referer": "https://www.google.com/",
        }
        self.category_map = {
            "netflix-movies": "/category/netfilx/%d8%a7%d9%81%d9%84%d8%a7%d9%85-netfilx/",
            "foreign-movies": "/category/foreign-movies-8/",
            "asian-movies": "/category/asian-movies/",
            "turkish-movies": "/category/turkish-movies/",
            "arabic-movies": "/category/arabic-movies-8/",
            "classic-movies": "/category/%d8%a7%d9%81%d9%84%d8%a7%d9%85-%d9%83%d9%84%d8%a7%d8%b3%d9%8a%d9%83%d9%8a%d9%87/",
            "dubbed-movies": "/category/%d8%a7%d9%81%d9%84%d8%a7%d9%85-%d9%83%d9%84%d8%a7%d8%b3%d9%8a%d9%83%d9%8a%d9%87/", # Note: user's HTML had same link or similar
            "indian-movies": "/category/indian-movies/",
            "netflix-series": "/category/netfilx/%d9%85%d8%b3%d9%84%d8%b3%d9%84%d8%a7%d8%aa-netfilx-1/",
            "foreign-series": "/category/foreign-series-3/",
            "turkish-series": "/category/turkish-series-2/",
            "arabic-series": "/category/arabic-series-6/",
            "cartoon-series": "/category/cartoon-series/",
            "korean-series": "/category/%d9%85%d8%b3%d9%84%d8%b3%d9%84%d8%a7%d8%aa-%d9%83%d9%88%d8%b1%d9%8a%d9%87/",
            "dubbed-series": "/category/%d9%85%d8%b3%d9%84%d8%b3%d9%84%d8%a7%d8%aa-%d9%85%d8%af%d8%a8%d9%84%d8%ac%d8%a9/",
            "egyptian-series": "/category/%d9%85%d8%b3%d9%84%d8%b3%d9%84%d8%a7%d8%aa-%d9%85%d8%b5%d8%b1%d9%8a%d9%87/",
            "indian-series": "/category/%d9%85%d8%b3%d9%84%d8%b3%d9%84%d8%a7%d8%aa-%d9%87%d9%86%d8%af%d9%8a%d8%a9/",
            "ramadan-2025": "/category/%d9%85%d8%b3%d9%84%d8%b3%d9%84%d8%a7%d8%aa-%d8%b1%d9%85%d8%b6%d8%a7%d9%86/ramadan-series-2025/",
            "ramadan-2024": "/category/%d9%85%d8%b3%d9%84%d8%b3%d9%84%d8%a7%d8%aa-%d8%b1%d9%85%d8%b6%d8%a7%d9%86/ramadan-series-2024/",
            "ramadan-2023": "/category/%d9%85%d8%b3%d9%84%d8%b3%d9%84%d8%a7%d8%aa-%d8%b1%d9%85%d8%b6%d8%a7%d9%86/ramadan-series-2023/",
            "ramadan-2022": "/category/%d9%85%d8%b3%d9%84%d8%b3%d9%84%d8%a7%d8%aa-%d8%b1%d9%85%d8%b6%d8%a7%d9%86/%d9%85%d8%b3%d9%84%d8%b3%d9%84%d8%a7%d8%aa-%d8%b1%d9%85%d8%b6%d8%a7%d9%86-2022/",
            "ramadan-2021": "/category/%d9%85%d8%b3%d9%84%d8%b3%d9%84%d8%a7%d8%aa-%d8%b1%d9%85%d8%b6%d8%a7%d9%86/%d9%85%d8%b3%d9%84%d8%b3%d9%84%d8%a7%d8%aa-%d8%b1%d9%85%d8%b6%d8%a7%d9%86-2021/",
            "ramadan-2020": "/category/%d9%85%d8%b3%d9%84%d8%b3%d9%84%d8%a7%d8%aa-%d8%b1%d9%85%d8%b6%d8%a7%d9%86/%d9%85%d8%b3%d9%84%d8%b3%d9%84%d8%a7%d8%aa-%d8%b1%d9%85%d8%b6%d8%a7%d9%86-2020-hd/",
            "ramadan-2019": "/category/%d9%85%d8%b3%d9%84%d8%b3%d9%84%d8%a7%d8%aa-%d8%b1%d9%85%d8%b6%d8%a7%d9%86/%d9%85%d8%b3%d9%84%d8%b3%d9%84%d8%a7%d8%aa-%d8%b1%d9%85%d8%b6%d8%a7%d9%86-2019/",
            "anime-movies": "/category/%d8%a7%d9%81%d9%84%d8%a7%d9%85-%d8%a7%d9%86%d9%8a%d9%85%d9%8a%d8%b4%d9%86/",
            "wwe": "/category/wwe-shows/",
            "tv-programs": "/category/%d8%a8%d8%a1%d8%a7%d9%85%d8%ac-%d8%aa%d9%84%d9%81%d8%b2%d9%8a%d9%88%d9%86%d9%8a%d8%a9/",
            "plays": "/category/%d9%85%d8%b3%d8%b1%d8%ad%d9%8a%d8%a7%d8%aa-%d8%b9%d8%b1%d8%a8%d9%8a/",
            "songs": "/category/%d8%a7%d8%ba%d8%a7%d9%86%d9%8a-%d8%b9%d8%b1%d8%a8%d9%8a/",
            "arabic-songs": "/category/%d8%a7%d8%ba%d8%a7%d9%86%d9%8a-%d8%b9%d8%b1%d8%a8%d9%8a/"
        }
        # Persistent Cache Setup
        try:
            from app.core.cache import PersistentCache
            import os
            cache_path = os.path.join(os.path.dirname(__file__), "..", "cache", "arabseed_cache.json")
            self._persistent_cache = PersistentCache(os.path.abspath(cache_path))
        except ImportError:
            self._persistent_cache = None

        self._cache = {}
        self._cache_ttl = 3600 * 3 # 3 hours for faster updates
        self._semaphore = asyncio.Semaphore(50) # Maximum concurrency for speed
        self.mirrors = ["https://m2.arabseed.one", "https://asd.homes", "https://arabseed.live", "https://a.asd.homes"]

    def clear_cache(self):
        """Clears both in-memory and persistent cache for this scraper."""
        self._cache = {}
        if self._persistent_cache:
            self._persistent_cache.clear()
        logger.info("🧹 ArabSeedScraper Cache Cleared")

    async def _get_html(self, url: str) -> Optional[str]:
        async with self._semaphore:
            now = time.time()
            # 1. Memory Cache
            if url in self._cache:
                ts, data = self._cache[url]
                if now - ts < self._cache_ttl:
                    return data
            
            # 2. Persistent Cache
            if self._persistent_cache:
                cached_data = self._persistent_cache.get(f"html_{url}")
                if cached_data:
                    self._cache[url] = (now, cached_data)
                    return cached_data

            # 3. Fetch with Mirror Rotation
            path = urlparse(url).path
            query = urlparse(url).query
            if query: path += f"?{query}"
            
            # Create a list of target URLs to try: current URL first, then mirrors
            targets = [url]
            for m in self.mirrors:
                m_url = urljoin(m, path)
                if m_url not in targets:
                    targets.append(m_url)

            last_err = None
            for target_url in targets:
                try:
                    logger.info(f"Fetching (ArabSeed): {target_url}")
                    if HAS_CURL_CFFI:
                        resp = await self.session.get(target_url, headers=self.headers, allow_redirects=True)
                    else:
                        resp = await self.session.get(target_url, headers=self.headers, follow_redirects=True)
                    
                    if resp.status_code == 200:
                        # Auto-heal base_url if we found a working mirror
                        new_base = f"{urlparse(target_url).scheme}://{urlparse(target_url).netloc}"
                        if self.base_url != new_base:
                            logger.info(f"🚀 ArabSeed auto-healed: {self.base_url} -> {new_base}")
                            self.base_url = new_base
                            # Rotate mirrors list
                            if new_base in self.mirrors:
                                self.mirrors.remove(new_base)
                            self.mirrors.insert(0, new_base)

                        self._cache[url] = (now, resp.text)
                        if self._persistent_cache:
                            self._persistent_cache.set(f"html_{url}", resp.text, ttl_seconds=self._cache_ttl)
                        return resp.text
                    elif resp.status_code in [404, 403, 503]:
                        logger.warning(f"Mirror {target_url} returned {resp.status_code}")
                        continue
                except Exception as e:
                    last_err = e
                    logger.warning(f"Failed to fetch {target_url}: {e}")
            
            return None

    def _extract_items(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, Any]]:
        items = []
        # ArabSeed structure: a.movie__block
        containers = soup.select('a.movie__block')
        
        for tag in containers:
            href = tag.get('href')
            if not href: continue
            
            full_url = urljoin(base_url, href)
            title = tag.get('title') or tag.select_one('h3').get_text(strip=True) if tag.select_one('h3') else "No Title"
            
            # Poster extraction: look for img or style
            img_node = tag.select_one('img')
            img_url = ""
            if img_node:
                img_url = img_node.get('data-src') or img_node.get('src')
            
            if not img_url and tag.get('style'):
                style = tag.get('style')
                match = re.search(r'url\((.*?)\)', style)
                if match:
                    img_url = match.group(1).strip("'\"")

            # Skip generic category links that ArabSeed sometimes includes in the main grid
            clean_title = self._clean_title(title).replace(" - MOVIDO", "")
            generic_categories = [
                "مسلسلات", "أفلام", "افلام", "رمضان", "برامج", "تلفزيونية", 
                "إضافات", "أحدث", "هندي", "أجنبي", "اجنبي", "مدبلجة", "أنمي", "انمي"
            ]
            if clean_title in generic_categories or "/category/" in href and not any(x in href for x in ["2025", "2024"]):
                if len(clean_title) < 15: # Category links are usually short single words
                    continue

            items.append({
                "id": base64.urlsafe_b64encode(full_url.encode()).decode().strip('='),
                "title": self._clean_title(title),
                "poster": f"/proxy/image?url={quote(urljoin(base_url, img_url))}" if img_url else "",
                "type": "series" if any(x in title for x in ["حلقة", "مسلسل", "موسم"]) else "movie",
                "source": "mycima",
                "url": full_url
            })
        return items

    def _clean_title(self, title: str) -> str:
        noise = ["مشاهدة", "فيلم", "كامل", "مترجم", "اون لاين", "HD", "تحميل", "بجودة", "عالية", "عرب سيد", "ArabSeed", "لاروزا", "Laroza", "LMINA", "lmina"]
        for n in noise:
            title = title.replace(n, "").strip()
        title = re.sub(r'\s+', ' ', title).strip("- ")
        # Append MOVIDO brand
        if title and "MOVIDO" not in title:
            title = f"{title} - MOVIDO"
        return title.replace("LMINA", "MOVIDO").replace("lmina", "MOVIDO")

    async def fetch_category(self, cat_id: str, page: int = 1) -> List[Dict[str, Any]]:
        path = self.category_map.get(cat_id)
        if not path:
            # Try to use cat_id as fallback path if it looks like a relative path
            if cat_id.startswith('category/'):
                path = f"/{cat_id}"
            else:
                return []
        
        url = f"{self.base_url}{path}page/{page}/" if page > 1 else f"{self.base_url}{path}"
        html = await self._get_html(url)
        return self._extract_items(BeautifulSoup(html, 'html.parser'), url) if html else []

    async def fetch_home(self, page: int = 1) -> List[Dict[str, Any]]:
        # Recently added items
        url = f"{self.base_url}/recently/page/{page}/" if page > 1 else f"{self.base_url}/recently/"
        html = await self._get_html(url)
        return self._extract_items(BeautifulSoup(html, 'html.parser'), url) if html else []

    async def search(self, query: str) -> List[Dict[str, Any]]:
        # ArabSeed search structure
        url = f"{self.base_url}/find/?word={quote(query)}"
        html = await self._get_html(url)
        return self._extract_items(BeautifulSoup(html, 'html.parser'), url) if html else []

    async def fetch_details(self, safe_id: str) -> Dict[str, Any]:
        try:
            # Re-add padding if missing
            temp_id = safe_id
            padding = len(temp_id) % 4
            if padding:
                temp_id += "=" * (4 - padding)
            url = base64.urlsafe_b64decode(temp_id).decode()
        except Exception as e:
            logger.error(f"Error decoding safe_id: {e}")
            # Fallback if it's already a URL
            if safe_id.startswith('http'): url = safe_id
            else: return {}

        html = await self._get_html(url)
        if not html: return {}

        soup = BeautifulSoup(html, 'html.parser')
        title_node = soup.select_one('h1') or soup.select_one('.Title, .title')
        title = title_node.get_text(strip=True) if title_node else "Unknown"
        
        details = {
            "id": safe_id,
            "title": self._clean_title(title),
            "description": self._extract_description(soup),
            "poster": self._extract_poster(soup, url),
            "type": "series" if any(x in title for x in ["حلقة", "مسلسل", "موسم"]) else "movie",
            "servers": [],
            "download_links": [],
            "episodes": [],
        }

        # ArabSeed specific Watch page suffix
        watch_url = url.strip('/') + '/watch/'
        watch_html = await self._get_html(watch_url)
        if watch_html:
            watch_soup = BeautifulSoup(watch_html, 'html.parser')
            # Extract servers (including AJAX ones)
            details["servers"] = await self._extract_watch_servers(watch_soup, watch_url)

        # ArabSeed specific Download page suffix
        download_url = url.strip('/') + '/download/'
        download_html = await self._get_html(download_url)
        if download_html:
            details["download_links"] = self._extract_download_links(BeautifulSoup(download_html, 'html.parser'), download_url)
        
        # Extract episodes if series
        if details["type"] == "series":
            details["episodes"] = self._extract_series_episodes(soup, url)
        
        # Persistent Cache details
        if self._persistent_cache:
            self._persistent_cache.set(f"details_{safe_id}", details, ttl_seconds=3600 * 12)
            
        return details

    def _extract_description(self, soup: BeautifulSoup) -> str:
        desc_node = soup.select_one('.content__wrapper, .Story, .desc, .post-description, .single-content')
        if not desc_node: return ""
        text = desc_node.get_text(strip=True)
        # Sanitize old names
        text = text.replace("عرب سيد", "MOVIDO").replace("ArabSeed", "MOVIDO").replace("لاروزا", "MOVIDO").replace("Laroza", "MOVIDO").replace("LMINA", "MOVIDO")
        # Remove extra marketing text
        noise_phrases = [
            "اسرع موقع فـــــي مـــصـــر", "اسرع موقعفـــــي مـــصـــر", "أشهر الممثلينالاكثر بحثابرومو", "أفضل تجربة مشاهدة",
            "أشهر الممثلين", "الاكثر بحثا", "برومو", "الكلالكلافلاممسلسلاتحلقاتممثلينمضاف حديثاتريند",
            "هي كيميا", "الست موناليزا", "وننسى اللي كان", "صحاب الأرض", "فخر الدلتا"
        ]
        for phrase in noise_phrases:
            text = text.replace(phrase, "")
        
        # Remove repeated words and extra whitespace
        text = re.sub(r'(MOVIDO\s*){2,}', 'MOVIDO ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        # Remove leading/trailing dashes and dots
        text = text.strip("- .")
        return text

    def _extract_poster(self, soup: BeautifulSoup, base_url: str) -> str:
        # New ArabSeed selectors
        img_node = soup.select_one('.poster-img, .lcp-cover-img, .poster__single img, .poster__image img, .Poster img')
        
        if img_node:
            poster_url = img_node.get('src') or img_node.get('data-src') or img_node.get('data-echo') or img_node.get('data-lazy-src')
            if poster_url:
                if poster_url.startswith('//'): poster_url = 'https:' + poster_url
                return f"/proxy/image?url={quote(urljoin(base_url, poster_url))}"
        
        # Fallback: find any image in a container that looks like a poster
        container = soup.select_one('.aseed-player-box, .poster__single, .post-image')
        if container:
            img = container.find('img')
            if img:
                poster_url = img.get('src') or img.get('data-src') or img.get('data-echo')
                if poster_url:
                    return f"/proxy/image?url={quote(urljoin(base_url, poster_url))}"

        return ""

    def _extract_series_episodes(self, soup: BeautifulSoup, base_url: str) -> List[Dict]:
        episodes = []
        # ArabSeed episodes structure
        ep_links = soup.select('.episodes__list a, .Season--Episodes--Items a')
        for a in ep_links:
            href = a.get('href')
            if not href: continue
            
            full_url = urljoin(base_url, href)
            ep_text = a.get_text(strip=True)
            
            match = re.search(r'(\d+)', ep_text)
            ep_num = int(match.group(1)) if match else 0
            
            episodes.append({
                "id": base64.urlsafe_b64encode(full_url.encode()).decode(),
                "title": f"الحلقة {ep_num}",
                "episode": ep_num,
                "url": full_url
            })
        return sorted(episodes, key=lambda x: x['episode'])

    async def _get_ajax_server(self, post_id: str, server: str, quality: str, token: str, referer: Optional[str] = None) -> Optional[str]:
        """Fetch server URL via ArabSeed's AJAX endpoint"""
        ajax_url = f"{self.base_url}/get__watch__server/"
        data = {
            "post_id": post_id,
            "server": server,
            "quality": quality,
            "csrf_token": token
        }
        headers = self.headers.copy()
        headers["X-Requested-With"] = "XMLHttpRequest"
        headers["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"
        if referer:
            headers["Referer"] = referer
        
        try:
            if HAS_CURL_CFFI:
                resp = await self.session.post(ajax_url, data=data, headers=headers)
            else:
                resp = await self.session.post(ajax_url, data=data, headers=headers)
            
            if resp.status_code == 200:
                json_data = resp.json()
                if json_data.get("type") == "success":
                    return json_data.get("server")
            return None
        except Exception as e:
            logger.error(f"Error in AJAX server fetch: {e}")
            return None

    async def _extract_watch_servers(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, str]]:
        servers = []
        
        # 1. Extract post_id and CSRF token from scripts (more robustly)
        post_id = ""
        csrf_token = ""
        
        # Try to find tokens in main__obj or object__info global structures
        scripts_text = "\n".join([s.text for s in soup.find_all('script')])
        
        # Look for post_id (including psot_id typo)
        post_match = re.search(r"(?:post_id|psot_id)['\"]?\s*[:=]\s*['\"]?(\d+)['\"]?", scripts_text)
        if post_match:
            post_id = post_match.group(1)
        
        # Look for csrf__token or csrf_token
        csrf_match = re.search(r"(?:csrf__token|csrf_token)['\"]?\s*[:=]\s*['\"]([^'\"]+)['\"]", scripts_text)
        if csrf_match:
            csrf_token = csrf_match.group(1)
            
        # Fallback to meta or input
        if not csrf_token:
            csrf_token_node = soup.select_one('meta[name="csrf-token"]') or soup.select_one('input[name="csrf__token"]') or soup.select_one('input[name="csrf_token"]')
            if csrf_token_node:
                csrf_token = csrf_token_node.get('content') or csrf_token_node.get('value')

        if not post_id:
            post_meta = soup.select_one('input[name="post_id"]') or soup.select_one('li[data-post]') or soup.select_one('div[data-post]') or soup.select_one('[data-post-id]')
            if post_meta:
                post_id = post_meta.get('value') or post_meta.get('data-post') or post_meta.get('data-post-id')

        # 2. Find all available qualities (Default to all if not found)
        qualities = []
        q_elements = soup.select('.qualities__list li[data-quality], .quality__swither li[data-quality], .watch__qualities li[data-quality], li[data-quality]')
        if q_elements:
            qualities = list(set([str(q.get('data-quality')) for q in q_elements if q.get('data-quality')]))
        
        # If we only found one or none, force try the standard HD qualities
        if len(qualities) <= 1:
            qualities = sorted(list(set(qualities + ['1080', '720', '480'])), key=lambda x: int(x) if x.isdigit() else 0, reverse=True)

        logger.info(f"Probing qualities: {qualities} for post_id: {post_id}")

        # 3. Fetch servers for each quality using /get__quality__servers/
        if post_id and csrf_token:
            quality_results = []
            for qu in qualities:
                res = await self._get_quality_servers_ajax(post_id, qu, csrf_token, base_url)
                quality_results.append(res)
                if len(qualities) > 1:
                    await asyncio.sleep(0.5) # Avoid rate limits
            
            # 4. Each quality result is HTML with the server list
            watch_server_tasks = []
            for idx, html_fragment in enumerate(quality_results):
                if isinstance(html_fragment, (str, bytes)) and html_fragment and "data-server" in str(html_fragment):
                    qu = qualities[idx]
                    fragment_soup = BeautifulSoup(html_fragment, 'html.parser')
                    li_tags = fragment_soup.select('li[data-server]')
                    
                    if not li_tags:
                        # Fallback for some alternate AJAX responses
                        li_tags = fragment_soup.find_all('li', {'data-server': True})

                    for li in li_tags:
                        s_id = li.get('data-server')
                        label = li.get_text(strip=True) or f"سيرفر {s_id}"
                        
                        # ArabSeed direct links often have data-link in the LI
                        data_link = li.get('data-link')
                        if data_link:
                            url = self._decode_data_link(data_link, base_url)
                            if url:
                                if "play.php" in url or "play?" in url:
                                    url = self._decode_data_link(url, base_url)
                                servers.append({"name": f"{label} ({qu}p)", "url": url})
                                continue
                        
                        watch_server_tasks.append((f"{label} ({qu}p)", self._get_ajax_server(post_id, s_id, qu, csrf_token, referer=base_url)))

            # 5. Process watch server tasks
            if watch_server_tasks:
                labels, coros = zip(*watch_server_tasks)
                results = await asyncio.gather(*coros, return_exceptions=True)
                for label, url in zip(labels, results):
                    if isinstance(url, str) and url:
                        servers.append({"name": label.replace("عرب سيد", "MOVIDO").replace("ArabSeed", "MOVIDO").replace("LMINA", "MOVIDO"), "url": url})

        # 6. Fallback: Extract from the existing static page search
        static_links = soup.select('li[data-link]')
        for li in static_links:
            data_link = li.get('data-link')
            s_qu = li.get('data-qu') or li.get('data-quality') or "Source"
            s_name = li.get_text(strip=True) or "Server"
            
            url_final = self._decode_data_link(data_link, base_url)
            if url_final:
                servers.append({"name": f"{s_name} ({s_qu}p)".replace("عرب سيد", "MOVIDO").replace("ArabSeed", "MOVIDO").replace("LMINA", "MOVIDO"), "url": url_final})

        # Enhanced Filter: Remove ads and unwanted content before de-duplication
        filtered_servers = []
        
        # Comprehensive ad domain blacklist (gambling, crypto, redirects, ad networks)
        ad_domains = [
            # Ad Networks
            'doubleclick', 'googlesyndication', 'google-analytics', 'googletagmanager', 
            'amazon-adsystem', 'pubmatic', 'taboola', 'outbrain', 'revcontent', 
            'adnxs', 'aaxads', 'zedo', 'exoclick', 'popads', 'popcash', 
            'propellerads', 'onclickads', 'realsrv', 'juicyads', 'adsterra',
            'clickadu', 'hilltopads', 'adcash', 'bidvertiser', 'infolinks',
            'media.net', 'criteo', 'smartadserver', 'openx', 'rubicon',
            
            # Gambling & Betting Sites
            'melbet', '1xbet', 'mostbet', 'bet365', '22bet', 'betwinner',
            'parimatch', 'betway', 'unibet', 'bwin', 'pinnacle', 'sportsbet',
            'betfair', 'ladbrokes', 'williamhill', 'coral', 'paddy',
            
            # Crypto & Trading Ads
            'tapbit', 'okx', 'binance', 'coinbase', 'kraken', 'bybit',
            'cryptoad', 'crypto-', 'trading', 'forex', 'bitcoin',
            
            # Redirect & Tracking Services
            'smartcpm', 'clickunder', 'adtarget', 'traffic', 'redirect',
            'attirecideryeah', 'asg.vidoba', 'short.', 'bit.ly', 'tinyurl',
            'adf.ly', 'bc.vc', 'clk.', 'go.', 'link.', 'url.',
            
            # Social Media Trackers
            'facebook', 'connect.facebook', 'twitter', 'instagram',
            'tiktok', 'snapchat', 'linkedin',
            
            # Analytics & Tracking
            'analytics', 'tracker', 'track', 'pixel', 'beacon', 'stat',
            'counter', 'metrics', 'telemetry',
            
            # Popup & Interstitial Ads
            'popup', 'popunder', 'popad', 'interstitial', 'overlay',
            'modal', 'lightbox',
            
            # Affiliate Networks
            'affiliate', 'commission', 'referral', 'partner',
            
            # Banner & Display Ads
            'banner', 'display', 'impression', 'adserver',
            
            # Known ArabSeed Ad Servers (specific)
            'vidbom', 'vidbem', 'vidbam', 'upstream', 'goved',
            'voe.sx', 'voe-unblock', 'streamtape', 'doodstream',
            'mixdrop', 'upstream.to', 'supervideo', 'streamlare',
            'filemoon', 'vtube', 'waaw', 'uqload', 'userload',
            
            # Malicious/Suspicious Domains
            'malware', 'phishing', 'scam', 'virus', 'trojan',
            'spam', 'fraud', 'fake', 'suspicious'
        ]
        
        # Ad-related keywords in URLs
        ad_keywords = [
            'ads', 'advertisement', 'promo', 'sponsored', 'campaign',
            'click', 'cpc', 'cpm', 'cpa', 'rtb', 'dsp', 'ssp'
        ]
        
        for s in servers:
            clean_url = s['url'].strip().lower()
            clean_name = s['name'].lower()
            
            # Skip if URL contains ad keywords
            if any(keyword in clean_url for keyword in ad_keywords):
                logger.debug(f"🚫 Blocked ad server (keyword): {s['name']} - {clean_url[:50]}")
                continue
            
            # Skip if name contains ad keywords
            if any(keyword in clean_name for keyword in ad_keywords):
                logger.debug(f"🚫 Blocked ad server (name): {s['name']}")
                continue
            
            # Skip if URL contains known ad domains
            if any(domain in clean_url for domain in ad_domains):
                logger.debug(f"🚫 Blocked ad server (domain): {s['name']} - {clean_url[:50]}")
                continue
            
            # Additional pattern checks
            # Block URLs with excessive redirects (multiple ? or &)
            if clean_url.count('?') > 2 or clean_url.count('&') > 5:
                logger.debug(f"🚫 Blocked suspicious URL (redirects): {clean_url[:50]}")
                continue
            
            # Block very short domains (often ad redirects)
            from urllib.parse import urlparse
            try:
                parsed = urlparse(clean_url)
                domain = parsed.netloc
                # Skip domains shorter than 5 chars (excluding TLD)
                if domain and len(domain.split('.')[0]) < 3:
                    logger.debug(f"🚫 Blocked short domain: {domain}")
                    continue
            except:
                pass
            
            # If passed all filters, add to clean list
            filtered_servers.append(s)
            logger.info(f"✅ Clean server: {s['name']}")
        
        # Final cleanup/de-duplication
        unique_results = []
        seen_urls = set()
        for s in filtered_servers:
            clean_url = s['url'].strip()
            if clean_url and clean_url not in seen_urls:
                unique_results.append(s)
                seen_urls.add(clean_url)
                
        # If still empty, check iframes (with same strict filtering)
        if not unique_results:
            logger.warning("⚠️ No clean servers found via AJAX, checking iframes as fallback...")
            for ifr in soup.find_all('iframe', src=True):
                src = ifr['src'].lower()
                
                # Apply same strict filtering as above
                if any(keyword in src for keyword in ad_keywords):
                    continue
                if any(domain in src for domain in ad_domains):
                    continue
                
                # Additional iframe-specific checks
                # Skip iframes with suspicious dimensions (often hidden ad trackers)
                width = ifr.get('width', '100%')
                height = ifr.get('height', '100%')
                if (width in ['1', '0', '1px'] or height in ['1', '0', '1px']):
                    logger.debug(f"🚫 Blocked hidden iframe: {src[:50]}")
                    continue
                
                unique_results.append({"name": "Main Server", "url": ifr['src']})
                logger.info(f"✅ Clean iframe server found: {src[:50]}")


        # Prioritize clean, known-good servers
        def get_server_priority(server):
            """Assign priority score to servers (higher = better)"""
            url = server['url'].lower()
            name = server['name'].lower()
            
            # Tier 1: Premium clean servers (100+ points)
            if any(x in url for x in ['larooza', 'larozavideo', 'q.larozavideo']):
                return 150
            if any(x in url for x in ['vidyard', 'vimeo', 'dailymotion', 'youtube']):
                return 120
            
            # Tier 2: Reliable hosting (50-99 points)
            if any(x in url for x in ['ok.ru', 'mail.ru', 'yandex', 'rutube']):
                return 80
            if any(x in url for x in ['fembed', 'streamsb', 'streamwish']):
                return 70
            
            # Tier 3: Acceptable servers (20-49 points)
            if any(x in url for x in ['mp4upload', 'sendvid', 'vidoza']):
                return 40
            
            # Tier 4: Unknown servers (10 points)
            # These passed filtering but are unknown
            return 10
        
        # Sort by priority (highest first)
        unique_results.sort(key=get_server_priority, reverse=True)
        
        logger.info(f"🎯 Returning {len(unique_results)} clean servers (sorted by quality)")
        return unique_results

    def _decode_data_link(self, data_link: str, base_url: str) -> Optional[str]:
        """Helper to decode ArabSeed's data-link (base64 or relative)"""
        if not data_link: return None
        
        # Case 1: Base64 in query param like ?url=aHR0... or ?id=aHR0... or ?vid=...
        match = re.search(r'[?&](?:url|id|vid)=([A-Za-z0-9+/=_-]{10,})', data_link)
        if match:
            try:
                b64 = match.group(1)
                # Normalize base64
                b64 = b64.replace('-', '+').replace('_', '/')
                b64 += "=" * ((4 - len(b64) % 4) % 4)
                decoded = base64.b64decode(b64).decode('utf-8')
                if decoded.startswith('http'):
                    return decoded
                # Sometimes it decodes to another relative path
                if decoded.startswith('/') or 'play.php' in decoded:
                    return urljoin(base_url, decoded)
                return decoded
            except: pass
            
        # Case 2: Direct URL
        if data_link.startswith('http'):
            return data_link
            
        # Case 3: Relative path
        return urljoin(base_url, data_link)

    async def _get_quality_servers_ajax(self, post_id: str, quality: str, token: str, referer: str) -> Optional[str]:
        """Fetch server list HTML for a specific quality"""
        url = f"{self.base_url}/get__quality__servers/"
        data = {
            "post_id": post_id,
            "quality": quality,
            "csrf_token": token
        }
        headers = self.headers.copy()
        headers["X-Requested-With"] = "XMLHttpRequest"
        headers["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"
        headers["Referer"] = referer
        
        try:
            resp = await self.session.post(url, data=data, headers=headers)
            if resp.status_code == 200:
                # Returns HTML string directly or JSON with html field
                try:
                    return resp.json().get("html") or resp.text
                except:
                    return resp.text
            return None
        except Exception:
            return None

    def _extract_download_links(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, str]]:
        links = []
        # ArabSeed Download structure: a.download__item
        items = soup.select('a.download__item')
        for a in items:
            href = a.get('href')
            if href:
                # ArabSeed links like /l/aHR0cHM...
                match = re.search(r'/l/(.*)', href)
                if match:
                    try:
                        b64_url = match.group(1)
                        b64_url += "=" * ((4 - len(b64_url) % 4) % 4)
                        direct_url = base64.b64decode(b64_url).decode()
                        quality_node = a.select_one('h4') or a.select_one('span')
                        quality = quality_node.get_text(strip=True) if quality_node else "Download"
                        
                        # Clean quality/name
                        quality = quality.replace("عرب سيد", "MOVIDO").replace("ArabSeed", "MOVIDO").replace("LMINA", "MOVIDO").replace("المباشر", "Direct")
                        links.append({"quality": quality, "url": direct_url})
                    except Exception as e:
                        logger.error(f"Error decoding download link: {e}")
                else:
                    quality = a.get_text(strip=True)
                    quality = quality.replace("عرب سيد", "MOVIDO").replace("ArabSeed", "MOVIDO").replace("LMINA", "MOVIDO")
                    links.append({"quality": quality, "url": href})
        return links

scraper = MyCimaScraper()
