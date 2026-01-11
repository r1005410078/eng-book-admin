"""
视频 Pydantic 模型
"""
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field

from app.models.video import VideoStatus, DifficultyLevel


class VideoBase(BaseModel):
    title: str = Field(..., description="视频标题")
    description: Optional[str] = Field(None, description="视频描述")
    category: Optional[str] = Field(None, description="分类")
    difficulty_level: Optional[DifficultyLevel] = Field(None, description="难度级别")
    tags: Optional[List[str]] = Field(None, description="标签列表")


class VideoCreate(VideoBase):
    pass


class VideoUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    difficulty_level: Optional[DifficultyLevel] = None
    tags: Optional[List[str]] = None
    status: Optional[VideoStatus] = None


class VideoResponse(VideoBase):
    id: int
    file_path: str
    thumbnail_path: Optional[str] = None
    duration: Optional[float] = None
    file_size: Optional[int] = None
    format: Optional[str] = None
    resolution: Optional[str] = None
    status: VideoStatus
    created_at: datetime
    updated_at: datetime
    
    # 进度信息（可选，从 ProcessingTask 聚合）
    progress: Optional[int] = Field(0, description="总体处理进度")

    class Config:
        from_attributes = True


class VideoListResponse(BaseModel):
    total: int
    items: List[VideoResponse]
    page: int
    size: int
