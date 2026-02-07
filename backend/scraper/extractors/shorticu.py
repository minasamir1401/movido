
import re
import logging
import asyncio
from typing import Optional, Dict
from curl_cffi.requests import AsyncSession
from urllib.parse import urljoin

logger = logging.getLogger(__name__)

class ShortIcuExtractor:
    @staticmethod
    async def extract(url: str) -> Optional[Dict]:
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://larooza.top/"
            }
            
            async with AsyncSession(impersonate="chrome124", verify=False, timeout=20) as session:
                logger.info(f"🔗 Bypassing Short.icu: {url}")
                
                # تتبع التحويلات (Redirects)
                resp = await session.get(url, headers=headers, allow_redirects=True)
                final_url = str(resp.url)
                
                # البحث عن Meta Refresh
                meta_match = re.search(r'meta[^>]+http-equiv=["\']refresh["\'][^>]+content=["\']\d+;\s*url=([^"\']+)["\']', resp.text, re.I)
                if meta_match:
                    new_url = urljoin(final_url, meta_match.group(1))
                    logger.info(f"✅ Meta refresh found: {new_url}")
                    from scraper.extractors.engine import ExtractorEngine
                    return await ExtractorEngine.extract(new_url)

                if 'short.icu' not in final_url:
                    from scraper.extractors.engine import ExtractorEngine
                    return await ExtractorEngine.extract(final_url)
                
                # البحث عن iframe أو رابط مخفي
                script_links = re.findall(r'(https?://[^"\'\s]+)', resp.text)
                for link in script_links:
                    if any(x in link for x in ['vidmoly', 'voe', 'ok.ru', 'vk.com', 'streaming']):
                        logger.info(f"✅ Found embedded link in Short.icu script: {link}")
                        from scraper.extractors.engine import ExtractorEngine
                        return await ExtractorEngine.extract(link)

                return None
        except Exception as e:
            logger.error(f"ShortIcu error: {e}")
            return None
