import asyncio
import logging
import time
from ..core.cache import api_cache
from ..core.database import db_manager
from scraper.engine import scraper
from scraper.courses import courses_scraper
from .social_poster import social_poster

logger = logging.getLogger("worker")

async def auto_broadcaster():
    """Checks for new content and posts to social media."""
    logger.info("Social Broadcaster started")
    while True:
        try:
            items = await scraper.fetch_home(page=1)
            for item in items[:5]:
                cache_key = f"broadcasted_{item['id']}"
                if not await api_cache.get(cache_key):
                    await social_poster.post_new_content(
                        item['title'], 
                        f"https://movido.com/details/{item['id']}", 
                        item['poster']
                    )
                    await api_cache.set(cache_key, True, ttl_seconds=86400 * 7)
        except Exception as e:
            logger.error(f"Broadcaster error: {e}")
        await asyncio.sleep(3600)

from scraper.mycima import scraper as mycima_scraper

async def warm_up_services():
    """Warms up scrapers and caches by pre-fetching popular content from all sources."""
    logger.info("🔥 Starting deep warm-up of all services (Larooza & ArabSeed)...")
    try:
        # 1. Warm up Home Pages in parallel
        home_tasks = [
            scraper.fetch_home(page=1),
            mycima_scraper.fetch_home(page=1)
        ]
        home_results = await asyncio.gather(*home_tasks, return_exceptions=True)
        
        larooza_items = home_results[0] if not isinstance(home_results[0], Exception) else []
        arabseed_items = home_results[1] if not isinstance(home_results[1], Exception) else []
        
        logger.info(f"✅ Home Pages fetched: Larooza({len(larooza_items)}), ArabSeed({len(arabseed_items)})")

        # 2. Pre-fetch details for latest items (Deep Heating)
        detail_tasks = []
        # Top 8 from Larooza
        if larooza_items:
            for item in larooza_items[:8]:
                detail_tasks.append(scraper.fetch_details(item['id']))
        
        # Top 8 from ArabSeed
        if arabseed_items:
            for item in arabseed_items[:8]:
                detail_tasks.append(mycima_scraper.fetch_details(item['id']))
        
        if detail_tasks:
            results = await asyncio.gather(*detail_tasks, return_exceptions=True)
            success_count = sum(1 for r in results if isinstance(r, dict) and r.get('id'))
            logger.info(f"✅ Deep heated {success_count} latest items")

        # 3. Warm up priority categories
        categories = ["arabic-movies", "english-movies", "turkish-series", "ramadan-2025"]
        cat_tasks = []
        for cat in categories:
            cat_tasks.append(scraper.fetch_category(cat, page=1))
            cat_tasks.append(mycima_scraper.fetch_category(cat, page=1))
        
        await asyncio.gather(*cat_tasks, return_exceptions=True)
        logger.info(f"✅ Priority categories warmed for both sources")
            
        # 4. Warm up priority courses
        await courses_scraper.fetch_latest_courses(page=1)
        await courses_scraper.fetch_category_courses("12", page=1) # Programming
        
        logger.info("🚀 Deep warm-up complete. System is ready and lightning fast!")
    except Exception as e:
        logger.warning(f"⚠️ Warm-up partially failed: {e}")

async def background_cache_refresher():
    """Periodically refreshes popular content in the background."""
    logger.info("🔄 Background Cache Refresher started")
    while True:
        try:
            # Refresh every 30 minutes
            await asyncio.sleep(1800) 
            logger.info("🔄 Refreshing system cache...")
            await warm_up_services()
        except Exception as e:
            logger.error(f"❌ Cache Refresher error: {e}")
            await asyncio.sleep(60)
