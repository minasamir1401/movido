import base64
from fastapi import APIRouter, HTTPException, Query
from typing import List
from datetime import datetime
import asyncio
from ...models.schemas import MovieBase, ContentDetails
from ...core.cache import api_cache
from scraper.engine import scraper
from scraper.anime4up import anime4up_scraper
import logging

router = APIRouter(prefix="/movies", tags=["movies"])
logger = logging.getLogger("api.movies")

@router.get("/latest", response_model=List[MovieBase])
async def get_latest(page: int = 1):
    cache_key = f"latest_{page}"
    cached = api_cache.get(cache_key)
    if cached:
        return cached
    
    try:
        items = await scraper.fetch_home(page=page)
        if items:
            api_cache.set(cache_key, items)
        return items
    except Exception as e:
        logger.error(f"Error fetching latest movies: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch latest content")

@router.get("/category/{cat_id}", response_model=List[MovieBase])
async def get_category(cat_id: str, page: int = 1):
    cache_key = f"cat_{cat_id}_{page}"
    cached = api_cache.get(cache_key)
    if cached:
        return cached
        
    try:
        items = await scraper.fetch_category(cat_id, page=page)
        if items:
            api_cache.set(cache_key, items)
        return items
    except Exception as e:
        logger.error(f"Error fetching category {cat_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch category {cat_id}")

@router.get("/search", response_model=List[MovieBase])
async def search(q: str):
    cache_key = f"global_search_{q}"
    cached = api_cache.get(cache_key)
    if cached:
        return cached
        
    try:
        # Perform both searches in parallel
        results = await asyncio.gather(
            scraper.search(q),
            anime4up_scraper.search(q),
            return_exceptions=True
        )
        
        movie_results = results[0] if not isinstance(results[0], Exception) else []
        anime_results = results[1] if not isinstance(results[1], Exception) else []
        
        if isinstance(results[0], Exception): logger.error(f"Movie search error: {results[0]}")
        if isinstance(results[1], Exception): logger.error(f"Anime search error: {results[1]}")

        # Merge results
        is_anime_query = any(k in q.lower() for k in ['انمي', 'أنمي', 'anime', 'episode', 'حلقة', 'jihen', 'darwin', 'clover', 'jihen'])
        
        if is_anime_query:
            combined = (anime_results or []) + (movie_results or [])
        else:
            combined = (movie_results or []) + (anime_results or [])
            
        final = combined[:50]
        
        if final:
            api_cache.set(cache_key, final, ttl_seconds=3600)
        return final
    except Exception as e:
        logger.error(f"Search API Error: {e}", exc_info=True)
        return []

@router.get("/details/{safe_id}", response_model=ContentDetails)
async def get_details(safe_id: str):
    cache_key = f"details_{safe_id}"
    cached = api_cache.get(cache_key)
    if cached:
        return cached
        
    try:
        # Check if the safe_id contains unsafe domains when decoded
        try:
            import base64
            decoded_url = base64.urlsafe_b64decode(safe_id).decode()
            
            # Check if the decoded URL contains unsafe domains
            unsafe_domains = ['larooza.homes', 'gaza.20', 'bit.ly', 'tinyurl.com', 'adf.ly', 'bc.vc', 'adfoc.us', 'shorte.st', 'ouo.io', 'clicksfly.com']
            for domain in unsafe_domains:
                if domain in decoded_url.lower():
                    raise HTTPException(status_code=400, detail="Invalid or blocked content URL")
        except (UnicodeDecodeError, ValueError):
            # If decoding fails, continue with normal processing
            pass
        
        details = await scraper.fetch_details(safe_id)
        if not details:
            raise HTTPException(status_code=404, detail="Content not found")
        
        # Enhanced SEO Schema for AI
        is_movie = "-movies" in safe_id or details.get("type") == "movie"
        schema_type = "Movie" if is_movie else "TVSeries"
        
        details["schema"] = {
            "@context": "https://schema.org",
            "@type": schema_type,
            "name": details.get("title"),
            "alternateName": details.get("title_en"),
            "image": details.get("poster"),
            "datePublished": details.get("year"),
            "description": details.get("description"),
            "url": f"https://lmina.com/watch/{safe_id}",
            "genre": details.get("genre", []),
            "inLanguage": "Arabic",
            "aggregateRating": {
                "@type": "AggregateRating",
                "ratingValue": details.get("rating") if details.get("rating") != "N/A" else "8.5",
                "bestRating": "10",
                "worstRating": "1",
                "ratingCount": "1500"
            },
            "author": {
                "@type": "Organization",
                "name": "LMINA"
            },
            "potentialAction": {
                "@type": "WatchAction",
                "target": {
                    "@type": "EntryPoint",
                    "urlTemplate": f"https://lmina.com/watch/{safe_id}",
                    "actionPlatform": [
                        "http://schema.org/DesktopWebPlatform",
                        "http://schema.org/MobileWebPlatform"
                    ]
                }
            }
        }
        
        if not is_movie and details.get("episodes"):
            details["schema"]["numberOfEpisodes"] = len(details.get("episodes", []))
            if details.get("seasons"):
                details["schema"]["numberOfSeasons"] = len(details.get("seasons", []))
        
        api_cache.set(cache_key, details, ttl_seconds=86400)
        return details
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching details for {safe_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch details")
