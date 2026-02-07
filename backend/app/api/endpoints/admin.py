from fastapi import APIRouter, HTTPException, Header, Body
from typing import List, Optional, Dict, Any
from ...core.database import db_manager
from ...core.config import settings
import logging
import time

router = APIRouter(prefix="/admin", tags=["admin"])
logger = logging.getLogger("api.admin")

@router.post("/login")
async def admin_login(payload: Dict[str, str] = Body(...)):
    password = payload.get("password")
    if password == settings.ADMIN_PASSWORD:
        # In a production app, use a JWT token. For now, a simple fixed token.
        return {"status": "success", "token": "admin_master_token_2025"}
    raise HTTPException(status_code=401, detail="كلمة المرور غير صحيحة")

@router.get("/stats")
async def get_stats(authorization: str = Header(None)):
    if authorization != "admin_master_token_2025":
        raise HTTPException(status_code=401, detail="غير مصرح لك")
    
    async with db_manager.get_connection() as db:
        # Get user count
        cursor = await db.execute("SELECT COUNT(*) as count FROM users")
        user_count = (await cursor.fetchone())["count"]
        
        # Get movie count
        cursor = await db.execute("SELECT COUNT(*) as count FROM movies")
        movie_count = (await cursor.fetchone())["count"]
        
        # Get total watch time (in hours)
        cursor = await db.execute("SELECT SUM(watch_time_total) as total FROM users")
        total_seconds = (await cursor.fetchone())["total"] or 0
        total_hours = total_seconds // 3600
        
        # Get fan users count
        cursor = await db.execute("SELECT COUNT(*) as count FROM users WHERE is_fan = 1")
        fan_count = (await cursor.fetchone())["count"]
        
        # Get recent activity (last 10 users)
        cursor = await db.execute("""
            SELECT id, points, watch_time_total, is_fan, created_at 
            FROM users 
            ORDER BY created_at DESC 
            LIMIT 20
        """)
        recent_users = [dict(row) for row in await cursor.fetchall()]

        # Get top watchers
        cursor = await db.execute("""
            SELECT id, watch_time_total, points 
            FROM users 
            ORDER BY watch_time_total DESC 
            LIMIT 5
        """)
        top_watchers = [dict(row) for row in await cursor.fetchall()]
        
        return {
            "stats": {
                "total_users": user_count,
                "total_movies": movie_count,
                "total_watch_hours": total_hours,
                "fan_users": fan_count
            },
            "recent_users": recent_users,
            "top_watchers": top_watchers
        }

@router.post("/users/update_points")
async def update_user_points(payload: Dict[str, Any] = Body(...), authorization: str = Header(None)):
    if authorization != "admin_master_token_2025":
        raise HTTPException(status_code=401, detail="غير مصرح لك")
    
    user_id = payload.get("user_id")
    points = payload.get("points")
    
    async with db_manager.get_connection() as db:
        await db.execute("UPDATE users SET points = ? WHERE id = ?", (points, user_id))
        await db.commit()
    
    return {"status": "success"}

@router.delete("/users/{user_id}")
async def delete_user(user_id: str, authorization: str = Header(None)):
    if authorization != "admin_master_token_2025":
        raise HTTPException(status_code=401, detail="غير مصرح لك")
    
    async with db_manager.get_connection() as db:
        await db.execute("DELETE FROM users WHERE id = ?", (user_id,))
        await db.commit()
    
    return {"status": "success"}
