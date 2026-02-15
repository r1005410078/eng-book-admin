import io
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.main import app
from app.core.config import settings
from app.core.database import get_db, engine
from app.models.base import Base
from app.models.course import Course, Unit, Lesson
from app.models.task_journal import TaskJournal

# Setup Test Client
client = TestClient(app)

@pytest.fixture(scope="module")
def db_session():
    # Create tables
    Base.metadata.create_all(bind=engine)
    session = Session(bind=engine)
    try:
        yield session
    finally:
        session.close()



@patch("app.api.v1.courses.file_handler")
@patch("app.api.v1.courses.process_course_lesson")
def test_upload_course_flow(mock_process_task, mock_file_handler, db_session):
    """
    Test the full upload flow with BackgroundTasks:
    1. Upload a course with 2 video files
    2. Course created immediately.
    3. Background task creates Lessons & Videos & Journals.
    4. Task triggered.
    """
    # Mock behaviors
    mock_file_handler.save_uploaded_file.return_value = "uploads/test.mp4"
    mock_process_task.delay.return_value = None
    
    # Mock files
    files = [
        ("files", ("lesson1.mp4", io.BytesIO(b"video1"), "video/mp4")),
        ("files", ("lesson2.mp4", io.BytesIO(b"video2"), "video/mp4"))
    ]
    
    # 1. Call Upload API
    response = client.post(
        f"{settings.API_V1_PREFIX}/courses/upload",
        data={
            "title": "Test Course 101",
            "description": "A test course for integration",
            "level": "intermediate"
        },
        files=files
    )
    
    # Verify Response (Immediate)
    assert response.status_code == 200, f"Upload failed: {response.text}"
    data = response.json()
    
    course_id = data["id"]
    assert data["title"] == "Test Course 101"
    
    # 2. Verify DB State (After Background Task inferred by TestClient)
    # Re-query to get fresh state
    db_session.expire_all()
    
    course = db_session.query(Course).filter(Course.id == course_id).first()
    assert course is not None
    
    units = db_session.query(Unit).filter(Unit.course_id == course_id).all()
    assert len(units) >= 1
    default_unit = units[0]
    
    lessons = db_session.query(Lesson).filter(Lesson.unit_id == default_unit.id).order_by(Lesson.order_index).all()
    target_lessons = [l for l in lessons if l.title in ["lesson1.mp4", "lesson2.mp4"]]
    assert len(target_lessons) == 2, "Lessons should be created by background task"
    
    # Check if task was called
    assert mock_process_task.delay.call_count == 2
    
    journals = db_session.query(TaskJournal).filter(TaskJournal.lesson_id.in_([l.id for l in target_lessons])).all()
    assert len(journals) >= 2

def test_get_course_detail(db_session):
    # Create course
    c = Course(title="Detail Test", description="Desc")
    db_session.add(c)
    db_session.commit()
    
    # API Call
    response = client.get(f"{settings.API_V1_PREFIX}/courses/{c.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Detail Test"

def test_modify_course(db_session):
    c = Course(title="Old Title")
    db_session.add(c)
    db_session.commit()
    
    response = client.patch(
        f"{settings.API_V1_PREFIX}/courses/{c.id}",
        data={"title": "New Title", "description": "New Desc"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "New Title"
    
    db_session.refresh(c)
    assert c.title == "New Title"

def test_get_course_progress(db_session):
    c = Course(title="Progress Test")
    db_session.add(c)
    db_session.commit()
    
    u = Unit(course_id=c.id, title="U1")
    db_session.add(u)
    db_session.commit()
    
    l = Lesson(unit_id=u.id, title="L1", processing_status="PROCESSING", progress_percent=50)
    db_session.add(l)
    db_session.commit()
    
    j1 = TaskJournal(lesson_id=l.id, step_name="TRANSCODE", action="START", context={})
    db_session.add(j1)
    db_session.commit()
    
    response = client.get(f"{settings.API_V1_PREFIX}/courses/{c.id}/progress")
    assert response.status_code == 200
    data = response.json()
    
    assert data["course_id"] == c.id
    assert len(data["lessons"]) == 1
    lesson_prog = data["lessons"][0]
    assert lesson_prog["processing_status"] == "PROCESSING"
    assert len(lesson_prog["logs"]) >= 1
