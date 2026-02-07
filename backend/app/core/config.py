from pydantic_settings import BaseSettings
from typing import Optional, List
import os

class Settings(BaseSettings):
    VERSION: str = "2.1.0-nitro"
    APP_TITLE: str = "MOVIDO Movies API"
    
    # Environment
    IS_HF: bool = os.environ.get("SPACE_ID") is not None or os.environ.get("HF_SPACE") is not None
    IS_RENDER: bool = os.environ.get("RENDER") is not None
    
    # Database
    DATABASE_NAME: str = "/tmp/netflix_clone.db" if IS_HF else "netflix_clone.db"
    
    # Cache
    CACHE_TTL: int = 43200  # 12 hours
    IMAGE_CACHE_TTL: int = 604800  # 1 week
    
    # Proxies
    PROXY_LIST: List[str] = [p.strip() for p in os.getenv("PROXY_LIST", "").split(",") if p.strip()]
    
    # Security
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "admin123")
    
    # Integrations
    TELEGRAM_BOT_TOKEN: Optional[str] = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHANNEL_ID: Optional[str] = os.getenv("TELEGRAM_CHANNEL_ID")
    
    class Config:
        env_file = ".env"

settings = Settings()
