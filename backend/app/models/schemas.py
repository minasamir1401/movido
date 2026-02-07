from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class MovieBase(BaseModel):
    id: str
    title: str
    poster: str
    type: str
    duration: Optional[str] = ""

class ContentDetails(MovieBase):
    description: Optional[str] = ""
    rating: Optional[str] = "N/A"
    year: Optional[str] = ""
    seasons: List[Any] = []
    episodes: List[Any] = []
    servers: List[Any] = []
    download_links: List[Any] = []
    recommendations: List[Any] = []
    schema_org: Optional[Dict[str, Any]] = Field(None, alias="schema")

class CommentBase(BaseModel):
    user_id: str
    content_id: str
    text: str

class CommentRead(CommentBase):
    id: int
    created_at: str
    is_fan: bool = False
    points: int = 0

class UserStatus(BaseModel):
    id: str
    points: int
    watch_time_total: int
    is_fan: bool
    ad_free_until: int
    referrer_id: Optional[str] = None
    created_at: str

class CourseProgressUpdate(BaseModel):
    user_id: str
    course_id: str
    lesson_id: str
    completed: int = 1
