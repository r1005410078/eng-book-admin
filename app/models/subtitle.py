"""
Subtitle 数据库模型
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Numeric, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.models.base import Base


class Subtitle(Base):
    """字幕模型"""
    __tablename__ = "subtitles"

    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(Integer, ForeignKey("videos.id", ondelete="CASCADE"), nullable=False, index=True, comment="视频ID")
    sequence_number = Column(Integer, nullable=False, comment="字幕序号")
    
    # 时间轴
    start_time = Column(Numeric(10, 3), nullable=False, comment="开始时间（秒）")
    end_time = Column(Numeric(10, 3), nullable=False, comment="结束时间（秒）")
    
    # 内容
    original_text = Column(Text, nullable=False, comment="原文（英文）")
    translation = Column(Text, nullable=True, comment="翻译（中文）")
    phonetic = Column(Text, nullable=True, comment="音标")
    
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
    video = relationship("Video", back_populates="subtitles")
    grammar_analysis = relationship("GrammarAnalysis", back_populates="subtitle", uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Subtitle(id={self.id}, video_id={self.video_id}, seq={self.sequence_number})>"
