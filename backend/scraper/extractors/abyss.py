
import re
import base64
import json
import logging
from typing import Optional
from curl_cffi.requests import AsyncSession

logger = logging.getLogger(__name__)

class AbyssExtractor:
    @staticmethod
    async def extract(url: str) -> Optional[dict]:
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                "Referer": "https://larooza.website/"
            }
            async with AsyncSession(impersonate="chrome124", verify=False) as session:
                # Handle short.icu redirection
                resp = await session.get(url, headers=headers, allow_redirects=True)
                text = resp.text
                final_url = str(resp.url)
                
                # Check for "datas" variable in Abyss player
                match = re.search(r'const datas = "([^"]+)"', text)
                if match:
                    encoded_data = match.group(1)
                    try:
                        decoded_bytes = base64.b64decode(encoded_data)
                        # The decoded data can be messy, but it contains URLs
                        # Sometimes it's JSON with binary junk, sometimes just strings
                        # We look for .m3u8 or .mp4
                        urls = re.findall(rb'https?://[^\s"\'\\]+\.(?:m3u8|mp4)[^\s"\'\\]*', decoded_bytes)
                        if urls:
                            stream_url = urls[0].decode('utf-8', errors='ignore')
                            return {
                                "url": stream_url,
                                "type": "hls" if ".m3u8" in stream_url.lower() else "mp4",
                                "headers": {"Referer": final_url}
                            }
                    except:
                        pass
                
                # Fallback: search directly in text
                m3u8_match = re.search(r'["\'](https?://[^"\']+\.m3u8[^"\']*)["\']', text)
                if m3u8_match:
                    return {"url": m3u8_match.group(1), "type": "hls", "headers": {"Referer": final_url}}

        except Exception as e:
            logger.error(f"Abyss extraction error: {e}")
        return None
