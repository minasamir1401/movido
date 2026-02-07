from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import StreamingResponse, RedirectResponse, FileResponse
import httpx
import os
import io
import re
import hashlib
import time
from urllib.parse import unquote, quote, urljoin, urlparse
from ...core.config import settings
from scraper.engine import scraper
from scraper.matches import matches_scraper
import logging


def _remove_ads_from_html(html_content):
    # Remove ad-related elements using string replacement
    ad_patterns = [
        '<div class="ad">', '<div class="ads">', '<div class="advertisement">',
        '<div class="promo">', '<div class="overlay">', '<div class="skip">',
        '<div class="sponsor">', '<div id="ad">', '<div id="ads">',
        '<div id="advertisement">', '<div id="promo">', '<div id="overlay">',
        '<div id="skip">', '<div id="sponsor">',
        # Specific ad elements from the example
        '<div id="adbd" class="overdiv">',
        'Disable ADBlock plugin',
        'Upgrade you account',
        'to watch videos with no limits',
        # Ad script patterns
        '<script', '</script>', 'google_ad', 'adsbygoogle', 'adblock',
        # Common ad iframe patterns
        '<iframe', '</iframe>', 'doubleclick', 'googlesyndication',
        # Popup ads
        'popup', 'modal', 'lightbox'
    ]
            
    # Remove ad-related elements
    for pattern in ad_patterns:
        # Case insensitive replacement
        html_content = re.sub(re.escape(pattern), '', html_content, flags=re.IGNORECASE)
            
    return html_content

try:
    from curl_cffi.requests import AsyncSession
    HAS_CURL_CFFI = True
except ImportError:
    HAS_CURL_CFFI = False

router = APIRouter(prefix="/proxy", tags=["proxy"])
logger = logging.getLogger("api.proxy")

# Aggressively unset system proxy variables to prevent 407 errors
for key in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy"]:
    if key in os.environ:
        del os.environ[key]

@router.get("/image")
async def proxy_image(url: str):
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")
    
    url = unquote(url)
    if url.startswith('/'):
        url = urljoin(scraper.BASE_URL, url)
    
    # Image Disk Cache
    cache_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "cache", "images")
    os.makedirs(cache_dir, exist_ok=True)
    
    url_hash = hashlib.md5(url.encode()).hexdigest()
    cache_path = os.path.join(cache_dir, f"{url_hash}.img")
    
    if os.path.exists(cache_path):
        if time.time() - os.path.getmtime(cache_path) < settings.IMAGE_CACHE_TTL:
            return FileResponse(cache_path, media_type="image/jpeg")

    try:
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True, verify=False, trust_env=False) as client:
            parsed_url = urlparse(url)
            headers = {
                "User-Agent": scraper.headers["User-Agent"],
                "Referer": f"{parsed_url.scheme}://{parsed_url.netloc}/"
            }
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                content = resp.content
                with open(cache_path, "wb") as f:
                    f.write(content)
                return StreamingResponse(io.BytesIO(content), media_type=resp.headers.get("Content-Type", "image/jpeg"))
            else:
                return RedirectResponse(url="https://placehold.co/600x400/000000/FFFFFF?text=Image+Error")
    except Exception as e:
        logger.error(f"Image proxy error: {e}")
        raise HTTPException(status_code=500, detail="Proxy error")

@router.get("/stream")
async def proxy_stream(url: str):
    """
    Proxies HLS streams to bypass CORS and Mixed Content issues.
    Rewrites M3U8 playlists to point chunks back to this proxy.
    """
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")
        
    url = unquote(url)
    
    # Check if the URL contains unsafe domains
    unsafe_domains = ['larooza.homes', 'gaza.20', 'bit.ly', 'tinyurl.com', 'adf.ly', 'bc.vc', 'adfoc.us', 'shorte.st', 'ouo.io', 'clicksfly.com']
    for domain in unsafe_domains:
        if domain in url.lower():
            raise HTTPException(status_code=400, detail="Invalid or blocked URL")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "Connection": "keep-alive",
        "Referer": "https://hamottv.rf.gd/",
        "Origin": "https://hamottv.rf.gd"
    }
    
    try:
        is_hamot_stream = any(x in url for x in ["showplustv.pro", "135.125.109.73", "31.57.111.12"])
        
        target_url = url
        request_headers = headers.copy()
        
        if is_hamot_stream:
             target_url = f"https://hamottv.rf.gd/?google_stream={quote(url)}"
             cookies = await matches_scraper.get_cookies()
             if not cookies:
                 cookies = await matches_scraper.get_cookies(force_refresh=True)
             request_headers["Cookie"] = "; ".join([f"{k}={v}" for k,v in cookies.items()])
             request_headers["Referer"] = "https://hamottv.rf.gd/"
        
        async with httpx.AsyncClient(timeout=15.0, verify=False, follow_redirects=True, trust_env=False) as client:
            resp = await client.get(target_url, headers=request_headers)
            
            if is_hamot_stream and (resp.status_code == 503 or "<script" in resp.text[:500]):
                 cookies = await matches_scraper.get_cookies(force_refresh=True)
                 request_headers["Cookie"] = "; ".join([f"{k}={v}" for k,v in cookies.items()])
                 resp = await client.get(target_url, headers=request_headers)

            if resp.status_code != 200:
                if not is_hamot_stream and resp.status_code in [401, 403, 404, 407]:
                    request_headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                    resp = await client.get(target_url, headers=request_headers)
                
                if resp.status_code != 200:
                    return Response(status_code=resp.status_code)
                
            content_type = resp.headers.get("content-type", "").lower()
            
            if "mpegurl" in content_type or url.endswith(".m3u8") or "#EXTM3U" in resp.text[:20]:
                content = resp.text
                base_url = str(resp.url).rsplit('/', 1)[0]
                
                new_content = []
                for line in content.splitlines():
                    if line.strip().startswith("#"):
                        new_content.append(line)
                    elif line.strip():
                        chunk_url = line.strip()
                        if not chunk_url.startswith("http"):
                            chunk_url = f"{base_url}/{chunk_url}"
                        encoded_chunk_url = quote(chunk_url)
                        new_line = f"/api/proxy/stream?url={encoded_chunk_url}"
                        new_content.append(new_line)
                    else:
                        new_content.append(line)
                        
                return Response(content="\n".join(new_content), media_type="application/vnd.apple.mpegurl")
            else:
                 return Response(content=resp.content, media_type=content_type)

    except Exception as e:
        logger.error(f"Stream proxy error: {e}")
        return Response(status_code=500)

@router.get("/download/info")
async def get_download_info(url: str):
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")
    try:
        from downloader import downloader
        info = await downloader.get_info(url)
        if not info or "error" in info:
            raise HTTPException(status_code=400, detail="Failed to fetch info")
        
        result = {
            "title": info.get("title", "Unknown"),
            "thumbnail": info.get("thumbnail", ""),
            "duration": info.get("duration", 0),
            "uploader": info.get("uploader", "Unknown"),
            "view_count": info.get("view_count", 0),
            "formats": []
        }
        
        if "formats" in info:
            for fmt in info["formats"]:
                url_val = fmt.get("url")
                if not url_val: continue
                result["formats"].append({
                    "format_id": fmt.get("format_id", ""),
                    "ext": fmt.get("ext", "mp4"),
                    "quality": fmt.get("format_note") or fmt.get("resolution") or "unknown",
                    "filesize": fmt.get("filesize") or fmt.get("filesize_approx") or 0,
                    "url": url_val,
                    "has_audio": fmt.get("acodec", "none") != "none",
                    "has_video": fmt.get("vcodec", "none") != "none",
                })
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/download")
async def download_file(url: str, filename: str = "video.mp4"):
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")
    url = unquote(url)
    ascii_filename = re.sub(r'[^\x00-\x7F]+', '_', filename)
    encoded_filename = quote(filename)
    
    async def stream_generator():
        async with httpx.AsyncClient(timeout=None, follow_redirects=True) as client:
            async with client.stream("GET", url, headers={"User-Agent": scraper.headers["User-Agent"]}) as resp:
                if resp.status_code == 200:
                    async for chunk in resp.aiter_bytes(chunk_size=1024*1024):
                        yield chunk

    headers = {
        "Content-Disposition": f"attachment; filename=\"{ascii_filename}\"; filename*=UTF-8''{encoded_filename}",
        "Access-Control-Expose-Headers": "Content-Disposition"
    }
    return StreamingResponse(stream_generator(), media_type="video/mp4", headers=headers)

@router.get("/player")
async def proxy_player(url: str):
    """
    Proxies a player HTML page to bypass X-Frame-Options and CSP.
    No extra protection layers (Stealth/Adblock) as requested.
    """
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")
            
    url = unquote(url)
        
    # Check if the URL contains unsafe domains
    unsafe_domains = ['larooza.homes', 'gaza.20', 'bit.ly', 'tinyurl.com', 'adf.ly', 'bc.vc', 'adfoc.us', 'shorte.st', 'ouo.io', 'clicksfly.com']
    for domain in unsafe_domains:
        if domain in url.lower():
            raise HTTPException(status_code=400, detail="Invalid or blocked URL")
        
    # Check for other potentially problematic patterns
    if 'larooza' in url.lower() or 'gaza.20' in url.lower():
        raise HTTPException(status_code=400, detail="Invalid or blocked URL")
        
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
    }
    
    try:
        if HAS_CURL_CFFI:
            async with AsyncSession(impersonate="chrome120", verify=False) as session:
                resp = await session.get(url, headers=headers, timeout=15.0)
                status_code = resp.status_code
                text = resp.text
                resp_headers = resp.headers
        else:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True, verify=False, trust_env=False) as client:
                resp = await client.get(url, headers=headers)
                status_code = resp.status_code
                text = resp.text
                resp_headers = resp.headers
            
        if status_code != 200:
            return Response(content=f"Error: {status_code}", status_code=status_code)
        
        def _remove_ads_from_html(html_content):
            # Remove ad-related elements using string replacement
            ad_patterns = [
                '<div class="ad">', '<div class="ads">', '<div class="advertisement">',
                '<div class="promo">', '<div class="overlay">', '<div class="skip">',
                '<div class="sponsor">', '<div id="ad">', '<div id="ads">',
                '<div id="advertisement">', '<div id="promo">', '<div id="overlay">',
                '<div id="skip">', '<div id="sponsor">',
                # Ad script patterns
                '<script', '</script>', 'google_ad', 'adsbygoogle', 'adblock',
                # Common ad iframe patterns
                '<iframe', '</iframe>', 'doubleclick', 'googlesyndication',
                # Popup ads
                'popup', 'modal', 'lightbox'
            ]
                    
            # Remove ad-related elements
            for pattern in ad_patterns:
                # Case insensitive replacement
                import re
                html_content = re.sub(re.escape(pattern), '', html_content, flags=re.IGNORECASE)
                    
            return html_content
                
        content = text
        base_url = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
                
        # Remove ad-related elements
        content = _remove_ads_from_html(content)
                
        # Essential Relative Path Rewriting
        content = content.replace('src="/', f'src="{base_url}/')
        content = content.replace('href="/', f'href="{base_url}/')
        
        response_headers = {
            "Content-Type": resp_headers.get("Content-Type", "text/html"),
            "Access-Control-Allow-Origin": "*",
            "X-Frame-Options": "ALLOWALL",
            "Content-Security-Policy": "frame-ancestors *",
        }
        
        excluded_headers = ["x-frame-options", "content-security-policy", "set-cookie", "report-to", "nel", "content-length", "content-encoding"]
        for k, v in resp_headers.items():
            if k.lower() not in excluded_headers:
                response_headers[k] = v
        
        return Response(content=content, headers=response_headers)
            
    except Exception as e:
        logger.error(f"Player proxy error: {e}")
        return Response(content=f"Proxy Error: {str(e)}", status_code=500)
