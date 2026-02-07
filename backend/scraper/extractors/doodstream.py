import re
import time
import random
import string
import logging
from curl_cffi.requests import AsyncSession

logger = logging.getLogger(__name__)

class DoodstreamExtractor:
    @classmethod
    async def extract(cls, url: str) -> str | None:
        """
        Extracts direct video URL from Doodstream/Dood/Dooood.
        """
        try:
            # Normalize URL to use 'd000d.com' or similar valid domain if needed, 
            # but usually we just follow the given URL.
            # Doodstream domains change often: dood.to, dood.so, dood.la, d000d.com, ds2play.com
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                "Referer": url,
            }

            async with AsyncSession(impersonate="chrome124", verify=False) as session:
                # 1. Fetch the Embed Page
                logger.info(f"Fetching Doodstream embed: {url}")
                resp = await session.get(url, headers=headers)
                if resp.status_code != 200:
                    return None
                
                content = resp.text
                
                # 2. Extract Key Info
                # Look for '/pass_md5/...'
                md5_match = re.search(r'["\'](/pass_md5/[^"\']+)["\']', content)
                if not md5_match:
                    md5_match = re.search(r'(/pass_md5/[^\s"\']+)', content)
                
                if not md5_match:
                    logger.warning("Doodstream: No pass_md5 found")
                    return None
                
                md5_endpoint = md5_match.group(1)
                from urllib.parse import urlparse
                domain = urlparse(url).netloc
                full_md5_url = f"https://{domain}{md5_endpoint}"

                # 3. Fetch Token
                # Referral must be the embed page
                headers["Referer"] = url
                token_resp = await session.get(full_md5_url, headers=headers)
                if token_resp.status_code != 200:
                    return None
                
                token_val = token_resp.text
                
                # 4. Construct Final URL
                # Logic: token_val + random_string + "?token=" + token_part + "&expiry=" ...
                # Actually Doodstream just returns the URL prefix in pass_md5, 
                # and we append 10 random chars.
                
                random_string = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
                final_url = f"{token_val}{random_string}?token={md5_endpoint.split('/')[-1]}&expiry={int(time.time()*1000)}"
                
                logger.info(f"Extracted Doodstream: {final_url}")
                return final_url

        except Exception as e:
            logger.error(f"Doodstream extraction failed: {e}")
            
        return None
