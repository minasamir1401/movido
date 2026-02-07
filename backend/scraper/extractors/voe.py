
import re
import base64
import json
import logging
import asyncio
from typing import Optional, Dict, Any
from urllib.parse import urljoin
from curl_cffi.requests import AsyncSession

logger = logging.getLogger(__name__)

class VoeExtractor:
    @staticmethod
    def voe_decode(ct: str, luts: str = None) -> Dict[str, Any]:
        """Professional VOE decoding logic with LUTs capability"""
        import json
        
        # المرحلة 1: معالجة الـ Rotation
        txt = ""
        for i in ct:
            x = ord(i)
            if 64 < x < 91: x = (x - 52) % 26 + 65
            elif 96 < x < 123: x = (x - 84) % 26 + 97
            txt += chr(x)
            
        # المرحلة 2: تطبيق الـ LUTs إذا وجدت (فك التشفير المتقدم)
        if luts:
            try:
                lut_list = ["".join([("\\" + x) if x in ".*+?^${}()|[]\\" else x for x in i]) for i in luts[2:-2].split("','")]
                for pattern in lut_list:
                    txt = re.sub(pattern, "", txt)
            except: pass

        try:
            # المرحلة 3: فك التشفير النهائي (Base64 -> Shift -3 -> Reverse -> Base64)
            decoded_stage1 = base64.b64decode(txt).decode("utf-8")
            shifted = "".join([chr(ord(i) - 3) for i in decoded_stage1])
            final_json = base64.b64decode(shifted[::-1]).decode("utf-8")
            return json.loads(final_json)
        except:
            return {}

    @classmethod
    async def extract(cls, url: str) -> Optional[dict]:
        alt_domains = ['voe.sx', 'voe.un', 'voe.to', 'voe.cc', 'voe.am']
        id_match = re.search(r'/(?:e|d)/([a-zA-Z0-9]+)', url)
        if not id_match: return None
        video_id = id_match.group(1)

        for domain in alt_domains:
            test_url = f"https://{domain}/e/{video_id}"
            try:
                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
                async with AsyncSession(impersonate="chrome124", verify=False, timeout=15) as session:
                    resp = await session.get(test_url, headers=headers, allow_redirects=True)
                    if resp.status_code != 200: continue
                    
                    text = resp.text
                    
                    # التقاط الـ Payload والـ Script معاً (كما في Mediaflow)
                    pattern = r'json">\["([^"]+)"]</script>\s*<script\s*src="([^"]+)"'
                    match = re.search(pattern, text, re.DOTALL)
                    
                    payload_data = None
                    luts_data = None
                    
                    if match:
                        payload_data = match.group(1)
                        script_url = urljoin(str(resp.url), match.group(2))
                        try:
                            script_resp = await session.get(script_url, headers=headers)
                            luts_match = re.search(r"(\[(?:'\W{2}'[,\]]){1,9})", script_resp.text)
                            if luts_match: luts_data = luts_match.group(1)
                        except: pass
                    else:
                        # محاولة الحصول على الـ Payload فقط إذا لم نجد الـ script
                        payload_match = re.search(r'json">\["([^"]+)"]</script>', text)
                        if payload_match: payload_data = payload_match.group(1)

                    if payload_data:
                        result = cls.voe_decode(payload_data, luts_data)
                        if result.get("source"):
                            logger.info(f"✅ VOE Success with professional decode: {domain}")
                            return {
                                "url": result["source"],
                                "type": "hls" if ".m3u8" in result["source"] else "mp4",
                                "headers": {"Referer": str(resp.url)}
                            }

                    # استراتيجية البحث الشامل (المنقذ الأخير)
                    final_res = re.search(r'["\'](https?://[^"\'\s]+\.(?:m3u8|mp4)[^"\'\s]*)["\']', text)
                    if final_res:
                        return {"url": final_res.group(1), "type": "hls" if ".m3u8" in final_res.group(1) else "mp4", "headers": {"Referer": str(resp.url)}}
            except: continue
        return None
