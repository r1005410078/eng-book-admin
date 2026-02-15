import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.main import app
from app.core.config import settings
from app.core.database import get_db, engine
from app.models.base import Base
from app.models.course import Course, Unit, Lesson
from app.models.video import Video, VideoStatus

# Setup Test Client
client = TestClient(app)

@pytest.fixture(scope="module")
def db_session():
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    # Create session
    from sqlalchemy.orm import Session as SQLSession
    session = SQLSession(bind=engine)
    
    yield session
    
    # Cleanup
    session.close()

def test_reprocess_lesson(db_session):
    """测试重新处理课时接口"""
    # Setup: Create Course -> Unit -> Lesson -> Video
    course = Course(title="Test Course")
    db_session.add(course)
    db_session.commit()
    
    unit = Unit(course_id=course.id, title="Test Unit", order_index=0)
    db_session.add(unit)
    db_session.commit()
    
    video = Video(
        title="Test Video",
        file_path="/tmp/test.mp4",
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
    
    # Test 1: Reprocess without force
    resp = client.post(
        f"{settings.API_V1_PREFIX}/lessons/{lesson.id}/reprocess"
    )
    assert resp.status_code == 202
    data = resp.json()
    assert data["lesson_id"] == lesson.id
    assert "task_id" in data
    assert data["status"] == "pending"
    assert "重新处理" in data["message"]
    
    # Verify lesson status updated
    db_session.refresh(lesson)
    assert lesson.processing_status == "PROCESSING"
    assert lesson.progress_percent == 0
    
    # Test 2: Reprocess with force=true
    resp = client.post(
        f"{settings.API_V1_PREFIX}/lessons/{lesson.id}/reprocess?force=true"
    )
    assert resp.status_code == 202
    
    # Test 3: Lesson not found
    resp = client.post(
        f"{settings.API_V1_PREFIX}/lessons/99999/reprocess"
    )
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()
    
    # Test 4: Lesson without video
    lesson_no_video = Lesson(
        unit_id=unit.id,
        title="No Video Lesson",
        processing_status="PENDING"
    )
    db_session.add(lesson_no_video)
    db_session.commit()
    
    resp = client.post(
        f"{settings.API_V1_PREFIX}/lessons/{lesson_no_video.id}/reprocess"
    )
    assert resp.status_code == 400
    assert "No video" in resp.json()["detail"]

def test_get_lesson_subtitles(db_session):
    """测试获取课时字幕接口"""
    # Setup
    course = Course(title="Subtitle Test Course")
    db_session.add(course)
    db_session.commit()
    
    unit = Unit(course_id=course.id, title="Test Unit", order_index=0)
    db_session.add(unit)
    db_session.commit()
    
    video = Video(
        title="Test Video",
        file_path="/tmp/test.mp4",
        status=VideoStatus.COMPLETED
    )
    db_session.add(video)
    db_session.commit()
    
    lesson = Lesson(
        unit_id=unit.id,
        title="Test Lesson",
        video_id=video.id,
        processing_status="READY"
    )
    db_session.add(lesson)
    db_session.commit()
    
    # Test: Get subtitles
    resp = client.get(
        f"{settings.API_V1_PREFIX}/lessons/{lesson.id}/subtitles"
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["lesson_id"] == lesson.id
    assert data["video_id"] == video.id
    assert "subtitles" in data
    assert "subtitle_count" in data

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
