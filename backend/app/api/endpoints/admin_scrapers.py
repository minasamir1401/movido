
from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any
from pydantic import BaseModel
from ...core.scraper_settings import scraper_settings
from ...core.cache import api_cache
from ...core.admin_auth import get_current_admin
import logging

router = APIRouter(prefix="/admin/scrapers", tags=["admin"])
logger = logging.getLogger("api.admin.scrapers")

class ScraperSettingsUpdate(BaseModel):
    larooza_enabled: bool = None
    arabseed_enabled: bool = None
    anime4up_enabled: bool = None
    fallback_mode: bool = None
    merge_results: bool = None
    primary_source: str = None

@router.get("/settings")
async def get_scraper_settings(current_admin: str = Depends(get_current_admin)):
    """Get current scraper settings"""
    return {
        "success": True,
        "settings": scraper_settings.get_all_settings(),
        "enabled_sources": scraper_settings.get_enabled_sources()
    }

@router.post("/settings")
async def update_scraper_settings(updates: ScraperSettingsUpdate, current_admin: str = Depends(get_current_admin)):
    """
    Update scraper settings.
    Automatically clears cache when switching sources.
    """
    try:
        # Convert to dict and remove None values
        updates_dict = {k: v for k, v in updates.dict().items() if v is not None}
        
        if not updates_dict:
            raise HTTPException(status_code=400, detail="No valid updates provided")
        
        # Validate primary_source if provided
        if "primary_source" in updates_dict:
            valid_sources = ["larooza", "arabseed"]
            if updates_dict["primary_source"] not in valid_sources:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Invalid primary_source. Must be one of: {valid_sources}"
                )
        
        # Update settings
        old_settings = scraper_settings.get_all_settings()
        scraper_settings.update_settings(updates_dict)
        
        # Clear cache if source configuration changed
        cache_cleared = False
        if any(key.endswith("_enabled") for key in updates_dict.keys()) or "primary_source" in updates_dict:
            # 1. Clear API and Image Caches
            from ...core.cache import clear_all_system_caches
            clear_all_system_caches()
            
            # 2. Clear In-memory Scraper Caches
            from scraper.engine import scraper as larooza_scraper
            from scraper.mycima import scraper as arabseed_scraper
            
            larooza_scraper.clear_cache()
            arabseed_scraper.clear_cache()
            
            cache_cleared = True
            logger.info("🧹 All system and scraper caches cleared due to scraper configuration change")
        
        return {
            "success": True,
            "message": "Scraper settings updated successfully",
            "cache_cleared": cache_cleared,
            "old_settings": old_settings,
            "new_settings": scraper_settings.get_all_settings()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating scraper settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/clear-cache")
async def clear_scraper_cache(current_admin: str = Depends(get_current_admin)):
    """Manually clear all system and scraper caches"""
    try:
        # 1. Clear API and Image Caches
        from ...core.cache import clear_all_system_caches
        clear_all_system_caches()
        
        # 2. Clear Scraper Caches
        from scraper.engine import scraper as larooza_scraper
        from scraper.mycima import scraper as arabseed_scraper
        
        larooza_scraper.clear_cache()
        arabseed_scraper.clear_cache()
        
        return {
            "success": True,
            "message": "All API, Image, and Scraper caches cleared successfully"
        }
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def check_scrapers_health(current_admin: str = Depends(get_current_admin)):
    """
    Check the health status of all enabled scrapers.
    Tests if they can fetch data successfully.
    """
    from scraper.engine import scraper as larooza_scraper
    from scraper.mycima import scraper as arabseed_scraper
    import asyncio
    
    health_status = {
        "larooza": {"enabled": False, "working": False, "error": None},
        "arabseed": {"enabled": False, "working": False, "error": None}
    }
    
    # Test Larooza
    if scraper_settings.is_enabled("larooza"):
        health_status["larooza"]["enabled"] = True
        try:
            items = await asyncio.wait_for(larooza_scraper.fetch_home(page=1), timeout=10.0)
            if items and len(items) > 0:
                health_status["larooza"]["working"] = True
                health_status["larooza"]["items_count"] = len(items)
            else:
                health_status["larooza"]["error"] = "No items returned"
        except asyncio.TimeoutError:
            health_status["larooza"]["error"] = "Timeout (>10s)"
        except Exception as e:
            health_status["larooza"]["error"] = str(e)
    
    # Test ArabSeed
    if scraper_settings.is_enabled("arabseed"):
        health_status["arabseed"]["enabled"] = True
        try:
            items = await asyncio.wait_for(arabseed_scraper.fetch_home(page=1), timeout=10.0)
            if items and len(items) > 0:
                health_status["arabseed"]["working"] = True
                health_status["arabseed"]["items_count"] = len(items)
            else:
                health_status["arabseed"]["error"] = "No items returned"
        except asyncio.TimeoutError:
            health_status["arabseed"]["error"] = "Timeout (>10s)"
        except Exception as e:
            health_status["arabseed"]["error"] = str(e)
    
    return {
        "success": True,
        "health": health_status,
        "timestamp": scraper_settings.get_all_settings().get("last_modified")
    }
