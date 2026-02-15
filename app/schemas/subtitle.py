from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime


# --- Basic Subtitle Schemas ---

class SubtitleBase(BaseModel):
    sequence_number: int
    start_time: float
    end_time: float
    original_text: str
    translation: Optional[str] = None
    phonetic: Optional[str] = None

class SubtitleCreate(SubtitleBase):
    pass

class SubtitleUpdate(BaseModel):
    sequence_number: Optional[int] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    original_text: Optional[str] = None
    translation: Optional[str] = None
    phonetic: Optional[str] = None

class SubtitleResponse(SubtitleBase):
    id: int
    video_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# --- Task Log Schemas ---

class TaskJournalLogResponse(BaseModel):
    step_name: str
    action: str
    context: Optional[dict] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

# --- Async Task Response ---

class AsyncTaskResponse(BaseModel):
    message: str
    video_id: Optional[int] = None
    task_id: Optional[str] = None
    status: str

# --- Processing Task Response ---

class ProcessingTaskResponse(BaseModel):
    id: int
    video_id: int
    task_type: str
    status: str
    progress: int
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

# --- Grammar Analysis Schemas ---

class GrammarAnalysisItem(BaseModel):
    """单个语法分析项"""
    word: str
    part_of_speech: str
    explanation: Optional[str] = None
    translation: Optional[str] = None
    
    class Config:
        from_attributes = True

# --- Subtitle Schemas ---

class SubtitleDetailResponse(BaseModel):
    """字幕详细信息"""
    sequence_number: int
    start_time: float
    end_time: float
    original_text: str
    translation: Optional[str] = None
    phonetic: Optional[str] = None
    grammar_analysis: List[GrammarAnalysisItem] = []
    
    class Config:
        from_attributes = True

class LessonSubtitlesResponse(BaseModel):
    """课程完整字幕数据"""
    lesson_id: int
    video_id: int
    subtitle_count: int
    subtitles: List[SubtitleDetailResponse]
