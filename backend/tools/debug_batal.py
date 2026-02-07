
import asyncio
import logging
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from scraper.engine import scraper

async def debug_servers():
    query = "مسلسل بطل العالم الحلقة 10"
    print(f"🔎 البحث عن: {query}...")
    
    results = await scraper.search(query)
    if not results:
        print("❌ لم يتم العثور على نتائج.")
        return

    target = results[0]
    print(f"✅ تم العثور على: {target['title']}")
    
    print("\n📦 محاولة استخراج كافة السيرفرات...")
    details = await scraper.fetch_details(target['id'])
    
    if details.get('servers'):
        print(f"🎉 نجح الاستخراج! تم العثور على {len(details['servers'])} سيرفر:")
        for idx, s in enumerate(details['servers'], 1):
            print(f" {idx}. {s['name']}: {s['url']}")
    else:
        print("❌ فشل! لم يتم العثور على سيرفرات.")

if __name__ == "__main__":
    asyncio.run(debug_servers())
