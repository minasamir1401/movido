
from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List
from ...core.admin_auth import get_current_admin
from ...core.database import db_manager
from ...core.cache import api_cache
import os
import psutil
import time
from datetime import datetime
import logging

router = APIRouter(prefix="/admin/dashboard", tags=["admin-dashboard"])
logger = logging.getLogger("api.admin.dashboard")

@router.get("/stats/overview")
async def get_overview_stats(current_admin: str = Depends(get_current_admin)):
    """
    Get general overview statistics for the dashboard.
    """
    try:
        stats = {
            "users": {"total": 0, "active_today": 0, "total_points": 0},
            "content": {"comments": 0, "courses": 0},
            "system": {"cache_size": 0, "uptime": 0}
        }
        
        async with db_manager.get_connection() as db:
            # Users Stats
            cursor = await db.execute("SELECT COUNT(*), SUM(points) FROM users")
            user_res = await cursor.fetchone()
            if user_res:
                stats["users"]["total"] = user_res[0] or 0
                stats["users"]["total_points"] = user_res[1] or 0
            
            # Comments Stats (assuming comments table exists, handle if not)
            try:
                cursor = await db.execute("SELECT COUNT(*) FROM comments")
                comment_res = await cursor.fetchone()
                if comment_res:
                    stats["content"]["comments"] = comment_res[0]
            except Exception:
                stats["content"]["comments"] = 0 # Table might not exist yet

             # Courses Stats (assuming courses table exists)
            try:
                cursor = await db.execute("SELECT COUNT(*) FROM courses")
                course_res = await cursor.fetchone()
                if course_res:
                    stats["content"]["courses"] = course_res[0]
            except Exception:
                stats["content"]["courses"] = 0 

        # System Stats
        process = psutil.Process(os.getpid())
        stats["system"]["uptime"] = int(time.time() - process.create_time())
        stats["system"]["cache_keys"] = len(api_cache.cache) if hasattr(api_cache, 'cache') else 0
        
        return {
            "success": True,
            "data": stats
        }
        
    except Exception as e:
        logger.error(f"Error fetching dashboard stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/users/list")
async def get_users_list(limit: int = 50, offset: int = 0, current_admin: str = Depends(get_current_admin)):
    """Get paginated list of users"""
    try:
        async with db_manager.get_connection() as db:
            cursor = await db.execute(
                "SELECT id, points, watch_time_total, is_fan, created_at FROM users ORDER BY points DESC LIMIT ? OFFSET ?", 
                (limit, offset)
            )
            users = await cursor.fetchall()
            return {
                "success": True,
                "users": [dict(u) for u in users]
            }
    except Exception as e:
         logger.error(f"Error fetching users: {e}")
         raise HTTPException(status_code=500, detail=str(e))

@router.get("/system/logs")
async def get_system_logs(lines: int = 20, current_admin: str = Depends(get_current_admin)):
    """Get last N lines of system logs (simulated or real if file exists)"""
    # This is a placeholder as we might not have direct file access to logs in this setup
    # But we can return some recent events stored in memory if we had them
    return {
        "success": True,
        "logs": ["System logs not fully implemented in file mode yet."] 
    }
