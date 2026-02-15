from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class ProgressUpdate(BaseModel):
    status: str = Field(..., description="ACTIVE, COMPLETED, SKIPPED, LOCKED")
    progress_percent: int = Field(..., ge=0, le=100)
    last_position_seconds: int = Field(0, ge=0)
    
class LearningStatusResponse(BaseModel):
    course_id: int
    total_lessons: int
    completed_lessons: int
    progress_percent_total: int
    last_accessed_lesson_id: Optional[int]
    is_completed: bool
