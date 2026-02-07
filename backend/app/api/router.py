from fastapi import APIRouter
from .endpoints import movies, courses, users, comments, matches, anime, admin, scrapers, admin_scrapers, admin_auth, admin_dashboard, proxy, larooza_extractor

api_router = APIRouter()
api_router.include_router(movies.router)
api_router.include_router(courses.router)
api_router.include_router(users.router)
api_router.include_router(comments.router)
api_router.include_router(proxy.router)
api_router.include_router(matches.router)
api_router.include_router(anime.router)
api_router.include_router(admin.router)
api_router.include_router(scrapers.router)
api_router.include_router(admin_scrapers.router)
api_router.include_router(admin_auth.router)
api_router.include_router(admin_dashboard.router)
api_router.include_router(larooza_extractor.router)
