from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import uuid
from ...models.schemas import UserStatus
from ...core.database import db_manager
import logging
import time

router = APIRouter(prefix="/user", tags=["users"])
logger = logging.getLogger("api.users")

@router.post("/init", response_model=UserStatus)
async def init_user(user_id: Optional[str] = None, referrer_id: Optional[str] = None):
    async with db_manager.get_connection() as db:
        if not user_id:
            user_id = str(uuid.uuid4())
        
        # Check if user exists
        cursor = await db.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user = await cursor.fetchone()
        
        if not user:
            await db.execute(
                "INSERT INTO users (id, referrer_id) VALUES (?, ?)", 
                (user_id, referrer_id)
            )
            if referrer_id:
                await db.execute(
                    "INSERT OR IGNORE INTO referrals (referrer_id, referred_id) VALUES (?, ?)",
                    (referrer_id, user_id)
                )
            await db.commit()
            cursor = await db.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            user = await cursor.fetchone()
            
        return dict(user)

@router.get("/status/{user_id}", response_model=UserStatus)
async def get_user_status(user_id: str):
    async with db_manager.get_connection() as db:
        cursor = await db.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user = await cursor.fetchone()
        if not user:
            return await init_user(user_id)
        return dict(user)

@router.post("/watch")
async def track_watch(user_id: str, minutes: int = 5):
    async with db_manager.get_connection() as db:
        await db.execute(
            "UPDATE users SET watch_time_total = watch_time_total + ?, points = points + ? WHERE id = ?",
            (minutes * 60, minutes, user_id)
        )
        
        cursor = await db.execute("SELECT watch_time_total, last_watch_reward_time, points FROM users WHERE id = ?", (user_id,))
        user_at = await cursor.fetchone()
        
        milestone = 4 * 3600
        if user_at["watch_time_total"] // milestone > user_at["last_watch_reward_time"] // milestone:
             await db.execute(
                 "UPDATE users SET points = points + 100, last_watch_reward_time = ? WHERE id = ?",
                 (user_at["watch_time_total"], user_id)
             )
        
        await db.commit()
        return {"status": "success", "new_points": user_at["points"] + minutes}

@router.post("/redeem")
async def redeem_reward(user_id: str, reward_type: str):
    costs = {"ad_free": 500, "fan_badge": 1000}
    cost = costs.get(reward_type)
    
    if not cost:
        raise HTTPException(status_code=400, detail="Invalid reward type")
        
    async with db_manager.get_connection() as db:
        cursor = await db.execute("SELECT points FROM users WHERE id = ?", (user_id,))
        user = await cursor.fetchone()
        
        if not user or user["points"] < cost:
            raise HTTPException(status_code=403, detail="Insufficient points")
            
        if reward_type == "ad_free":
            ad_free_until = int(time.time()) + (24 * 3600)
            await db.execute(
                "UPDATE users SET points = points - ?, ad_free_until = ? WHERE id = ?",
                (cost, ad_free_until, user_id)
            )
        elif reward_type == "fan_badge":
            await db.execute(
                "UPDATE users SET points = points - ?, is_fan = 1 WHERE id = ?",
                (cost, user_id)
            )
            
        await db.commit()
        return {"status": "success", "reward": reward_type}
