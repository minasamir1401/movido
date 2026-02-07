
import asyncio
import logging
import sys
import os

# إضافة المسار الحالي لـ python path لجلب الموديلات
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scraper.engine import scraper

async def debug_episode():
    query = "مسلسل الحلانجي الحلقة 5"
    print(f"🔎 البحث عن: {query}...")
    
    results = await scraper.search(query)
    if not results:
        print("❌ لم يتم العثور على نتائج بحث.")
        return

    # جلب تفاصيل أول نتيجة (غالباً هي الحلقة المطلوبة)
    target = results[0]
    print(f"✅ تم العثور على: {target['title']}")
    print(f"🔗 الرابط: {target['url']}")
    
    print("\n📦 محاولة استخراج السيرفرات...")
    details = await scraper.fetch_details(target['id'])
    
    if details.get('servers'):
        print(f"🎉 نجح الاستخراج! تم العثور على {len(details['servers'])} سيرفر:")
        for s in details['servers']:
            print(f" - {s['name']}: {s['url']}")
    else:
        print("❌ فشل! لا توجد سيرفرات.")
        
    if details.get('download_links'):
        print(f"\n📥 روابط التحميل ({len(details['download_links'])}):")
        for dl in details['download_links']:
            print(f" - {dl['quality']}: {dl['url']}")
    else:
        print("\n❌ لا توجد روابط تحميل.")

if __name__ == "__main__":
    asyncio.run(debug_episode())
