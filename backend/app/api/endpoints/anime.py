import base64
from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any
from scraper.mycima import scraper as mycima_scraper
from scraper.anime4up import anime4up_scraper
from scraper.animerco import animerco_scraper
from ...core.cache import api_cache
import logging

router = APIRouter(prefix="/anime", tags=["anime"])
logger = logging.getLogger("api.anime")

@router.get("/home")
async def get_anime_home():
    cache_key = "anime_home_v2"
    cached = await api_cache.get(cache_key)
    if cached:
        return cached
    
    try:
        # Fetch data from ArabSeed 'cartoon-series' category
        items = await mycima_scraper.fetch_category("cartoon-series", page=1)
        
        # Structure it as sections for the frontend
        # We can split the items into mock sections or just return one "Latest" section
        data = {
            "Latest Updates": items,
            "Featured Series": items[:10] if items else [] # Just a duplicate for UI visual if needed
        }
        
        await api_cache.set(cache_key, data, ttl_seconds=3600)
        return data
    except Exception as e:
        logger.error(f"Error fetching anime home: {e}")
        # Fallback to empty
        return {}

@router.get("/list")
async def get_anime_list(page: int = 1):
    cache_key = f"anime_list_v2_{page}"
    cached = await api_cache.get(cache_key)
    if cached:
        return cached
    
    try:
        # Fetch pagination from ArabSeed
        items = await mycima_scraper.fetch_category("cartoon-series", page=page)
        await api_cache.set(cache_key, items, ttl_seconds=3600)
        return items
    except Exception as e:
        logger.error(f"Error fetching anime list: {e}")
        return []

@router.get("/search")
async def search_anime(q: str):
    cache_key = f"anime_search_v2_{q}"
    cached = await api_cache.get(cache_key)
    if cached:
        return cached
    
    try:
        # User wants anime search. 
        # Since we switched the main view to ArabSeed, we should probably search ArabSeed.
        # However, ArabSeed search returns everything. We might want to filter or just accept it.
        items = await mycima_scraper.search(q)
        
        # Optional: Filter for anime-ish results if possible, but hard to tell by title alone.
        # We can also search anime4up as aggregation if needed, but keeping it simple for now.
        
        await api_cache.set(cache_key, items, ttl_seconds=3600)
        return items
    except Exception as e:
        logger.error(f"Error searching anime: {e}")
        return []

@router.get("/details/{safe_id}")
async def get_anime_details(safe_id: str):
    try:
        # Decode to check domain
        try:
            decoded_url = base64.urlsafe_b64decode(safe_id + "==").decode()
        except:
            decoded_url = safe_id
            
        # Dispatch to correct scraper
        if any(x in decoded_url for x in ["asd.homes", "arabseed", "mycima", "wecima"]):
            return await mycima_scraper.fetch_details(safe_id)
        elif "animerco.org" in decoded_url:
            return await animerco_scraper.fetch_details(safe_id)
        else:
            # Default fallback (or if old IDs are cached)
            return await anime4up_scraper.fetch_details(safe_id)
            
    except Exception as e:
        logger.error(f"Error fetching anime details: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch details")

@router.get("/episode/{safe_id}")
async def get_anime_episode(safe_id: str):
    try:
        # Decode to check domain
        try:
            decoded_url = base64.urlsafe_b64decode(safe_id + "==").decode()
        except:
            decoded_url = safe_id
            
        if any(x in decoded_url for x in ["asd.homes", "arabseed", "mycima", "wecima"]):
            # MyCima handles episodes differently (usually just details of the episode page)
            # The fetch_details method in mycima can handle episode URLs too
            return await mycima_scraper.fetch_details(safe_id)
        elif "animerco.org" in decoded_url:
            return await animerco_scraper.fetch_episode(safe_id)
        else:
            return await anime4up_scraper.fetch_episode(safe_id)
            
    except Exception as e:
        logger.error(f"Error fetching episode: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch episode")
