import asyncio
import httpx
import re
import logging
import base64
from typing import List, Dict, Optional, Any
from bs4 import BeautifulSoup
# from curl_cffi.requests import AsyncSession

from urllib.parse import urljoin, quote, urlparse
import time

logger = logging.getLogger("courses_scraper")

class CoursesScraper:
    BASE_URL = "https://www.m3aarf.com"
    COURSES_URL = "https://www.m3aarf.com/certified/courses"
    
    def __init__(self):
        # self.session = AsyncSession(impersonate="chrome120", timeout=30, verify=False)
        self.session = httpx.AsyncClient(timeout=30.0, verify=False, follow_redirects=True)

        self._cache = {}
        self._cache_ttl = 3600
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "ar,en-US;q=0.9,en;q=0.8",
            "Referer": "https://www.google.com/",
        }
        self.category_map = {
            "programming": "12",
            "graphic-design": "13",
            "languages": "14",
            "marketing": "15"
        }

    async def _get_html(self, url: str) -> Optional[str]:
        now = time.time()
        if url in self._cache:
            ts, data = self._cache[url]
            if now - ts < self._cache_ttl:
                return data

        try:
            # 1. Try DIRECT fast request with curl_cffi first (Much faster)
            try:
                logger.info(f"⚡ Fetching {url} via direct httpx...")
                resp = await self.session.get(url, headers=self.headers)
                if resp.status_code == 200:
                    # Simple check to ensure we didn't get a captcha page with 200 OK
                    if "Just a moment..." not in resp.text and "challenges.cloudflare.com" not in resp.text:
                        self._cache[url] = (now, resp.text)
                        return resp.text
                    else:
                        logger.warning(f"⚠️ Cloudflare challenge detected on {url}")
                else:
                    logger.warning(f"⚠️ Direct fetch failed with status {resp.status_code}")
            except Exception as e:
                logger.warning(f"⚠️ Direct fetch error: {e}")

            # 2. Fallback to FlareSolverr (Slower but reliable)
            logger.info(f"🐢 Fallback to FlareSolverr for {url}...")
            flaresolverr_url = "http://localhost:8191/v1"
            payload = {
                "cmd": "request.get",
                "url": url,
                "maxTimeout": 60000
            }
            async with httpx.AsyncClient(timeout=90.0) as client:
                response = await client.post(flaresolverr_url, json=payload)
                if response.status_code == 200:
                    data = response.json()
                    if data.get('status') == 'ok':
                        html = data.get('solution', {}).get('response', '')
                        self._cache[url] = (now, html)
                        return html
        except Exception as e:
            logger.error(f"Failed to fetch {url}: {e}")
        return None

    def _extract_course_items(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        items = []
        # The card itself is the <a> tag with class course-card-custom
        cards = soup.select('.course-card-custom')
        
        for card in cards:
            href = card.get('href')
            if not href: continue

            title_tag = card.select_one('.card-title, h3, h2, .course-title')
            title = title_tag.get_text(strip=True) if title_tag else ""
            
            img_tag = card.select_one('img')
            img_url = ""
            if img_tag:
                # Prioritize data-src because src is often a placeholder
                img_url = img_tag.get('data-src') or img_tag.get('src') or ""
                
            if img_url and not img_url.startswith('http'):
                img_url = urljoin(self.BASE_URL, img_url)
            
            instructor = card.select_one('.channel_title, .instructor-name, .teacher-name').get_text(strip=True) if card.select_one('.channel_title, .instructor-name, .teacher-name') else ""
            
            lessons_count = ""
            # Try specific selector for new design
            lesson_span = card.select_one('.text-icon span')
            if lesson_span:
                lessons_count = lesson_span.get_text(strip=True)
            else:
                l_tag = card.select_one('.lessons-count, .count')
                if l_tag: lessons_count = l_tag.get_text(strip=True)
            
            # Simple ID generation from URL
            course_id = href.split('/')[-2] if '/' in href else href
            safe_id = base64.urlsafe_b64encode(href.encode()).decode()

            items.append({
                "id": safe_id,
                "course_id": course_id,
                "title": title,
                "poster": f"/proxy/image?url={quote(img_url)}" if img_url else "",
                "instructor": instructor,
                "lessons_count": lessons_count,
                "type": "course"
            })
        return items

    async def fetch_latest_courses(self, page: int = 1) -> List[Dict[str, Any]]:
        url = f"{self.COURSES_URL}?page={page}"
        html = await self._get_html(url)
        if not html: return []
        return self._extract_course_items(BeautifulSoup(html, 'html.parser'))

    async def fetch_category_courses(self, cat_id: str, page: int = 1) -> List[Dict[str, Any]]:
        # Map slugs to IDs if necessary
        actual_cat_id = self.category_map.get(cat_id.lower(), cat_id)
        url = f"{self.BASE_URL}/certified/cat/{actual_cat_id}?page={page}"
        html = await self._get_html(url)
        if not html: return []
        return self._extract_course_items(BeautifulSoup(html, 'html.parser'))

    async def search_courses(self, query: str) -> List[Dict[str, Any]]:
        url = f"{self.COURSES_URL}?search={quote(query)}"
        html = await self._get_html(url)
        if not html: return []
        return self._extract_course_items(BeautifulSoup(html, 'html.parser'))

    async def fetch_course_details(self, safe_id: str) -> Dict[str, Any]:
        try:
            url = base64.urlsafe_b64decode(safe_id).decode()
        except: return {}

        html = await self._get_html(url)
        if not html: return {}
        
        soup = BeautifulSoup(html, 'html.parser')
        
        title = soup.find('h1').get_text(strip=True) if soup.find('h1') else ""
        description = soup.select_one('.course-desc, .description, #description').get_text(strip=True) if soup.select_one('.course-desc, .description, #description') else ""
        instructor = soup.select_one('.instructor-info h4, .teacher-name').get_text(strip=True) if soup.select_one('.instructor-info h4, .teacher-name') else ""
        
        lessons = []
        
        def extract_lessons_from_soup(s):
            params = []
            l_items = s.select('a[href*="/lesson/"]')
            for item in l_items:
                l_href = item.get('href')
                l_title = item.get_text(strip=True)
                l_id = l_href.split('/')[-1].replace('-video', '') if '/' in l_href else l_href
                duration = item.parent.select_one('.duration, .time').get_text(strip=True) if item.parent.select_one('.duration, .time') else ""
                
                params.append({
                    "id": l_id,
                    "title": l_title,
                    "duration": duration,
                    "link": urljoin(self.BASE_URL, l_href)
                })
            return params

        # 1. Get lessons from page 1
        lessons.extend(extract_lessons_from_soup(soup))

        # 2. Handle Pagination (Parallel Fetching)
        pagination_links = soup.select('.pagination .page-item a.page-link')
        if pagination_links:
            page_numbers = []
            for link in pagination_links:
                try:
                    p_num = int(link.get_text(strip=True))
                    page_numbers.append(p_num)
                except ValueError:
                    # Check href for page number if text is 'Next' or icons
                    href_val = link.get('href', '')
                    if 'page=' in href_val:
                        try:
                            page_numbers.append(int(href_val.split('page=')[-1]))
                        except: pass
            
            if page_numbers:
                max_page = max(page_numbers)
                logger.info(f"📚 Found {max_page} pages for course. Fetching parallel...")
                
                tasks = []
                for p in range(2, max_page + 1):
                    p_url = f"{url}?page={p}" if '?' not in url else f"{url}&page={p}"
                    tasks.append(self._get_html(p_url))
                
                results = await asyncio.gather(*tasks)
                
                for res in results:
                    if res:
                        p_soup = BeautifulSoup(res, 'html.parser')
                        lessons.extend(extract_lessons_from_soup(p_soup))
                        
        # 3. Add Index
        for idx, lesson in enumerate(lessons):
            lesson['index'] = idx + 1

        return {
            "id": safe_id,
            "title": title,
            "description": description,
            "instructor": instructor,
            "lessons": lessons,
            "type": "course"
        }

    async def fetch_lesson_video(self, lesson_id: str) -> Optional[str]:
        # lesson_id can be like "2011"
        url = f"{self.BASE_URL}/lesson/{lesson_id}-video"
        html = await self._get_html(url)
        if not html: return None
        
        # Search for YouTube iframe
        soup = BeautifulSoup(html, 'html.parser')
        iframe = soup.select_one('iframe[src*="youtube.com"], iframe[src*="youtu.be"]')
        if iframe:
            return iframe.get('src')
        
        # Fallback to regex for any youtube link in JS or hidden
        match = re.search(r'https?://(?:www\.)?youtube\.com/embed/[\w-]+', html)
        if match:
            return match.group(0)
            
        return None

courses_scraper = CoursesScraper()
