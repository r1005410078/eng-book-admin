from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Boolean, event, Index
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.sql import func
from app.models.base import Base

class TaskJournal(Base):
    __tablename__ = "task_journals"

    id = Column(Integer, primary_key=True, index=True)
    lesson_id = Column(Integer, ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False, index=True)
    step_name = Column(String(50), nullable=False) # e.g., TRANSCODE, SUBTITLE, TRANSLATE
    action = Column(String(20), nullable=False) # START, COMPLETE, FAIL
    context = Column(JSONB, nullable=True) # Input params, file paths
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    
    lesson = relationship("Lesson", back_populates="task_journals")

    __table_args__ = (
        Index('ix_task_journals_lesson_step', 'lesson_id', 'step_name'),
    )
