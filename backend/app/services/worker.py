import asyncio
import logging
import time
from ..core.cache import api_cache
from ..core.database import db_manager
from scraper.engine import scraper
from scraper.courses import courses_scraper
from social_poster import social_poster

logger = logging.getLogger("worker")

async def auto_broadcaster():
    """Checks for new content and posts to social media."""
    logger.info("Social Broadcaster started")
    while True:
        try:
            items = await scraper.fetch_home(page=1)
            for item in items[:5]:
                cache_key = f"broadcasted_{item['id']}"
                if not api_cache.get(cache_key):
                    await social_poster.post_new_content(
                        item['title'], 
                        f"https://lmina.co/details/{item['id']}", 
                        item['poster']
                    )
                    api_cache.set(cache_key, True, ttl_seconds=86400 * 7)
        except Exception as e:
            logger.error(f"Broadcaster error: {e}")
        await asyncio.sleep(3600)

async def warm_up_services():
    """Warms up scrapers and caches."""
    logger.info("Warming up services...")
    try:
        await scraper.fetch_home(page=1)
        # Warm up priority courses
        await courses_scraper.fetch_latest_courses(page=1)
        await courses_scraper.fetch_category_courses("12", page=1) # Programming
        logger.info("Warm-up complete")
    except Exception as e:
        logger.warning(f"Warm-up failed: {e}")
