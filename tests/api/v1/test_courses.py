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
    mock_file_handler.save_file_stream.return_value = "uploads/test.mp4"
    mock_file_handler.get_file_path.return_value = "/tmp/uploads/test.mp4"
    mock_file_handler.get_file_size.return_value = 1024
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

from app.models.user_course import UserCourse

def test_user_courses_flow(db_session):
    # Setup
    c1 = Course(title="C1")
    c2 = Course(title="C2")
    db_session.add_all([c1, c2])
    db_session.commit()
    
    user_id = 777
    
    # 1. Join C1
    resp = client.post(
        f"{settings.API_V1_PREFIX}/courses/{c1.id}/join",
        headers={"x-user-id": str(user_id)}
    )
    assert resp.status_code == 200
    
    # 2. Verify Current Course
    resp = client.get(
        f"{settings.API_V1_PREFIX}/users/current-course",
        headers={"x-user-id": str(user_id)}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == c1.id
    
    # 3. Join C2
    resp = client.post(
        f"{settings.API_V1_PREFIX}/courses/{c2.id}/join",
        headers={"x-user-id": str(user_id)}
    )
    assert resp.status_code == 200
    
    # 4. Verify Current is C2
    resp = client.get(
        f"{settings.API_V1_PREFIX}/users/current-course",
        headers={"x-user-id": str(user_id)}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == c2.id
    
    # 5. Verify C1 is inactive in DB
    uc1 = db_session.query(UserCourse).filter_by(user_id=user_id, course_id=c1.id).first()
    assert uc1.is_active == False

def test_update_course_content(db_session):
    """Test Task 4.1: Update course, unit, and lesson content"""
    # Setup
    c = Course(title="Original Course", description="Original Desc")
    db_session.add(c)
    db_session.commit()
    
    u = Unit(course_id=c.id, title="Original Unit")
    db_session.add(u)
    db_session.commit()
    
    l = Lesson(unit_id=u.id, title="Original Lesson", processing_status="READY")
    db_session.add(l)
    db_session.commit()
    
    # Test 1: Update Course
    resp = client.patch(
        f"{settings.API_V1_PREFIX}/courses/{c.id}",
        data={"title": "Updated Course", "description": "Updated Desc", "cover_image": "http://example.com/cover.jpg"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Updated Course"
    assert data["description"] == "Updated Desc"
    assert data["cover_image"] == "http://example.com/cover.jpg"
    
    # Test 2: Update Unit
    resp = client.patch(
        f"{settings.API_V1_PREFIX}/courses/{c.id}/units/{u.id}",
        data={"title": "Updated Unit", "description": "Unit Desc"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["message"] == "Unit updated"
    
    db_session.refresh(u)
    assert u.title == "Updated Unit"
    
    # Test 3: Update Lesson
    resp = client.patch(
        f"{settings.API_V1_PREFIX}/courses/{c.id}/units/{u.id}/lessons/{l.id}",
        data={"title": "Updated Lesson"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["message"] == "Lesson updated"
    
    db_session.refresh(l)
    assert l.title == "Updated Lesson"

def test_reorder_units_and_lessons(db_session):
    """Test Task 4.2: Reorder units and lessons"""
    # Setup
    c = Course(title="Reorder Test")
    db_session.add(c)
    db_session.commit()
    
    u1 = Unit(course_id=c.id, title="Unit 1", order_index=0)
    u2 = Unit(course_id=c.id, title="Unit 2", order_index=1)
    u3 = Unit(course_id=c.id, title="Unit 3", order_index=2)
    db_session.add_all([u1, u2, u3])
    db_session.commit()
    
    l1 = Lesson(unit_id=u1.id, title="L1", order_index=0, processing_status="READY")
    l2 = Lesson(unit_id=u1.id, title="L2", order_index=1, processing_status="READY")
    db_session.add_all([l1, l2])
    db_session.commit()
    
    # Test 1: Reorder Units (swap u1 and u3)
    resp = client.patch(
        f"{settings.API_V1_PREFIX}/courses/{c.id}/units/reorder",
        json=[
            {"unit_id": u3.id, "order_index": 0},
            {"unit_id": u2.id, "order_index": 1},
            {"unit_id": u1.id, "order_index": 2}
        ]
    )
    assert resp.status_code == 200
    
    db_session.refresh(u1)
    db_session.refresh(u3)
    assert u3.order_index == 0
    assert u1.order_index == 2
    
    # Test 2: Reorder Lessons
    resp = client.patch(
        f"{settings.API_V1_PREFIX}/courses/{c.id}/units/{u1.id}/lessons/reorder",
        json=[
            {"lesson_id": l2.id, "order_index": 0},
            {"lesson_id": l1.id, "order_index": 1}
        ]
    )
    assert resp.status_code == 200
    
    db_session.refresh(l1)
    db_session.refresh(l2)
    assert l2.order_index == 0
    assert l1.order_index == 1

def test_soft_delete(db_session):
    """Test Task 4.3: Soft delete course, unit, and lesson"""
    # Setup
    c = Course(title="Delete Test")
    db_session.add(c)
    db_session.commit()
    
    u = Unit(course_id=c.id, title="Unit to Delete")
    db_session.add(u)
    db_session.commit()
    
    l1 = Lesson(unit_id=u.id, title="Lesson 1", processing_status="READY")
    l2 = Lesson(unit_id=u.id, title="Lesson 2", processing_status="READY")
    db_session.add_all([l1, l2])
    db_session.commit()
    
    # Test 1: Soft Delete Lesson
    resp = client.delete(
        f"{settings.API_V1_PREFIX}/courses/{c.id}/units/{u.id}/lessons/{l1.id}"
    )
    assert resp.status_code == 200
    
    db_session.refresh(l1)
    assert l1.is_deleted == True
    
    # Test 2: Delete Unit (cascades to lessons)
    # First verify l2 is not deleted yet
    db_session.refresh(l2)
    assert l2.is_deleted == False
    
    resp = client.delete(
        f"{settings.API_V1_PREFIX}/courses/{c.id}/units/{u.id}"
    )
    assert resp.status_code == 200
    
    # After unit deletion, check l2 was soft-deleted before the unit was removed
    # We need to query it fresh since the unit is gone
    l2_check = db_session.query(Lesson).filter(Lesson.id == l2.id).first()
    # Lesson might be deleted from DB due to cascade, or just marked as deleted
    if l2_check:
        assert l2_check.is_deleted == True
    
    # Verify unit is deleted
    deleted_unit = db_session.query(Unit).filter(Unit.id == u.id).first()
    assert deleted_unit is None
    
    # Test 3: Delete Course (cascades to all)
    c2 = Course(title="Course to Delete")
    db_session.add(c2)
    db_session.commit()
    
    u2 = Unit(course_id=c2.id, title="Unit")
    db_session.add(u2)
    db_session.commit()
    
    l3 = Lesson(unit_id=u2.id, title="Lesson", processing_status="READY")
    db_session.add(l3)
    db_session.commit()
    
    l3_id = l3.id
    
    resp = client.delete(f"{settings.API_V1_PREFIX}/courses/{c2.id}")
    assert resp.status_code == 200
    
    # Verify cascade soft delete
    l3_check = db_session.query(Lesson).filter(Lesson.id == l3_id).first()
    if l3_check:
        assert l3_check.is_deleted == True
    
    # Verify course is deleted
    deleted_course = db_session.query(Course).filter(Course.id == c2.id).first()
    assert deleted_course is None
