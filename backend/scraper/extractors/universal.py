"""
Universal Video Extractor
استخراج عام لجميع السيرفرات غير المدعومة
Supports: Film77, Vidspeed, Abstream, Mxdrop, Dsvplay, Short.icu, etc.
"""
import re
import logging
from typing import Optional, Dict
from curl_cffi.requests import AsyncSession
from urllib.parse import urlparse, urljoin

logger = logging.getLogger(__name__)

class UniversalExtractor:
    """Universal extractor for various video hosting services"""
    
    @staticmethod
    def _unpack_js(packed: str) -> str:
        """Unpacks JavaScript packed code (eval(function(p,a,c,k,e,d)))"""
        try:
            # Extract the packed parameters
            match = re.search(
                r"}\('(.+)',(\d+),(\d+),'(.+)'\.split\('\|'\)",
                packed,
                re.DOTALL
            )
            if not match:
                return ""
            
            payload, radix, count, symbols = match.groups()
            radix = int(radix)
            count = int(count)
            symbols = symbols.split('|')
            
            def lookup(match):
                word = match.group(0)
                pos = int(word, radix) if radix > 10 else int(word)
                return symbols[pos] if pos < len(symbols) and symbols[pos] else word
            
            # Replace all words with their symbols
            unpacked = re.sub(r'\b\w+\b', lookup, payload)
            return unpacked
        except Exception as e:
            logger.debug(f"Unpack failed: {e}")
            return ""
    
    @staticmethod
    async def extract(url: str) -> Optional[Dict]:
        """
        Universal extraction for various hosts
        Returns: {"url": "direct_url", "type": "mp4/hls", "headers": {...}}
        """
        try:
            domain = urlparse(url).netloc.lower()
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": url,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
            }
            
            async with AsyncSession(impersonate="chrome124", verify=False, allow_redirects=True) as session:
                logger.info(f"🔍 Universal extracting: {domain}")
                resp = await session.get(url, headers=headers, timeout=20)
                
                if resp.status_code != 200:
                    logger.warning(f"{domain} returned status {resp.status_code}")
                    return None
                
                text = resp.text
                final_url = str(resp.url)
                
                # Handle redirects (especially for short.icu)
                if 'short.icu' in domain or len(text) < 5000:
                    redirect_match = re.search(
                        r'window\.location\.href\s*=\s*["\']([^"\']+)["\']',
                        text
                    )
                    if redirect_match:
                        redirect_url = redirect_match.group(1)
                        logger.info(f"🔄 Following redirect: {redirect_url}")
                        resp = await session.get(redirect_url, headers=headers)
                        text = resp.text
                        final_url = str(resp.url)
                        domain = urlparse(final_url).netloc.lower()
                
                # Unpack JavaScript if needed
                all_text = text
                if "eval(function(p,a,c,k,e,d)" in text:
                    packed_matches = re.findall(
                        r'eval\(function\(p,a,c,k,e,d\).+?split\([\'\"]\|[\'\"]\)\)',
                        text,
                        re.DOTALL
                    )
                    for packed in packed_matches:
                        unpacked = UniversalExtractor._unpack_js(packed)
                        if unpacked:
                            all_text += "\n" + unpacked
                
                # Fix protocol-relative URLs
                all_text = re.sub(r'["\']//([^"\'\s]+\.(?:m3u8|mp4))', r'"https://\1', all_text)
                
                # Strategy 1: Look for specific variable patterns
                patterns = [
                    # Mxdrop/Mixdrop style
                    r'(?:wurl|vfile|video_url|v_url|vurl|vsrc)\s*[:=]\s*["\']([^"\']+)["\']',
                    r'\["(?:wurl|vfile)"\]\s*=\s*["\']([^"\']+)["\']',
                    
                    # JWPlayer/VideoJS style
                    r'file\s*[:=]\s*["\']([^"\']+)["\']',
                    r'source\s*[:=]\s*["\']([^"\']+)["\']',
                    r'src\s*[:=]\s*["\']([^"\']+)["\']',
                    
                    # Voe style (h, m, l keys)
                    r'["\'](?:h|m|l)["\']\s*[:=]\s*["\']([^"\']+)["\']',
                    
                    # Generic sources
                    r'sources?\s*[:=]\s*\[?\s*["\']([^"\']+)["\']',
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, all_text)
                    if match:
                        video_url = match.group(1)
                        if video_url.startswith('//'):
                            video_url = 'https:' + video_url
                        elif not video_url.startswith('http'):
                            video_url = urljoin(final_url, video_url)
                        
                        # Validate it's a real video URL
                        if any(ext in video_url.lower() for ext in ['.m3u8', '.mp4']):
                            if not any(skip in video_url.lower() for skip in ['track', 'pixel', 'ads', 'loading']):
                                logger.info(f"✅ {domain} extracted: {video_url[:80]}...")
                                return {
                                    "url": video_url,
                                    "type": "hls" if ".m3u8" in video_url else "mp4",
                                    "headers": {"Referer": final_url}
                                }
                
                # Strategy 2: Direct M3U8/MP4 search
                # Priority: M3U8
                m3u8_matches = re.findall(r'(https?://[^"\'\s]+\.m3u8[^"\'\s]*)', all_text)
                for m3u8_url in m3u8_matches:
                    if not any(skip in m3u8_url.lower() for skip in ['track', 'pixel', 'ads', 'loading']):
                        clean_url = m3u8_url.replace(r'\/', '/')
                        logger.info(f"✅ {domain} extracted (M3U8): {clean_url[:80]}...")
                        return {
                            "url": clean_url,
                            "type": "hls",
                            "headers": {"Referer": final_url}
                        }
                
                # Priority: MP4
                mp4_matches = re.findall(r'(https?://[^"\'\s]+\.mp4[^"\'\s]*)', all_text)
                for mp4_url in mp4_matches:
                    if not any(skip in mp4_url.lower() for skip in ['track', 'pixel', 'ads', 'loading']):
                        clean_url = mp4_url.replace(r'\/', '/')
                        logger.info(f"✅ {domain} extracted (MP4): {clean_url[:80]}...")
                        return {
                            "url": clean_url,
                            "type": "mp4",
                            "headers": {"Referer": final_url}
                        }
                
                # Strategy 3: Base64 encoded streams
                b64_matches = re.findall(r'["\']([A-Za-z0-9+/]{40,}=*?)["\']', all_text)
                for b64 in b64_matches[:10]:  # Limit to first 10 to avoid performance issues
                    try:
                        import base64
                        decoded = base64.b64decode(b64).decode('utf-8', errors='ignore')
                        if '.m3u8' in decoded or '.mp4' in decoded:
                            stream_match = re.search(
                                r'(https?://[^\s"\'\\\]+\.(?:m3u8|mp4)[^\s"\'\\\]*)',
                                decoded
                            )
                            if stream_match:
                                stream_url = stream_match.group(1)
                                logger.info(f"✅ {domain} extracted (Base64): {stream_url[:80]}...")
                                return {
                                    "url": stream_url,
                                    "type": "hls" if ".m3u8" in stream_url else "mp4",
                                    "headers": {"Referer": final_url}
                                }
                    except:
                        continue
                
                logger.warning(f"❌ {domain}: No video URL found")
                return None
                
        except Exception as e:
            logger.error(f"Universal extraction error for {url}: {e}")
            return None
