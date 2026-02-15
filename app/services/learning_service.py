from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.course import Course, Unit, Lesson
from app.models.user_progress import UserProgress
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class LearningService:
    def __init__(self, db: Session):
        self.db = db

    def update_lesson_progress(self, user_id: int, lesson_id: int, status: str, progress: int, position: int):
        """
        更新用户在特定课时的学习进度，并在完成时自动解锁下一课。
        """
        # Find or create progress record
        progress_record = self.db.query(UserProgress).filter(
            UserProgress.user_id == user_id,
            UserProgress.lesson_id == lesson_id
        ).first()

        now = datetime.now()

        if not progress_record:
            progress_record = UserProgress(
                user_id=user_id,
                lesson_id=lesson_id,
                status=status or 'ACTIVE',
                progress_percent=progress,
                last_position_seconds=position,
                updated_at=now
            )
            self.db.add(progress_record)
        else:
            # Update existing
            # If status is provided
            if status:
                # Once COMPLETED, stay COMPLETED (unless re-locking logic exists, which is rare)
                # But allow SKIPPED -> COMPLETED
                if progress_record.status == 'COMPLETED' and status != 'COMPLETED':
                    # Do not revert completion status automatically
                    pass 
                else:
                    progress_record.status = status
            
            # Update progress only if it increases (optional, but good for video watching)
            # Or always update last_position
            if progress > progress_record.progress_percent:
                progress_record.progress_percent = progress
                
            progress_record.last_position_seconds = position
            progress_record.updated_at = now
            
            # Set completed_at if newly completed
            if status == 'COMPLETED' and not progress_record.completed_at:
                progress_record.completed_at = now

        self.db.commit()
        self.db.refresh(progress_record)
        
        # Unlock next lesson logic if COMPLETED
        if progress_record.status == 'COMPLETED':
            self._unlock_next_lesson(user_id, lesson_id)
            
        return progress_record

    def _unlock_next_lesson(self, user_id: int, current_lesson_id: int):
        """
        查找并解锁下一课时
        """
        # 1. Get current lesson to find context
        current_lesson = self.db.query(Lesson).filter(Lesson.id == current_lesson_id).first()
        if not current_lesson:
            return

        # 2. Try to find next lesson in SAME unit
        next_lesson = self.db.query(Lesson).filter(
            Lesson.unit_id == current_lesson.unit_id,
            Lesson.order_index > current_lesson.order_index,
            Lesson.is_deleted == False
        ).order_by(Lesson.order_index.asc()).first()

        # 3. If no next lesson in unit, find NEXT unit's first lesson
        if not next_lesson:
            # First, find current unit order
            current_unit = self.db.query(Unit).filter(Unit.id == current_lesson.unit_id).first()
            if current_unit:
                # Find next unit
                next_unit = self.db.query(Unit).filter(
                    Unit.course_id == current_unit.course_id,
                    Unit.order_index > current_unit.order_index
                ).order_by(Unit.order_index.asc()).first()
                
                if next_unit:
                    # Find first lesson of next unit
                    next_lesson = self.db.query(Lesson).filter(
                        Lesson.unit_id == next_unit.id,
                        Lesson.is_deleted == False
                    ).order_by(Lesson.order_index.asc()).first()

        # 4. If found next lesson, unlock it
        if next_lesson:
            logger.info(f"Unlocking next lesson {next_lesson.id} for user {user_id}")
            self._ensure_lesson_unlocked(user_id, next_lesson.id)

    def _ensure_lesson_unlocked(self, user_id: int, lesson_id: int):
        progress = self.db.query(UserProgress).filter(
            UserProgress.user_id == user_id,
            UserProgress.lesson_id == lesson_id
        ).first()

        now = datetime.now()
        if not progress:
            # Create as ACTIVE (Unlocked)
            progress = UserProgress(
                user_id=user_id,
                lesson_id=lesson_id,
                status='ACTIVE',
                updated_at=now
            )
            self.db.add(progress)
            self.db.commit()
        elif progress.status == 'LOCKED':
            progress.status = 'ACTIVE'
            progress.updated_at = now
            self.db.commit()

    def get_course_learning_status(self, user_id: int, course_id: int):
        """
        获取用户在某课程的总体学习状态
        """
        # 1. Total Lessons (Active)
        # Verify joined query: Course -> Unit -> Lesson
        total_lessons = self.db.query(func.count(Lesson.id)).join(Unit).filter(
            Unit.course_id == course_id,
            Lesson.is_deleted == False
        ).scalar()
        
        # 2. Completed Lessons
        # UserProgress -> Lesson -> Unit
        completed_lessons = self.db.query(func.count(UserProgress.id)).join(Lesson).join(Unit).filter(
            Unit.course_id == course_id,
            UserProgress.user_id == user_id,
            UserProgress.status == 'COMPLETED',
            Lesson.is_deleted == False
        ).scalar()
        
        # 3. Last Accessed Lesson
        last_accessed = self.db.query(UserProgress).join(Lesson).join(Unit).filter(
            Unit.course_id == course_id,
            UserProgress.user_id == user_id,
            Lesson.is_deleted == False
        ).order_by(UserProgress.updated_at.desc()).first()
        
        last_lesson_id = last_accessed.lesson_id if last_accessed else None
        
        # Calculate overall percent?
        percent = 0
        if total_lessons and total_lessons > 0:
            percent = int((completed_lessons / total_lessons) * 100)
            
        return {
            "course_id": course_id,
            "total_lessons": total_lessons or 0,
            "completed_lessons": completed_lessons or 0,
            "progress_percent_total": percent,
            "last_accessed_lesson_id": last_lesson_id,
            "is_completed": (completed_lessons == total_lessons) and (total_lessons > 0)
        }
