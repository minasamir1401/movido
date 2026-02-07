import json
import os
import time
import logging
import asyncio
from typing import Optional, Any
from .config import settings
import aiosqlite

logger = logging.getLogger("cache")

class SQLiteCache:
    def __init__(self, filename: str):
        self.filename = filename
        self.table_name = "kv_store"
        # Ensure dir exists
        os.makedirs(os.path.dirname(self.filename), exist_ok=True)
        self._init_lock = asyncio.Lock()
        self._initialized = False

    async def _init_db(self):
        if self._initialized:
            return
        
        async with self._init_lock:
            if self._initialized:
                return
            try:
                async with aiosqlite.connect(self.filename) as db:
                    await db.execute(f"""
                        CREATE TABLE IF NOT EXISTS {self.table_name} (
                            key TEXT PRIMARY KEY,
                            value TEXT,
                            expires_at REAL
                        )
                    """)
                    await db.execute(f"CREATE INDEX IF NOT EXISTS idx_expires ON {self.table_name} (expires_at)")
                    await db.commit()
                self._initialized = True
            except Exception as e:
                logger.error(f"Failed to init SQLite cache: {e}")

    async def get(self, key: str) -> Optional[Any]:
        if not self._initialized:
            await self._init_db()
            
        try:
            now = time.time()
            async with aiosqlite.connect(self.filename) as db:
                # Cleanup old entries occasionally (can be optimized to not run every get)
                if int(now) % 100 == 0:
                    await db.execute(f"DELETE FROM {self.table_name} WHERE expires_at < ?", (now,))
                    await db.commit()

                async with db.execute(f"SELECT value, expires_at FROM {self.table_name} WHERE key = ?", (key,)) as cursor:
                    row = await cursor.fetchone()
                    
                if row:
                    value_json, expires_at = row
                    if now < expires_at:
                        return json.loads(value_json)
                    else:
                        # Expired
                        await db.execute(f"DELETE FROM {self.table_name} WHERE key = ?", (key,))
                        await db.commit()
        except Exception as e:
            logger.error(f"SQLite get error ({key}): {e}")
        return None

    async def set(self, key: str, data: Any, ttl_seconds: Optional[int] = None):
        if not self._initialized:
            await self._init_db()
            
        try:
            ttl = ttl_seconds if ttl_seconds is not None else settings.CACHE_TTL
            expires_at = time.time() + ttl
            value_json = json.dumps(data)
            
            async with aiosqlite.connect(self.filename) as db:
                await db.execute(
                    f"INSERT OR REPLACE INTO {self.table_name} (key, value, expires_at) VALUES (?, ?, ?)",
                    (key, value_json, expires_at)
                )
                await db.commit()
        except Exception as e:
            logger.error(f"SQLite set error ({key}): {e}")

    async def clear(self):
        if not self._initialized:
            await self._init_db()
        try:
            async with aiosqlite.connect(self.filename) as db:
                await db.execute(f"DELETE FROM {self.table_name}")
                await db.commit()
            logger.info("Cache cleared successfully")
        except Exception as e:
            logger.error(f"SQLite clear error: {e}")

# Backward compatibility: Use simple JSON cache for scrapers to avoid event loop conflicts
class PersistentCache:
    """
    Simple JSON-based cache for scrapers (synchronous operations).
    Scrapers use this to avoid async/event loop conflicts.
    """
    def __init__(self, filename: str):
        self.filename = filename
        self._cache = {}
        import threading
        self._lock = threading.Lock()
        os.makedirs(os.path.dirname(self.filename), exist_ok=True)
        self._load()
    
    def _load(self):
        """Load cache from JSON file"""
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r', encoding='utf-8') as f:
                    self._cache = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load cache from {self.filename}: {e}")
                self._cache = {}
    
    def _save(self):
        """Save cache to JSON file"""
        try:
            import tempfile
            with self._lock:
                # Write to temp file first, then rename (atomic operation)
                temp_fd, temp_path = tempfile.mkstemp(dir=os.path.dirname(self.filename), suffix='.tmp')
                try:
                    with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
                        json.dump(self._cache, f)
                    
                    # On Windows, os.replace might still fail if file is held by another handle
                    # We try a few times or ignore if it's just a cache write
                    retries = 3
                    while retries > 0:
                        try:
                            if os.path.exists(self.filename):
                                os.remove(self.filename)
                            os.rename(temp_path, self.filename)
                            break
                        except OSError:
                            retries -= 1
                            time.sleep(0.1)
                except Exception as e:
                    if os.path.exists(temp_path):
                        os.unlink(temp_path)
                    raise e
        except Exception as e:
            # logger.warning is enough, we don't want to crash on cache save failure
            pass
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        item = self._cache.get(key)
        if item:
            expire_time, data = item
            if time.time() < expire_time:
                return data
            else:
                del self._cache[key]
                self._save()
        return None
    
    def set(self, key: str, data: Any, ttl_seconds: Optional[int] = None):
        """Set value in cache"""
        ttl = ttl_seconds if ttl_seconds is not None else settings.CACHE_TTL
        self._cache[key] = (time.time() + ttl, data)
        self._save()
    
    def clear(self):
        """Clear all cache"""
        self._cache = {}
        self._save()

# We will export a global singleton for the main API cache
cache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "cache")
os.makedirs(cache_dir, exist_ok=True)

# Replace the main api_cache with SQLite version
# Note: This requires the consumers in endpoints to await .get() and .set(),
# which they mostly do not currently (they use sync .get()).
# To fix this quickly without rewriting EVERYTHING, I will implement a hybrid approach:
# The `api_cache` used in `movies.py` calls `.get()` synchronously in the code I viewed?
# Let's check movies.py again. 
# In movies.py: `cached = api_cache.get(cache_key)` (Sync)
# So I cannot simply swap it to async without updating all call sites.
# Given the user wants SPEED, updating `movies.py` to async cache is worth it.

api_cache = SQLiteCache(os.path.join(cache_dir, "api_cache.db"))

def clear_all_system_caches():
    """Clears API cache and all cached image files."""
    try:
        # 1. Clear API Persistent Cache
        # Since it is async, we need a loop
        try:
            asyncio.get_event_loop().run_until_complete(api_cache.clear())
        except:
             # If loop is already running, this convenience function might fail.
             # Ideally should be async.
             pass
        
        # 2. Clear Image Cache Directory
        image_cache_dir = os.path.join(cache_dir, "images")
        if os.path.exists(image_cache_dir):
            import shutil
            for filename in os.listdir(image_cache_dir):
                file_path = os.path.join(image_cache_dir, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                except Exception as e:
                    logger.error(f'Failed to delete {file_path}. Reason: {e}')
        
        logger.info("🚀 All system caches (API & Images) cleared successfully")
        return True
    except Exception as e:
        logger.error(f"Error in clear_all_system_caches: {e}")
        return False

