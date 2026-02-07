import re
import logging
from curl_cffi.requests import AsyncSession

logger = logging.getLogger(__name__)

class OkPrimeExtractor:
    @staticmethod
    def _decode_packed(packed_str):
        """
        Decodes Dean Edwards packer code.
        """
        try:
            # More flexible pattern for Dean Edwards packer
            pattern = r"\}\s*\(\s*['\"](.*?)['\"]\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*['\"](.*?)['\"]\s*\.\s*split\s*\(\s*['\"]\|['\"]\s*\)"
            match = re.search(pattern, packed_str)
            
            if not match:
                # Try another common pattern
                pattern = r"return p\}\s*\(\s*['\"](.*?)['\"]\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*['\"](.*?)['\"]\s*\.split"
                match = re.search(pattern, packed_str)
            
            if not match:
                return None
                
            p = match.group(1)
            a = int(match.group(2))
            c = int(match.group(3))
            k = match.group(4).split('|')
            
            def baseN(num, b):
                return ((num == 0) and "0") or \
                       (baseN(num // b, b).lstrip("0") + "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"[num % b])

            d = {}
            for i in range(c):
                key = baseN(i, a)
                if i < len(k):
                     val = k[i] if k[i] else key
                     d[key] = val
                     
            def replace(match):
                word = match.group(0)
                return d.get(word, word)
            
            return re.sub(r"\b\w+\b", replace, p)
        except Exception as e:
            logger.error(f"Error unpacking script: {e}")
            return None

    @classmethod
    async def extract(cls, url: str, depth: int = 0) -> dict | None:
        """
        Extracts the direct video link from an OkPrime/Larooza iframe URL.
        Recurse up to 3 times for nested components.
        """
        if depth > 3: return None

        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain = f"{parsed.scheme}://{parsed.netloc}/"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Referer": url,
            "Origin": domain.rstrip('/')
        }

        try:
            async with AsyncSession(impersonate="chrome124", verify=False, timeout=20) as session:
                logger.info(f"Fetching OkPrime [D:{depth}]: {url}")
                resp = await session.get(url, headers=headers)
                if resp.status_code != 200: return None
                
                content = resp.text
                final_referer = url

                # 1. Check for JS Redirection (window.location.href)
                js_redir = re.search(r'window\.location\.href\s*=\s*["\'](https?://[^"\']+)["\']', content)
                if js_redir:
                    redir_url = js_redir.group(1)
                    logger.info(f"Following OkPrime JS Redir: {redir_url}")
                    return await cls.extract(redir_url, depth + 1)

                # 2. Look for nested iframes that might be the actual player
                # (Excluding known ad/tracking iframes)
                inner_iframe = re.search(r'<iframe[^>]+src=["\'](https?://[^"\']+)["\']', content)
                if inner_iframe:
                    inner_url = inner_iframe.group(1)
                    if not any(x in inner_url.lower() for x in ['ads', 'google', 'analytics', 'facebook', 'twitter']):
                        logger.info(f"Nested iframe detected: {inner_url}")
                        # If the inner URL is from a different domain, let ExtractorEngine handle it (or recurse here)
                        if any(x in inner_url for x in ['okprime', 'laroza', 'mom', 'homes', 'bond', 'film77']):
                            return await cls.extract(inner_url, depth + 1)

                # 3. Find and unpack the script (Dean Edwards Packer)
                # Patterns to find packed code: eval(function(p,a,c,k,e,d)...)
                all_text = content
                packed_matches = re.findall(r'eval\(function\(p,a,c,k,e,d\).+?split\([\'"]\|[\'"]\)\)', content, re.DOTALL)
                for p in packed_matches:
                    unpacked = cls._decode_packed(p)
                    if unpacked:
                        all_text += "\n" + unpacked

                # 4. Extract direct Stream (M3U8 highest priority, then MP4)
                # Priority 1: M3U8
                m3u8_match = re.search(r'["\'](https?://[^"\']+\.m3u8[^"\']*)["\']', all_text)
                if m3u8_match:
                    s_url = m3u8_match.group(1).replace(r'\/', '/')
                    return {"url": s_url, "type": "hls", "headers": {"Referer": final_referer, "Origin": domain.rstrip('/')}}

                # Priority 2: MP4
                mp4_match = re.search(r'["\'](https?://[^"\']+\.mp4[^"\']*)["\']', all_text)
                if mp4_match:
                    s_url = mp4_match.group(1).replace(r'\/', '/')
                    return {"url": s_url, "type": "mp4", "headers": {"Referer": final_referer, "Origin": domain.rstrip('/')}}
                
                # Priority 3: Sources object in JS (JWPlayer style)
                sources_match = re.search(r'sources\s*:\s*\[(.*?Sync.*?)\]', all_text, re.DOTALL)
                if sources_match:
                    file_match = re.search(r'file\s*:\s*["\'](https?://[^"\']+)["\']', sources_match.group(1))
                    if file_match:
                        file_url = file_match.group(1).replace(r'\/', '/')
                        return {
                            "url": file_url, 
                            "type": "hls" if ".m3u8" in file_url else "mp4",
                            "headers": {"Referer": final_referer}
                        }

        except Exception as e:
            logger.error(f"OkPrime extraction failed at depth {depth}: {e}")
            
        return None
