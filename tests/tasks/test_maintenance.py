import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
from sqlalchemy import text
from app.models.course import Lesson, Unit, Course
from app.models.video import Video, VideoStatus
from app.models.processing_task import ProcessingTask, TaskStatus, TaskType
from app.tasks.maintenance_tasks import cleanup_deleted_lessons, monitor_stuck_tasks

class MockSession:
    """Wrapper to prevent task from closing the test session"""
    def __init__(self, real_session):
        self._session = real_session
    
    def __getattr__(self, name):
        if name == 'close':
            return lambda: None # No-op
        return getattr(self._session, name)

@pytest.fixture
def mock_session_local(db_session):
    # Wrap the test session so task can use it but not close it
    mock_s = MockSession(db_session)
    with patch('app.tasks.maintenance_tasks.SessionLocal', return_value=mock_s):
        yield mock_s

def test_cleanup_deleted_lessons(mock_session_local, db_session):
    # 1. Setup Data - Create Course, Unit, Video
    course = Course(title="GC Course")
    db_session.add(course)
    db_session.flush()
    
    unit = Unit(course_id=course.id, title="GC Unit")
    db_session.add(unit)
    db_session.flush()
    
    video = Video(title="GC Video", file_path="/fake/path.mp4", status=VideoStatus.COMPLETED)
    db_session.add(video)
    db_session.commit() # Commit to get ID and ensure visibility
    
    # 2. Create Deleted Lesson pointing to Video
    lesson = Lesson(
        unit_id=unit.id, 
        title="Deleted Lesson", 
        video_id=video.id, 
        is_deleted=True # Mark as deleted
    )
    db_session.add(lesson)
    db_session.commit()
    
    # Verify setup
    assert lesson.video_id == video.id
    
    # 3. Mock file_handler
    with patch('app.tasks.maintenance_tasks.file_handler.delete_video_files') as mock_delete:
        mock_delete.return_value = True
        
        # 4. Run Task
        cleanup_deleted_lessons()
        
        # 5. Verify file deletion called
        mock_delete.assert_called_with(video.id)
        
    # 6. Verify DB cleanup
    # Video should be deleted
    deleted_video = db_session.query(Video).filter(Video.id == video.id).first()
    assert deleted_video is None
    
    # Lesson should still exist but video_id None
    updated_lesson = db_session.query(Lesson).filter(Lesson.id == lesson.id).first()
    assert updated_lesson is not None
    assert updated_lesson.video_id is None

def test_monitor_stuck_tasks(mock_session_local, db_session):
    # 1. Create Stuck Task
    v = Video(title="Task Video", file_path="x", status=VideoStatus.PROCESSING)
    db_session.add(v)
    db_session.commit()
    
    stuck_task = ProcessingTask(
        video_id=v.id,
        task_type=TaskType.AUDIO_EXTRACTION,
        status=TaskStatus.PROCESSING,
        progress=50
    )
    db_session.add(stuck_task)
    db_session.commit()
    
    # 2. Force started_at to be old
    old_time = datetime.utcnow() - timedelta(hours=2)
    db_session.execute(
        text("UPDATE processing_tasks SET started_at = :t WHERE id = :id"),
        {"t": old_time, "id": stuck_task.id}
    )
    db_session.commit()
    
    # 3. Run Monitor Task
    monitor_stuck_tasks()
    
    # 4. Verify Task Failed
    db_session.expire_all()
    task = db_session.query(ProcessingTask).get(stuck_task.id)
    assert task.status == TaskStatus.FAILED
    assert "timed out" in task.error_message.lower()
