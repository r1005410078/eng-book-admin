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


# 异步任务相关响应模型

class AsyncTaskResponse(BaseModel):
    """异步任务触发响应"""
    message: str = Field(..., description="响应消息")
    video_id: int = Field(..., description="视频ID")
    task_id: Optional[str] = Field(None, description="Celery 任务ID")
    status: str = Field(..., description="任务状态")


class SubTaskProgress(BaseModel):
    """子任务进度"""
    name: str = Field(..., description="任务名称")
    status: str = Field(..., description="任务状态")
    progress: int = Field(..., description="任务进度 (0-100)")


class TaskProgressResponse(BaseModel):
    """任务进度查询响应"""
    video_id: int = Field(..., description="视频ID")
    status: str = Field(..., description="总体状态")
    progress: int = Field(..., description="总体进度 (0-100)")
    tasks: List[SubTaskProgress] = Field(..., description="子任务列表")
    started_at: Optional[datetime] = Field(None, description="开始时间")
    updated_at: Optional[datetime] = Field(None, description="最后更新时间")
