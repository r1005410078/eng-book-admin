from datetime import datetime
from typing import List, Optional, Any
from pydantic import BaseModel, HttpUrl, Field

class LessonDetailContent(BaseModel):
    id: int
    title: str
    video_url: Optional[str]
    subtitles: List[dict] # Simplified for now, should be separate Pydantic model
    grammar_points: List[dict] # Simplified
    materials: List[dict] = []
    
class UserLessonProgress(BaseModel):
    status: str
    last_position: int
    completed_at: Optional[datetime]
    is_locked: bool
