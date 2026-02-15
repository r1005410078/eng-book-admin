import os
import time
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.main import app
from app.core.config import settings
from app.core.database import engine
from app.models.base import Base
from app.models.course import Course, Unit, Lesson
from app.models.task_journal import TaskJournal

# Setup Test Client
client = TestClient(app)

# Real Asset Directory
TEST_ASSETS_DIR = "tests/assets"

@pytest.fixture(scope="module")
def db_session():
    session = Session(bind=engine)
    try:
        yield session
    finally:
        session.close()

def get_test_files():
    """Get all MP4 files from tests/assets"""
    files = []
    if not os.path.exists(TEST_ASSETS_DIR):
        print(f"⚠️ Warning: Directory {TEST_ASSETS_DIR} does not exist.")
        return []
        
    for f in os.listdir(TEST_ASSETS_DIR):
        if f.lower().endswith(".mp4"):
            files.append(os.path.join(TEST_ASSETS_DIR, f))
    return files

@pytest.mark.skipif(not os.path.exists(TEST_ASSETS_DIR), reason="Test assets directory not found")
@patch("app.api.v1.courses.process_course_lesson")
def test_upload_real_course_assets(mock_process_task, db_session):
    """
    Integration Test using REAL video assets from tests/assets:
    1. Upload all MP4 files in tests/assets to create a new course.
    2. Verify immediate response.
    3. Verify background task execution for EACH file.
    """
    # Fix potential Redis connection hang by mocking the task trigger
    mock_process_task.delay.return_value = None
    
    test_files = get_test_files()
    if not test_files:
        pytest.skip("No MP4 files found in tests/assets")
    
    print(f"\n🚀 Found {len(test_files)} test files: {[os.path.basename(f) for f in test_files]}")
    
    # Prepare files for upload
    files_payload = []
    opened_files = []
    
    try:
        for file_path in test_files:
            f = open(file_path, "rb")
            opened_files.append(f)
            filename = os.path.basename(file_path)
            files_payload.append(("files", (filename, f, "video/mp4")))
            
        print("🚀 Starting Upload...")
        response = client.post(
            f"{settings.API_V1_PREFIX}/courses/upload",
            data={
                "title": "Real Assets Course Integration",
                "description": "Integration test with multiple real video files",
                "level": "intermediate"
            },
            files=files_payload
        )
        print("✅ Upload Request Finished")
        
        # 2. Verify Response
        assert response.status_code == 200, f"Upload failed: {response.text}"
        data = response.json()
        course_id = data["id"]
        print(f"✅ Course Created: ID={course_id}, Title={data['title']}")
        
        # 3. Verify Background Processing for EACH file
        db_session.expire_all()
        
        # Check Unit
        units = db_session.query(Unit).filter(Unit.course_id == course_id).all()
        assert len(units) >= 1
        unit_id = units[0].id
        
        # Check Lessons for each file
        for file_path in test_files:
            filename = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            
            # Find lesson
            lesson = db_session.query(Lesson).filter(
                Lesson.unit_id == unit_id,
                Lesson.title == filename
            ).first()
            
            assert lesson is not None, f"Lesson for {filename} should be created"
            print(f"✅ Lesson Created: ID={lesson.id}, Title={lesson.title}")
            
            # Check Video
            from app.models.video import Video
            video = db_session.query(Video).filter(Video.id == lesson.video_id).first()
            assert video is not None
            
            # Check file on disk
            full_path = str(settings.UPLOAD_DIR) + "/" + str(video.file_path)
            full_path = os.path.normpath(full_path)
            
            assert os.path.exists(full_path), f"File should be saved to {full_path}"
            assert os.path.getsize(full_path) == file_size, f"File size mismatch for {filename}"
            print(f"✅ File Verified: {full_path} ({file_size} bytes)")
            
            # Check Journal
            journals = db_session.query(TaskJournal).filter(TaskJournal.lesson_id == lesson.id).all()
            assert len(journals) >= 1
        
        # Check Task Triggered Count
        assert mock_process_task.delay.call_count == len(test_files)
        print(f"✅ Celery Task Triggered {mock_process_task.delay.call_count} times")

    finally:
        # Close all file handles
        for f in opened_files:
            f.close()

if __name__ == "__main__":
    import sys
    sys.exit(pytest.main(["-v", __file__]))
