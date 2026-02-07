
import re
import logging
import base64
from typing import Optional, Dict
from curl_cffi.requests import AsyncSession

logger = logging.getLogger(__name__)

class DsvplayExtractor:
    """Enhanced Dsvplay extractor with packed JS unpacking and deep link search"""
    
    @staticmethod
    def unpack(packed: str) -> str:
        """Simple unpacker for 'packed' JavaScript (p,a,c,k,e,d)"""
        try:
            pattern = r"}\('(.*)',\s*(\d+),\s*(\d+),\s*'(.*)'\.split\('\|'\)"
            match = re.search(pattern, packed)
            if not match: return packed
            
            p, a, c, k = match.groups()
            a, c = int(a), int(c)
            k = k.split('|')
            
            def e(c):
                return ('' if c < a else e(int(c / a))) + chr(c % a + 161 if c % a > 35 else c % a + 29 if c % a > 9 else c % a + 48)

            while c > 0:
                c -= 1
                if k[c]:
                    p = re.sub(rf'\b{e(c)}\b', k[c], p)
            return p
        except Exception:
            return packed

    @classmethod
    async def extract(cls, url: str) -> Optional[Dict]:
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://larooza.top/",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
            }
            
            async with AsyncSession(impersonate="chrome124", verify=False, timeout=30) as session:
                logger.info(f"🔍 Deep extracting Dsvplay: {url}")
                resp = await session.get(url, headers=headers, allow_redirects=True)
                
                if resp.status_code != 200:
                    return None
                
                text = resp.text
                
                # التحقق من وجود كود معبأ (Packed)
                if "eval(function(p,a,c,k,e,d)" in text:
                    packed_match = re.search(r"eval\(function\(p,a,c,k,e,d\).+?\.split\('\|'\)\)\)", text)
                    if packed_match:
                        unpacked = cls.unpack(packed_match.group(0))
                        text += unpacked # دمج النص المفكوك للبحث فيه
                
                # البحث عن روابط الفيديو (MP4, M3U8)
                # نمط 1: روابط واضحة
                vurl_match = re.search(r'["\'](https?://[^"\'\s]+\.(?:m3u8|mp4)[^"\'\s]*)["\']', text)
                if not vurl_match:
                    # نمط 2: متغيرات JavaScript
                    vurl_match = re.search(r'(?:file|source|src|url)\s*[:=]\s*["\']([^"\'\s]+)["\']', text)

                if vurl_match:
                    video_url = vurl_match.group(1)
                    # تنظيف الرابط إذا كان يحتوي على ترميز خاص
                    video_url = video_url.replace('\\/', '/')
                    
                    if video_url.startswith('//'):
                        video_url = 'https:' + video_url
                        
                    if any(ext in video_url.lower() for ext in ['.m3u8', '.mp4']):
                        logger.info(f"✅ Dsvplay extracted: {video_url[:80]}...")
                        return {
                            "url": video_url,
                            "type": "hls" if ".m3u8" in video_url.lower() else "mp4",
                            "headers": {"Referer": url}
                        }
                
                # محاولة فك تشفير Base64 (شائع في Dsvplay)
                b64_matches = re.findall(r'["\']([a-zA-Z0-9+/]{40,})={0,2}["\']', text)
                for b64_str in b64_matches:
                    try:
                        decoded = base64.b64decode(b64_str).decode('utf-8', errors='ignore')
                        if any(ext in decoded for ext in ['.m3u8', '.mp4']):
                            # وجدنا الرابط!
                            link = re.search(r'(https?://[^\s"\']+)', decoded)
                            if link:
                                video_url = link.group(1)
                                logger.info(f"✅ Dsvplay extracted (Base64): {video_url[:80]}...")
                                return {
                                    "url": video_url,
                                    "type": "hls" if ".m3u8" in video_url.lower() else "mp4",
                                    "headers": {"Referer": url}
                                }
                    except:
                        continue

                logger.warning("❌ Dsvplay: Failed to find direct link")
                return None
                
        except Exception as e:
            logger.error(f"Dsvplay error: {e}")
            return None
