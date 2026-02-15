import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
from app.models.course import Course, Unit, Lesson
from app.models.user_progress import UserProgress

client = TestClient(app)

from app.core.database import get_db

def test_learning_flow(db_session):
    # Override dependency to use same session
    app.dependency_overrides[get_db] = lambda: db_session
    
    try:
        # 1. Setup Course Structure (Course -> Unit -> Lesson 1, Lesson 2)
        course = Course(title="Learning Flow Course")
        db_session.add(course)
        db_session.flush()
        
        unit = Unit(course_id=course.id, title="Unit 1")
        db_session.add(unit)
        db_session.flush()
        
        # Use real Video ID if FK constraint exists?
        # Lesson.video_id is nullable (in alembic).
        l1 = Lesson(unit_id=unit.id, title="L1", order_index=1, processing_status="READY")
        l2 = Lesson(unit_id=unit.id, title="L2", order_index=2, processing_status="READY")
        db_session.add(l1)
        db_session.add(l2)
        db_session.commit()
        
        user_id = 999
        
        # 3. Report Progress L1 (Active)
        resp = client.post(
            f"{settings.API_V1_PREFIX}/lessons/{l1.id}/progress",
            json={"status": "ACTIVE", "progress_percent": 50, "last_position_seconds": 60},
            headers={"x-user-id": str(user_id)}
        )
        assert resp.status_code == 200, f"Response: {resp.text}"
        
        # Verify DB
        db_session.expire_all() # Ensure we see updates made by API (if API used same session, session already has updates but good to be sure)
        p1 = db_session.query(UserProgress).filter_by(user_id=user_id, lesson_id=l1.id).first()
        assert p1.status == "ACTIVE"
        assert p1.progress_percent == 50
        
        # Check L2 status (Should be None)
        p2 = db_session.query(UserProgress).filter_by(user_id=user_id, lesson_id=l2.id).first()
        assert p2 is None 
        
        # 4. Complete L1
        resp = client.post(
            f"{settings.API_V1_PREFIX}/lessons/{l1.id}/progress",
            json={"status": "COMPLETED", "progress_percent": 100, "last_position_seconds": 120},
            headers={"x-user-id": str(user_id)}
        )
        assert resp.status_code == 200
        
        # Verify L2 is Unlocked
        db_session.expire_all()
        p2 = db_session.query(UserProgress).filter_by(user_id=user_id, lesson_id=l2.id).first()
        assert p2 is not None
        assert p2.status == "ACTIVE" # Unlocked!
        
        # 5. Get Learning Status
        resp = client.get(
            f"{settings.API_V1_PREFIX}/courses/{course.id}/learning-status",
            headers={"x-user-id": str(user_id)}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_lessons"] == 2
        assert data["completed_lessons"] == 1
        assert data["progress_percent_total"] == 50
        assert data["last_accessed_lesson_id"] in [l1.id, l2.id] 
    finally:
        app.dependency_overrides.clear()

from unittest.mock import AsyncMock, patch

def test_ask_syntax(db_session):
    # Override dependency
    app.dependency_overrides[get_db] = lambda: db_session
    
    try:
        # 1. Setup Data
        c = Course(title="Syntax Course")
        db_session.add(c); db_session.flush()
        u = Unit(course_id=c.id, title="Syntax Unit")
        db_session.add(u); db_session.flush()
        l = Lesson(unit_id=u.id, title="Syntax Lesson", processing_status="READY")
        db_session.add(l)
        db_session.commit()
        
        # 2. Mock OpenAI Service
        # Note: We patch where it is IMPORTED in the module under test!
        with patch("app.api.v1.lessons.openai_service.answer_syntax_question", new_callable=AsyncMock) as mock_ask:
            mock_ask.return_value = "这是一个简单句。"
            
            resp = client.post(
                f"{settings.API_V1_PREFIX}/lessons/{l.id}/ask-syntax",
                json={"question": "分析这个句子", "context_text": "I run fast."},
                headers={"x-user-id": "1"}
            )
            
            assert resp.status_code == 200, f"Error: {resp.text}"
            data = resp.json()
            assert data["answer"] == "这是一个简单句。"
            
            # Verify Mock Call
            mock_ask.assert_called_once()
            args, kwargs = mock_ask.call_args
            assert kwargs['question'] == "分析这个句子"
            assert kwargs['context'] == "I run fast."
            
    finally:
        app.dependency_overrides.clear()
