from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Boolean, event, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.sql import func
from app.models.base import Base

class UserProgress(Base):
    __tablename__ = "user_progress"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    lesson_id = Column(Integer, ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(20), nullable=False, server_default='LOCKED') # LOCKED, ACTIVE, COMPLETED, SKIPPED
    progress_percent = Column(Integer, nullable=False, default=0)
    last_position_seconds = Column(Integer, nullable=False, default=0)
    completed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    
    lesson = relationship("Lesson", back_populates="user_progress")
    
    __table_args__ = (
        UniqueConstraint('user_id', 'lesson_id', name='uq_user_lesson_progress'),
    )

class PracticeSubmission(Base):
    __tablename__ = "practice_submissions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    lesson_id = Column(Integer, ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False, index=True)
    practice_type = Column(String(50), nullable=False) # SHADOWING, LISTENING
    score = Column(Integer, nullable=True)
    content_url = Column(String(255), nullable=True) # Uploaded audio/text
    feedback = Column(JSONB, nullable=True) # AI feedback
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    
    lesson = relationship("Lesson", back_populates="practice_submissions")
