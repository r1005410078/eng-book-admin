import io
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.core.config import settings
from app.core.database import engine
from app.models.base import Base
from app.models.course import Course, Unit, Lesson

# Setup Test Client
client = TestClient(app)

@pytest.fixture(scope="module")
def db_session():
    session = Session(bind=engine)
    try:
        yield session
    finally:
        session.close()

@patch("app.api.v1.courses.process_course_lesson")
def test_course_lifecycle_integration(mock_process_task, db_session):
    """
    Complete Integration Scenario:
    1. Upload Course (Task 1.2) -> Verify creation
    2. Modify Course (Task 1.3) -> Verify update
    3. Get Progress (Task 1.4) -> Verify initial state
    """
    # Mock Celery task to avoid actual execution but allow tracking calls
    mock_process_task.delay.return_value = None

    # --- Step 1: Upload Course ---
    print("\n🔹 Step 1: Upload Course")
    files = [
        ("files", ("scenario_lesson.mp4", io.BytesIO(b"dummy_video_content_for_integration"), "video/mp4"))
    ]
    
    upload_data = {
        "title": "Integration Scenario Course",
        "description": "Initial Description",
        "level": "beginner"
    }
    
    resp_upload = client.post(
        f"{settings.API_V1_PREFIX}/courses/upload",
        data=upload_data,
        files=files
    )
    
    assert resp_upload.status_code == 200
    course_data = resp_upload.json()
    course_id = course_data["id"]
    
    # Assertions
    assert course_data["title"] == upload_data["title"]
    assert course_data["description"] == upload_data["description"]
    print(f"✅ Course Uploaded: ID={course_id}")
    
    # Verify DB State (Background tasks should have run synchronously in TestClient)
    # We need to refresh session to see what background task (if any logic ran) did.
    # Note: Our `upload_course` pushes logic to background_tasks. 
    # TestClient waits for them.
    db_session.expire_all()
    
    # Verify Lesson Created
    units = db_session.query(Unit).filter(Unit.course_id == course_id).all()
    assert len(units) == 1
    unit_id = units[0].id
    
    lessons = db_session.query(Lesson).filter(Lesson.unit_id == unit_id).all()
    assert len(lessons) == 1
    lesson_id = lessons[0].id
    print(f"✅ Lesson Created: ID={lesson_id}")
    
    # Verify Task Triggered
    assert mock_process_task.delay.called
    print("✅ Background Task Triggered")

    # --- Step 2: Modify Course ---
    print("\n🔹 Step 2: Modify Course")
    update_data = {
        "title": "Updated Scenario Course Title",
        "description": "Updated Description"
    }
    
    resp_modify = client.patch(
        f"{settings.API_V1_PREFIX}/courses/{course_id}",
        data=update_data
    )
    
    assert resp_modify.status_code == 200
    mod_data = resp_modify.json()
    
    # Assertions
    assert mod_data["title"] == update_data["title"]
    assert mod_data["description"] == update_data["description"]
    
    # Verify Persistence
    resp_get = client.get(f"{settings.API_V1_PREFIX}/courses/{course_id}")
    assert resp_get.json()["title"] == update_data["title"]
    print("✅ Course Modified Successfully")

    # --- Step 3: Get Progress ---
    print("\n🔹 Step 3: Get Progress")
    resp_progress = client.get(f"{settings.API_V1_PREFIX}/courses/{course_id}/progress")
    
    assert resp_progress.status_code == 200
    prog_data = resp_progress.json()
    
    # Assertions
    assert prog_data["course_id"] == course_id
    assert len(prog_data["lessons"]) == 1
    
    lesson_prog = prog_data["lessons"][0]
    assert lesson_prog["lesson_id"] == lesson_id
    # Since we mocked the task, status should stay at whatever `upload_course` set (PENDING)
    assert lesson_prog["processing_status"] == "PENDING"
    
    # Check Logs (Should contain INIT from upload)
    logs = lesson_prog["logs"]
    assert len(logs) > 0
    assert logs[0]["step_name"] == "INIT"
    print(f"✅ Progress Verified: Status={lesson_prog['processing_status']}, Logs={len(logs)}")

    print("\n🎉 Integration Scenario Completed Successfully!")

if __name__ == "__main__":
    import sys
    sys.exit(pytest.main(["-v", __file__]))
