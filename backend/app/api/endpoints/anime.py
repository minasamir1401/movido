import base64
from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any
from scraper.anime4up import anime4up_scraper
from scraper.animerco import animerco_scraper
from ...core.cache import api_cache
import logging

router = APIRouter(prefix="/anime", tags=["anime"])
logger = logging.getLogger("api.anime")

@router.get("/home")
async def get_anime_home():
    cache_key = "anime_home"
    cached = api_cache.get(cache_key)
    if cached:
        return cached
    
    try:
        data = await anime4up_scraper.fetch_home()
        api_cache.set(cache_key, data, ttl_seconds=3600)
        return data
    except Exception as e:
        logger.error(f"Error fetching anime home: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch anime home")

@router.get("/list")
async def get_anime_list(page: int = 1):
    cache_key = f"anime_list_{page}"
    cached = api_cache.get(cache_key)
    if cached:
        return cached
    
    try:
        items = await anime4up_scraper.fetch_anime_list(page=page)
        api_cache.set(cache_key, items)
        return items
    except Exception as e:
        logger.error(f"Error fetching anime list: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch anime list")

@router.get("/search")
async def search_anime(q: str):
    cache_key = f"anime_search_{q}"
    cached = api_cache.get(cache_key)
    if cached:
        return cached
    
    try:
        items = await anime4up_scraper.search(q)
        api_cache.set(cache_key, items, ttl_seconds=3600)
        return items
    except Exception as e:
        logger.error(f"Error searching anime: {e}")
        raise HTTPException(status_code=500, detail="Search operation failed")

@router.get("/details/{safe_id}")
async def get_anime_details(safe_id: str):
    # cache_key = f"anime_details_{safe_id}"
    # cached = api_cache.get(cache_key)
    # if cached:
    #     return cached
    
    try:
        # Determine which scraper to use based on the safe_id
        try:
            decoded_url = base64.urlsafe_b64decode(safe_id).decode()
            
            # Check if the decoded URL contains unsafe domains
            unsafe_domains = ['larooza.homes', 'gaza.20', 'bit.ly', 'tinyurl.com', 'adf.ly', 'bc.vc', 'adfoc.us', 'shorte.st', 'ouo.io', 'clicksfly.com']
            for domain in unsafe_domains:
                if domain in decoded_url.lower():
                    raise HTTPException(status_code=400, detail="Invalid or blocked content URL")
            
            if "animerco.org" in decoded_url:
                details = await animerco_scraper.fetch_details(safe_id)
            else:
                details = await anime4up_scraper.fetch_details(safe_id)
        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except:
            # Default to anime4up_scraper if decoding fails
            details = await anime4up_scraper.fetch_details(safe_id)
        
        if not details:
            raise HTTPException(status_code=404, detail="Anime not found")
        # api_cache.set(cache_key, details, ttl_seconds=86400)
        return details
    except Exception as e:
        logger.error(f"Error fetching anime details: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch details")

@router.get("/episode/{safe_id}")
async def get_anime_episode(safe_id: str):
    # Temporarily disabled cache to force fresh data
    # cache_key = f"anime_episode_{safe_id}"
    # cached = api_cache.get(cache_key)
    # if cached:
    #     return cached
    
    try:
        # Determine which scraper to use based on the safe_id
        try:
            decoded_url = base64.urlsafe_b64decode(safe_id).decode()
            
            # Check if the decoded URL contains unsafe domains
            unsafe_domains = ['larooza.homes', 'gaza.20', 'bit.ly', 'tinyurl.com', 'adf.ly', 'bc.vc', 'adfoc.us', 'shorte.st', 'ouo.io', 'clicksfly.com']
            for domain in unsafe_domains:
                if domain in decoded_url.lower():
                    raise HTTPException(status_code=400, detail="Invalid or blocked content URL")
            
            if "animerco.org" in decoded_url:
                episode = await animerco_scraper.fetch_episode(safe_id)
            else:
                episode = await anime4up_scraper.fetch_episode(safe_id)
        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except:
            # Default to anime4up_scraper if decoding fails
            episode = await anime4up_scraper.fetch_episode(safe_id)
        
        if not episode:
            raise HTTPException(status_code=404, detail="Episode not found")
        # api_cache.set(cache_key, episode, ttl_seconds=86400)
        return episode
    except Exception as e:
        logger.error(f"Error fetching episode: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch episode")
