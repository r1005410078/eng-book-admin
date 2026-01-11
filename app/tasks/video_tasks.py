"""
视频处理异步任务
"""
import asyncio
import logging
from datetime import datetime
from pathlib import Path

from celery import shared_task
from sqlalchemy.orm import Session

from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.video import Video, VideoStatus
from app.models.processing_task import ProcessingTask, TaskType, TaskStatus
from app.models.subtitle import Subtitle
from app.services.ffmpeg_service import ffmpeg_service
from app.services.whisper_service import whisper_service
from app.utils.file_handler import file_handler
from app.tasks.subtitle_tasks import enhance_video_subtitles

logger = logging.getLogger(__name__)

def get_db_session():
    """获取数据库会话上下文管理器"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def update_task_progress(
    db: Session,
    task_id: int,
    progress: int,
    status: TaskStatus = TaskStatus.PROCESSING,
    error_message: str = None
):
    """更新任务进度"""
    task = db.query(ProcessingTask).filter(ProcessingTask.id == task_id).first()
    if task:
        task.progress = progress
        task.status = status
        if error_message:
            task.error_message = str(error_message)
        if status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
            task.completed_at = datetime.utcnow()
        if status == TaskStatus.PROCESSING and not task.started_at:
            task.started_at = datetime.utcnow()
        db.commit()

def process_video_content(video_id: int, trigger_next_task: bool = True):
    """
    处理视频内容的核心同步逻辑
    
    Args:
        video_id: 视频ID
        trigger_next_task: 是否自动触发下一个任务（字幕增强）
    """
    logger.info(f"Start processing video content for video {video_id}")
    
    db = SessionLocal()
    try:
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            logger.error(f"Video {video_id} not found")
            return

        video.status = VideoStatus.PROCESSING
        db.commit()

        # 1. 音频提取任务
        audio_task = ProcessingTask(
            video_id=video.id,
            task_type=TaskType.AUDIO_EXTRACTION,
            status=TaskStatus.PENDING
        )
        db.add(audio_task)
        db.commit()
        db.refresh(audio_task)

        try:
            update_task_progress(db, audio_task.id, 0, TaskStatus.PROCESSING)
            
            video_path = file_handler.get_file_path(video.file_path)
            
            # 更新元数据
            if not video.duration:
                metadata = ffmpeg_service.get_video_metadata(video_path)
                video.duration = metadata.get("duration")
                video.resolution = metadata.get("resolution")
                video.format = metadata.get("format")
                video.file_size = metadata.get("size")
                
                thumb_path = ffmpeg_service.generate_thumbnail(video_path)
                if thumb_path:
                    relative_thumb_path = str(thumb_path.relative_to(file_handler.upload_dir))
                    video.thumbnail_path = relative_thumb_path
                
                db.commit()
            
            # 提取音频
            ffmpeg_service.extract_audio(video_path)
            
            update_task_progress(db, audio_task.id, 100, TaskStatus.COMPLETED)
            logger.info(f"Audio extracted for video {video_id}")
            
        except Exception as e:
            logger.error(f"Audio extraction failed: {e}")
            update_task_progress(db, audio_task.id, 0, TaskStatus.FAILED, str(e))
            video.status = VideoStatus.FAILED
            db.commit()
            return

        # 2. 字幕生成任务
        subtitle_task = ProcessingTask(
            video_id=video.id,
            task_type=TaskType.SUBTITLE_GENERATION,
            status=TaskStatus.PENDING
        )
        db.add(subtitle_task)
        db.commit()
        db.refresh(subtitle_task)

        try:
            update_task_progress(db, subtitle_task.id, 0, TaskStatus.PROCESSING)
            
            segments = whisper_service.transcribe(
                audio_path=file_handler.get_audio_path(video.id),
                model_name="medium"
            )
            
            update_task_progress(db, subtitle_task.id, 90, TaskStatus.PROCESSING)
            
            # 保存字幕
            for seg in segments:
                subtitle = Subtitle(
                    video_id=video.id,
                    sequence_number=seg["sequence_number"],
                    start_time=seg["start_time"],
                    end_time=seg["end_time"],
                    original_text=seg["original_text"]
                )
                db.add(subtitle)
            
            # 保存 SRT
            srt_content = whisper_service.generate_srt_content(segments)
            srt_path = file_handler.get_subtitle_path(video.id)
            with open(srt_path, "w", encoding="utf-8") as f:
                f.write(srt_content)
                
            db.commit()
            
            update_task_progress(db, subtitle_task.id, 100, TaskStatus.COMPLETED)
            logger.info(f"Subtitles generated for video {video_id}")
            
            if trigger_next_task:
                enhance_video_subtitles.delay(video_id)
            
        except Exception as e:
            logger.error(f"Subtitle generation failed: {e}")
            update_task_progress(db, subtitle_task.id, 0, TaskStatus.FAILED, str(e))
            video.status = VideoStatus.FAILED
            db.commit()
            return

    except Exception as e:
        logger.error(f"Video processing failed: {e}")
        try:
            video = db.query(Video).filter(Video.id == video_id).first()
            if video:
                video.status = VideoStatus.FAILED
                db.commit()
        except:
            pass
    finally:
        db.close()


@celery_app.task(bind=True, name="app.tasks.video_tasks.process_uploaded_video")
def process_uploaded_video(self, video_id: int):
    """
    处理上传的视频（Celery 任务包装器）
    """
    process_video_content(video_id, trigger_next_task=True)
