import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.main import app
from app.core.config import settings
from app.core.database import get_db, engine
from app.models.base import Base
from app.models.course import Course, Unit, Lesson
from app.models.video import Video, VideoStatus
from app.models.processing_task import ProcessingTask
from app.models.subtitle import Subtitle
from unittest.mock import patch, MagicMock

# Setup Test Client
client = TestClient(app)

@pytest.fixture(scope="module")
def db_session():
    # Create tables
    Base.metadata.create_all(bind=engine)
    session = Session(bind=engine)
    yield session
    session.close()

def test_reprocess_lesson(db_session):
    """测试重新处理课时视频"""
    # Setup: Create Course -> Unit -> Lesson -> Video
    course = Course(title="Test Course")
    db_session.add(course)
    db_session.commit()
    
    unit = Unit(course_id=course.id, title="Test Unit", order_index=0)
    db_session.add(unit)
    db_session.commit()
    
    video = Video(
        title="Test Video",
        file_path="/uploads/test.mp4",
        status=VideoStatus.COMPLETED
    )
    db_session.add(video)
    db_session.commit()
    
    lesson = Lesson(
        unit_id=unit.id,
        title="Test Lesson",
        video_id=video.id,
        processing_status="READY",
        progress_percent=100
    )
    db_session.add(lesson)
    db_session.commit()
    
    # Add some old subtitles (tasks will be created by actual processing)
    subtitle = Subtitle(
        video_id=video.id,
        sequence_number=1,
        start_time=0.0,
        end_time=2.0,
        original_text="Hello"
    )
    db_session.add(subtitle)
    db_session.commit()
    
    # Mock Celery task
    with patch('app.api.v1.lessons.process_uploaded_video') as mock_task:
        mock_task.delay.return_value = MagicMock(id="test-task-123")
        
        # Test: Reprocess
        resp = client.post(
            f"{settings.API_V1_PREFIX}/lessons/{lesson.id}/reprocess"
        )
        
        assert resp.status_code == 202
        data = resp.json()
        assert data["message"] == "课时重新处理已启动"
        assert data["video_id"] == video.id
        assert data["task_id"] == "test-task-123"
        assert data["status"] == "pending"
        
        # Verify Celery task was called
        mock_task.delay.assert_called_once_with(video.id)
        
        # Verify status was updated
        db_session.refresh(lesson)
        db_session.refresh(video)
        
        assert lesson.processing_status == "PROCESSING"
        assert lesson.progress_percent == 0
        assert video.status == VideoStatus.PROCESSING
        
        # Verify old subtitles were deleted
        subtitles_count = db_session.query(Subtitle).filter(
            Subtitle.video_id == video.id
        ).count()
        assert subtitles_count == 0

def test_reprocess_lesson_not_found(db_session):
    """测试重新处理不存在的课时"""
    resp = client.post(
        f"{settings.API_V1_PREFIX}/lessons/99999/reprocess"
    )
    assert resp.status_code == 404
    assert "Lesson not found" in resp.json()["detail"]

def test_reprocess_lesson_no_video(db_session):
    """测试重新处理没有关联视频的课时"""
    course = Course(title="Test Course 2")
    db_session.add(course)
    db_session.commit()
    
    unit = Unit(course_id=course.id, title="Test Unit 2", order_index=0)
    db_session.add(unit)
    db_session.commit()
    
    lesson = Lesson(
        unit_id=unit.id,
        title="Test Lesson No Video",
        video_id=None,  # No video
        processing_status="PENDING"
    )
    db_session.add(lesson)
    db_session.commit()
    
    resp = client.post(
        f"{settings.API_V1_PREFIX}/lessons/{lesson.id}/reprocess"
    )
    assert resp.status_code == 400
    assert "No video associated" in resp.json()["detail"]

def test_reprocess_lesson_with_force(db_session):
    """测试使用 force 参数强制重新处理"""
    course = Course(title="Test Course 3")
    db_session.add(course)
    db_session.commit()
    
    unit = Unit(course_id=course.id, title="Test Unit 3", order_index=0)
    db_session.add(unit)
    db_session.commit()
    
    video = Video(
        title="Test Video 3",
        file_path="/uploads/test3.mp4",
        status=VideoStatus.PROCESSING  # Already processing
    )
    db_session.add(video)
    db_session.commit()
    
    lesson = Lesson(
        unit_id=unit.id,
        title="Test Lesson 3",
        video_id=video.id,
        processing_status="PROCESSING"
    )
    db_session.add(lesson)
    db_session.commit()
    
    with patch('app.api.v1.lessons.process_uploaded_video') as mock_task:
        mock_task.delay.return_value = MagicMock(id="test-task-456")
        
        # Test with force=true
        resp = client.post(
            f"{settings.API_V1_PREFIX}/lessons/{lesson.id}/reprocess?force=true"
        )
        
        assert resp.status_code == 202
        data = resp.json()
        assert data["task_id"] == "test-task-456"
