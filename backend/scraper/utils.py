import re
import base64
import logging
from typing import Optional
from urllib.parse import urljoin

logger = logging.getLogger("scraper_utils")

class MediaExtractor:
    @staticmethod
    def decode_packed(packed_str: str) -> Optional[str]:
        """Decodes Dean Edwards packed JavaScript."""
        try:
            pattern = r"\}\s*\('(.*?)',\s*(\d+),\s*(\d+),\s*'(.*?)'\.split"
            match = re.search(pattern, packed_str)
            if not match: return None
            
            p, a, c, k = match.groups()
            a, c = int(a), int(c)
            k = k.split('|')
            
            def baseN(num, b):
                return ((num == 0) and "0") or \
                       (baseN(num // b, b).lstrip("0") + "0123456789abcdefghijklmnopqrstuvwxyz"[num % b])

            result = p
            for i in range(c - 1, -1, -1):
                key = baseN(i, a)
                if i < len(k) and k[i]:
                    result = re.sub(r'\b' + re.escape(key) + r'\b', k[i], result)
            return result
        except Exception as e:
            logger.debug(f"Unpacking failed: {e}")
            return None

    @classmethod
    async def extract_direct_url(cls, html: str, current_url: str = "") -> Optional[str]:
        """
        Ultra-aggressive extraction of direct video URLs from HTML.
        Handles hex, base64, packed JS, and raw regex.
        """
        if not html: return None
        
        # 1. Normalization
        content = html.replace('\\/', '/')
        
        # 2. Decode Hex
        hex_matches = re.findall(r'(?:\\x[0-9a-fA-F]{2}){10,}', content)
        for hm in hex_matches:
            try:
                decoded = bytes.fromhex(hm.replace('\\x', '')).decode('utf-8', errors='ignore')
                content += " " + decoded
            except: continue

        # 3. Decode Base64
        b64_matches = re.findall(r'["\']([A-Za-z0-9+/]{40,}=*)["\']', content)
        for bm in b64_matches:
            try:
                decoded = base64.b64decode(bm).decode('utf-8', errors='ignore')
                if 'http' in decoded: content += " " + decoded
            except: continue

        # 4. Unpack JS
        if 'eval(function(p,a,c,k,e,' in content:
            # Find all packed scripts
            packed_scripts = re.findall(r'eval\(function\(p,a,c,k,e,.*?.split\(\'\|\'\)\)\)', content)
            for ps in packed_scripts:
                unpacked = cls.decode_packed(ps)
                if unpacked: content += " " + unpacked

        # 5. Extraction Regex
        media_patterns = [
            r'["\'](https?://[^"\']+\.(?:mp4|m3u8|m4s|ts|webm|mov|mkv)[^"\']*)["\']',
            r'[:=]\s*(https?://[^\s"\'<>;]+(?:\.mp4|\.m3u8)[^\s"\'<>;]*)'
        ]
        
        for pattern in media_patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                found = match.group(1).replace('\\', '')
                if 'http' in found and not any(x in found for x in ['.js', '.css', 'ads', 'analytics', 'facebook']):
                    # Critical Validation: Must be a media file or known provider
                    if any(x in found for x in ['.mp4', '.m3u8', '.webm', 'googlevideo', 'okcdn', 'mxcontent', 'vood', 'filelions']):
                        return found

        # 6. Fallback: JSON keys
        for key in ['"file"', '"src"', '"url"', '"embed_url"']:
            match = re.search(f'{key}\s*:\s*"([^"]+)"', content)
            if match:
                val = match.group(1).replace('\\', '')
                if val.startswith('http') and ('.mp4' in val or '.m3u8' in val):
                    return val

        return None
