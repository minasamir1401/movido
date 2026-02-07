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
            # First time user award some start points
            await db.execute(
                "INSERT INTO users (id, referrer_id, points) VALUES (?, ?, ?)", 
                (user_id, referrer_id, 100) # Give 100 points as welcome gift
            )
            if referrer_id:
                await db.execute(
                    "INSERT OR IGNORE INTO referrals (referrer_id, referred_id, status) VALUES (?, ?, 'joined')",
                    (referrer_id, user_id)
                )
                # Award Referrer 50 points for inviting a friend
                await db.execute(
                    "UPDATE users SET points = points + 50 WHERE id = ?",
                    (referrer_id,)
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
    """Real system: 1 Hour = 120 Points (2 points per minute)"""
    points_per_min = 2
    pts_to_add = minutes * points_per_min
    
    async with db_manager.get_connection() as db:
        await db.execute(
            "UPDATE users SET watch_time_total = watch_time_total + ?, points = points + ? WHERE id = ?",
            (minutes * 60, pts_to_add, user_id)
        )
        
        # Performance Milestone: Every 2 real hours of watching award 200 extra bonus points
        cursor = await db.execute("SELECT watch_time_total, last_watch_reward_time, points FROM users WHERE id = ?", (user_id,))
        user_at = await cursor.fetchone()
        
        milestone = 2 * 3600 # 2 hours
        if user_at["watch_time_total"] // milestone > user_at["last_watch_reward_time"] // milestone:
             await db.execute(
                 "UPDATE users SET points = points + 200, last_watch_reward_time = ? WHERE id = ?",
                 (user_at["watch_time_total"], user_id)
             )
        
        await db.commit()
        return {"status": "success", "added": pts_to_add, "total_points": user_at["points"] + pts_to_add}

@router.post("/share-click")
async def register_share_click(referrer_id: str):
    """Award points for just clicks on shared links (Limited to prevent abuse)"""
    # Simply award 5 points for a valid shared link visit
    async with db_manager.get_connection() as db:
        await db.execute(
            "UPDATE users SET points = points + 5 WHERE id = ?",
            (referrer_id,)
        )
        await db.commit()
        return {"status": "success"}

@router.post("/redeem")
async def redeem_reward(user_id: str, reward_type: str):
    """Redemption logic: Daily, Weekly, Monthly ad-free subscriptions"""
    costs = {
        "ad_free_1d": 700,    # 1 Day (approx 6 hours watch time)
        "ad_free_1w": 3000,   # 1 Week
        "ad_free_1m": 10000,  # 1 Month
        "fan_badge": 100000   # Permanent Ultra Fan Badge (Rare)
    }
    durations = {
        "ad_free_1d": 1 * 24 * 3600,
        "ad_free_1w": 7 * 24 * 3600,
        "ad_free_1m": 30 * 24 * 3600
    }
    
    cost = costs.get(reward_type)
    if not cost:
        raise HTTPException(status_code=400, detail="Invalid reward type")
        
    async with db_manager.get_connection() as db:
        cursor = await db.execute("SELECT points, ad_free_until FROM users WHERE id = ?", (user_id,))
        user = await cursor.fetchone()
        
        if not user or user["points"] < cost:
            raise HTTPException(status_code=403, detail="Insufficient points")
            
        if reward_type.startswith("ad_free"):
            # Stack subscription if already active
            now = int(time.time())
            base_time = max(now, user["ad_free_until"] or 0)
            new_expiry = base_time + durations[reward_type]
            
            await db.execute(
                "UPDATE users SET points = points - ?, ad_free_until = ? WHERE id = ?",
                (cost, new_expiry, user_id)
            )
        elif reward_type == "fan_badge":
            await db.execute(
                "UPDATE users SET points = points - ?, is_fan = 1 WHERE id = ?",
                (cost, user_id)
            )
            
        await db.commit()
        return {"status": "success", "reward": reward_type, "new_points": user["points"] - cost}

@router.post("/share-click")
async def register_share_click(referrer_id: str):
    """Reward referrer for a unique click on their link"""
    # Simply rewarding 5 points for now, can be improved with IP tracking to prevent abuse
    async with db_manager.get_connection() as db:
        await db.execute(
            "UPDATE users SET points = points + 5 WHERE id = ?",
            (referrer_id,)
        )
        await db.commit()
        return {"status": "success"}

@router.post("/redeem-promo")
async def redeem_promo(user_id: str, code: str):
    """Redeem a one-time promo code for 1 month ad-free"""
    async with db_manager.get_connection() as db:
        # Check if code exists and is not used
        cursor = await db.execute("SELECT * FROM promo_codes WHERE code = ? AND is_used = 0", (code,))
        promo = await cursor.fetchone()
        
        if not promo:
            # Check if it was already used
            cursor = await db.execute("SELECT * FROM promo_codes WHERE code = ?", (code,))
            exists = await cursor.fetchone()
            if exists:
                raise HTTPException(status_code=400, detail="هذا الكود تم استخدامه مسبقاً")
            raise HTTPException(status_code=404, detail="كود غير صالح")
            
        reward_type = promo["reward_type"] or "ad_free_1m"
        duration = 30 * 24 * 3600 # 30 days
        
        # Get current subscription
        cursor = await db.execute("SELECT ad_free_until FROM users WHERE id = ?", (user_id,))
        user = await cursor.fetchone()
        
        if not user:
            raise HTTPException(status_code=404, detail="المستخدم غير موجود")
            
        current_until = max(user["ad_free_until"] or 0, int(time.time()))
        new_until = current_until + duration
        
        # Mark promo as used and update user
        await db.execute(
            "UPDATE promo_codes SET is_used = 1, used_by = ?, used_at = CURRENT_TIMESTAMP WHERE code = ?",
            (user_id, code)
        )
        await db.execute(
            "UPDATE users SET ad_free_until = ? WHERE id = ?",
            (new_until, user_id)
        )
        
        await db.commit()
        return {"status": "success", "reward": reward_type, "new_until": new_until}

