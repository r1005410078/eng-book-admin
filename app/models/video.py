"""
Video 数据库模型
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, BigInteger, DateTime, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import relationship
import enum

from app.models.base import Base


class VideoStatus(str, enum.Enum):
    """视频处理状态"""
    UPLOADING = "uploading"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class DifficultyLevel(str, enum.Enum):
    """难度级别"""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class Video(Base):
    """视频模型"""
    __tablename__ = "videos"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False, comment="视频标题")
    description = Column(Text, nullable=True, comment="视频描述")
    
    # 文件信息
    file_path = Column(String(500), nullable=False, comment="视频文件路径")
    thumbnail_path = Column(String(500), nullable=True, comment="缩略图路径")
    duration = Column(Integer, nullable=True, comment="视频时长（秒）")
    file_size = Column(BigInteger, nullable=True, comment="文件大小（字节）")
    format = Column(String(50), nullable=True, comment="视频格式")
    resolution = Column(String(20), nullable=True, comment="分辨率，如 1920x1080")
    
    # 状态和分类
    status = Column(
        SQLEnum(VideoStatus),
        default=VideoStatus.UPLOADING,
        nullable=False,
        comment="处理状态"
    )
    difficulty_level = Column(
        SQLEnum(DifficultyLevel),
        nullable=True,
        comment="难度级别"
    )
    category = Column(String(100), nullable=True, comment="分类")
    tags = Column(ARRAY(String), nullable=True, comment="标签列表")
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, comment="创建时间")
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
        comment="更新时间"
    )
    
    # 关系
    subtitles = relationship("Subtitle", back_populates="video", cascade="all, delete-orphan")
    processing_tasks = relationship("ProcessingTask", back_populates="video", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Video(id={self.id}, title='{self.title}', status='{self.status}')>"
