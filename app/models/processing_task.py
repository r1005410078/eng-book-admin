"""
ProcessingTask 数据库模型
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
import enum

from app.models.base import Base


class TaskType(str, enum.Enum):
    """任务类型"""
    AUDIO_EXTRACTION = "audio_extraction"
    SUBTITLE_GENERATION = "subtitle_generation"
    TRANSLATION = "translation"
    PHONETIC = "phonetic"
    GRAMMAR_ANALYSIS = "grammar_analysis"


class TaskStatus(str, enum.Enum):
    """任务状态"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ProcessingTask(Base):
    """处理任务模型"""
    __tablename__ = "processing_tasks"

    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(
        Integer,
        ForeignKey("videos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="视频ID"
    )
    
    # 任务信息
    task_type = Column(SQLEnum(TaskType), nullable=False, comment="任务类型")
    status = Column(
        SQLEnum(TaskStatus),
        default=TaskStatus.PENDING,
        nullable=False,
        comment="任务状态"
    )
    progress = Column(Integer, default=0, nullable=False, comment="进度（0-100）")
    error_message = Column(Text, nullable=True, comment="错误信息")
    
    # 时间戳
    started_at = Column(DateTime, nullable=True, comment="开始时间")
    completed_at = Column(DateTime, nullable=True, comment="完成时间")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, comment="创建时间")
    
    # 关系
    video = relationship("Video", back_populates="processing_tasks")

    def __repr__(self):
        return f"<ProcessingTask(id={self.id}, type='{self.task_type}', status='{self.status}')>"
