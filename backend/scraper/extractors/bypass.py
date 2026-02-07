
import re
import base64
import json
import logging
from typing import Optional
from urllib.parse import urlparse
from curl_cffi.requests import AsyncSession
from scraper.extractors.okprime import OkPrimeExtractor

logger = logging.getLogger(__name__)

class BypassExtractor:
    """
    Python implementation of host extraction logic from stream-bypass project.
    """
    
    @staticmethod
    async def extract(url: str) -> Optional[dict]:
        domain = urlparse(url).netloc.lower()
        
        # 1. Voe.sx (Lauradaydo) - Handled by specialized VoeExtractor or logic below
        if any(x in domain for x in ['voe.sx', 'lauradaydo']):
            from scraper.extractors.voe import VoeExtractor
            return await VoeExtractor.extract(url)

        # 2. Mixdrop / Mxdrop
        if any(x in domain for x in ['mixdrop', 'mxdrop']):
             return await BypassExtractor._extract_mixdrop(url)

        # 4. Streamtape
        if 'streamtape' in domain:
             return await BypassExtractor._extract_streamtape(url)

        # 5. Upstream
        if 'upstream' in domain:
             return await BypassExtractor._extract_upstream(url)
             
        # 6. Vidoza
        if 'vidoza' in domain:
             return await BypassExtractor._extract_vidoza(url)

        # 7. ReviewRate (ArabSeed Private)
        if 'reviewrate' in domain:
             return await BypassExtractor._extract_reviewrate(url)

        # 8. Up4fun
        if 'up4fun' in domain:
             return await BypassExtractor._extract_up4fun(url)

        return None

    @staticmethod
    async def _extract_mixdrop(url: str) -> Optional[dict]:
        try:
            async with AsyncSession(impersonate="chrome124", verify=False) as session:
                resp = await session.get(url, timeout=15)
                text = resp.text
                
                # Check for packed JS
                if "eval(function(p,a,c,k,e,d)" in text:
                    unpacked = OkPrimeExtractor._decode_packed(text)
                    if unpacked: text += unpacked
                
                match = re.search(r'MDCore\.wurl\s*=\s*["\']([^"\']+)["\']', text)
                if match:
                    wurl = match.group(1)
                    if wurl.startswith('//'): wurl = 'https:' + wurl
                    return {"url": wurl, "type": "mp4", "headers": {"Referer": url}}
        except: pass
        return None

    @staticmethod
    async def _extract_upstream(url: str) -> Optional[dict]:
        try:
            async with AsyncSession(impersonate="chrome124", verify=False) as session:
                resp = await session.get(url, timeout=15)
                text = resp.text
                
                if "eval(function(p,a,c,k,e,d)" in text:
                    unpacked = OkPrimeExtractor._decode_packed(text)
                    if unpacked:
                        m3u8_match = re.search(r'file\s*:\s*["\']([^"\']+)["\']', unpacked)
                        if m3u8_match:
                            return {"url": m3u8_match.group(1), "type": "hls", "headers": {"Referer": url}}
        except: pass
        return None

    @staticmethod
    async def _extract_vidoza(url: str) -> Optional[dict]:
        try:
            async with AsyncSession(impersonate="chrome124", verify=False) as session:
                resp = await session.get(url, timeout=15)
                text = resp.text
                
                # Vidoza usually has src: "..."
                match = re.search(r'src\s*:\s*["\']([^"\']+)["\']', text)
                if match:
                    return {"url": match.group(1), "type": "mp4", "headers": {"Referer": url}}
        except: pass
        return None

    @staticmethod
    async def _extract_streamtape(url: str) -> Optional[dict]:
        """
        Specialized logic for Streamtape.
        """
        try:
            async with AsyncSession(impersonate="chrome124", verify=False) as session:
                resp = await session.get(url, timeout=15)
                text = resp.text
                
                # Streamtape logic is often: document.getElementById('videolink').innerHTML = "part1" + "part2" ...
                # We look for the 'videolink' pattern
                match = re.search(r"document\.getElementById\(['\"]robotlink['\"]\)\.innerHTML\s*=\s*(['\"].*?['\"]);", text)
                if not match:
                    match = re.search(r"document\.getElementById\(['\"]videolink['\"]\)\.innerHTML\s*=\s*(['\"].*?['\"]);", text)
                
                if match:
                    # The value is usually a series of strings added together
                    # e.g. 'part1' + 'part2' ...
                    parts = re.findall(r"['\"]([^'\"]+)['\"]", match.group(1))
                    if parts:
                        link = "".join(parts)
                        if link.startswith('//'): link = 'https:' + link
                        # Add token if needed (Streamtape often needs &token= at the end)
                        return {"url": link, "type": "mp4", "headers": {"Referer": url}}
        except: pass
        return None

    @staticmethod
    async def _extract_reviewrate(url: str) -> Optional[dict]:
        try:
            async with AsyncSession(impersonate="chrome124", verify=False) as session:
                resp = await session.get(url, timeout=15)
                text = resp.text
                
                # Check for direct MP4
                match = re.search(r'(https?://[^\s"\']+\.mp4[^\s"\']*)', text)
                if match:
                    return {"url": match.group(1), "type": "mp4", "headers": {"Referer": url}}
                
                # Check for m3u8
                match = re.search(r'(https?://[^\s"\']+\.m3u8[^\s"\']*)', text)
                if match:
                    return {"url": match.group(1), "type": "hls", "headers": {"Referer": url}}
        except: pass
        return None

    @staticmethod
    async def _extract_up4fun(url: str) -> Optional[dict]:
        try:
            async with AsyncSession(impersonate="chrome124", verify=False) as session:
                resp = await session.get(url, timeout=15)
                text = resp.text
                
                if "eval(function(p,a,c,k,e,d)" in text:
                    unpacked = OkPrimeExtractor._decode_packed(text)
                    if unpacked:
                        # Search for file: "..." or src: "..."
                        match = re.search(r'(?:file|src)\s*[:=]\s*["\'](https?://[^"\']+)["\']', unpacked)
                        if match:
                            s_url = match.group(1).replace(r'\/', '/')
                            return {
                                "url": s_url, 
                                "type": "hls" if ".m3u8" in s_url else "mp4", 
                                "headers": {"Referer": url}
                            }
        except: pass
        return None
