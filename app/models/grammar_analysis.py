"""
GrammarAnalysis 数据库模型
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import relationship

from app.models.base import Base


class GrammarAnalysis(Base):
    """语法分析模型"""
    __tablename__ = "grammar_analysis"

    id = Column(Integer, primary_key=True, index=True)
    subtitle_id = Column(
        Integer,
        ForeignKey("subtitles.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
        comment="字幕ID"
    )
    
    # 语法分析内容
    sentence_structure = Column(String(100), nullable=True, comment="句子结构类型")
    grammar_points = Column(ARRAY(String), nullable=True, comment="语法点列表")
    difficult_words = Column(
        JSONB,
        nullable=True,
        comment="难点词汇 [{word, definition, phonetic, part_of_speech}]"
    )
    phrases = Column(ARRAY(String), nullable=True, comment="常用短语列表")
    explanation = Column(Text, nullable=True, comment="整体语法解释")
    
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
    subtitle = relationship("Subtitle", back_populates="grammar_analysis")

    def __repr__(self):
        return f"<GrammarAnalysis(id={self.id}, subtitle_id={self.subtitle_id})>"
