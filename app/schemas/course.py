from datetime import datetime
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, HttpUrl, Field

# --- Shared Properties ---

class CourseBase(BaseModel):
    title: str = Field(..., max_length=255)
    description: Optional[str] = None
    level: Optional[str] = None
    tags: Optional[List[str]] = []
    cover_image: Optional[str] = None

class UnitBase(BaseModel):
    title: str = Field(..., max_length=255)
    description: Optional[str] = None
    order_index: int = 0

class LessonBase(BaseModel):
    title: str = Field(..., max_length=255)
    description: Optional[str] = None
    order_index: int = 0
    # processing_status is managed by system

# --- Create Schemas ---

class CourseCreate(CourseBase):
    pass

class UnitCreate(UnitBase):
    course_id: int

class LessonCreate(LessonBase):
    unit_id: int
    video_id: Optional[int] = None # Can be linked later or created with video upload

# --- Update Schemas ---

class CourseUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    level: Optional[str] = None
    tags: Optional[List[str]] = None
    cover_image: Optional[str] = None

class UnitUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    order_index: Optional[int] = None

class LessonUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    order_index: Optional[int] = None
    processing_status: Optional[str] = None # Admin force update?

# --- Response Schemas ---

class LessonResponse(LessonBase):
    id: int
    unit_id: int
    video_id: Optional[int]
    processing_status: str
    progress_percent: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class UnitResponse(UnitBase):
    id: int
    course_id: int
    lessons: List[LessonResponse] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class CourseResponse(CourseBase):
    id: int
    units: List[UnitResponse] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# --- Complex Response for Progress/Details ---

class TaskJournalResponse(BaseModel):
    step_name: str
    action: str
    created_at: datetime
    context: Optional[dict] = None
    
    class Config:
        from_attributes = True

class LessonProgressResponse(BaseModel):
    lesson_id: int
    processing_status: str
    progress_percent: int
    logs: List[TaskJournalResponse] = []
    
    class Config:
        from_attributes = True

class CourseProgressResponse(BaseModel):
    course_id: int
    lessons: List[LessonProgressResponse]

class SubtitleTrackResponse(BaseModel):
    language: str
    url: str
    label: str

class LessonContentResponse(BaseModel):
    lesson_id: int
    title: str
    video_url: str
    duration: Optional[float]
    thumbnail_url: Optional[str]
    subtitles: List[SubtitleTrackResponse] = []
    status: str
