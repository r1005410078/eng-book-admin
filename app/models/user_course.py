from sqlalchemy import Column, Integer, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from app.models.base import Base

class UserCourse(Base):
    """
    用户课程关联表 (Enrollment)
    用于记录用户加入的课程以及当前激活的课程
    """
    __tablename__ = "user_course_enrollments"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    
    is_active = Column(Boolean, default=False, nullable=False, comment="是否为当前正在学习的课程") 
    joined_at = Column(DateTime, default=datetime.now, nullable=False)
    last_accessed_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)
    
    # Relationships
    # course = relationship("Course", backref="enrollments") # Avoid circular import if Course not imported here.
    # We will import Course in __init__ or use string "Course" if Models are imported in Base.

    __table_args__ = (
        UniqueConstraint('user_id', 'course_id', name='uq_user_course_enrollment'),
    )
