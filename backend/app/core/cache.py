import json
import os
import time
import logging
from typing import Optional, Any
from .config import settings

logger = logging.getLogger("cache")

class PersistentCache:
    def __init__(self, filename: str):
        self.filename = filename
        self._cache = {}
        # Ensure dir exists on init
        os.makedirs(os.path.dirname(self.filename), exist_ok=True)
        self._load()

    def _load(self):
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r', encoding='utf-8') as f:
                    self._cache = json.load(f)
                logger.info(f"Loaded {len(self._cache)} items from cache")
            except Exception as e:
                logger.error(f"Failed to load cache: {e}")
                self._cache = {}

    def _save(self):
        try:
            # Atomic save: write to temp then rename
            os.makedirs(os.path.dirname(self.filename), exist_ok=True)
            temp_file = f"{self.filename}.tmp"
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(self._cache, f)
            os.replace(temp_file, self.filename)
        except Exception as e:
            logger.error(f"Failed to save cache: {e}")

    def get(self, key: str) -> Optional[Any]:
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
        ttl = ttl_seconds if ttl_seconds is not None else settings.CACHE_TTL
        self._cache[key] = (time.time() + ttl, data)
        self._save()

cache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "cache")
os.makedirs(cache_dir, exist_ok=True)
api_cache = PersistentCache(os.path.join(cache_dir, "api_cache.json"))
