from fastapi import APIRouter
from .endpoints import movies, courses, users, comments, proxy, matches, anime

api_router = APIRouter()
api_router.include_router(movies.router)
api_router.include_router(courses.router)
api_router.include_router(users.router)
api_router.include_router(comments.router)
api_router.include_router(proxy.router)
api_router.include_router(matches.router)
api_router.include_router(anime.router)
