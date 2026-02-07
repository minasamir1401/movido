
import re
import logging
from typing import Optional
from curl_cffi.requests import AsyncSession

logger = logging.getLogger(__name__)

class VidmolyExtractor:
    @staticmethod
    async def extract(url: str) -> Optional[dict]:
        """
        Extracts video from Vidmoly / Vidoba / etc.
        """
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                "Referer": url
            }
            
            async with AsyncSession(impersonate="chrome124", verify=False) as session:
                resp = await session.get(url, headers=headers)
                text = resp.text
                
                # Handle "Click here to view" redirection (common in Vidmoly)
                if ("Please wait" in text or "startLoading" in text) and "?g=" not in url:
                     match = re.search(r"url\s*\+=\s*['\"]\?g=([a-f0-9]+)['\"]", text)
                     if match:
                         g_val = match.group(1)
                         redirect_url = f"{url}&g={g_val}" if "?" in url else f"{url}?g={g_val}"
                         logger.info(f"Vidmoly following internal redirect: {redirect_url}")
                         resp = await session.get(redirect_url, headers=headers)
                         text = resp.text

                # 1. Search for file sources (m3u8/mp4) in JS
                sources = re.findall(r'file\s*:\s*["\'](https?://[^"\']+)["\']', text)
                for src in sources:
                    if ".m3u8" in src:
                        return {"url": src, "type": "hls", "headers": {"Referer": url}}
                    if ".mp4" in src:
                        return {"url": src, "type": "mp4", "headers": {"Referer": url}}

                # 2. Packed JS?
                if "eval(function(p,a,c,k,e,d)" in text:
                    # Generic unpacker (borrowed from OkPrime logic if needed, but usually simple regex works on unpacked too)
                    # For now, let's try to assume the sources are not heavily packed or we need a specific unpacker import
                    # We can assume `file:` is inside the packed code
                    from scraper.extractors.okprime import OkPrimeExtractor
                    unpacked = OkPrimeExtractor._decode_packed(text)
                    if unpacked:
                        sources = re.findall(r'file\s*:\s*["\'](https?://[^"\']+)["\']', unpacked)
                        for src in sources:
                            if ".m3u8" in src:
                                return {"url": src, "type": "hls", "headers": {"Referer": url}}
                            if ".mp4" in src:
                                return {"url": src, "type": "mp4", "headers": {"Referer": url}}

                # 3. JWPlayer setup
                jw_match = re.search(r'jwplayer\("vplayer"\)\.setup\({(.*?)}\)', text, re.DOTALL)
                if jw_match:
                    json_str = jw_match.group(1)
                    src_match = re.search(r'file\s*:\s*["\']([^"\']+)["\']', json_str)
                    if src_match:
                         return {"url": src_match.group(1), "type": "hls", "headers": {"Referer": url}}

        except Exception as e:
            logger.error(f"Vidmoly extraction failed: {e}")
            
        return None
