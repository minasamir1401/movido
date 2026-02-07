import logging
import re
from typing import Optional
from urllib.parse import urlparse
from curl_cffi.requests import AsyncSession

# Import Extractors
from scraper.extractors.okprime import OkPrimeExtractor
from scraper.extractors.doodstream import DoodstreamExtractor
from scraper.extractors.vidmoly import VidmolyExtractor
from scraper.extractors.voe import VoeExtractor
from scraper.extractors.bypass import BypassExtractor
from scraper.extractors.arabseed import ArabSeedExtractor
from scraper.extractors.vk import VKExtractor
from scraper.extractors.universal import UniversalExtractor
from scraper.extractors.dsvplay import DsvplayExtractor
from scraper.extractors.shorticu import ShortIcuExtractor

logger = logging.getLogger(__name__)

class ExtractorEngine:
    """
    Central routing engine for "Hybrid Cloud Extraction".
    """
    _cache = {}
    
    @staticmethod
    def clear_cache():
        """Clears the in-memory extraction cache."""
        ExtractorEngine._cache.clear()
        logger.info("🧹 ExtractorEngine Cache Cleared")

    @staticmethod
    async def extract(url: str) -> Optional[dict]:
        """
        Returns cached result or performs extraction.
        """
        import time
        now = time.time()
        if url in ExtractorEngine._cache:
            ts, data = ExtractorEngine._cache[url]
            if now - ts < 3600: # 1 hour cache
                logger.info(f"⚡ Cache Hit (ExtractorEngine): {url}")
                return data
        
        # Logic is moved to _extract_internal
        res = await ExtractorEngine._extract_internal(url)
        
        if res:
            ExtractorEngine._cache[url] = (now, res)
        return res

    @staticmethod
    async def _extract_internal(url: str) -> Optional[dict]:
        """
        Internal extraction logic.
        """
        try:
            # Domain-specific routing
            domain = urlparse(url).netloc.lower()
            
            # 1. ArabSeed / asd.homes
            if any(x in domain for x in ['asd.homes', 'asd.life', 'asd.movie', 'asd.cloud']):
                res = await ArabSeedExtractor.extract(url)
                if res: return res

            # 1b. Larooza / OkPrime / Local Domains
            if any(x in domain for x in ['larooza', 'okprime', 'laroza', 'mom', 'homes', 'bond', 'film77', 'vidspeed', 'short.icu', 'abstream', 'rox']):
                res = await OkPrimeExtractor.extract(url)
                if res:
                    return {
                        "url": res["url"],
                        "type": "hls",
                        "headers": res.get("headers", {})
                    }

            # 2. Vidmoly / Vidoba
            if any(x in domain for x in ['vidmoly', 'vidoba', 'flashtoro']):
                res = await VidmolyExtractor.extract(url)
                if res: return res

            # 5. Voe.sx / Lauradaydo
            if any(x in domain for x in ['voe.sx', 'lauradaydo', 'v-o-e']):
                res = await VoeExtractor.extract(url)
                if res: return res

            # 6. Stream-Bypass Integrated Hosts (Mixdrop, Streamtape, Upstream, Vidoza, ReviewRate, Up4fun, SaveFiles)
            if any(x in domain for x in ['mixdrop', 'mxdrop', 'streamtape', 'upstream', 'vidoza', 'videzz', 'reviewrate', 'up4fun', 'savefiles']):
                res = await BypassExtractor.extract(url)
                if res: return res

            # 7. Doodstream
            if any(x in domain for x in ['dood', 'ds2play', 'd000d', 'd0000d', 'dooood', 'bysezejataos', 'frizat', 'doody']):
                mp4 = await DoodstreamExtractor.extract(url)
                if mp4:
                    return {
                        "url": mp4, 
                        "type": "mp4", 
                        "headers": {"Referer": f"https://{domain}/"}
                    }

            # 9. OkRu
            if 'ok.ru' in domain or 'odnoklassniki' in domain:
                try:
                    from scraper.extractors.okru import OkRuExtractor
                    res = await OkRuExtractor.extract(url)
                    if res: return res
                except Exception: pass

            # 10. VK.com
            if 'vk.com' in domain:
                res = await VKExtractor.extract(url)
                if res: return res

            # 11. Dsvplay
            if 'dsvplay' in domain:
                res = await DsvplayExtractor.extract(url)
                if res: return res

            # 12. Short.icu
            if 'short.icu' in domain:
                res = await ShortIcuExtractor.extract(url)
                if res: return res

            # 13. Universal Extractor (Film77, Vidspeed, Abstream, Mxdrop, etc.)
            if any(x in domain for x in ['film77', 'vidspeed', 'abstream', 'mxdrop', 'minochinos', 'uploady', '1cloudfile', 'usersdrive']):
                res = await UniversalExtractor.extract(url)
                if res: return res


            # --- Enhanced Generic Fallback ---
            # Note: Already imported at top of file
            
            # Use AsyncSession (impersonate) for better bypass
            async with AsyncSession(impersonate="chrome124", verify=False, allow_redirects=True, timeout=20) as session:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                    "Referer": url,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
                }
                
                logger.info(f"Generic extracting: {url}")
                resp = await session.get(url, headers=headers)
                if resp.status_code == 200:
                    text = resp.text
                    final_url = str(resp.url)
                    
                    # 1. Specialized Vidmoly Redirection
                    if "vidmoly.net" in domain and "Please wait" in text and "startLoading()" in text:
                        match = re.search(r"url \+= '\?g=([a-f0-9]+)'", text)
                        if match:
                            g_val = match.group(1)
                            redirect_url = f"{url}?g={g_val}"
                            logger.info(f"Following Vidmoly redirection: {redirect_url}")
                            resp = await session.get(redirect_url, headers=headers)
                            text = resp.text
                            final_url = str(resp.url)

                    # 1. SPECIAL REDIRECTS (Voe, Vidmoly, etc.)
                    if len(text) < 5000: # Usually small redirect pages
                        # Voe.sx -> lauradaydo.com (Handle various spacings)
                        match = re.search(r'window\.location\.href\s*=\s*["\'](https?://[^"\']+)["\']', text)
                        if not match:
                             match = re.search(r'window\.location\s*=\s*["\'](https?://[^"\']+)["\']', text)
                        
                        if match:
                            redir_url = match.group(1)
                            logger.info(f"Following JS redirection: {redir_url}")
                            # Recursive call or fetch here
                            resp = await session.get(redir_url, headers=headers)
                            text = resp.text
                            final_url = str(resp.url)
                            domain = urlparse(final_url).netloc.lower()

                    # 2. Unpack MULTIPLE times if needed (Deep Unpacking)
                    all_text = text
                    for _ in range(5): # Up to 5 levels of unpacking
                        if "eval(function(p,a,c,k,e,d)" in all_text:
                            packed_matches = re.findall(r'eval\(function\(p,a,c,k,e,d\).+?split\([\'"]\|[\'"]\)\)', all_text, re.DOTALL)
                            if not packed_matches: break
                            
                            new_text = ""
                            for p in packed_matches:
                                unpacked = OkPrimeExtractor._decode_packed(p)
                                if unpacked: new_text += unpacked
                            
                            if not new_text or new_text in all_text: break
                            all_text += "\n" + new_text
                        else:
                            break

                    # 3. Protocol-relative URL fix (e.g. //s-delivery33.mxcontent.net/...)
                    all_text = re.sub(r'["\']//([^"\'\s]+\.(?:m3u8|mp4)[^"\'\s]*)', r'"https://\1', all_text)

                    # 4. specialized MDCore (Mxdrop/Mixdrop)
                    if "MDCore" in all_text or "mxdrop" in domain or "mixdrop" in domain:
                        # Sometimes it's inside a function or variable
                        # patterns for wurl, vfile, v_url, etc.
                        patterns = [
                            r'(?:wurl|vfile|video_url|v_url|vurl|vsrc)\s*[:=]\s*["\']([^"\']+)["\']',
                            r'\["(?:wurl|vfile)"\]\s*=\s*["\']([^"\']+)["\']'
                        ]
                        for p in patterns:
                            match = re.search(p, all_text)
                            if match:
                                wurl = match.group(1)
                                if wurl.startswith('//'): wurl = 'https:' + wurl
                                return {"url": wurl, "type": "mp4", "headers": {"Referer": final_url}}

                    # 5. Generic Source / Logic Detection
                    # Look for h, m, l keys (Voe style)
                    voe_source = re.search(r'["\'](?:h|m|l)["\']\s*[:=]\s*["\'](https?://[^"\']+)["\']', all_text)
                    if voe_source:
                         s_url = voe_source.group(1).replace(r'\/', '/')
                         # Check for ad-related content
                         if not any(x in s_url.lower() for x in ['track', 'pixel', 'ads', 'loading', 'placeholder', 'advertisement', 'promo', 'popup', 'popunder', 'popad', 'click', 'tracker', 'analytics', 'stat', 'beacon', 'affiliate', 'banner', 'doubleclick', 'googlesyndication', 'google-analytics', 'googletagmanager', 'facebook', 'connect.facebook', 'twitter', 'google', 'amazon-adsystem', 'pubmatic', 'taboola', 'outbrain', 'revcontent', 'adnxs', 'aaxads', 'zedo', 'exoclick', 'popads', 'popcash', 'propellerads', 'onclickads', 'realsrv', 'juicyads', 'melbet', '1xbet', 'mostbet', 'bet365', 'tapbit', 'okx', 'cryptoad', 'smartcpm', 'clickunder', 'adtarget', 'traffic']):
                             return {"url": s_url, "type": "mp4" if ".mp4" in s_url else "hls", "headers": {"Referer": final_url}}

                    # High priority: m3u8
                    m3u8_matches = re.findall(r'(https?://[^"\']+\.m3u8[^"\']*)', all_text)
                    if m3u8_matches:
                        for m_url in m3u8_matches:
                            if any(x in m_url.lower() for x in ['track', 'pixel', 'ads', 'loading', 'placeholder', 'advertisement', 'promo', 'popup', 'popunder', 'popad', 'click', 'tracker', 'analytics', 'stat', 'beacon', 'affiliate', 'banner', 'doubleclick', 'googlesyndication', 'google-analytics', 'googletagmanager', 'facebook', 'connect.facebook', 'twitter', 'google', 'amazon-adsystem', 'pubmatic', 'taboola', 'outbrain', 'revcontent', 'adnxs', 'aaxads', 'zedo', 'exoclick', 'popads', 'popcash', 'propellerads', 'onclickads', 'realsrv', 'juicyads', 'melbet', '1xbet', 'mostbet', 'bet365', 'tapbit', 'okx', 'cryptoad', 'smartcpm', 'clickunder', 'adtarget', 'traffic']): continue
                            clean_url = m_url.replace(r'\/', '/')
                            # Verify it doesn't look like a fake/placeholder
                            if 'bunny' not in clean_url.lower():
                                return {"url": clean_url, "type": "hls", "headers": {"Referer": final_url}}
                    
                    # Medium priority: mp4
                    mp4_matches = re.findall(r'(https?://[^"\']+\.mp4[^"\']*)', all_text)
                    if mp4_matches:
                        for m_url in mp4_matches:
                            if any(x in m_url.lower() for x in ['track', 'pixel', 'ads', 'loading', 'placeholder', 'advertisement', 'promo', 'popup', 'popunder', 'popad', 'click', 'tracker', 'analytics', 'stat', 'beacon', 'affiliate', 'banner', 'doubleclick', 'googlesyndication', 'google-analytics', 'googletagmanager', 'facebook', 'connect.facebook', 'twitter', 'google', 'amazon-adsystem', 'pubmatic', 'taboola', 'outbrain', 'revcontent', 'adnxs', 'aaxads', 'zedo', 'exoclick', 'popads', 'popcash', 'propellerads', 'onclickads', 'realsrv', 'juicyads', 'melbet', '1xbet', 'mostbet', 'bet365', 'tapbit', 'okx', 'cryptoad', 'smartcpm', 'clickunder', 'adtarget', 'traffic']): continue
                            clean_url = m_url.replace(r'\/', '/')
                            if 'bunny' not in clean_url.lower():
                                return {"url": clean_url, "type": "mp4", "headers": {"Referer": final_url}}
                    
                    # Search specifically for file: "https://..." in scripts (JWPlayer/VideoJS style)
                    script_file_match = re.search(r'file\s*[:=]\s*["\'](https?://[^"\']+)["\']', all_text)
                    if script_file_match:
                        file_url = script_file_match.group(1).replace(r'\/', '/')
                        if any(x in file_url.lower() for x in ['.m3u8', '.mp4']) and 'bunny' not in file_url.lower() and not any(x in file_url.lower() for x in ['track', 'pixel', 'ads', 'loading', 'placeholder', 'advertisement', 'promo', 'popup', 'popunder', 'popad', 'click', 'tracker', 'analytics', 'stat', 'beacon', 'affiliate', 'banner', 'doubleclick', 'googlesyndication', 'google-analytics', 'googletagmanager', 'facebook', 'connect.facebook', 'twitter', 'google', 'amazon-adsystem', 'pubmatic', 'taboola', 'outbrain', 'revcontent', 'adnxs', 'aaxads', 'zedo', 'exoclick', 'popads', 'popcash', 'propellerads', 'onclickads', 'realsrv', 'juicyads', 'melbet', '1xbet', 'mostbet', 'bet365', 'tapbit', 'okx', 'cryptoad', 'smartcpm', 'clickunder', 'adtarget', 'traffic']):
                            return {
                                "url": file_url, 
                                "type": "hls" if ".m3u8" in file_url else "mp4",
                                "headers": {"Referer": final_url}
                            }
                    
                    # Low priority: Search for base64 encoded streams (common in Voe/Abyss)
                    b64_matches = re.findall(r'["\']([A-Za-z0-9+/]{40,}=*?)["\']', all_text)
                    for b64 in b64_matches:
                        try:
                            import base64
                            decoded = base64.b64decode(b64).decode('utf-8', errors='ignore')
                            if '.m3u8' in decoded or '.mp4' in decoded:
                                stream_match = re.search(r'(https?://[^\s"\'\\]+\.(?:m3u8|mp4)[^\s"\'\\]*)', decoded)
                                if stream_match:
                                    s_url = stream_match.group(1)
                                    # Check for ad-related content
                                    if not any(x in s_url.lower() for x in ['track', 'pixel', 'ads', 'loading', 'placeholder', 'advertisement', 'promo', 'popup', 'popunder', 'popad', 'click', 'tracker', 'analytics', 'stat', 'beacon', 'affiliate', 'banner', 'doubleclick', 'googlesyndication', 'google-analytics', 'googletagmanager', 'facebook', 'connect.facebook', 'twitter', 'google', 'amazon-adsystem', 'pubmatic', 'taboola', 'outbrain', 'revcontent', 'adnxs', 'aaxads', 'zedo', 'exoclick', 'popads', 'popcash', 'propellerads', 'onclickads', 'realsrv', 'juicyads', 'melbet', '1xbet', 'mostbet', 'bet365', 'tapbit', 'okx', 'cryptoad', 'smartcpm', 'clickunder', 'adtarget', 'traffic']):
                                        return {
                                            "url": s_url, 
                                            "type": "hls" if ".m3u8" in s_url else "mp4",
                                            "headers": {"Referer": final_url}
                                        }
                        except: pass

        except Exception as e:
            logger.error(f"Extractor Engine Error: {e}")
        
        return None


