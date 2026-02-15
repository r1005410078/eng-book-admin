"""
课程内容处理异步任务
(Journal-Based Workflow)
"""
import asyncio
import logging
from datetime import datetime
from celery import shared_task
from sqlalchemy.orm import Session
from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.course import Lesson
from app.models.task_journal import TaskJournal
from app.models.video import Video, VideoStatus
from app.models.subtitle import Subtitle
from app.services.ffmpeg_service import ffmpeg_service
from app.services.whisper_service import whisper_service
from app.utils.file_handler import file_handler
from app.tasks.subtitle_tasks import enhance_video_subtitles

logger = logging.getLogger(__name__)

def log_journal(db: Session, lesson_id: int, step: str, action: str, context: dict = None):
    """记录任务日志"""
    journal = TaskJournal(
        lesson_id=lesson_id,
        step_name=step,
        action=action,
        context=context or {},
        created_at=datetime.utcnow()
    )
    db.add(journal)
    db.commit()
    logger.info(f"[Lesson {lesson_id}] {step} - {action}")

@celery_app.task(bind=True, name="app.tasks.course_tasks.process_course_lesson")
def process_course_lesson(self, lesson_id: int):
    """
    处理课时视频的全流程
    Steps:
    1. TRANSCODE (Metadata & Thumbnail)
    2. AUDIO_EXTRACT
    3. SUBTITLE (Whisper)
    4. ANALYSIS (AI Grammar)
    """
    db = SessionLocal()
    try:
        lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
        if not lesson or not lesson.video_id:
            logger.error(f"Lesson {lesson_id} not found or no video linked")
            return

        video = db.query(Video).filter(Video.id == lesson.video_id).first()
        if not video:
            logger.error(f"Video {lesson.video_id} not found")
            return

        # Update Status
        lesson.processing_status = "PROCESSING"
        lesson.progress_percent = 5
        db.commit()

        # --- Step 1: Metadata & Transcode Check ---
        step = "METADATA"
        log_journal(db, lesson_id, step, "START")
        try:
            video_path = file_handler.get_file_path(video.file_path)
            
            # Extract Metadata
            metadata = ffmpeg_service.get_video_metadata(video_path)
            video.duration = metadata.get("duration")
            video.resolution = metadata.get("resolution")
            video.format = metadata.get("format")
            video.file_size = metadata.get("size")
            
            # Generate Thumbnail
            thumb_path = ffmpeg_service.generate_thumbnail(video_path)
            if thumb_path:
                relative_thumb_path = str(thumb_path.relative_to(file_handler.upload_dir))
                video.thumbnail_path = relative_thumb_path
            
            db.commit()
            log_journal(db, lesson_id, step, "COMPLETE", metadata)
            lesson.progress_percent = 10
            db.commit()
            
        except Exception as e:
            log_journal(db, lesson_id, step, "FAIL", {"error": str(e)})
            lesson.processing_status = "FAILED"
            db.commit()
            return

        # --- Step 2: Audio Extraction ---
        step = "AUDIO_EXTRACT"
        log_journal(db, lesson_id, step, "START")
        try:
            ffmpeg_service.extract_audio(video_path)
            log_journal(db, lesson_id, step, "COMPLETE")
            lesson.progress_percent = 30
            db.commit()
        except Exception as e:
            log_journal(db, lesson_id, step, "FAIL", {"error": str(e)})
            lesson.processing_status = "FAILED"
            db.commit()
            return

        # --- Step 3: Subtitle Generation ---
        step = "SUBTITLE"
        log_journal(db, lesson_id, step, "START")
        try:
            segments = whisper_service.transcribe(
                audio_path=file_handler.get_audio_path(video.id),
                model_name="medium"
            )
            
            # Clear old subtitles if any
            db.query(Subtitle).filter(Subtitle.video_id == video.id).delete()
            
            # Save Subtitles
            for seg in segments:
                subtitle = Subtitle(
                    video_id=video.id,
                    sequence_number=seg["sequence_number"],
                    start_time=seg["start_time"],
                    end_time=seg["end_time"],
                    original_text=seg["original_text"]
                )
                db.add(subtitle)
            
            log_journal(db, lesson_id, step, "COMPLETE", {"count": len(segments)})
            lesson.progress_percent = 60
            db.commit()
        except Exception as e:
            log_journal(db, lesson_id, step, "FAIL", {"error": str(e)})
            lesson.processing_status = "FAILED"
            db.commit()
            return

        # --- Step 4: AI Analysis (Translation & Grammar) ---
        step = "ANALYSIS"
        log_journal(db, lesson_id, step, "START")
        try:
            # We reuse the existing subtitle task logic for AI enhancement
            # But here we call it synchronously or allow it to be async?
            # Ideally, we call it here to keep the journal flow consistent.
            # But enhancing takes time. Let's assume we trigger it and wait for it
            # OR we just mark this step complete when we trigger the next task.
            # For simplicity and 'Journal' completeness, let's trigger it.
            
            # NOTE: enhance_video_subtitles in app/tasks/subtitle_tasks.py uses its own ProcessingTask logic.
            # If we want to strictly follow Journaling for Lessons, we should probably refactor that logic out.
            # For now, let's assume we trigger it and hope for the best, 
            # OR better: run the enhance logic here if possible.
            # The enhance_video_subtitles is a Celery task.
            
            # Simple approach: Mark Analysis as "QUEUED" via Journal and trigger it.
            # But the user wants a full flow.
            # Let's import the synchronous content processor if available.
            # Checking imports... from app.tasks.subtitle_tasks import enhance_subtitles_content
            from app.tasks.subtitle_tasks import enhance_subtitles_content
            
            # We need an async loop to run enhance_subtitles_content if it's async
            # Warning: Celery task is already async, creating a loop inside might be tricky if one exists.
            # As enhance_subtitles_content is 'async def', we need to run it.
            
            # Run async function synchronously
            asyncio.run(enhance_subtitles_content(video.id))
            
            log_journal(db, lesson_id, step, "COMPLETE")
            lesson.progress_percent = 90
            db.commit()
            
        except Exception as e:
            log_journal(db, lesson_id, step, "FAIL", {"error": str(e)})
            # We don't fail the whole lesson if AI analysis fails, maybe just warning
            # But strictly speaking, we want it all.
            # Let's fail it for now to be safe.
            lesson.processing_status = "FAILED"
            db.commit()
            return

        # --- Done ---
        lesson.processing_status = "READY"
        lesson.progress_percent = 100
        db.commit()
        log_journal(db, lesson_id, "Workflow", "COMPLETE")

    except Exception as e:
        logger.error(f"Unexpected error in process_course_lesson: {e}")
        try:
            # Last ditch effort to mark failed
            l = db.query(Lesson).filter(Lesson.id == lesson_id).first()
            if l:
                l.processing_status = "FAILED"
                db.commit()
        except:
            pass
    finally:
        db.close()
