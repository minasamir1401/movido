from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
import httpx
import logging

router = APIRouter(prefix="/proxy", tags=["proxy"])
logger = logging.getLogger("api.proxy")

@router.get("/image")
async def proxy_image(url: str = Query(...)):
    """
    Proxies images to bypass connection issues or CORS/Referer blocking.
    """
    if not url:
        raise HTTPException(status_code=400, detail="Missing URL")

    try:
        async with httpx.AsyncClient(verify=False, follow_redirects=True, timeout=20.0) as client:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer": "https://asd.pics/" # Use a static ASCII referer
            }
            resp = await client.get(url, headers=headers)
            
            if resp.status_code != 200:
                logger.warning(f"Failed to fetch image: {url} - Status: {resp.status_code}")
                return Response(status_code=404)

            return Response(
                content=resp.content,
                media_type=resp.headers.get("content-type", "image/jpeg")
            )
    except Exception as e:
        logger.error(f"Image proxy error: {e}")
        return Response(status_code=500)
