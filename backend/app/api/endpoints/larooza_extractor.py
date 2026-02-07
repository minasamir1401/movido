"""
Larooza Extractor API Endpoint
استخراج سيرفرات Larooza وروابط المشاهدة المباشرة
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Optional
import logging
import asyncio

from scraper.engine import scraper as larooza_scraper
from scraper.extractors.engine import ExtractorEngine

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/larooza", tags=["larooza"])

@router.get("/servers")
async def get_video_servers(
    vid: str = Query(..., description="Video ID from Larooza (e.g., Yg22o3HXS)")
):
    """
    استخراج جميع سيرفرات المشاهدة من رابط Larooza
    ضمان السرعة عبر إرجاع السيرفرات فوراً
    """
    try:
        # بناء الرابط الكامل (تجربة عدة نطاقات لضمان النتيجة)
        base_domains = ["https://larooza.top", "https://q.larozavideo.net", "https://larooza.hair"]
        details = None
        video_url = ""
        
        for domain in base_domains:
            video_url = f"{domain}/video.php?vid={vid}"
            import base64
            safe_id = base64.urlsafe_b64encode(video_url.encode()).decode().strip('=')
            
            details = await larooza_scraper.fetch_details(safe_id)
            if details and details.get('servers'):
                break
        
        if not details:
            raise HTTPException(status_code=404, detail="Video or Servers not found")
        
        # تجهيز قائمة السيرفرات
        all_servers = []
        
        # تحسين: محاولة استخراج الروابط المباشرة بشكل متوازي وسريع
        async def process_server(server):
            embed_url = server.get('url')
            name = server.get('name', 'Unknown Server')
            
            info = {
                "name": name,
                "embed_url": embed_url,
                "direct_url": None,
                "status": "pending",
                "type": "embed" # افتراضياً هو embed
            }
            
            try:
                # محاولة سريعة جداً للاستخراج (timeout 5s فقط)
                result = await asyncio.wait_for(ExtractorEngine.extract(embed_url), timeout=5.0)
                if result and result.get('url'):
                    info.update({
                        "direct_url": result['url'],
                        "status": "success",
                        "type": result.get('type', 'hls'),
                        "headers": result.get('headers', {})
                    })
            except:
                info["status"] = "failed"
            
            return info

        # تشغيل الاستخراج لجميع السيرفرات معاً لضمان السرعة
        tasks = [process_server(s) for s in details.get('servers', [])]
        all_servers = await asyncio.gather(*tasks)
        
        working_servers = [s for s in all_servers if s['status'] == 'success']
        
        return {
            "success": True,
            "title": details.get('title', ''),
            "poster": details.get('poster', ''),
            "type": details.get('type', 'movie'),
            "servers": all_servers,
            "working_servers": working_servers if working_servers else all_servers,
            "working_count": len(working_servers),
            "total_count": len(all_servers),
            "episodes": details.get('episodes', []),
            "download_links": details.get('download_links', [])
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error extracting servers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/extract")
async def extract_direct_url(
    url: str = Query(..., description="Embed URL to extract direct video URL from")
):
    """
    استخراج الرابط المباشر من رابط embed
    
    Supports: Vidmoly, VOE, OK.ru, VK, Mxdrop, Abstream, Dsvplay, and more
    """
    try:
        logger.info(f"🔍 Extracting: {url}")
        
        result = await ExtractorEngine.extract(url)
        
        if not result or not result.get('url'):
            raise HTTPException(status_code=404, detail="Could not extract direct URL")
        
        return {
            "success": True,
            "embed_url": url,
            "direct_url": result['url'],
            "type": result.get('type', 'unknown'),
            "headers": result.get('headers', {})
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Extraction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/episode-servers")
async def get_episode_servers(
    series_vid: str = Query(..., description="Series video ID"),
    episode: int = Query(..., description="Episode number")
):
    """
    استخراج سيرفرات حلقة معينة من مسلسل
    """
    try:
        # استخراج تفاصيل المسلسل
        video_url = f"https://larooza.top/video.php?vid={series_vid}"
        import base64
        safe_id = base64.urlsafe_b64encode(video_url.encode()).decode().strip('=')
        
        details = await larooza_scraper.fetch_details(safe_id)
        
        if not details:
            raise HTTPException(status_code=404, detail="Series not found")
        
        # البحث عن الحلقة المطلوبة
        episodes = details.get('episodes', [])
        target_episode = None
        
        for ep in episodes:
            if ep.get('episode') == episode:
                target_episode = ep
                break
        
        if not target_episode:
            raise HTTPException(status_code=404, detail=f"Episode {episode} not found")
        
        # استخراج سيرفرات الحلقة
        episode_url = target_episode['url']
        episode_safe_id = base64.urlsafe_b64encode(episode_url.encode()).decode().strip('=')
        
        episode_details = await larooza_scraper.fetch_details(episode_safe_id)
        
        # استخراج الروابط المباشرة
        servers_with_direct_urls = []
        
        for server in episode_details.get('servers', []):
            embed_url = server.get('url')
            server_name = server.get('name', 'Unknown')
            
            server_info = {
                "name": server_name,
                "embed_url": embed_url,
                "status": "pending",
                "direct_url": None
            }
            
            try:
                result = await ExtractorEngine.extract(embed_url)
                if result and result.get('url'):
                    server_info.update({
                        "status": "success",
                        "direct_url": result['url'],
                        "type": result.get('type'),
                        "headers": result.get('headers', {})
                    })
                else:
                    server_info["status"] = "failed"
            except Exception as e:
                server_info["status"] = "error"
                server_info["error"] = str(e)
            
            servers_with_direct_urls.append(server_info)
        
        working_servers = [s for s in servers_with_direct_urls if s['status'] == 'success']
        
        return {
            "success": True,
            "series_title": details.get('title', ''),
            "episode": episode,
            "episode_title": target_episode.get('title', ''),
            "episode_url": episode_url,
            "servers": servers_with_direct_urls,
            "working_servers": working_servers,
            "working_count": len(working_servers),
            "total_count": len(servers_with_direct_urls)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
