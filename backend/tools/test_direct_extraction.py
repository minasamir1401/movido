"""
Test Direct URL Extraction from All Larooza Servers
اختبار استخراج الروابط المباشرة من جميع سيرفرات Larooza
"""
import asyncio
import sys
import json
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scraper.extractors.engine import ExtractorEngine

async def test_all_servers():
    """Test extraction from all servers in the saved JSON"""
    
    # Load the servers data
    json_file = Path(__file__).parent / "larooza_servers_output.json"
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"\n{'='*70}")
    print(f"🎬 اختبار استخراج الروابط المباشرة")
    print(f"📺 العنوان: {data['title']}")
    print(f"🎯 عدد السيرفرات: {data['total_servers']}")
    print(f"{'='*70}\n")
    
    results = {
        "title": data['title'],
        "video_url": data['video_url'],
        "servers": [],
        "working_servers": 0,
        "failed_servers": 0
    }
    
    for server in data['servers']:
        server_id = server['id']
        server_name = server['name']
        server_type = server['type']
        embed_url = server['embed_url']
        
        print(f"\n{'─'*70}")
        print(f"🎯 السيرفر {server_id}: {server_name} ({server_type})")
        print(f"📎 Embed URL: {embed_url}")
        print(f"{'─'*70}")
        
        try:
            # Extract direct URL
            result = await ExtractorEngine.extract(embed_url)
            
            if result and result.get('url'):
                direct_url = result['url']
                video_type = result.get('type', 'unknown')
                headers = result.get('headers', {})
                
                print(f"✅ نجح الاستخراج!")
                print(f"   🎥 النوع: {video_type.upper()}")
                print(f"   🔗 الرابط المباشر: {direct_url[:100]}...")
                if headers:
                    print(f"   📋 Headers: {headers}")
                
                results['servers'].append({
                    "id": server_id,
                    "name": server_name,
                    "type": server_type,
                    "embed_url": embed_url,
                    "status": "success",
                    "direct_url": direct_url,
                    "video_type": video_type,
                    "headers": headers
                })
                results['working_servers'] += 1
            else:
                print(f"❌ فشل الاستخراج - لم يتم العثور على رابط مباشر")
                results['servers'].append({
                    "id": server_id,
                    "name": server_name,
                    "type": server_type,
                    "embed_url": embed_url,
                    "status": "failed",
                    "error": "No direct URL found"
                })
                results['failed_servers'] += 1
                
        except Exception as e:
            print(f"❌ خطأ في الاستخراج: {str(e)}")
            results['servers'].append({
                "id": server_id,
                "name": server_name,
                "type": server_type,
                "embed_url": embed_url,
                "status": "error",
                "error": str(e)
            })
            results['failed_servers'] += 1
    
    # Summary
    print(f"\n{'='*70}")
    print(f"📊 ملخص النتائج")
    print(f"{'='*70}")
    print(f"✅ السيرفرات الناجحة: {results['working_servers']}/{data['total_servers']}")
    print(f"❌ السيرفرات الفاشلة: {results['failed_servers']}/{data['total_servers']}")
    print(f"📈 نسبة النجاح: {(results['working_servers']/data['total_servers']*100):.1f}%")
    
    # Save results
    output_file = Path(__file__).parent / "direct_urls_output.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ تم حفظ النتائج في: {output_file}")
    
    # Show working servers
    if results['working_servers'] > 0:
        print(f"\n{'='*70}")
        print(f"🎉 السيرفرات الناجحة:")
        print(f"{'='*70}")
        for server in results['servers']:
            if server['status'] == 'success':
                print(f"\n✅ {server['name']} ({server['type']})")
                print(f"   🔗 {server['direct_url'][:80]}...")
    
    return results

if __name__ == "__main__":
    asyncio.run(test_all_servers())
