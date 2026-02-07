
import base64
import re
import logging
from typing import Optional
from urllib.parse import urlparse, parse_qs
from curl_cffi.requests import AsyncSession

logger = logging.getLogger(__name__)

class ArabSeedExtractor:
    @staticmethod
    def decode_base64(encoded_str: str) -> str:
        try:
            # Handle URL-safe base64
            cleaned = encoded_str.replace('-', '+').replace('_', '/')
            padding = len(cleaned) % 4
            if padding:
                cleaned += '=' * (4 - padding)
            return base64.b64decode(cleaned).decode('utf-8')
        except Exception as e:
            logger.error(f"Failed to decode ArabSeed base64: {e}")
            return ""

    @classmethod
    async def extract(cls, url: str) -> Optional[dict]:
        """
        Handles ArabSeed wrapper URLs (play.php?url=... or /play/?id=...)
        """
        try:
            parsed = urlparse(url)
            qs = parse_qs(parsed.query)
            
            encoded_url = None
            if 'url' in qs:
                encoded_url = qs['url'][0]
            elif 'id' in qs:
                encoded_url = qs['id'][0]
            elif 'vid' in qs:
                # Some versions might use vid
                encoded_url = qs['vid'][0]
            
            if encoded_url:
                real_url = cls.decode_base64(encoded_url)
                if real_url:
                    if real_url.startswith('//'):
                        real_url = 'https:' + real_url
                    
                    logger.info(f"ArabSeed decoded URL: {real_url}")
                    
                    # Now we need to extract from the real URL
                    # We can use the ExtractorEngine or call specialized extractors
                    from scraper.extractors.engine import ExtractorEngine
                    return await ExtractorEngine.extract(real_url)
            
            # If not a wrapper or decoding failed, try generic extraction on the page itself
            # because some ArabSeed pages might have the player directly.
            from scraper.extractors.okprime import OkPrimeExtractor
            return await OkPrimeExtractor.extract(url)

        except Exception as e:
            logger.error(f"ArabSeed extraction failed: {e}")
        
        return None
