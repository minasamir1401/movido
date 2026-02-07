"""
🔓 MOVIDO Advanced Server Breaker - أداة كسر التشفير المتقدمة
ضمان استخراج الروابط المباشرة من جميع أنواع السيرفرات
"""
import asyncio
import base64
import re
import json
from curl_cffi.requests import AsyncSession
from urllib.parse import unquote, urlparse, parse_qs
import hashlib

class ServerBreaker:
    """كاسر التشفير المتقدم"""
    
    def __init__(self):
        self.session = None
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "*/*",
            "Accept-Language": "ar,en-US;q=0.9",
            "Referer": "https://google.com/",
        }
    
    async def init_session(self):
        """تهيئة الجلسة"""
        self.session = AsyncSession(impersonate="chrome124", timeout=20, verify=False)
    
    def decode_packed_js(self, packed_str):
        """فك تشفير JavaScript المضغوط (Dean Edwards packer)"""
        try:
            pattern = r"}\s*\('(.*?)',\s*(\d+),\s*(\d+),\s*'(.*?)'\.split"
            match = re.search(pattern, packed_str, re.DOTALL)
            if not match:
                return None
            
            p, a, c, k = match.groups()
            a, c = int(a), int(c)
            k = k.split('|')
            
            def base_n(num, base):
                if num == 0:
                    return "0"
                digits = "0123456789abcdefghijklmnopqrstuvwxyz"
                result = ""
                while num:
                    result = digits[num % base] + result
                    num //= base
                return result or "0"
            
            result = p
            for i in range(c - 1, -1, -1):
                key = base_n(i, a)
                if i < len(k) and k[i]:
                    result = re.sub(r'\b' + re.escape(key) + r'\b', k[i], result)
            
            return result
        except Exception as e:
            print(f"      ⚠️ فشل فك الضغط: {e}")
            return None
    
    def extract_all_urls(self, text):
        """استخراج جميع الروابط من النص"""
        urls = []
        
        # 1. روابط M3U8
        m3u8_patterns = [
            r'["\']([^"\']*\.m3u8[^"\']*)["\']',
            r'file\s*:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
            r'source\s*:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
            r'src\s*:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
            r'hls\s*:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
            r'playlist\s*:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
        ]
        
        for pattern in m3u8_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if 'http' in match:
                    urls.append({"type": "m3u8", "url": match.replace('\\/', '/')})
        
        # 2. روابط MP4
        mp4_patterns = [
            r'["\']([^"\']*\.mp4[^"\']*)["\']',
            r'file\s*:\s*["\']([^"\']+\.mp4[^"\']*)["\']',
            r'source\s*:\s*["\']([^"\']+\.mp4[^"\']*)["\']',
        ]
        
        for pattern in mp4_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if 'http' in match and not any(x in match for x in ['.js', '.css', 'logo', 'thumb']):
                    urls.append({"type": "mp4", "url": match.replace('\\/', '/')})
        
        # 3. روابط عامة (googlevideo, etc)
        general_patterns = [
            r'["\']((https?://[^"\']+googlevideo\.com[^"\']+))["\']',
            r'["\']((https?://[^"\']+\.(?:mp4|m3u8|ts)[^"\']*?))["\']',
        ]
        
        for pattern in general_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                url = match[0] if isinstance(match, tuple) else match
                if 'http' in url:
                    urls.append({"type": "direct", "url": url.replace('\\/', '/')})
        
        return urls
    
    def decode_base64_strings(self, text):
        """فك تشفير جميع نصوص Base64 في الصفحة"""
        decoded_urls = []
        
        # البحث عن base64 strings
        b64_patterns = [
            r'atob\(["\']([A-Za-z0-9+/=]{20,})["\']\)',
            r'base64[,\s]*["\']([A-Za-z0-9+/=]{20,})["\']\)',
            r'decode\(["\']([A-Za-z0-9+/=]{20,})["\']\)',
        ]
        
        for pattern in b64_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                try:
                    # محاولة فك التشفير
                    decoded = base64.b64decode(match).decode('utf-8', errors='ignore')
                    if 'http' in decoded:
                        # استخراج الروابط من النص المفكوك
                        urls = self.extract_all_urls(decoded)
                        decoded_urls.extend(urls)
                except:
                    pass
        
        return decoded_urls
    
    async def break_okprime(self, url, html):
        """كسر تشفير OkPrime"""
        print("      🔓 كسر OkPrime...")
        links = []
        
        # OkPrime يستخدم sources array
        sources_pattern = r'sources\s*:\s*\[(.*?)\]'
        sources_match = re.search(sources_pattern, html, re.DOTALL)
        if sources_match:
            sources_text = sources_match.group(1)
            urls = re.findall(r'["\']([^"\']+\.(?:m3u8|mp4)[^"\']*)["\']', sources_text)
            for found_url in urls:
                links.append({"type": "okprime_source", "url": found_url})
        
        # البحث عن file: parameter
        file_pattern = r'file\s*:\s*["\']([^"\']+)["\']'
        file_matches = re.findall(file_pattern, html)
        for match in file_matches:
            if '.m3u8' in match or '.mp4' in match:
                links.append({"type": "okprime_file", "url": match})
        
        return links
    
    async def break_voe(self, url, html):
        """كسر تشفير VOE"""
        print("      🔓 كسر VOE...")
        links = []
        
        # VOE يستخدم 'hls' variable
        hls_pattern = r'["\']hls["\']\s*:\s*["\']([^"\']+)["\']'
        hls_match = re.search(hls_pattern, html)
        if hls_match:
            links.append({"type": "voe_hls", "url": hls_match.group(1)})
        
        # VOE أيضاً يخفي الرابط في base64
        voe_b64_pattern = r'prompt\(["\']([A-Za-z0-9+/=]{30,})["\']\)'
        voe_matches = re.findall(voe_b64_pattern, html)
        for match in voe_matches:
            try:
                decoded = base64.b64decode(match).decode('utf-8', errors='ignore')
                if 'http' in decoded and '.m3u8' in decoded:
                    links.append({"type": "voe_decoded", "url": decoded})
            except:
                pass
        
        return links
    
    async def break_mixdrop(self, url, html):
        """كسر تشفير MixDrop"""
        print("      🔓 كسر MixDrop...")
        links = []
        
        # MixDrop يستخدم MDCore
        mdcore_pattern = r'MDCore\.wurl\s*=\s*["\']([^"\']+)["\']'
        mdcore_match = re.search(mdcore_pattern, html)
        if mdcore_match:
            wurl = mdcore_match.group(1)
            # فك التشفير
            if wurl.startswith('//'):
                wurl = 'https:' + wurl
            links.append({"type": "mixdrop_wurl", "url": wurl})
        
        return links
    
    async def break_vidmoly(self, url, html):
        """كسر تشفير Vidmoly"""
        print("      🔓 كسر Vidmoly...")
        links = []
        
        # Vidmoly يستخدم sources
        sources_pattern = r'sources:\s*\[(.*?)\]'
        sources_match = re.search(sources_pattern, html, re.DOTALL)
        if sources_match:
            sources_text = sources_match.group(1)
            urls = re.findall(r'["\']([^"\']+\.(?:m3u8|mp4)[^"\']*)["\']', sources_text)
            for found_url in urls:
                links.append({"type": "vidmoly_source", "url": found_url})
        
        return links
    
    async def break_doodstream(self, url, html):
        """كسر تشفير Doodstream"""
        print("      🔓 كسر Doodstream...")
        links = []
        
        # Doodstream يستخدم /pass_md5/
        pass_pattern = r'/pass_md5/([^"\']+)'
        pass_match = re.search(pass_pattern, html)
        if pass_match:
            pass_md5 = pass_match.group(1)
            # بناء الرابط
            parsed = urlparse(url)
            base_url = f"{parsed.scheme}://{parsed.netloc}"
            video_url = f"{base_url}/pass_md5/{pass_md5}"
            links.append({"type": "doodstream_pass", "url": video_url})
        
        return links
    
    async def break_server(self, server):
        """كسر تشفير سيرفر واحد"""
        url = server['url']
        name = server['name']
        
        print(f"\n{'='*80}")
        print(f"🎬 {name}")
        print(f"🔗 {url[:80]}...")
        print(f"{'='*80}")
        
        all_links = []
        
        try:
            # جلب الصفحة
            self.headers['Referer'] = url
            resp = await self.session.get(url, headers=self.headers, allow_redirects=True)
            html = resp.text
            final_url = str(resp.url)
            
            print(f"   ✅ تم جلب الصفحة (الحجم: {len(html):,} حرف)")
            
            if final_url != url:
                print(f"   🔄 تم التوجيه: {final_url[:60]}...")
            
            # تحديد نوع السيرفر
            server_type = 'generic'
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
            
            print(f"   📌 النوع: {server_type.upper()}")
            
            # 1. فك تشفير JavaScript المضغوط
            if 'eval(function(p,a,c,k,e' in html:
                print("   🔍 وجدنا JavaScript مشفر...")
                packed_pattern = r"eval\(function\(p,a,c,k,e,.*?\)\)"
                packed_scripts = re.findall(packed_pattern, html, re.DOTALL)
                for packed in packed_scripts:
                    unpacked = self.decode_packed_js(packed)
                    if unpacked:
                        print("      ✅ تم فك الضغط بنجاح!")
                        html += "\n" + unpacked  # إضافة للبحث
            
            # 2. استخراج خاص بنوع السيرفر
            if server_type == 'okprime':
                links = await self.break_okprime(url, html)
                all_links.extend(links)
            elif server_type == 'voe':
                links = await self.break_voe(url, html)
                all_links.extend(links)
            elif server_type == 'mixdrop':
                links = await self.break_mixdrop(url, html)
                all_links.extend(links)
            elif server_type == 'vidmoly':
                links = await self.break_vidmoly(url, html)
                all_links.extend(links)
            elif server_type == 'doodstream':
                links = await self.break_doodstream(url, html)
                all_links.extend(links)
            
            # 3. استخراج عام من كل الصفحة
            print("   🔍 استخراج عام...")
            general_links = self.extract_all_urls(html)
            all_links.extend(general_links)
            
            # 4. فك تشفير Base64
            print("   🔓 فك تشفير Base64...")
            b64_links = self.decode_base64_strings(html)
            all_links.extend(b64_links)
            
            # إزالة التكرارات
            unique_links = []
            seen = set()
            for link in all_links:
                url_key = link['url'].split('?')[0]
                if url_key not in seen and 'http' in link['url']:
                    seen.add(url_key)
                    unique_links.append(link)
            
            if unique_links:
                print(f"\n   ✅ تم استخراج {len(unique_links)} رابط مباشر:")
                for i, link in enumerate(unique_links[:5], 1):  # عرض أول 5
                    print(f"      {i}. [{link['type']}] {link['url'][:70]}...")
                if len(unique_links) > 5:
                    print(f"      ... و {len(unique_links) - 5} روابط أخرى")
            else:
                print("   ⚠️ لم يتم العثور على روابط (قد يحتاج browser automation)")
            
            await asyncio.sleep(0.3)  # تأخير صغير
            
            return {
                "server": name,
                "server_url": url,
                "server_type": server_type,
                "links": unique_links,
                "source": server.get('source', 'unknown')
            }
            
        except Exception as e:
            print(f"   ❌ خطأ: {e}")
            return {
                "server": name,
                "server_url": url,
                "links": [],
                "error": str(e)
            }
    
    async def break_all_servers(self):
        """كسر تشفير جميع السيرفرات"""
        # قراءة السيرفرات
        with open("extracted_servers.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        
        servers = data['servers']
        
        print("=" * 80)
        print("🔓 MOVIDO Advanced Server Breaker")
        print("=" * 80)
        print(f"\n📊 إجمالي السيرفرات: {len(servers)}")
        
        await self.init_session()
        
        results = []
        for i, server in enumerate(servers, 1):
            print(f"\n\n{'#'*80}")
            print(f"# السيرفر {i}/{len(servers)}")
            print(f"{'#'*80}")
            
            result = await self.break_server(server)
            results.append(result)
        
        await self.session.close()
        
        # حفظ النتائج
        print("\n\n" + "=" * 80)
        print("💾 حفظ النتائج")
        print("=" * 80)
        
        # حساب الإحصائيات
        total_links = sum(len(r['links']) for r in results)
        successful_servers = sum(1 for r in results if r['links'])
        
        output = {
            "total_servers": len(servers),
            "successful_servers": successful_servers,
            "total_direct_links": total_links,
            "results": results
        }
        
        with open("broken_servers.json", "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ تم كسر {successful_servers}/{len(servers)} سيرفر بنجاح")
        print(f"🔗 إجمالي الروابط المباشرة: {total_links}")
        print(f"📁 تم الحفظ في: broken_servers.json")
        
        # إحصائيات مفصلة
        print("\n" + "=" * 80)
        print("📊 إحصائيات التفصيلية")
        print("=" * 80)
        
        # أنواع الروابط
        link_types = {}
        for result in results:
            for link in result['links']:
                ltype = link['type']
                link_types[ltype] = link_types.get(ltype, 0) + 1
        
        if link_types:
            print("\n📈 أنواع الروابط:")
            for ltype, count in sorted(link_types.items(), key=lambda x: x[1], reverse=True):
                print(f"   {ltype}: {count} رابط")
        
        # أفضل السيرفرات
        print("\n🏆 أفضل السيرفرات:")
        sorted_results = sorted(results, key=lambda x: len(x['links']), reverse=True)
        for i, result in enumerate(sorted_results[:5], 1):
            if result['links']:
                print(f"   {i}. {result['server']}: {len(result['links'])} رابط")
        
        print("\n" + "=" * 80)
        print("✅ اكتمل كسر التشفير بنجاح!")
        print("=" * 80)

async def main():
    breaker = ServerBreaker()
    await breaker.break_all_servers()

if __name__ == "__main__":
    asyncio.run(main())
