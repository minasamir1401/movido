"""
أداة متقدمة لكسر تشفير السيرفرات واستخراج الروابط المباشرة
"""
import asyncio
import base64
import re
import json
from curl_cffi.requests import AsyncSession
from urllib.parse import unquote, urlparse

async def break_server_encryption():
    """كسر تشفير السيرفرات واستخراج الروابط المباشرة"""
    
    # قراءة السيرفرات المستخرجة
    with open("extracted_servers.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    
    servers = data['servers']
    
    print("=" * 80)
    print("🔓 كسر تشفير السيرفرات")
    print("=" * 80)
    print(f"\n📊 إجمالي السيرفرات: {len(servers)}")
    
    session = AsyncSession(impersonate="chrome124", timeout=15, verify=False)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ar,en-US;q=0.9",
    }
    
    direct_links = []
    
    for i, server in enumerate(servers, 1):
        print(f"\n{'='*80}")
        print(f"🎬 السيرفر {i}/{len(servers)}: {server['name']}")
        print(f"🔗 URL: {server['url'][:80]}...")
        print(f"{'='*80}")
        
        url = server['url']
        server_type = None
        
        # تحديد نوع السيرفر
        if 'okprime' in url or 'ok.ru' in url:
            server_type = 'okprime'
        elif 'mixdrop' in url or 'mxdrop' in url:
            server_type = 'mixdrop'
        elif 'dood' in url:
            server_type = 'doodstream'
        elif 'voe' in url:
            server_type = 'voe'
        elif 'vidmoly' in url:
            server_type = 'vidmoly'
        elif 'upstream' in url:
            server_type = 'upstream'
        elif 'short.icu' in url:
            server_type = 'shortlink'
        elif 'vk.com' in url:
            server_type = 'vk'
        else:
            server_type = 'generic'
        
        print(f"📌 النوع: {server_type.upper()}")
        
        try:
            # جلب الصفحة
            resp = await session.get(url, headers=headers, allow_redirects=True)
            html = resp.text
            final_url = str(resp.url)
            
            print(f"✅ تم جلب الصفحة (الحجم: {len(html)} حرف)")
            if final_url != url:
                print(f"🔄 تم التوجيه إلى: {final_url[:80]}...")
            
            # استخراج الروابط المباشرة
            extracted = []
            
            # 1. البحث عن روابط M3U8
            m3u8_patterns = [
                r'["\']([^"\']*\.m3u8[^"\']*)["\']',
                r'file:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
                r'source:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
                r'src:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
            ]
            
            for pattern in m3u8_patterns:
                matches = re.findall(pattern, html, re.IGNORECASE)
                for match in matches:
                    if 'http' in match:
                        extracted.append({"type": "m3u8", "url": match})
            
            # 2. البحث عن روابط MP4
            mp4_patterns = [
                r'["\']([^"\']*\.mp4[^"\']*)["\']',
                r'file:\s*["\']([^"\']+\.mp4[^"\']*)["\']',
                r'source:\s*["\']([^"\']+\.mp4[^"\']*)["\']',
            ]
            
            for pattern in mp4_patterns:
                matches = re.findall(pattern, html, re.IGNORECASE)
                for match in matches:
                    if 'http' in match and not any(x in match for x in ['.js', '.css']):
                        extracted.append({"type": "mp4", "url": match})
            
            # 3. فك تشفير Base64 المخفي
            b64_patterns = [
                r'atob\(["\']([A-Za-z0-9+/=]+)["\']\)',
                r'base64[,\s]*["\']([A-Za-z0-9+/=]{20,})["\']\)',
            ]
            
            for pattern in b64_patterns:
                matches = re.findall(pattern, html)
                for match in matches:
                    try:
                        decoded = base64.b64decode(match).decode('utf-8', errors='ignore')
                        if 'http' in decoded and ('.m3u8' in decoded or '.mp4' in decoded):
                            extracted.append({"type": "base64_decoded", "url": decoded})
                    except:
                        pass
            
            # 4. استخراج من JavaScript المعقد
            # البحث عن eval(function(p,a,c,k,e,d))
            if 'eval(function(p,a,c,k,e' in html:
                print("   🔍 وجدنا JavaScript مشفر (packed)...")
                # محاولة فك التشفير
                packed_pattern = r"eval\(function\(p,a,c,k,e,.*?\)\)"
                packed = re.findall(packed_pattern, html, re.DOTALL)
                if packed:
                    print(f"   📦 تم العثور على {len(packed)} كود مشفر")
            
            # 5. استخراج خاص بكل نوع سيرفر
            if server_type == 'okprime':
                # OkPrime غالباً يستخدم sources array
                sources_pattern = r'sources:\s*\[(.*?)\]'
                sources_match = re.search(sources_pattern, html, re.DOTALL)
                if sources_match:
                    sources_text = sources_match.group(1)
                    urls = re.findall(r'["\']([^"\']+\.(?:m3u8|mp4)[^"\']*)["\']', sources_text)
                    for url_found in urls:
                        extracted.append({"type": "okprime_source", "url": url_found})
            
            elif server_type == 'voe':
                # VOE يستخدم 'hls' variable
                hls_pattern = r'["\']hls["\']\s*:\s*["\']([^"\']+)["\']'
                hls_match = re.search(hls_pattern, html)
                if hls_match:
                    extracted.append({"type": "voe_hls", "url": hls_match.group(1)})
            
            # إزالة التكرارات
            unique_extracted = []
            seen_urls = set()
            for item in extracted:
                url_clean = item['url'].split('?')[0]  # إزالة query params للمقارنة
                if url_clean not in seen_urls:
                    seen_urls.add(url_clean)
                    unique_extracted.append(item)
            
            if unique_extracted:
                print(f"\n✅ تم استخراج {len(unique_extracted)} رابط مباشر:")
                for j, link in enumerate(unique_extracted, 1):
                    print(f"   {j}. [{link['type']}] {link['url'][:80]}...")
                    direct_links.append({
                        "server": server['name'],
                        "server_url": url,
                        "type": link['type'],
                        "direct_url": link['url'],
                        "source": server['source']
                    })
            else:
                print("   ⚠️ لم يتم العثور على روابط مباشرة (قد يحتاج JavaScript execution)")
            
            # تأخير صغير لتجنب الحظر
            await asyncio.sleep(0.5)
            
        except Exception as e:
            print(f"   ❌ خطأ: {e}")
    
    await session.close()
    
    # حفظ النتائج
    print("\n" + "=" * 80)
    print("💾 حفظ الروابط المباشرة")
    print("=" * 80)
    
    result = {
        "total_servers": len(servers),
        "direct_links_found": len(direct_links),
        "links": direct_links
    }
    
    with open("direct_links.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ تم استخراج {len(direct_links)} رابط مباشر من {len(servers)} سيرفر")
    print(f"📁 تم الحفظ في: direct_links.json")
    
    # إحصائيات
    print("\n" + "=" * 80)
    print("📊 إحصائيات الاستخراج")
    print("=" * 80)
    
    types_count = {}
    for link in direct_links:
        link_type = link['type']
        types_count[link_type] = types_count.get(link_type, 0) + 1
    
    print(f"\n📈 أنواع الروابط المستخرجة:")
    for ltype, count in sorted(types_count.items(), key=lambda x: x[1], reverse=True):
        print(f"   {ltype}: {count} رابط")
    
    # أفضل السيرفرات
    print(f"\n🏆 أفضل السيرفرات (التي تم استخراج روابط منها):")
    server_success = {}
    for link in direct_links:
        server_name = link['server']
        server_success[server_name] = server_success.get(server_name, 0) + 1
    
    for server, count in sorted(server_success.items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"   ✅ {server}: {count} رابط")
    
    print("\n" + "=" * 80)
    print("✅ اكتمل كسر التشفير!")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(break_server_encryption())
