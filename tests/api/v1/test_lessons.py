import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.main import app
from app.core.config import settings
from app.core.database import engine
from app.models.course import Course, Unit, Lesson
from app.models.video import Video, VideoStatus
from app.models.subtitle import Subtitle
from datetime import datetime

client = TestClient(app)

@pytest.fixture(scope="module")
def db_session():
    session = Session(bind=engine)
    try:
        yield session
    finally:
        session.close()

def test_get_lesson_content(db_session):
    """
    Test GET /lessons/{id}/content and subtitle.vtt
    """
    # 1. Setup Data
    # Create fake video
    video = Video(
        title="Test Lesson Video",
        file_path="videos/9999/test.mp4",
        status=VideoStatus.COMPLETED,
        duration=100.5,
        created_at=datetime.now()
    )
    db_session.add(video)
    db_session.commit()
    
    # Create fake lesson
    lesson = Lesson(
        unit_id=1, # Dummy
        title="Test Lesson Content",
        video_id=video.id,
        processing_status="READY",
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    db_session.add(lesson)
    db_session.commit()
    
    # Create subtitles
    subs = [
        Subtitle(
            video_id=video.id,
            sequence_number=1,
            start_time=0.5,
            end_time=2.0,
            original_text="Hello world"
        ),
        Subtitle(
            video_id=video.id,
            sequence_number=2,
            start_time=2.5,
            end_time=5.0,
            original_text="Welcome to testing"
        )
    ]
    db_session.add_all(subs)
    db_session.commit()
    
    # 2. Test Content Endpoint
    resp = client.get(f"{settings.API_V1_PREFIX}/lessons/{lesson.id}/content")
    assert resp.status_code == 200
    data = resp.json()
    
    print(f"Content Response: {data}")
    
    assert data["lesson_id"] == lesson.id
    # URL construction check
    assert "/uploads/videos/9999/test.mp4" in data["video_url"]
    assert len(data["subtitles"]) > 0
    sub_url = data["subtitles"][0]["url"]
    assert f"/lessons/{lesson.id}/subtitle.vtt" in sub_url
    
    # 3. Test Subtitle VTT Endpoint
    # Need to extract relative path from sub_url or just construct it
    # sub_url might be full URL or relative. In test client, we use relative.
    # Our API returns path relative to API root usually? 
    # In lesson.py: f"{settings.API_V1_PREFIX}/lessons/{lesson_id}/subtitle.vtt" -> /api/v1/lessons/...
    
    resp_vtt = client.get(sub_url)
    assert resp_vtt.status_code == 200
    assert resp_vtt.headers["content-type"].startswith("text/plain")
    vtt_content = resp_vtt.text
    
    print("VTT Content:\n", vtt_content)
    
    assert "WEBVTT" in vtt_content
    assert "Hello world" in vtt_content
    # Check timestamp format
    assert "00:00:00.500 --> 00:00:02.000" in vtt_content

    # Cleanup (Optional, transaction rollback preferred but using shared DB here)
    # db_session.delete(lesson)
    # db_session.delete(video)
    # db_session.commit()
