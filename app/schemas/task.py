from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel
from enum import Enum

class TaskType(str, Enum):
    AUDIO_EXTRACTION = "audio_extraction"
    SUBTITLE_GENERATION = "subtitle_generation"
    TRANSLATION = "translation"
    PHONETIC = "phonetic"
    GRAMMAR_ANALYSIS = "grammar_analysis"

class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class TaskResponse(BaseModel):
    id: int
    video_id: int
    video_title: Optional[str] = None
    task_type: TaskType
    status: TaskStatus
    progress: int
    error_message: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class TaskListResponse(BaseModel):
    total: int
    items: List[TaskResponse]
    page: int
    size: int
