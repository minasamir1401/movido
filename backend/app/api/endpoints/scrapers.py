from fastapi import APIRouter, HTTPException, Header, Body
from typing import Dict, Any
from ...core.scraper_manager import scraper_manager
from ...core.config import settings
from ...core.cache import api_cache
import logging

router = APIRouter(prefix="/scrapers", tags=["scrapers"])
logger = logging.getLogger("api.scrapers")

@router.get("/status")
async def get_scrapers_status(authorization: str = Header(None)):
    """Get status of all scrapers (Admin only)"""
    if authorization != "admin_master_token_2025":
        raise HTTPException(status_code=401, detail="غير مصرح لك")
    
    return {
        "scrapers": scraper_manager.get_all_status(),
        "stats": scraper_manager.get_stats()
    }

@router.post("/check-health")
async def check_scrapers_health(authorization: str = Header(None)):
    """Manually trigger health check for all scrapers"""
    if authorization != "admin_master_token_2025":
        raise HTTPException(status_code=401, detail="غير مصرح لك")
    
    await scraper_manager.check_all_scrapers()
    
    return {
        "status": "success",
        "message": "تم فحص جميع السكريبرز",
        "scrapers": scraper_manager.get_all_status()
    }

@router.post("/toggle")
async def toggle_scraper(
    payload: Dict[str, Any] = Body(...),
    authorization: str = Header(None)
):
    """Enable or disable a scraper"""
    if authorization != "admin_master_token_2025":
        raise HTTPException(status_code=401, detail="غير مصرح لك")
    
    scraper_name = payload.get("scraper_name")
    enabled = payload.get("enabled")
    
    if not scraper_name or enabled is None:
        raise HTTPException(status_code=400, detail="Missing parameters")
    
    scraper_manager.set_scraper_enabled(scraper_name, enabled)
    api_cache.clear()
    
    return {
        "status": "success",
        "scraper": scraper_name,
        "enabled": enabled
    }

@router.post("/set-priority")
async def set_scraper_priority(
    payload: Dict[str, Any] = Body(...),
    authorization: str = Header(None)
):
    """Set scraper priority (1 = highest)"""
    if authorization != "admin_master_token_2025":
        raise HTTPException(status_code=401, detail="غير مصرح لك")
    
    scraper_name = payload.get("scraper_name")
    priority = payload.get("priority")
    
    if not scraper_name or priority is None:
        raise HTTPException(status_code=400, detail="Missing parameters")
    
    scraper_manager.set_scraper_priority(scraper_name, int(priority))
    api_cache.clear()
    
    return {
        "status": "success",
        "scraper": scraper_name,
        "priority": priority
    }

@router.post("/clear-all-cache")
async def clear_all_cache(authorization: str = Header(None)):
    """Clear all system caches (Admin only)"""
    if authorization != "admin_master_token_2025":
        raise HTTPException(status_code=401, detail="غير مصرح لك")
    
    from ...core.cache import clear_all_system_caches
    success = clear_all_system_caches()
    
    # Also clear individual scraper in-memory caches
    from scraper.engine import scraper as larooza_scraper
    from scraper.mycima import scraper as mycima_scraper
    
    larooza_scraper.clear_cache()
    if hasattr(mycima_scraper, 'clear_cache'):
        mycima_scraper.clear_cache()

    return {
        "status": "success" if success else "partial_success",
        "message": "تم مسح جميع الملفات المؤقتة بنجاح"
    }

@router.get("/available")
async def get_available_scrapers(content_type: str = "arabic"):
    """
    Get list of available scrapers for a content type
    Public endpoint - used by frontend to determine which scraper to use
    """
    available = scraper_manager.get_available_scrapers(content_type)
    primary = scraper_manager.get_primary_scraper(content_type)
    
    return {
        "content_type": content_type,
        "available_scrapers": available,
        "primary_scraper": primary,
        "total_available": len(available)
    }
