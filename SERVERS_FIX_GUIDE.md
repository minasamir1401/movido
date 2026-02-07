# 🔧 دليل فك تشفير السيرفرات الفاشلة

## 📊 ملخص السيرفرات الفاشلة

| السيرفر | المشكلة | الحل الموصى به | الأدوات |
|---------|---------|-----------------|---------|
| **VK.com** | No video URL found | yt-dlp + API | yt-dlp, vk-api |
| **Short.icu** | Redirect loop | Selenium + redirect bypass | Universal Bypass, Selenium |
| **Dsvplay** | No video URL found | M3U8 extraction | requests, m3u8 parser |
| **VOE.sx** | 404 Error | Link expired/changed | Retry + new URL |
| **OK.ru** | No video URL found | yt-dlp + JSON parsing | yt-dlp, ok-ru-dl |

---

## 1️⃣ VK.com (Server 2)

### 🔍 المشكلة:
- VK يستخدم تشفير معقد للفيديوهات
- الروابط تنتهي صلاحيتها بسرعة
- يحتاج cookies للوصول

### ✅ الحل الأفضل: **yt-dlp**

```python
# استخدام yt-dlp (الأفضل)
import subprocess
import json

def extract_vk_with_ytdlp(url: str):
    """Extract VK video using yt-dlp"""
    try:
        cmd = [
            'yt-dlp',
            '--dump-json',
            '--no-warnings',
            url
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return {
                "url": data.get('url'),
                "type": "mp4" if '.mp4' in data.get('url', '') else "hls",
                "headers": {"Referer": "https://vk.com/"}
            }
    except Exception as e:
        print(f"yt-dlp error: {e}")
    return None
```

### 🔧 الحل البديل: VK API

```python
import vk_api

def extract_vk_with_api(video_id: str):
    """Extract using VK API (requires access token)"""
    vk_session = vk_api.VkApi(token='YOUR_ACCESS_TOKEN')
    vk = vk_session.get_api()
    
    try:
        video = vk.video.get(videos=video_id)
        if video['items']:
            files = video['items'][0]['files']
            # Get highest quality
            for quality in ['mp4_1080', 'mp4_720', 'mp4_480', 'mp4_360']:
                if quality in files:
                    return {
                        "url": files[quality],
                        "type": "mp4",
                        "headers": {"Referer": "https://vk.com/"}
                    }
    except Exception as e:
        print(f"VK API error: {e}")
    return None
```

---

## 2️⃣ Short.icu (Server 5)

### 🔍 المشكلة:
- URL shortener مع إعلانات
- Redirect loops
- Countdown timers

### ✅ الحل الأفضل: **Selenium + Redirect Bypass**

```python
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

async def extract_short_icu(url: str):
    """Extract video from short.icu using Selenium"""
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-blink-features=AutomationControlled')
    
    driver = webdriver.Chrome(options=options)
    
    try:
        driver.get(url)
        
        # Wait for redirect or click "Continue" button
        try:
            # Try to find and click continue button
            continue_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "btn-main"))
            )
            continue_btn.click()
            time.sleep(2)
        except:
            pass
        
        # Wait for final redirect
        WebDriverWait(driver, 15).until(
            lambda d: 'short.icu' not in d.current_url
        )
        
        final_url = driver.current_url
        driver.quit()
        
        # Now extract from final URL
        from scraper.extractors.engine import ExtractorEngine
        return await ExtractorEngine.extract(final_url)
        
    except Exception as e:
        driver.quit()
        print(f"Short.icu error: {e}")
        return None
```

### 🔧 الحل البديل: Universal Bypass Extension

```python
# استخدام requests مع follow redirects
import requests

def bypass_short_icu(url: str):
    """Bypass short.icu using requests"""
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    
    try:
        # Follow redirects
        response = session.get(url, allow_redirects=True, timeout=15)
        final_url = response.url
        
        # Check if we escaped short.icu
        if 'short.icu' not in final_url:
            return final_url
    except Exception as e:
        print(f"Bypass error: {e}")
    return None
```

---

## 3️⃣ Dsvplay (Server 9)

### 🔍 المشكلة:
- M3U8 segments مخفية
- JavaScript obfuscation
- Dynamic loading

### ✅ الحل الأفضل: **M3U8 Parser + Network Monitoring**

```python
import re
import m3u8
from curl_cffi.requests import AsyncSession

async def extract_dsvplay_advanced(url: str):
    """Advanced Dsvplay extraction with M3U8 parsing"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": url
    }
    
    async with AsyncSession(impersonate="chrome124", verify=False) as session:
        resp = await session.get(url, headers=headers)
        text = resp.text
        
        # Strategy 1: Find eval() packed code
        eval_match = re.search(r'eval\((.*?)\)', text, re.DOTALL)
        if eval_match:
            try:
                # Unpack JavaScript
                import js2py
                unpacked = js2py.eval_js(f"({eval_match.group(1)})")
                text += str(unpacked)
            except:
                pass
        
        # Strategy 2: Find M3U8 playlist
        m3u8_patterns = [
            r'file:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
            r'source:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
            r'(https?://[^"\'\s]+\.m3u8[^"\'\s]*)'
        ]
        
        for pattern in m3u8_patterns:
            match = re.search(pattern, text)
            if match:
                m3u8_url = match.group(1)
                
                # Parse M3U8 to get best quality
                try:
                    playlist = m3u8.load(m3u8_url)
                    if playlist.playlists:
                        # Get highest bandwidth
                        best = max(playlist.playlists, key=lambda p: p.stream_info.bandwidth)
                        video_url = best.absolute_uri
                    else:
                        video_url = m3u8_url
                    
                    return {
                        "url": video_url,
                        "type": "hls",
                        "headers": {"Referer": url}
                    }
                except:
                    return {
                        "url": m3u8_url,
                        "type": "hls",
                        "headers": {"Referer": url}
                    }
        
        return None
```

---

## 4️⃣ VOE.sx (Server 10)

### 🔍 المشكلة:
- 404 Error (الرابط انتهت صلاحيته)
- التشفير يتغير باستمرار
- Anti-bot protection

### ✅ الحل: **Retry + Fresh URL**

```python
async def extract_voe_with_retry(url: str, max_retries=3):
    """VOE with aggressive retry and fresh URL fetching"""
    
    for attempt in range(max_retries):
        try:
            # Try different domains
            domains = ['voe.sx', 'voe.to', 'voe.cc']
            
            for domain in domains:
                test_url = url.replace('voe.sx', domain)
                
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Referer": test_url,
                    "Accept": "*/*"
                }
                
                async with AsyncSession(impersonate="chrome124", verify=False, timeout=30) as session:
                    resp = await session.get(test_url, headers=headers)
                    
                    if resp.status_code == 200:
                        # Use existing VOE extraction logic
                        from scraper.extractors.voe import VoeExtractor
                        result = await VoeExtractor.extract(test_url)
                        if result:
                            return result
        except:
            await asyncio.sleep(2)
    
    return None
```

**ملاحظة**: إذا كان الرابط 404، يجب الحصول على رابط جديد من Larooza.

---

## 5️⃣ OK.ru (Server 11)

### 🔍 المشكلة:
- JSON metadata معقد
- Multiple quality options
- Requires parsing data-options

### ✅ الحل الأفضل: **yt-dlp**

```python
import subprocess
import json

async def extract_okru_with_ytdlp(url: str):
    """Extract OK.ru using yt-dlp"""
    try:
        cmd = [
            'yt-dlp',
            '--dump-json',
            '--no-warnings',
            '--format', 'best',
            url
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return {
                "url": data.get('url'),
                "type": "mp4",
                "headers": {"Referer": "https://ok.ru/"}
            }
    except Exception as e:
        print(f"yt-dlp OK.ru error: {e}")
    return None
```

### 🔧 الحل البديل: Enhanced JSON Parsing

```python
import re
import json
from html import unescape

async def extract_okru_enhanced(url: str):
    """Enhanced OK.ru extraction"""
    async with AsyncSession(impersonate="chrome124", verify=False, timeout=30) as session:
        resp = await session.get(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://ok.ru/"
        })
        
        text = resp.text
        
        # Try multiple patterns
        patterns = [
            r'data-options="([^"]+)"',
            r'data-module="OKVideo"[^>]*data-options="([^"]+)"',
            r'"videos":\s*(\[.*?\])',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                try:
                    json_str = unescape(match.group(1))
                    data = json.loads(json_str)
                    
                    # Navigate JSON structure
                    if 'flashvars' in data:
                        metadata = data['flashvars'].get('metadata')
                        if isinstance(metadata, str):
                            metadata = json.loads(metadata)
                        
                        videos = metadata.get('videos', [])
                        
                        # Get best quality
                        quality_order = ['1080', '720', '480', '360', '240']
                        for quality in quality_order:
                            for video in videos:
                                if video.get('name') == quality:
                                    return {
                                        "url": video['url'],
                                        "type": "mp4",
                                        "headers": {"Referer": "https://ok.ru/"}
                                    }
                except:
                    continue
        
        return None
```

---

## 📦 المكتبات المطلوبة

```bash
# Install required packages
pip install yt-dlp
pip install selenium
pip install m3u8
pip install js2py
pip install vk-api
pip install webdriver-manager
```

---

## 🎯 خطة التنفيذ

### المرحلة 1: yt-dlp Integration ⭐ (الأولوية)
```bash
# تثبيت yt-dlp
pip install yt-dlp

# استخدامه لـ VK و OK.ru
```

### المرحلة 2: Selenium for Short.icu
```bash
pip install selenium webdriver-manager
```

### المرحلة 3: M3U8 Parser for Dsvplay
```bash
pip install m3u8 js2py
```

### المرحلة 4: VOE Fresh URL Strategy
- إعادة جلب الرابط من Larooza
- تجربة domains مختلفة

---

## 📈 النسبة المتوقعة بعد التحسين

| الحالة | السيرفرات | النسبة |
|--------|-----------|--------|
| **الحالية** | 6/11 | 54.5% |
| **بعد yt-dlp** | 8/11 | 72.7% |
| **بعد Selenium** | 9/11 | 81.8% |
| **بعد M3U8 Parser** | 10/11 | 90.9% |
| **الهدف النهائي** | 11/11 | 100% ✅ |

---

## 🚀 التوصيات

1. **ابدأ بـ yt-dlp** - سيحل VK و OK.ru فوراً (+18%)
2. **أضف Selenium** - لحل Short.icu (+9%)
3. **حسّن M3U8 parsing** - لحل Dsvplay (+9%)
4. **VOE** - يحتاج روابط جديدة من Larooza

**النتيجة النهائية المتوقعة: 90-100% نسبة نجاح! 🎉**
