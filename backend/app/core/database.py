import aiosqlite
from .config import settings
from contextlib import asynccontextmanager
import logging

logger = logging.getLogger("database")

class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path

    @asynccontextmanager
    async def get_connection(self):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            try:
                yield db
            except Exception as e:
                logger.error(f"Database connection error: {e}")
                raise e

    async def execute_write(self, query: str, params: tuple = ()) -> int:
        """Executes a write operation (INSERT, UPDATE, DELETE) with safety mechanisms."""
        async with self.get_connection() as db:
            try:
                cursor = await db.execute(query, params)
                await db.commit()
                return cursor.lastrowid
            except Exception as e:
                await db.rollback()
                logger.error(f"Database write error: {e} | Query: {query}")
                raise e

    async def fetch_one(self, query: str, params: tuple = ()):
        """Safely fetches a single row."""
        async with self.get_connection() as db:
            try:
                async with db.execute(query, params) as cursor:
                    return await cursor.fetchone()
            except Exception as e:
                logger.error(f"Database fetch_one error: {e} | Query: {query}")
                return None

    async def fetch_all(self, query: str, params: tuple = ()):
        """Safely fetches all rows."""
        async with self.get_connection() as db:
            try:
                async with db.execute(query, params) as cursor:
                    return await cursor.fetchall()
            except Exception as e:
                logger.error(f"Database fetch_all error: {e} | Query: {query}")
                return []

    async def init_db(self):
        async with self.get_connection() as db:
            # Reusing the existing schema logic but organized
            schema = [
                """CREATE TABLE IF NOT EXISTS movies (
                    id TEXT PRIMARY KEY, title TEXT, poster TEXT, year TEXT, 
                    rating TEXT, description TEXT, category TEXT
                )""",
                """CREATE TABLE IF NOT EXISTS series (
                    id TEXT PRIMARY KEY, title TEXT, poster TEXT, year TEXT, 
                    rating TEXT, description TEXT, category TEXT
                )""",
                """CREATE TABLE IF NOT EXISTS episodes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, series_id TEXT, 
                    episode_number INTEGER, title TEXT, watch_link TEXT,
                    FOREIGN KEY(series_id) REFERENCES series(id)
                )""",
                """CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY, points INTEGER DEFAULT 0, 
                    watch_time_total INTEGER DEFAULT 0, last_watch_reward_time INTEGER DEFAULT 0,
                    is_fan INTEGER DEFAULT 0, ad_free_until INTEGER DEFAULT 0,
                    referrer_id TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )""",
                """CREATE TABLE IF NOT EXISTS referrals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, referrer_id TEXT, referred_id TEXT,
                    status TEXT DEFAULT 'pending', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(referrer_id, referred_id)
                )""",
                """CREATE TABLE IF NOT EXISTS comments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, content_id TEXT, user_id TEXT,
                    text TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                )""",
                """CREATE TABLE IF NOT EXISTS course_progress (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, course_id TEXT,
                    lesson_id TEXT, completed INTEGER DEFAULT 0, last_position INTEGER DEFAULT 0,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, course_id, lesson_id),
                    FOREIGN KEY(user_id) REFERENCES users(id)
                )""",
                "CREATE INDEX IF NOT EXISTS idx_users_referrer ON users(referrer_id)",
                "CREATE INDEX IF NOT EXISTS idx_referrals_referrer ON referrals(referrer_id)",
                "CREATE INDEX IF NOT EXISTS idx_comments_content ON comments(content_id)",
                "CREATE INDEX IF NOT EXISTS idx_course_progress_user ON course_progress(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_course_progress_course ON course_progress(course_id)"
            ]
            for statement in schema:
                await db.execute(statement)
            await db.commit()
            logger.info("Database initialized successfully")

db_manager = Database(settings.DATABASE_NAME)
