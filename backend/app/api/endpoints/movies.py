import base64
from fastapi import APIRouter, HTTPException, Query
from typing import List
from datetime import datetime
import asyncio
from ...models.schemas import MovieBase, ContentDetails
from ...core.cache import api_cache
from scraper.engine import scraper
from scraper.mycima import scraper as mycima_scraper
from scraper.anime4up import anime4up_scraper
from ...core.scraper_settings import scraper_settings
import logging

router = APIRouter(prefix="/movies", tags=["movies"])
logger = logging.getLogger("api.movies")

@router.get("/latest", response_model=List[MovieBase])
async def get_latest(page: int = 1):
    cache_key = f"latest_{page}"
    cached = await api_cache.get(cache_key)
    if cached:
        return cached
    
    try:
        # Get enabled scrapers based on settings
        enabled_sources = scraper_settings.get_enabled_sources()
        logger.info(f"Fetching latest with enabled sources: {enabled_sources}")
        
        tasks = []
        source_map = {}
        
        # Build tasks for enabled scrapers
        if "larooza" in enabled_sources:
            tasks.append(scraper.fetch_home(page=page))
            source_map[len(tasks) - 1] = "larooza"
        
        if "arabseed" in enabled_sources:
            tasks.append(mycima_scraper.fetch_home(page=page))
            source_map[len(tasks) - 1] = "arabseed"
        
        # If no sources enabled, return error
        if not tasks:
            logger.error("No scrapers enabled!")
            raise HTTPException(status_code=503, detail="No content sources are currently enabled")
        
        # Fetch in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results with fallback
        all_items = []
        working_sources = []
        
        for idx, result in enumerate(results):
            source_name = source_map.get(idx, "unknown")
            if not isinstance(result, Exception) and result:
                all_items.extend(result)
                working_sources.append(source_name)
                logger.info(f"✅ {source_name}: {len(result)} items")
            else:
                error_msg = str(result) if isinstance(result, Exception) else "No items returned"
                logger.warning(f"❌ {source_name}: {error_msg}")
        
        # If all sources failed
        if not all_items:
            logger.error("All enabled scrapers failed to return content")
            raise HTTPException(status_code=503, detail="All content sources are currently unavailable")
        
        # Merge and deduplicate if enabled
        if scraper_settings.should_merge_results() and len(working_sources) > 1:
            seen = set()
            merged = []
            for item in all_items:
                t = item.get('title', '').strip().lower()
                if t and t not in seen:
                    merged.append(item)
                    seen.add(t)
            all_items = merged
        
        if all_items:
            await api_cache.set(cache_key, all_items, ttl_seconds=1800)
            return all_items
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_latest: {e}")
            
    raise HTTPException(status_code=500, detail="Failed to fetch latest content")

@router.get("/category/{cat_id}", response_model=List[MovieBase])
async def get_category(cat_id: str, page: int = 1):
    cache_key = f"cat_{cat_id}_{page}"
    cached = await api_cache.get(cache_key)
    if cached:
        return cached
        
    try:
        # Fetch from both in parallel
        results = await asyncio.gather(
            scraper.fetch_category(cat_id, page=page),
            mycima_scraper.fetch_category(cat_id, page=page),
            return_exceptions=True
        )
        
        larooza_items = results[0] if not isinstance(results[0], Exception) else []
        arabseed_items = results[1] if not isinstance(results[1], Exception) else []

        seen = set()
        merged = []
        
        # Prioritize Larooza as primary for categories
        for source in [larooza_items, arabseed_items]:
            for item in (source or []):
                t = item.get('title', '').strip().lower()
                if t and t not in seen:
                    merged.append(item)
                    seen.add(t)
                    
        if merged:
            await api_cache.set(cache_key, merged, ttl_seconds=3600)
            return merged
            
    except Exception as e:
        logger.error(f"Error fetching category {cat_id}: {e}")
            
    raise HTTPException(status_code=500, detail=f"Failed to fetch category {cat_id}")

@router.get("/search", response_model=List[MovieBase])
async def search(q: str):
    cache_key = f"global_search_{q}"
    cached = await api_cache.get(cache_key)
    if cached:
        return cached
        
    try:
        # Perform all searches in parallel
        results = await asyncio.gather(
            scraper.search(q),
            mycima_scraper.search(q),
            anime4up_scraper.search(q),
            return_exceptions=True
        )
        
        larooza_res = results[0] if not isinstance(results[0], Exception) else []
        arabseed_res = results[1] if not isinstance(results[1], Exception) else []
        anime_res = results[2] if not isinstance(results[2], Exception) else []
        
        if isinstance(results[0], Exception): logger.error(f"Larooza search error: {results[0]}")
        if isinstance(results[1], Exception): logger.error(f"ArabSeed search error: {results[1]}")
        if isinstance(results[2], Exception): logger.error(f"Anime search error: {results[2]}")

        # Merge and deduplicate
        seen = set()
        combined = []
        is_anime = any(k in q.lower() for k in ['انمي', 'أنمي', 'anime', 'episode', 'حلقة'])
        
        sources = [anime_res, larooza_res, arabseed_res] if is_anime else [larooza_res, arabseed_res, anime_res]
        for source in sources:
            if not source: continue
            for item in source:
                t = item.get('title', '').strip().lower()
                if t and t not in seen:
                    combined.append(item)
                    seen.add(t)
            
        final = combined[:60]
        if final:
            await api_cache.set(cache_key, final, ttl_seconds=3600)
        return final
    except Exception as e:
        logger.error(f"Search API Error: {e}", exc_info=True)
        return []

@router.get("/details/{safe_id}", response_model=ContentDetails)
async def get_details(safe_id: str, refresh: bool = False):
    cache_key = f"details_{safe_id}"
    if not refresh:
        cached = await api_cache.get(cache_key)
        if cached:
            return cached
        
    try:
        # 1. Decode URL and Identify Scraper
        import base64
        temp_id = safe_id
        padding = len(temp_id) % 4
        if padding: temp_id += "=" * (4 - padding)
        
        try:
            decoded_url = base64.urlsafe_b64decode(temp_id).decode()
        except:
            decoded_url = safe_id if safe_id.startswith('http') else ""

        if not decoded_url:
            raise HTTPException(status_code=400, detail="Invalid content ID")

        # 2. Security Check
        unsafe_domains = ['larooza.homes', 'gaza.20', 'bit.ly', 'tinyurl.com']
        if any(domain in decoded_url.lower() for domain in unsafe_domains):
            raise HTTPException(status_code=400, detail="Blocked content source")
        
       # 3. Route based on URL domain OR use primary source from settings
        details = None
        source_used = None
        
        # Check URL domain first
        if "larozavideo" in decoded_url or "laroza" in decoded_url:
            if scraper_settings.is_enabled("larooza"):
                logger.info(f"Routing to Larooza (URL-based): {decoded_url}")
                details = await scraper.fetch_details(safe_id)
                source_used = "larooza"
        elif any(x in decoded_url for x in ["asd.homes", "arabseed", "asd.pics", "asd.homes"]):
            if scraper_settings.is_enabled("arabseed"):
                logger.info(f"Routing to ArabSeed (URL-based): {decoded_url}")
                details = await mycima_scraper.fetch_details(safe_id)
                source_used = "arabseed"
        elif "animerco" in decoded_url or "anime4up" in decoded_url:
            if scraper_settings.is_enabled("anime4up"):
                details = await anime4up_scraper.fetch_details(safe_id)
                source_used = "anime4up"
        
        # If no match or disabled, use fallback strategy
        if not details and scraper_settings.is_fallback_enabled():
            primary = scraper_settings.get_primary_source()
            logger.info(f"Using fallback with primary source: {primary}")
            
            if primary == "larooza" and scraper_settings.is_enabled("larooza"):
                try:
                    details = await scraper.fetch_details(safe_id)
                    source_used = "larooza"
                except Exception as e:
                    logger.warning(f"Primary source (larooza) failed: {e}")
            
            if not details and scraper_settings.is_enabled("arabseed"):
                try:
                    details = await mycima_scraper.fetch_details(safe_id)
                    source_used = "arabseed"
                except Exception as e:
                    logger.warning(f"Fallback to arabseed failed: {e}")

        if not details or (not details.get('servers') and not details.get('episodes') and not details.get('download_links')):
            raise HTTPException(status_code=404, detail="Content details not found")
        
        # Add source information
        details["_source"] = source_used
        
        # 4. Final Processing (SEO & Cache)
        
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
            "url": f"https://movido.com/watch/{safe_id}",
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
                "name": "MOVIDO"
            },
            "potentialAction": {
                "@type": "WatchAction",
                "target": {
                    "@type": "EntryPoint",
                    "urlTemplate": f"https://movido.com/watch/{safe_id}",
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
        
        await api_cache.set(cache_key, details, ttl_seconds=86400)
        return details
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching details for {safe_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch details")
