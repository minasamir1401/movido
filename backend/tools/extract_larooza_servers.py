"""
Larooza Server Extractor
استخراج جميع سيرفرات المشاهدة من Larooza مع روابط التحميل
"""
import asyncio
import sys
import os
import json
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote

class LaroozaServerExtractor:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ar,en-US;q=0.9,en;q=0.8",
            "Referer": "https://larooza.top/",
        }
        
    async def extract_servers(self, video_url: str):
        """استخراج جميع السيرفرات من رابط الفيديو"""
        print(f"\n{'='*60}")
        print(f"🎬 استخراج السيرفرات من: {video_url}")
        print(f"{'='*60}\n")
        
        async with httpx.AsyncClient(timeout=30, verify=False, follow_redirects=True) as client:
            # 1. جلب صفحة الفيديو الأساسية
            print("📥 جاري جلب صفحة الفيديو...")
            resp = await client.get(video_url, headers=self.headers)
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # استخراج العنوان
            title_tag = soup.find('h1')
            title = title_tag.get_text(strip=True) if title_tag else "Unknown"
            print(f"📺 العنوان: {title}\n")
            
            # 2. جلب صفحة المشاهدة (play.php)
            play_url = video_url.replace('video.php', 'play.php')
            print(f"📥 جاري جلب صفحة المشاهدة: {play_url}")
            play_resp = await client.get(play_url, headers=self.headers)
            play_soup = BeautifulSoup(play_resp.text, 'html.parser')
            
            # 3. استخراج السيرفرات
            servers = []
            
            # الطريقة 1: استخراج من data-embed-url
            server_items = play_soup.select('li[data-embed-url]')
            print(f"\n✅ تم العثور على {len(server_items)} سيرفر من خلال data-embed-url\n")
            
            for idx, item in enumerate(server_items, 1):
                embed_url = item.get('data-embed-url')
                if not embed_url:
                    continue
                    
                if not embed_url.startswith('http'):
                    embed_url = urljoin(play_url, embed_url)
                
                # استخراج اسم السيرفر
                name_tag = item.select_one('strong')
                name = name_tag.get_text(strip=True) if name_tag else f"Server {idx}"
                
                # تنظيف الاسم
                name = name.replace("سيرفر", "Server").strip()
                
                server_info = {
                    "id": idx,
                    "name": name,
                    "embed_url": embed_url,
                    "type": self._detect_server_type(embed_url)
                }
                
                servers.append(server_info)
                
                print(f"🎯 السيرفر {idx}: {name}")
                print(f"   النوع: {server_info['type']}")
                print(f"   الرابط: {embed_url}\n")
            
            # الطريقة 2: استخراج من iframes (احتياطي)
            if not servers:
                print("⚠️ لم يتم العثور على سيرفرات من data-embed-url، جاري البحث في iframes...\n")
                iframes = play_soup.find_all('iframe', src=True)
                
                for idx, iframe in enumerate(iframes, 1):
                    src = iframe['src']
                    if any(x in src.lower() for x in ['ads', 'google', 'facebook', 'analytics']):
                        continue
                        
                    if not src.startswith('http'):
                        src = urljoin(play_url, src)
                    
                    server_info = {
                        "id": idx,
                        "name": f"Server {idx}",
                        "embed_url": src,
                        "type": self._detect_server_type(src)
                    }
                    
                    servers.append(server_info)
                    print(f"🎯 السيرفر {idx}: Server {idx}")
                    print(f"   النوع: {server_info['type']}")
                    print(f"   الرابط: {src}\n")
            
            # 4. استخراج روابط التحميل
            print(f"\n{'='*60}")
            print("📥 جاري استخراج روابط التحميل...")
            print(f"{'='*60}\n")
            
            download_links = await self._extract_downloads(client, video_url)
            
            # 5. استخراج الحلقات (إذا كان مسلسل)
            episodes = []
            if "حلقة" in title or "الحلقة" in title:
                print(f"\n{'='*60}")
                print("📺 جاري استخراج قائمة الحلقات...")
                print(f"{'='*60}\n")
                episodes = self._extract_episodes(soup, video_url)
            
            # النتيجة النهائية
            result = {
                "title": title,
                "video_url": video_url,
                "play_url": play_url,
                "servers": servers,
                "download_links": download_links,
                "episodes": episodes,
                "total_servers": len(servers),
                "total_downloads": len(download_links),
                "total_episodes": len(episodes)
            }
            
            return result
    
    def _detect_server_type(self, url: str) -> str:
        """تحديد نوع السيرفر من الرابط"""
        url_lower = url.lower()
        
        if 'vidbom' in url_lower or 'vidbem' in url_lower:
            return 'Vidbom'
        elif 'doodstream' in url_lower or 'dood' in url_lower:
            return 'Doodstream'
        elif 'voe.sx' in url_lower or 'voe' in url_lower:
            return 'VOE'
        elif 'okru' in url_lower or 'ok.ru' in url_lower:
            return 'OK.ru'
        elif 'vidmoly' in url_lower:
            return 'Vidmoly'
        elif 'filemoon' in url_lower:
            return 'Filemoon'
        elif 'streamtape' in url_lower:
            return 'Streamtape'
        elif 'uqload' in url_lower:
            return 'Uqload'
        elif 'larooza' in url_lower or 'okprime' in url_lower:
            return 'Larooza/OkPrime'
        elif 'short.icu' in url_lower:
            return 'Short.icu'
        else:
            return 'Unknown'
    
    async def _extract_downloads(self, client, video_url: str):
        """استخراج روابط التحميل"""
        download_links = []
        
        # جرب صفحة التحميل
        dl_url = video_url.replace('video.php', 'download.php')
        
        try:
            resp = await client.get(dl_url, headers=self.headers)
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # ابحث عن روابط التحميل
            for link in soup.select('a[href*="http"]'):
                href = link.get('href')
                text = link.get_text(strip=True)
                
                # تحقق من مؤشرات التحميل
                is_download = any(q in text.lower() or q in href.lower() 
                                for q in ['download', 'تحميل', '720', '1080', '480', 'mp4', 'mkv'])
                
                if is_download and 'larooza' not in href:
                    quality = text if text else "Unknown Quality"
                    download_links.append({
                        "quality": quality,
                        "url": href
                    })
                    print(f"📥 {quality}: {href}")
        
        except Exception as e:
            print(f"⚠️ خطأ في استخراج روابط التحميل: {e}")
        
        if not download_links:
            print("⚠️ لم يتم العثور على روابط تحميل مباشرة")
        
        return download_links
    
    def _extract_episodes(self, soup: BeautifulSoup, base_url: str):
        """استخراج قائمة الحلقات"""
        episodes = []
        
        # ابحث عن قوائم الحلقات
        episode_dropdowns = soup.select('select.episodeoption')
        
        for dropdown in episode_dropdowns:
            options = dropdown.find_all('option')
            for opt in options:
                href = opt.get('value')
                if not href or 'select-ep' in href or '#' in href:
                    continue
                
                full_url = urljoin(base_url, href)
                ep_text = opt.get_text(strip=True)
                
                # استخراج رقم الحلقة
                import re
                match = re.search(r'(\d+)', ep_text)
                ep_num = int(match.group(1)) if match else 0
                
                if ep_num > 0:
                    episodes.append({
                        "episode": ep_num,
                        "title": ep_text,
                        "url": full_url
                    })
                    print(f"📺 الحلقة {ep_num}: {full_url}")
        
        # إذا لم نجد من القوائم المنسدلة، ابحث في الروابط
        if not episodes:
            for link in soup.find_all('a', href=True):
                href = link.get('href')
                text = link.get_text(strip=True)
                
                if 'حلقة' in text and 'video.php?vid=' in href:
                    import re
                    match = re.search(r'(\d+)', text)
                    ep_num = int(match.group(1)) if match else 0
                    
                    full_url = urljoin(base_url, href)
                    
                    if ep_num > 0:
                        episodes.append({
                            "episode": ep_num,
                            "title": text,
                            "url": full_url
                        })
                        print(f"📺 الحلقة {ep_num}: {full_url}")
        
        return sorted(episodes, key=lambda x: x['episode'])

async def main():
    # الرابط المطلوب
    video_url = "https://larooza.top/video.php?vid=Yg22o3HXS"
    
    extractor = LaroozaServerExtractor()
    result = await extractor.extract_servers(video_url)
    
    # طباعة الملخص
    print(f"\n{'='*60}")
    print("📊 ملخص النتائج")
    print(f"{'='*60}\n")
    print(f"📺 العنوان: {result['title']}")
    print(f"🎯 عدد السيرفرات: {result['total_servers']}")
    print(f"📥 عدد روابط التحميل: {result['total_downloads']}")
    print(f"📺 عدد الحلقات: {result['total_episodes']}")
    
    # حفظ النتيجة في ملف JSON
    output_file = Path(__file__).parent / "larooza_servers_output.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ تم حفظ النتائج في: {output_file}")
    
    return result

if __name__ == "__main__":
    asyncio.run(main())
