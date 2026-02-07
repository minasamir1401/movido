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
        "https://larooza.hair",
        "https://larooza.top",
        "https://q.larozavideo.net",
        "https://larooza.mom", 
        "https://larooza.site", 
        "https://larooza.lol",
        "https://larooza.cfd",
        "https://larooza.video",
        "https://larooza.bond"
    ]
    DEFAULT_BASE_URL = "https://larooza.hair"
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
        "ramadan-2022": ["رمضان 2022", "37ramadan-2022"],
        "ramadan-2021": ["رمضان 2021", "24ramadan-2021"],
        "ramadan-2020": ["رمضان 2020", "9ramadan-2020"],
        "ramadan-2019": ["رمضان 2019", "ramadan-2019"],
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
            self.session = AsyncSession(impersonate="chrome124", timeout=10, verify=False)
        else:
            self.session = httpx.AsyncClient(timeout=10.0, verify=False, follow_redirects=True)

        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "ar,en-US;q=0.9,en;q=0.8",
            "Cache-Control": "max-age=0",
            "Upgrade-Insecure-Requests": "1",
            "Connection": "keep-alive",
            "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
        }
        
        # Persistent Cache Setup
        try:
            from app.core.cache import PersistentCache
            cache_path = os.path.join(os.path.dirname(__file__), "..", "cache", "scraper_cache.json")
            self._persistent_cache = PersistentCache(os.path.abspath(cache_path))
        except ImportError:
            self._persistent_cache = None
            
        self._cache = {}
        self._cache_ttl = 3600 * 3 # 3 hours for faster updates
        self._semaphore = asyncio.Semaphore(50) # Maximum concurrency for speed
        self._category_map = {}
        self._discovery_lock = asyncio.Lock()
        self._last_discovery = 0

    def clear_cache(self):
        """Clears both in-memory and persistent cache for this scraper."""
        self._cache = {}
        if self._persistent_cache:
            self._persistent_cache.clear()
        logger.info("🧹 LaroozaScraper Cache Cleared")

    async def _resolve_new_domain(self) -> Optional[str]:
        """Discovery mechanism to find the new Larooza domain via search."""
        try:
            logger.info("🕵️‍♂️ All mirrors failed. Initiating Domain Discovery Protocol...")
            
            # Use DuckDuckGo HTML (lightweight, no strict blocking)
            search_query = "موقع لاروزا فيديو الأصلي"
            search_url = f"https://html.duckduckgo.com/html/?q={quote(search_query)}"
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            
            # Fetch search results
            async with httpx.AsyncClient(timeout=15, verify=False) as client:
                resp = await client.get(search_url, headers=headers)
                
            if resp.status_code == 200:
                # Find result links
                soup = BeautifulSoup(resp.text, 'html.parser')
                results = soup.select('.result__a')
                
                for link in results[:3]: # Check top 3 results
                    href = link.get('href')
                    if not href: continue
                    
                    # Extract actual URL from DDG redirect
                    # format: //duckduckgo.com/l/?uddg=...
                    if 'uddg=' in href:
                        from urllib.parse import unquote
                        match = re.search(r'uddg=([^&]+)', href)
                        if match:
                             candidate = unquote(match.group(1))
                        else:
                             continue
                    else:
                        candidate = href
                        
                    parsed = urlparse(candidate)
                    if not parsed.scheme or not parsed.netloc: continue
                    
                    # Basic validation filters
                    if any(x in candidate for x in ['facebook', 'twitter', 'instagram', 'youtube', 'pinterest']):
                        continue
                        
                    domain = f"{parsed.scheme}://{parsed.netloc}"
                    logger.info(f"🔎 Testing candidate domain: {domain}")
                    
                    # Verify it's actually Larooza
                    try:
                        async with self.session.get(domain, headers=self.headers, timeout=10) as check_resp:
                            if check_resp.status_code == 200 and ('laro' in check_resp.text.lower() or 'video.php' in check_resp.text or 'br-movies' in check_resp.text):
                                logger.info(f"✅ CONFIRMED: New domain is {domain}")
                                return domain
                    except:
                        continue
                        
            return None
        except Exception as e:
            logger.error(f"Discovery failed: {e}")
            return None

    async def _get_html(self, url: str) -> Optional[str]:
        """Unified HTML fetching with caching, smart mirror rotation, and Domain Discovery."""
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
            
            # Determine if we should try mirrors
            is_base_url = False
            path = ""
            current_domain = urlparse(url).netloc
            
            # Check if this URL belongs to one of our known mirrors
            for mirror in ScraperConfig.MIRRORS + [self.base_url]:
                if urlparse(mirror).netloc == current_domain:
                    is_base_url = True
                    # Extract relative path + query
                    parsed = urlparse(url)
                    path = parsed.path
                    if parsed.query:
                        path += f"?{parsed.query}"
                    break
            
            # Prepare targets
            targets = [url]
            if is_base_url:
                # Add current base_url domain counterparts if different from input url
                base_netloc = urlparse(self.base_url).netloc
                if base_netloc != current_domain:
                    targets.append(urljoin(self.base_url, path))
                    
                # Add rest of mirrors
                for mirror in ScraperConfig.MIRRORS:
                    m_netloc = urlparse(mirror).netloc
                    if m_netloc not in [current_domain, base_netloc]:
                        targets.append(urljoin(mirror, path))
            
            last_error = None
            max_depth = 3
            current_depth = 0
            
            # Use a while loop with a manual index to handle target list modifications during iteration
            idx = 0
            while idx < len(targets) and current_depth < max_depth:
                target_url = targets[idx]
                idx += 1
                try:
                    logger.info(f"Fetching: {target_url} (Attempt {current_depth + 1})")
                    if HAS_CURL_CFFI:
                        resp = await self.session.get(target_url, headers=self.headers, allow_redirects=True)
                    else:
                        resp = await self.session.get(target_url, headers=self.headers, follow_redirects=True)
                    
                    if resp.status_code == 200:
                        # Check for Meta Refresh (Soft Redirect)
                        meta_refresh = re.search(r'<meta[^>]+http-equiv=["\']?refresh["\']?[^>]+content=["\']?\d+;URL=([^"\']+)["\']?', resp.text, re.IGNORECASE)
                        if meta_refresh:
                            refresh_url = meta_refresh.group(1)
                            if not refresh_url.startswith('http'):
                                refresh_url = urljoin(target_url, refresh_url)
                            
                            logger.info(f"🔄 Meta Refresh Detected -> {refresh_url}")
                            if refresh_url not in targets:
                                targets.append(refresh_url)
                            current_depth += 1
                            continue # Try the next target in the list (the one we just added)

                        # Update base_url to the working one if we switched domains
                        # This ensures future requests go directly to the working mirror
                        new_base = f"{urlparse(target_url).scheme}://{urlparse(target_url).netloc}"
                        if is_base_url and "laro" in new_base:
                            if self.base_url != new_base:
                                logger.info(f"🚀 Base URL auto-healed: {self.base_url} -> {new_base}")
                                self.base_url = new_base
                            # Also update config mirrors to keep it at top
                            if new_base in ScraperConfig.MIRRORS:
                                ScraperConfig.MIRRORS.remove(new_base)
                            ScraperConfig.MIRRORS.insert(0, new_base)

                        # Cache and return result
                        self._cache[url] = (now, resp.text)
                        if self._persistent_cache:
                            self._persistent_cache.set(f"html_{url}", resp.text, ttl_seconds=self._cache_ttl)
                        return resp.text
                    elif resp.status_code in [404, 403, 503, 502, 500]:
                         logger.warning(f"Got {resp.status_code} from {target_url}")
                except Exception as e:
                    last_error = e
                    logger.warning(f"Failed to fetch {target_url}: {e}")
            
            # --- LAST RESORT: DOMAIN DISCOVERY ---
            # If we are strictly looking for base URL content (home/category) and everything failed
            if is_base_url:
                async with self._discovery_lock:
                    # Double check if another thread already found it
                    if time.time() - self._last_discovery > 60: # Limit discovery requests
                        self._last_discovery = time.time()
                        new_domain = await self._resolve_new_domain()
                        if new_domain:
                            self.base_url = new_domain
                            if new_domain not in ScraperConfig.MIRRORS:
                                ScraperConfig.MIRRORS.insert(0, new_domain)
                            
                            # Retry with new domain
                            final_url = urljoin(new_domain, path)
                            try:
                                if HAS_CURL_CFFI:
                                    resp = await self.session.get(final_url, headers=self.headers)
                                else:
                                    resp = await self.session.get(final_url, headers=self.headers)
                                if resp.status_code == 200:
                                    return resp.text
                            except: pass

            logger.error(f"❌ All mirrors & discovery failed for {url}. Last error: {last_error}")
            return None

    def _extract_items(self, soup: BeautifulSoup, current_url: str) -> List[Dict[str, Any]]:
        extracted = []
        seen_urls = set()
        
        # 1. Broad selector search (The traditional way)
        items_tags = soup.select('.thumbnail, .pm-li-video, .video-block, .movie-item, .video-card, .item, .pm-video-thumb, .video-post, .pm-video-thumb, div.col-md-3, div.col-sm-2, div.col-sm-6, div.col-xs-6')
        
        # 2. Add all links that look like video links as candidates if not enough items found
        if len(items_tags) < 5:
            links = soup.find_all('a', href=True)
            for link in links:
                href = link['href']
                if 'video.php?vid=' in href or '/v/' in href:
                    # Find closest parent that looks like a container
                    parent = link.find_parent('div', class_=re.compile(r'item|video|thumb|block|post'))
                    if parent and parent not in items_tags:
                        items_tags.append(parent)
                    elif link not in items_tags:
                        items_tags.append(link)

        for item in items_tags:
            link_tag = item if item.name == 'a' else item.find('a', href=True)
            if not link_tag: continue
            
            href = link_tag['href']
            if any(x in href.lower() for x in ['facebook', 'twitter', 'whatsapp', 'telegram', 'v=(?:logout|login|register)']):
                continue
                
            if not href.startswith('http'):
                from urllib.parse import urljoin
                href = urljoin(self.base_url, href)
            
            if href in seen_urls: continue
            seen_urls.add(href)
            
            safe_id = base64.urlsafe_b64encode(href.encode()).decode().strip('=')
            
            # Extract title: check link title first, then text
            title = link_tag.get('title') or item.get_text(separator=" ", strip=True)
            if not title or len(title) < 2: continue
            
            # Clean title
            title = self._clean_title(title)
            # Remove common episode phrases for search matching
            title = re.sub(r'الحلقة\s+\d+.*', '', title).strip()
            
            img_tag = item.find('img')
            poster = ""
            if img_tag:
                # Handle lazy loading attributes like data-echo, data-src, etc.
                poster = img_tag.get('data-echo') or img_tag.get('data-src') or img_tag.get('src') or ""
                if poster.startswith('//'): poster = 'https:' + poster
                elif poster and not poster.startswith('http'):
                    from urllib.parse import urljoin
                    poster = urljoin(self.base_url, poster)
                    
            # Skip placeholders if possible
            if 'data:image' in poster or 'spacer.gif' in poster:
                poster = ""

            extracted.append({
                "id": safe_id,
                "title": title,
                "poster": poster,
                "type": "series" if any(x in href.lower() for x in ["series", "moslslat", "drama", "episode", "season"]) else "movie",
                "source": "larooza",
                "url": href
            })
            
        return extracted

    def _clean_title(self, title: str) -> str:
        """Removes noise and garbage characters from titles."""
        noise = ["مشاهدة", "فيلم", "كامل", "مترجم", "اون لاين", "HD", "تحميل", "بجودة", "عالية", "", "اضغط هنا", "لاروزا", "Laroza", "عرب سيد", "ArabSeed", "LMINA", "lmina"]
        for n in noise:
            title = title.replace(n, "").strip()
        # Remove extra whitespace and leading/trailing dashes
        title = re.sub(r'\s+', ' ', title)
        title = re.sub(r'\d{4}', '', title).strip("- ")
        # Append MOVIDO brand
        if title and "MOVIDO" not in title:
            title = f"{title} - MOVIDO"
        return title.replace("LMINA", "MOVIDO").replace("lmina", "MOVIDO")

    async def fetch_home(self, page: int = 1) -> List[Dict[str, Any]]:
        # Modified to use newvideos1.php as requested
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
            # Re-add padding if missing
            temp_id = safe_id
            padding = len(temp_id) % 4
            if padding:
                temp_id += "=" * (4 - padding)
            url = base64.urlsafe_b64decode(temp_id).decode()
        except Exception as e: 
            logger.error(f"Error decoding safe_id: {e}")
            return {}

        # Clear cache for this specific URL to ensure we get fresh servers
        if url in self._cache:
            del self._cache[url]
        play_url = url.replace("video.php", "play.php")
        if play_url in self._cache:
            del self._cache[play_url]

        html = await self._get_html(url)
        if not html: return {}

        soup = BeautifulSoup(html, 'html.parser')
        title = soup.find('h1').get_text(strip=True) if soup.find('h1') else "Unknown"
        
        details = {
            "id": safe_id,
            "title": title,
            "description": self._extract_description(soup),
            "poster": self._extract_poster(soup, url),
            "type": "series" if any(x in title for x in ["حلقة", "مسلسل", "موسم"]) else "movie",
            "servers": [],
            "download_links": await self._extract_downloads(url),
            "episodes": [],
        }

        # Try to extract servers from current page
        details["servers"] = self._extract_servers(soup, url)
        
        # IMPROVED RECURSION: If found servers are internal Larooza links, follow them!
        # This handles cases like مسلسل الحلانجي where servers are inside embed.php/play.php
        internal_embeds = [s for s in details["servers"] if any(x in s['url'] for x in ['embed.php', 'play.php']) and 'larooza' in s['url']]
        
        # Also check if no servers found but we have a video.php as base URL
        if not details["servers"] and "video.php" in url:
            internal_embeds.append({"name": "Internal", "url": url.replace("video.php", "play.php")})

        if internal_embeds:
            logger.info(f"🔄 Found {len(internal_embeds)} internal Larooza embeds. Following for real hosts...")
            for internal in internal_embeds:
                try:
                    inner_html = await self._get_html(internal['url'])
                    if inner_html:
                        inner_soup = BeautifulSoup(inner_html, 'html.parser')
                        real_hosts = self._extract_servers(inner_soup, internal['url'])
                        # Append any NEW real hosts found inside
                        for rh in real_hosts:
                            if not any(rh['url'] == s['url'] for s in details["servers"]):
                                details["servers"].append(rh)
                except: continue

        # Filter out internal/recursive Larooza links to only show real video players
        details["servers"] = [s for s in details["servers"] if not (any(x in s['url'] for x in ['video.php', 'play.php', 'embed.php']) and 'larooza' in s['url'])]

        if details["type"] == "series":
            details["episodes"] = await self._extract_series_episodes(soup, title, url)

        # PROMOTE Download Links to Servers if they are known video hosts
        video_hosts = ['voe', 'ok.ru', 'vk.com', 'vidmoly', 'dood', 'filemoon', 'mixdrop', 'upstream', 'vidoza', 'okprime', 'mp4upload', 'uploady']
        if details.get('download_links'):
            for dl in details['download_links']:
                dl_url = dl['url'].lower()
                if any(host in dl_url for host in video_hosts):
                    # Check if already in servers
                    if not any(dl['url'] == s['url'] for s in details['servers']):
                        name = dl['quality'].split(' لل')[0] if ' لل' in dl['quality'] else dl['quality']
                        details['servers'].append({
                            "name": name.strip() if name else "External Server",
                            "url": dl['url']
                        })

        # FINAL RE-INDEX & FILTERING: Remove broken servers and ensure consistency
        # Blacklist of broken/unreliable servers requested by USER
        server_blacklist = ['vk.com', 'short.icu', 'dsvplay', 'odnoklassniki', 'ok.ru']
        
        final_list = []
        seen_urls = set()
        active_idx = 1
        
        for s in details.get('servers', []):
            url = s['url']
            url_lower = url.lower()
            
            # Skip if in blacklist
            if any(broken in url_lower for broken in server_blacklist):
                continue
                
            if url in seen_urls: continue
            seen_urls.add(url)
            
            # Clean name logic
            name = s['name']
            if "Server" in name:
                name = name.split('-')[-1].strip() if '-' in name else name.replace("Server", "").strip()
            
            # Identify Host
            try:
                domain = urlparse(url).netloc.replace('www.', '').split('.')[0].upper()
            except:
                domain = "VIDEO"
            
            if not name or name.isdigit() or name == "Main" or name == "External":
                name = domain
                
            final_list.append({
                "name": f"Server {active_idx} - {name}",
                "url": url
            })
            active_idx += 1
        
        details['servers'] = final_list

        # Cache extracted details persistently
        if self._persistent_cache:
            self._persistent_cache.set(f"details_{safe_id}", details, ttl_seconds=3600 * 12)
            
        return details

    def _extract_description(self, soup: BeautifulSoup) -> str:
        desc_node = soup.select_one('.story, .desc, .entry-content')
        if not desc_node: return ""
        text = desc_node.get_text(strip=True)
        # Sanitize old names
        text = text.replace("عرب سيد", "MOVIDO").replace("ArabSeed", "MOVIDO").replace("لاروزا", "MOVIDO").replace("Laroza", "MOVIDO").replace("LMINA", "MOVIDO")
        return text

    def _extract_poster(self, soup: BeautifulSoup, base_url: str) -> str:
        """Extract poster with priority on main content area, ignoring sidebar ads."""
        img_node = None
        
        # Priority 1: Look in main content/series areas (most reliable)
        main_content_selectors = [
            '.pm-series-brief .pm-poster-img img',  # Series poster
            '.content-series-page .pm-poster-img img',
            '#content .pm-poster-img img',
            '.pm-video-thumb img',  # Video page
            '#video-posters img',
            '.movie-poster img',
            '.poster img'
        ]
        
        for selector in main_content_selectors:
            img_node = soup.select_one(selector)
            if img_node:
                break
        
        # Priority 2: If not found, look for the FIRST image in #content (main area only)
        if not img_node:
            content_area = soup.select_one('#content, .content-series-page, .pm-section-highlighted')
            if content_area:
                for img in content_area.find_all('img', limit=5):  # Check first 5 images only
                    src = img.get('data-echo') or img.get('data-src') or img.get('src', '')
                    # Filter out small icons, placeholders, and sidebar images
                    if any(x in src.lower() for x in ['thumb', 'poster', 'upload']) and \
                       not any(x in src.lower() for x in ['icon', 'logo', 'avatar', 'echo-lzld']):
                        img_node = img
                        break
        
        # Priority 3: Last resort - any image that looks like a poster (but avoid sidebar)
        if not img_node:
            for img in soup.find_all('img'):
                # Skip if image is in sidebar or navigation
                parent_classes = ' '.join(img.find_parent().get('class', []))
                if any(x in parent_classes for x in ['sidebar', 'nav', 'menu', 'footer', 'header']):
                    continue
                    
                src = img.get('data-echo') or img.get('data-src') or img.get('src', '')
                if any(x in src.lower() for x in ['thumb', 'poster', 'upload']) and \
                   not any(x in src.lower() for x in ['icon', 'logo', 'avatar', 'echo-lzld']):
                    img_node = img
                    break
                    
        if img_node:
            poster_url = img_node.get('data-echo') or img_node.get('data-src') or img_node.get('src')
            if poster_url:
                if poster_url.startswith('//'): poster_url = 'https:' + poster_url
                full_url = urljoin(base_url, poster_url)
                return f"/proxy/image?url={quote(full_url)}"
        return ""

    async def _extract_series_episodes(self, soup: BeautifulSoup, title: str, base_url: str) -> List[Dict]:
        """Extracts episodes from dropdowns or list containers."""
        episodes = []
        seen_ids = set()
        
        # 1. Try to extract from dropdown menus (Standard Larooza series structure)
        # Seasons are linked to episode dropdowns via IDs, but we just need the episode links.
        episode_dropdowns = soup.select('select.episodeoption')
        for dropdown in episode_dropdowns:
            options = dropdown.find_all('option')
            for opt in options:
                href = opt.get('value')
                # Skip placeholder or invalid links
                if not href or 'select-ep' in href or '#' in href:
                    continue
                
                full_url = urljoin(base_url, href)
                ep_text = opt.get_text(strip=True)
                
                ep_id = base64.urlsafe_b64encode(full_url.encode()).decode().strip('=')
                
                # Extract numerical episode for sorting and deduplication
                match = re.search(r'(\d+)', ep_text)
                ep_num = int(match.group(1)) if match else 0
                
                if ep_num > 0 and ep_num in seen_ids:
                    continue
                
                episodes.append({
                    "id": ep_id,
                    "title": self._clean_title(ep_text),
                    "episode": ep_num,
                    "url": full_url
                })
                if ep_num > 0: seen_ids.add(ep_num)
                else: seen_ids.add(ep_id)

        # 2. Fallback: Extract from common list containers or scan for "Episode" links
        if not episodes:
            # Common CSS selectors for episode lists
            containers = soup.select('.EpisodesList a, .episodes-list a, .series-episodes a, .Episode--List a, #episodes a, .episode-item a')
            
            # If no containers found, try scanning links that look like episodes
            if not containers:
                series_name = re.sub(r'الحلقة.*', '', title).replace("مشاهدة", "").replace("مسلسل", "").strip()
                containers = [a for a in soup.find_all('a', href=True) if "الحلقة" in a.get_text() and (not series_name or series_name in a.get_text())]

            for a in containers:
                href = a.get('href')
                if not href or 'javascript' in href:
                    continue
                
                # Filter to only include video/watch/play links
                if not any(x in href for x in ['video.php', 'play.php', 'watch.php']):
                    continue
                
                full_url = urljoin(base_url, href)
                ep_text = a.get_text(strip=True)
                
                ep_id = base64.urlsafe_b64encode(full_url.encode()).decode().strip('=')
                
                match = re.search(r'(\d+)', ep_text)
                ep_num = int(match.group(1)) if match else 0
                
                if ep_num > 0 and ep_num in seen_ids:
                    continue
                
                episodes.append({
                    "id": ep_id,
                    "title": self._clean_title(ep_text),
                    "episode": ep_num,
                    "url": full_url
                })
                if ep_num > 0: seen_ids.add(ep_num)
                else: seen_ids.add(ep_id)
            
        # Return sorted list (oldest to newest)
        return sorted(episodes, key=lambda x: x['episode'])

    def _extract_servers(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, str]]:
        """Extracts server links using multiple advanced patterns and merges them with clean names."""
        found_servers = []
        seen_urls = set()
        
        def add_server(name, url):
            if not url or "javascript" in url or "#" == url: return
            if not url.startswith('http'):
                url = urljoin(base_url, url)
            
            # Use lowercase for comparison to avoid duplicates
            u_lower = url.lower().split('?')[0].rstrip('/')
            if u_lower in seen_urls: return
            seen_urls.add(u_lower)

            # Determine a friendly name
            host = urlparse(url).netloc.replace('www.', '').split('.')[0].upper()
            if not host or len(host) < 2: host = "VIDEO"
            
            # Clean original name
            clean_name = name.replace("سيرفر", "").replace("مشاهدة", "").replace("Server", "").strip()
            if not clean_name or clean_name.isdigit():
                clean_name = host
            
            found_servers.append({
                "name": clean_name,
                "url": url,
                "host": host
            })

        # Pattern 1: Search in data-embed-url
        for item in soup.select('[data-embed-url]'):
            add_server(item.get_text(strip=True), item.get('data-embed-url'))
            
        # Pattern 2: Search in specific list items that usually hold servers
        for item in soup.select('.WatchList li, .server-item, .servers-list li'):
            url = item.get('data-embed-url') or item.get('data-url')
            if not url:
                link = item.find('a', href=True)
                if link: url = link['href']
            
            if url:
                add_server(item.get_text(strip=True), url)

        # Pattern 3: Search for any iframe that might be a player
        for ifr in soup.find_all('iframe', src=True):
            src = ifr['src']
            if not any(x in src.lower() for x in ['ads', 'google', 'facebook', 'analytics', 'counter']):
                add_server("Main Server", src)

        # Pattern 4: Global host keyword search
        host_keywords = ['voe', 'ok.ru', 'vk.com', 'vidmoly', 'dood', 'filemoon', 'mixdrop', 'upstream', 'vidoza', 'okprime', 'mp4upload']
        for a in soup.find_all('a', href=True):
            if any(k in a['href'].lower() for k in host_keywords):
                add_server(a.get_text(strip=True) or "External", a['href'])

        # Final Formatting: "Server 1 - NAME"
        final_servers = []
        for idx, s in enumerate(found_servers, 1):
            final_servers.append({
                "name": f"Server {idx} - {s['name']}",
                "url": s['url']
            })
                    
        return final_servers


            
    
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
                    clean_label = clean_label.replace("لاروزا", "MOVIDO").replace("Laroza", "MOVIDO").replace("عرب سيد", "MOVIDO").replace("ArabSeed", "MOVIDO").replace("LMINA", "MOVIDO")
                    links.append({"quality": clean_label or urlparse(href).netloc, "url": href})
                    seen_urls.add(href)
            if links: break
        return links

scraper = LaroozaScraper()
