from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
import os
import asyncio
import logging
from datetime import datetime
from contextlib import asynccontextmanager

from .core.config import settings
from .core.database import db_manager
from .api.router import api_router
from .services.worker import auto_broadcaster, warm_up_services, background_cache_refresher

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    try:
        logger.info("Initializing Database...")
        await db_manager.init_db()
        logger.info("Database initialized successfully")
        
        # Start background tasks
        asyncio.create_task(auto_broadcaster())
        asyncio.create_task(warm_up_services())
        asyncio.create_task(background_cache_refresher())
        
        logger.info("Application started successfully")
    except Exception as e:
        logger.critical(f"CRITICAL STARTUP ERROR: {e}")
        # We don't exit here to allow debugging, but log critical error
    
    yield
    # Shutdown logic
    logger.info("Application shutting down")

app = FastAPI(
    title=settings.APP_TITLE,
    version=settings.VERSION,
    lifespan=lifespan
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global Exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error", "error": str(exc)},
    )

# Middleware configuration
# We remove GZipMiddleware as it can cause ERR_EMPTY_RESPONSE when proxying video streams
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition", "Content-Length", "X-Request-ID"]
)
# app.add_middleware(GZipMiddleware, minimum_size=1000) # Disabled for stream stability

@app.middleware("http")
async def enterprise_logging_middleware(request: Request, call_next):
    import time
    import uuid
    request_id = str(uuid.uuid4())
    start_time = time.time()
    
    # Enrich logger context if using structured logging (skipped for now for simplicity)
    
    try:
        response = await call_next(request)
        duration = time.time() - start_time
        logger.info(f"[{request_id}] {request.method} {request.url.path} - {response.status_code} ({duration:.2f}s)")
        response.headers["X-Request-ID"] = request_id
        return response
    except Exception as e:
        logger.error(f"[{request_id}] Request Failed: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": "Something went wrong. Please contact support.", "request_id": request_id}
        )

# Routes
@app.get("/health")
async def health():
    return {"status": "ok", "version": settings.VERSION}

app.include_router(api_router)

from downloader import downloader

@app.get("/downloader")
async def get_download_info(url: str):
    return await downloader.get_info(url)

@app.get("/robots.txt")
async def robots():
    content = """User-agent: *
Allow: /
Allow: /search
Allow: /watch/
Allow: /category/
Allow: /courses/
Allow: /downloader

# Sitemaps
Sitemap: https://movido.com/sitemap.xml

# AI Crawler optimization
User-agent: GPTBot
Disallow: /admin
Disallow: /api/
Allow: /

User-agent: ChatGPT-User
Disallow: /admin
Disallow: /api/
Allow: /

User-agent: Google-Extended
Allow: /
"""
    return Response(content=content, media_type="text/plain")

@app.get("/sitemap.xml")
async def sitemap():
    from scraper.engine import scraper
    
    base_url = "https://movido.com"
    pages = ["/", "/downloader", "/courses", "/search"]
    
    # Add major categories
    categories = [
        "ramadan-2025", "english-movies", "arabic-movies", 
        "arabic-series", "turkish-series", "anime-movies"
    ]
    for cat in categories:
        pages.append(f"/category/{cat}")
        
    # Add latest items (fetch first page of home)


    xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml_content += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    for page in pages:
        xml_content += f"  <url>\n"
        xml_content += f"    <loc>{base_url}{page}</loc>\n"
        xml_content += f"    <lastmod>{current_date}</lastmod>\n"
        xml_content += f"    <changefreq>daily</changefreq>\n"
        xml_content += f"    <priority>{'1.0' if page == '/' else '0.8' if '/watch/' in page else '0.6'}</priority>\n"
        xml_content += f"  </url>\n"
        
    xml_content += "</urlset>"
    return Response(content=xml_content, media_type="application/xml")

# Frontend Serving
base_dir = os.path.dirname(os.path.abspath(__file__))
frontend_path = os.path.join(base_dir, "..", "..", "meih-netflix-clone", "dist")

if os.path.exists(frontend_path):
    assets_path = os.path.join(frontend_path, "assets")
    if os.path.exists(assets_path):
        app.mount("/assets", StaticFiles(directory=assets_path), name="assets")
    
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        if full_path.startswith(("api/", "health")):
            return JSONResponse(status_code=404, detail="Not Found")
        
        file_path = os.path.join(frontend_path, full_path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(frontend_path, "index.html"))

import asyncio
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
