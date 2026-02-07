
import re
import json
import logging
from typing import Optional, Dict
from curl_cffi.requests import AsyncSession

logger = logging.getLogger(__name__)

class VKExtractor:
    @staticmethod
    async def extract(url: str) -> Optional[Dict]:
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://vk.com/"
            }
            
            async with AsyncSession(impersonate="chrome124", verify=False, timeout=30) as session:
                resp = await session.get(url, headers=headers, allow_redirects=True)
                if resp.status_code != 200: return None
                
                text = resp.text
                
                # البحث عن كائن الفيديو في JavaScript
                video_config = re.search(r'videoConfig\s*:\s*({.+?}),\s*playerConfig', text)
                if not video_config:
                    video_config = re.search(r'var\s+playerParams\s*=\s*({.+?});', text)
                
                if video_config:
                    try:
                        data = json.loads(video_config.group(1).replace('\\/', '/'))
                        # التحقق من وجود HLS
                        if 'hls' in data:
                            return {"url": data['hls'], "type": "hls", "headers": {"Referer": "https://vk.com/"}}
                        
                        # التحقق من الجودات العالية
                        for quality in ['url1080', 'url720', 'url480', 'url360']:
                            if quality in data:
                                return {"url": data[quality], "type": "mp4", "headers": {"Referer": "https://vk.com/"}}
                    except: pass

                # البحث عن أنماط m3u8 مباشرة (حل أولي)
                hls_match = re.search(r'["\'](https?://[^"\'\s]+\.m3u8[^"\'\s]*)["\']', text)
                if hls_match:
                    return {"url": hls_match.group(1).replace('\\/', '/'), "type": "hls", "headers": {"Referer": "https://vk.com/"}}

                # البحث عن النسخة المحمولة (أحياناً تكون أسهل)
                if 'video_ext.php' in url:
                    mobile_url = url.replace('vk.com/video_ext.php', 'm.vk.com/video')
                    m_resp = await session.get(mobile_url, headers=headers)
                    m_match = re.search(r'source\s*src=["\']([^"\']+)["\']', m_resp.text)
                    if m_match:
                        return {"url": m_match.group(1), "type": "mp4", "headers": {"Referer": "https://vk.com/"}}

                logger.warning("❌ VK: Extraction failed")
                return None
        except Exception as e:
            logger.error(f"VK Error: {e}")
            return None
