import asyncio
import base64
import logging
import re
import time
from typing import Any, Dict, List, Optional
from urllib.parse import quote, urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger("animerco_scraper")

class AnimercoScraper:
    def __init__(self):
        self.base_url = "https://ww1.animerco.org"
        self.session = httpx.AsyncClient(timeout=30.0, verify=False, follow_redirects=True)
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "ar,en-US;q=0.9,en;q=0.8",
            "Referer": "https://ww1.animerco.org/",
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

    async def _get_html(self, url: str) -> Optional[str]:
        async with self._semaphore:
            now = time.time()
            if url in self._cache:
                ts, data = self._cache[url]
                if now - ts < self._cache_ttl:
                    return data

            try:
                resp = await self.session.get(url, headers=self.headers)
                if resp.status_code == 200:
                    self._cache[url] = (now, resp.text)
                    return resp.text
            except Exception as e:
                logger.error(f"Fetch error for {url}: {e}")
            return None

    def _extract_anime_items(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        items = []
        # Target various card types: .anime-card, .episode-card, .search-card, .poster-card
        containers = soup.select('.anime-card, .episode-card, .search-card, .poster-card, .item, .post-item')

        for tag in containers:
            # Most links are in a.image or a direct a child
            link_node = tag.select_one('a.image') or tag.find('a', href=True)
            if not link_node: continue
            
            href = link_node.get('href', '')
            if not href: continue
            
            full_url = urljoin(self.base_url, href)
            
            # Title is often in a[title] or h2/h3
            title_text = link_node.get('title') or ""
            if not title_text:
                title_el = tag.select_one('h2, h3, .title, .info h3')
                if title_el:
                    title_text = title_el.get_text(strip=True)
            
            # FIXED: Poster extraction - Animerco uses data-src on <a> tag, not <img>
            # Priority: 1. data-src on link, 2. style background-image, 3. img tag
            img_url = ""
            
            # 1. Check data-src on the link itself (PRIMARY for Animerco)
            img_url = link_node.get('data-src') or ""
            
            # 2. Check style for background-image (FALLBACK)
            if not img_url:
                style = link_node.get('style') or ""
                if 'url(' in style:
                    m = re.search(r'url\(["\']?(.*?)["\']?\)', style)
                    if m:
                        img_url = m.group(1).strip("'\"")
            
            # 3. Check img tag (FALLBACK for other structures)
            if not img_url:
                img_node = tag.find('img')
                if img_node:
                    img_url = img_node.get('data-src') or img_node.get('src') or ""
                    if not title_text:
                        title_text = img_node.get('alt') or ""

            # Only add items with valid images
            if img_url and img_url.strip():
                # Make sure URL is absolute
                full_img_url = urljoin(self.base_url, img_url)
                items.append({
                    "id": base64.urlsafe_b64encode(full_url.encode()).decode(),
                    "title": title_text or "بدون عنوان",
                    "poster": f"/proxy/image?url={quote(full_img_url)}",
                    "type": "anime"
                })
        return items

    async def fetch_home(self) -> Dict[str, List[Dict[str, Any]]]:
        sections = {}
        all_ids = set()

        def add_items(section_name, items):
            if not items: return
            if section_name not in sections:
                sections[section_name] = []
            for item in items:
                if item["id"] not in all_ids:
                    sections[section_name].append(item)
                    all_ids.add(item["id"])

        try:
            # 1. Fetch the Library page (Fetch first 20 pages for MASSIVE content)
            for page in range(1, 21):
                library_url = urljoin(self.base_url, f"/animes/page/{page}/" if page > 1 else "/animes/")
                html_lib = await self._get_html(library_url)
                if html_lib:
                    soup_lib = BeautifulSoup(html_lib, 'html.parser')
                    lib_items = self._extract_anime_items(soup_lib)
                    if lib_items:
                        # Mix items into general library or page-specific sections
                        if page <= 2:
                            add_items("مكتبة الأنمي", lib_items)
                        else:
                            add_items(f"اكتشف المزيد - صفحة {page}", lib_items)
                else:
                    # If we hit an empty page, stop
                    break

            # 2. Fetch Featured and other sections from Root
            html_home = await self._get_html(self.base_url)
            if html_home:
                soup_home = BeautifulSoup(html_home, 'html.parser')
                
                # Featured slider
                featured_soup = soup_home.select_one('.featured-slider, .featured-content, .slider, #slider, .hero-slider')
                if featured_soup:
                    add_items("أنميات مميزة", self._extract_anime_items(featured_soup))

                # Dynamic sections (Trending, Latest, etc.)
                for sec in soup_home.select('section, .media-carousel, .row, .block-items, .items, .items-container'):
                    title_node = sec.select_one('.title, h2, h3, .block-title, .widget-title, .section-title')
                    if not title_node: continue
                    sec_title = title_node.get_text(strip=True)
                    if not sec_title or len(sec_title) > 60: continue
                    
                    items = self._extract_anime_items(sec)
                    if items:
                        add_items(sec_title, items)

        except Exception as e:
            logger.error(f"Error in fetch_home: {e}")
            
        return sections

    async def fetch_anime_list(self, page: int = 1) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/animes/page/{page}/" if page > 1 else f"{self.base_url}/animes/"
        html = await self._get_html(url)
        if not html: return []
        return self._extract_anime_items(BeautifulSoup(html, 'html.parser'))

    async def search(self, query: str) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/?s={quote(query)}"
        html = await self._get_html(url)
        if not html: return []
        return self._extract_anime_items(BeautifulSoup(html, 'html.parser'))

    async def fetch_details(self, safe_id: str) -> Dict[str, Any]:
        try:
            url = base64.urlsafe_b64decode(safe_id).decode()
        except: return {}

        html = await self._get_html(url)
        if not html: return {}
        
        soup = BeautifulSoup(html, 'html.parser')
        title_el = soup.find('h1')
        title = title_el.get_text(strip=True) if title_el else "Unknown"
        
        is_episode = "/episodes/" in url
        
        # Details metadata
        meta = {}
        for li in soup.select('.anime-info li, .meta-info li, .info-list li'):
            text = li.get_text(strip=True)
            if ':' in text:
                key, val = text.split(':', 1)
                meta[key.strip()] = val.strip()

        details = {
            "id": safe_id,
            "title": title,
            "description": soup.select_one('.anime-story, .story, .description, .post-content').get_text(strip=True) if soup.select_one('.anime-story, .story, .description, .post-content') else "",
            "poster": self._extract_poster(soup),
            "type": "anime",
            "meta": meta,
            "seasons": [],
            "episodes": [],
            "servers": [],
            "download_links": []
        }

        if is_episode:
            # It's an episode page, extract servers and downloads
            details["servers"] = await self._extract_servers(soup, url)
            details["download_links"] = self._extract_downloads(soup)
            
            # Try to find the parent anime for episodes list/breadcrumb
            parent_link = soup.select_one('.page-controls a.btn.seasons, .breadcrumb a:nth-last-child(2)')
            if parent_link and parent_link.get('href'):
                p_url = urljoin(self.base_url, parent_link['href'])
                p_html = await self._get_html(p_url)
                if p_html:
                    p_soup = BeautifulSoup(p_html, 'html.parser')
                    # Pass p_url (parent url) not url
                    details["episodes"] = self._extract_episodes_from_soup(p_soup, p_url)
                    details["seasons"] = self._extract_seasons(p_soup)
        else:
            # It's an anime/season page
            details["seasons"] = self._extract_seasons(soup)
            details["episodes"] = self._extract_episodes_from_soup(soup, url)

            # FIX: If we have episodes, auto-fetch servers for the first episode 
            # so the player doesn't show "No server selected"
            if details["episodes"]:
                try:
                    # Sort to get the first episode
                    eps = sorted(details["episodes"], key=lambda x: int(x["episode"]) if x["episode"].isdigit() else 999)
                    first_ep_url = eps[0]["url"]
                    ep_html = await self._get_html(first_ep_url)
                    if ep_html:
                        ep_soup = BeautifulSoup(ep_html, 'html.parser')
                        details["servers"] = await self._extract_servers(ep_soup, first_ep_url)
                        details["download_links"] = self._extract_downloads(ep_soup)
                except Exception as e:
                    logger.error(f"Auto-fetch first episode servers failed: {e}")

            # If it's a series and has seasons but no episodes yet, fetch the first season
            if details["seasons"] and not details["episodes"]:
                try:
                    s_url = base64.urlsafe_b64decode(details["seasons"][0]["id"]).decode()
                    s_html = await self._get_html(s_url)
                    if s_html:
                        s_soup = BeautifulSoup(s_html, 'html.parser')
                        details["episodes"] = self._extract_episodes_from_soup(s_soup, s_url)
                        
                        # Again, if we found episodes, fetch the first one's servers
                        if details["episodes"] and not details["servers"]:
                            eps = sorted(details["episodes"], key=lambda x: int(x["episode"]) if x["episode"].isdigit() else 999)
                            first_ep_url = eps[0]["url"]
                            ep_html = await self._get_html(first_ep_url)
                            if ep_html:
                                ep_soup = BeautifulSoup(ep_html, 'html.parser')
                                details["servers"] = await self._extract_servers(ep_soup, first_ep_url)
                                details["download_links"] = self._extract_downloads(ep_soup)
                except: pass

        return details

    def _extract_seasons(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        seasons = []
        nodes = soup.select('.seasons-list a, .anime-seasons a, a[href*="/seasons/"]')
        seen = set()
        for a in nodes:
            url = urljoin(self.base_url, a['href'])
            if url in seen: continue
            seen.add(url)
            seasons.append({
                "number": len(seasons) + 1,
                "title": a.get_text(strip=True),
                "id": base64.urlsafe_b64encode(url.encode()).decode(),
            })
        return seasons

    def _extract_episodes_from_soup(self, soup: BeautifulSoup, current_url: str) -> List[Dict[str, Any]]:
        episodes = []
        # Improved selectors for episodes
        nodes = soup.select('.episodes-lists a, .anime-episodes a, .episode-item a, a[href*="/episodes/"]')
        seen = set()
        for a in nodes:
            url = urljoin(self.base_url, a['href'])
            text = a.get_text(strip=True)
            
            # Skip navigation links or empty text
            if not text or any(x in text for x in ["التالية", "السابقة", "المواسم", "قائمة"]):
                if not re.search(r'\d+', text): continue
            
            if url in seen or url.rstrip('/') == current_url.rstrip('/'): continue
            seen.add(url)
            num = re.search(r'(\d+)', text)
            
            episodes.append({
                "id": base64.urlsafe_b64encode(url.encode()).decode(),
                "title": text or f"الحلقة {num.group(1) if num else ''}",
                "episode": num.group(1) if num else "",
                "url": url
            })
        
        # Sort episodes by number if possible
        try:
            episodes.sort(key=lambda x: int(x["episode"]) if x["episode"].isdigit() else 0)
        except: pass
            
        return episodes

    async def _extract_servers(self, soup: BeautifulSoup, current_url: str = "") -> List[Dict[str, Any]]:
        servers = []
        ajax_url = urljoin(self.base_url, "/wp-admin/admin-ajax.php")
        
        # Comprehensive list of selectors for player options
        opts = soup.select('a.option[data-post], .server-list a, .watch-servers a, #playeroptionsul li, .dooplay_player_option')
        
        seen_urls = set()
        dt_ajax = {}
        
        # Extract dtAjax variable for valid nonce
        for s in soup.find_all('script'):
            if s.string and 'var dtAjax' in s.string:
                try:
                    start = s.string.find('var dtAjax = ') + len('var dtAjax = ')
                    end = s.string.find(';', start)
                    json_str = s.string[start:end]
                    import json
                    dt_ajax = json.loads(json_str)
                except Exception as e:
                    logger.error(f"Failed to parse dtAjax: {e}")
                break

        for opt in opts:
            # Handle both <a> and <li> with data attributes
            target = opt if opt.get('data-post') else opt.find('a', attrs={'data-post': True}) or opt
            
            name = target.get_text(strip=True)
            post_id = target.get('data-post')
            nume = target.get('data-nume')
            data_nonce = target.get('data-nonce')
            type_val = target.get('data-type')
            
            if post_id and nume:
                try:
                    # Try common actions
                    for action in ["player_ajax", "dooplay_player_ajax", "doo_player_ajax"]:
                        # Prepare variations of payload
                        payloads = []
                        
                        # Standard with 'nonce' key
                        if data_nonce:
                            payloads.append({
                                "action": action,
                                "post": post_id,
                                "nume": nume,
                                "type": type_val or "tv",
                                "nonce": data_nonce
                            })
                            payloads.append({
                                "action": action,
                                "post": post_id,
                                "nume": nume,
                                "type": type_val or "tv",
                                "security": data_nonce
                            })
                        
                        # Using dtAjax values if available
                        if dt_ajax.get('nonce'):
                            payloads.append({
                                "action": action,
                                "post": post_id,
                                "nume": nume,
                                "type": type_val or "tv",
                                "nonce": dt_ajax['nonce']
                            })
                            
                        if dt_ajax.get('security'):
                             payloads.append({
                                "action": action,
                                "post": post_id,
                                "nume": nume,
                                "type": type_val or "tv",
                                "security": dt_ajax['security']
                            })

                        # Minimal headers to avoid WAF blocking
                        ajax_headers = {
                            "User-Agent": self.headers["User-Agent"],
                            "Referer": current_url,
                            "Content-Type": "application/x-www-form-urlencoded"
                        }

                        success = False
                        for p in payloads:
                            try:
                                resp = await self.session.post(ajax_url, data=p, headers=ajax_headers)
                                
                                if resp.status_code == 200:
                                    text = resp.text
                                    # Check if response contains iframe src
                                    if 'src=' in text or 'iframe' in text or 'embed_url' in text:
                                        # Try multiple regex patterns
                                        patterns = [
                                            r'src=["\'](.*?)["\']',
                                            r'"embed_url"\s*:\s*"([^"]+)"',
                                            r'<iframe[^>]+src=["\'](.*?)["\']'
                                        ]
                                        
                                        for pattern in patterns:
                                            m = re.search(pattern, text)
                                            if m:
                                                url = m.group(1)
                                                if url.startswith('//'): url = 'https:' + url
                                                if url and url.startswith('http') and url not in seen_urls and self._is_safe_server_url(url):
                                                    servers.append({
                                                        "name": name or f"Server {nume}",
                                                        "url": url,
                                                        "type": "iframe"
                                                    })
                                                    seen_urls.add(url)
                                                    success = True
                                                    break
                                        if success: break
                            except Exception as e:
                                logger.debug(f"AJAX request failed: {e}")
                        
                        if success: break
                        
                except Exception as e:
                    logger.error(f"Server extraction error: {e}")
            
            # Fallback for direct links in options if AJAX fails or not present
            href = target.get('href')
            if href and 'javascript' not in href and '#' not in href:
                full_href = urljoin(self.base_url, href)
                if full_href not in seen_urls and self._is_safe_server_url(full_href):
                    servers.append({"name": name or "سيرفر خارجي", "url": full_href, "type": "iframe"})
                    seen_urls.add(full_href)
        
        # Final fallback: Look for any iframe already in the page
        if not servers:
            for iframe in soup.select('.player-container iframe, #player iframe, .watch-container iframe, iframe'):
                src = iframe.get('src')
                if src and "animerco" not in src and not any(x in src.lower() for x in ['ads', 'google', 'facebook', 'tracker']):
                    if src.startswith('//'): src = 'https:' + src
                    if src not in seen_urls and self._is_safe_server_url(src):
                        servers.append({"name": "سيرفر افتراضي", "url": src, "type": "iframe"})
                        seen_urls.add(src)
        
        # Super Fallback: Use Download links as Servers if they are streamable
        if not servers:
            downloads = self._extract_downloads(soup)
            for dl in downloads:
                url = dl.get('url', '')
                if '/links/' in url:
                    try:
                        # Follow redirect headers only to be fast
                        head_resp = await self.session.head(url, follow_redirects=True)
                        final_url = str(head_resp.url)
                        
                        # Convert common file hosts to embed/stream format
                        stream_url = None
                        name = dl.get('server', 'Server')
                        
                        if 'mp4upload' in final_url:
                            # https://www.mp4upload.com/xv8... -> https://www.mp4upload.com/embed-xv8...
                            file_id = re.search(r'mp4upload\.com/([a-zA-Z0-9]+)', final_url)
                            if file_id: stream_url = f"https://www.mp4upload.com/embed-{file_id.group(1)}.html"
                            name = "MP4Upload"
                        elif 'dood' in final_url:
                            # https://dood.li/d/... -> https://dood.li/e/...
                            file_id = re.search(r'dood\.(?:li|la|com|ws|so|re|wf)/[de]/([a-zA-Z0-9]+)', final_url)
                            if file_id: stream_url = f"https://dood.li/e/{file_id.group(1)}"
                            name = "DoodStream"
                        elif 'mixdrop' in final_url:
                            # https://mixdrop.co/f/... -> https://mixdrop.co/e/...
                            file_id = re.search(r'mixdrop\.(?:co|to|ch|ag)/[fe]/([a-zA-Z0-9]+)', final_url)
                            if file_id: stream_url = f"https://mixdrop.co/e/{file_id.group(1)}"
                            name = "MixDrop"
                        elif 'mega.nz' in final_url:
                             if '/file/' in final_url:
                                stream_url = final_url.replace('/file/', '/embed/')
                             elif '/#F!' not in final_url and '/folder/' not in final_url:
                                 # Assume it's a file link if straightforward
                                 pass
                             name = "Mega"
                        elif '4shared' in final_url:
                             # 4shared embed: https://www.4shared.com/web/embed/file/<id>
                             # url: https://www.4shared.com/video/abcdef/Name.html
                             # This is harder to guess without visiting, but let's try generic
                             pass
                            
                        if stream_url and stream_url not in seen_urls and self._is_safe_server_url(stream_url):
                            servers.append({"name": name, "url": stream_url, "type": "iframe"})
                            seen_urls.add(stream_url)
                            
                    except Exception as e:
                        logger.error(f"Fallback server conversion failed for {url}: {e}")

        return servers

    def _extract_downloads(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        downloads = []
        # Target the specific table structure found on Animerco
        table_rows = soup.select('#download table tbody tr')
        if table_rows:
            for tr in table_rows:
                cols = tr.find_all('td')
                if len(cols) >= 3:
                    link_node = cols[0].find('a')
                    if link_node and link_node.get('href'):
                        quality = cols[2].get_text(strip=True)
                        server_node = cols[1].find(class_='favicon')
                        server_name = ""
                        if server_node and server_node.get('data-src'):
                            # Try to extract domain from icon URL
                            m = re.search(r'domain=(.*?)(&|$)', server_node['data-src'])
                            if m:
                                server_name = m.group(1).capitalize()
                        
                        if not server_name:
                            server_name = cols[1].get_text(strip=True)
                            
                        downloads.append({
                            "quality": f"{server_name} - {quality}",
                            "url": urljoin(self.base_url, link_node['href'])
                        })
        
        # Fallback for other formats
        if not downloads:
            items = soup.select('.download-links a, a[href*="/links/"], .download-btns a')
            for row in items:
                text = row.get_text(strip=True)
                href = row.get('href', '')
                if any(x in text.lower() or x in href.lower() for x in ["تحميل", "download", "/links/"]):
                    downloads.append({
                        "quality": text or "رابط تحميل",
                        "url": urljoin(self.base_url, href)
                    })
        return downloads

    def _extract_poster(self, soup: BeautifulSoup) -> str:
        # Improved poster extraction for details page
        poster_els = soup.select('.anime-poster, .poster, .image, .post-thumbnail, .thumb')
        for el in poster_els:
            # Check img tag
            img = el.find('img')
            if img:
                url = img.get('data-src') or img.get('src')
                if url and not url.endswith('.gif'): # Skip loaders
                    return f"/proxy/image?url={quote(urljoin(self.base_url, url))}"
            
            # Check data-src on element itself
            url = el.get('data-src')
            if url:
                return f"/proxy/image?url={quote(urljoin(self.base_url, url))}"
            
            # Check background image
            style = el.get('style', '')
            if 'url(' in style:
                m = re.search(r'url\(["\']?(.*?)["\']?\)', style)
                if m:
                    url = m.group(1).strip("'\"")
                    if url:
                        return f"/proxy/image?url={quote(urljoin(self.base_url, url))}"
        
        # Fallback to any img in main content
        main_img = soup.select_one('.post-content img, .entry-content img')
        if main_img:
            url = main_img.get('data-src') or main_img.get('src')
            if url:
                return f"/proxy/image?url={quote(urljoin(self.base_url, url))}"
                
        return ""

    async def fetch_episode(self, safe_id: str) -> Dict[str, Any]:
        # Backward compatibility
        details = await self.fetch_details(safe_id)
        return {
            "title": details.get("title", "Episode"),
            "servers": details.get("servers", []),
            "download_links": details.get("download_links", []),
            "next_episode": self._extract_nav_link(BeautifulSoup("", "html.parser"), "التالية"), # Placeholder
            "prev_episode": self._extract_nav_link(BeautifulSoup("", "html.parser"), "السابقة")
        }

    def _extract_nav_link(self, soup: BeautifulSoup, text: str) -> Optional[str]:
        a = soup.find('a', string=re.compile(text)) or soup.select_one(f'.{"next" if "تالية" in text else "prev"}-episode a')
        if a and a.get('href'):
            url = urljoin(self.base_url, a['href'])
            return base64.urlsafe_b64encode(url.encode()).decode()
        return None

animerco_scraper = AnimercoScraper()
