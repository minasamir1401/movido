from fastapi import APIRouter, HTTPException, Query
from typing import List
from ...models.schemas import CommentRead
from ...core.database import db_manager
import logging

router = APIRouter(prefix="/comments", tags=["comments"])
logger = logging.getLogger("api.comments")

@router.post("")
async def post_comment(user_id: str, content_id: str, text: str):
    if not text.strip():
        raise HTTPException(status_code=400, detail="Comment text cannot be empty")
    
    async with db_manager.get_connection() as db:
        await db.execute(
            "INSERT INTO comments (user_id, content_id, text) VALUES (?, ?, ?)",
            (user_id, content_id, text)
        )
        # Reward user
        await db.execute("UPDATE users SET points = points + 10 WHERE id = ?", (user_id,))
        await db.commit()
        return {"status": "success"}

@router.get("/{content_id}", response_model=List[CommentRead])
async def get_comments(content_id: str):
    async with db_manager.get_connection() as db:
        cursor = await db.execute("""
            SELECT c.*, COALESCE(u.is_fan, 0) as is_fan, COALESCE(u.points, 0) as points 
            FROM comments c 
            LEFT JOIN users u ON c.user_id = u.id 
            WHERE c.content_id = ? 
            ORDER BY c.created_at DESC
        """, (content_id,))
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
