"""
اختبار سريع لنظام الكاش الجديد
"""
import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_sqlite_cache():
    from app.core.cache import SQLiteCache, PersistentCache
    import tempfile
    
    print("🧪 اختبار SQLiteCache...")
    
    # Test async cache
    temp_db = os.path.join(tempfile.gettempdir(), "test_cache.db")
    cache = SQLiteCache(temp_db)
    
    # Test set/get
    await cache.set("test_key", {"data": "test_value"}, ttl_seconds=60)
    result = await cache.get("test_key")
    assert result == {"data": "test_value"}, "❌ فشل اختبار async cache"
    print("✅ SQLiteCache async: نجح")
    
    # Test sync wrapper
    print("\n🧪 اختبار PersistentCache (sync wrapper)...")
    temp_db2 = os.path.join(tempfile.gettempdir(), "test_cache2.db")
    sync_cache = PersistentCache(temp_db2)
    
    sync_cache.set("sync_key", {"sync": "data"}, ttl_seconds=60)
    sync_result = sync_cache.get("sync_key")
    assert sync_result == {"sync": "data"}, "❌ فشل اختبار sync cache"
    print("✅ PersistentCache sync: نجح")
    
    # Cleanup
    await cache.clear()
    sync_cache.clear()
    
    print("\n✅ جميع الاختبارات نجحت!")
    print("🚀 النظام جاهز للاستخدام")

if __name__ == "__main__":
    asyncio.run(test_sqlite_cache())
