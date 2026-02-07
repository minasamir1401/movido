
import re
import json
import logging
from typing import Optional
from html import unescape
from curl_cffi.requests import AsyncSession

logger = logging.getLogger(__name__)

class OkRuExtractor:
    @staticmethod
    async def extract(url: str) -> Optional[dict]:
        try:
            # تنظيف الرابط
            url = url.replace('/video/', '/videoembed/')
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://ok.ru/'
            }
            
            async with AsyncSession(impersonate="chrome124", verify=False, timeout=30) as client:
                response = await client.get(url, headers=headers, allow_redirects=True)
                if response.status_code != 200: return None

                html_content = response.text
                
                # البحث في data-options (الطريقة الرسمية كما في Mediaflow)
                div_match = re.search(r'data-options="([^"]+)"', html_content)
                if div_match:
                    try:
                        data = json.loads(unescape(div_match.group(1)))
                        metadata = data.get('flashvars', {}).get('metadata')
                        if isinstance(metadata, str): metadata = json.loads(metadata)
                        
                        # تجربة جودات HLS المتعددة
                        final_url = (
                            metadata.get("hlsMasterPlaylistUrl") or 
                            metadata.get("hlsManifestUrl") or 
                            metadata.get("ondemandHls")
                        )
                        
                        if final_url:
                            logger.info(f"✅ OK.ru HLS success: {final_url[:50]}")
                            return {"url": final_url, "type": "hls", "headers": {"Referer": "https://ok.ru/"}}
                        
                        # إذا لم يوجد HLS، نبحث عن MP4
                        videos = metadata.get('videos', [])
                        if videos:
                            best_video = max(videos, key=lambda x: int(x.get('name', '0')) if x.get('name', '').isdigit() else 0)
                            return {"url": best_video['url'], "type": "mp4", "headers": {"Referer": "https://ok.ru/"}}
                    except: pass

                # البحث العميق عن أي رابط Media
                deep_match = re.search(r'["\'](https?://[^"\'\s]+\.(?:m3u8|mp4)[^"\'\s]*)["\']', html_content)
                if deep_match:
                    return {"url": deep_match.group(1), "type": "hls" if ".m3u8" in deep_match.group(1) else "mp4", "headers": {"Referer": "https://ok.ru/"}}

        except Exception as e:
            logger.error(f"OkRu error: {e}")
        return None
