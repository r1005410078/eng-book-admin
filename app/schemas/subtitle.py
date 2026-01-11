"""
字幕 Pydantic 模型
"""
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class SubtitleBase(BaseModel):
    sequence_number: int
    start_time: float
    end_time: float
    original_text: str
    translation: Optional[str] = None
    phonetic: Optional[str] = None


class SubtitleCreate(SubtitleBase):
    video_id: int


class SubtitleUpdate(BaseModel):
    original_text: Optional[str] = None
    translation: Optional[str] = None
    phonetic: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None


class SubtitleResponse(SubtitleBase):
    id: int
    video_id: int
    created_at: datetime
    updated_at: datetime
    
    # 可选：关联的语法分析 ID
    grammar_analysis_id: Optional[int] = None

    class Config:
        from_attributes = True


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
