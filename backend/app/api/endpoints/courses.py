from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional
from ...models.schemas import CourseProgressUpdate
from ...core.cache import api_cache
from ...core.database import db_manager
from scraper.courses import courses_scraper
import logging

router = APIRouter(prefix="/courses", tags=["courses"])
logger = logging.getLogger("api.courses")

@router.get("/latest")
async def get_latest_courses(page: int = 1):
    cache_key = f"courses_latest_{page}"
    cached = await api_cache.get(cache_key)
    if cached: return cached
    
    try:
        items = await courses_scraper.fetch_latest_courses(page=page)
        if items: await api_cache.set(cache_key, items)
        return items
    except Exception as e:
        logger.error(f"Error fetching latest courses: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch latest courses")

@router.get("/category/{cat_id}")
async def get_category_courses(cat_id: str, page: int = 1):
    cache_key = f"courses_cat_{cat_id}_{page}"
    cached = await api_cache.get(cache_key)
    if cached: return cached
    
    try:
        items = await courses_scraper.fetch_category_courses(cat_id, page=page)
        if items: await api_cache.set(cache_key, items)
        return items
    except Exception as e:
        logger.error(f"Error fetching course category {cat_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch course category {cat_id}")

@router.get("/details/{safe_id}")
async def get_course_details(safe_id: str, user_id: Optional[str] = None):
    cache_key = f"course_details_{safe_id}"
    details = await api_cache.get(cache_key)
    
    if not details:
        try:
            details = await courses_scraper.fetch_course_details(safe_id)
            if not details:
                raise HTTPException(status_code=404, detail="Course not found")
            await api_cache.set(cache_key, details, ttl_seconds=86400)
        except HTTPException: raise
        except Exception as e:
            logger.error(f"Error fetching course details for {safe_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to fetch course details")

    if user_id and details:
        async with db_manager.get_connection() as db:
            cursor = await db.execute(
                "SELECT lesson_id, completed FROM course_progress WHERE user_id = ? AND course_id = ?",
                (user_id, safe_id)
            )
            rows = await cursor.fetchall()
            completed_map = {row['lesson_id']: row['completed'] for row in rows}
            
            total_completed = 0
            for lesson in details.get('lessons', []):
                lesson['completed'] = completed_map.get(lesson['id'], 0) == 1
                if lesson['completed']: total_completed += 1
            
            total_lessons = len(details.get('lessons', []))
            details['progress_percentage'] = (total_completed / total_lessons * 100) if total_lessons > 0 else 0
            details['completed_count'] = total_completed

    return details

@router.post("/progress")
async def update_course_progress(data: CourseProgressUpdate):
    async with db_manager.get_connection() as db:
        await db.execute("""
            INSERT INTO course_progress (user_id, course_id, lesson_id, completed)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, course_id, lesson_id) 
            DO UPDATE SET completed = excluded.completed, updated_at = CURRENT_TIMESTAMP
        """, (data.user_id, data.course_id, data.lesson_id, data.completed))
        
        if data.completed == 1:
            await db.execute("UPDATE users SET points = points + 5 WHERE id = ?", (data.user_id,))
            
        await db.commit()
        return {"status": "success"}

@router.get("/lesson/{lesson_id}")
async def get_lesson_video(lesson_id: str):
    cache_key = f"lesson_video_{lesson_id}"
    cached = await api_cache.get(cache_key)
    if cached: return {"video_url": cached}
    
    try:
        video_url = await courses_scraper.fetch_lesson_video(lesson_id)
        if video_url:
            await api_cache.set(cache_key, video_url)
            return {"video_url": video_url}
        raise HTTPException(status_code=404, detail="Video not found")
    except Exception as e:
        logger.error(f"Error fetching lesson video {lesson_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch lesson video")
