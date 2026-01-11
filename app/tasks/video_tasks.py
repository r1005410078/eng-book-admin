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

@celery_app.task(bind=True, name="app.tasks.video_tasks.process_uploaded_video")
def process_uploaded_video(self, video_id: int):
    """
    处理上传的视频：
    1. 提取元数据（如果上传时未完成）
    2. 提取音频
    3. 生成字幕 (Whisper)
    4. 触发字幕增强任务
    """
    logger.info(f"Start processing video {video_id}")
    
    db = SessionLocal()
    try:
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            logger.error(f"Video {video_id} not found")
            return

        # 更新视频状态
        video.status = VideoStatus.PROCESSING
        db.commit()

        # 1. 任务：音频提取
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
            
            # 更新视频元数据（如果之前缺失）
            if not video.duration:
                metadata = ffmpeg_service.get_video_metadata(video_path)
                video.duration = metadata.get("duration")
                video.resolution = metadata.get("resolution")
                video.format = metadata.get("format")
                video.file_size = metadata.get("size")
                
                # 生成缩略图
                thumb_path = ffmpeg_service.generate_thumbnail(video_path)
                if thumb_path:
                    relative_thumb_path = str(thumb_path.relative_to(file_handler.upload_dir))
                    video.thumbnail_path = relative_thumb_path
                
                db.commit()
            
            # 提取音频
            audio_path = ffmpeg_service.extract_audio(video_path)
            
            update_task_progress(db, audio_task.id, 100, TaskStatus.COMPLETED)
            logger.info(f"Audio extracted for video {video_id}")
            
        except Exception as e:
            logger.error(f"Audio extraction failed: {e}")
            update_task_progress(db, audio_task.id, 0, TaskStatus.FAILED, str(e))
            video.status = VideoStatus.FAILED
            db.commit()
            return

        # 2. 任务：字幕生成
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
            
            # 使用 Whisper 生成字幕
            # 可以分阶段更新进度，这里简单处理为完成后更新
            # Whisper 转录可能比较耗时，后续可以添加更细粒度的进度回调
            segments = whisper_service.transcribe(
                audio_path=file_handler.get_audio_path(video.id),
                model_name="medium"  # 可以根据配置调整
            )
            
            update_task_progress(db, subtitle_task.id, 90, TaskStatus.PROCESSING)
            
            # 保存到数据库
            for seg in segments:
                subtitle = Subtitle(
                    video_id=video.id,
                    sequence_number=seg["sequence_number"],
                    start_time=seg["start_time"],
                    end_time=seg["end_time"],
                    original_text=seg["original_text"]
                )
                db.add(subtitle)
            
            # 生成并保存 SRT 文件
            srt_content = whisper_service.generate_srt_content(segments)
            srt_path = file_handler.get_subtitle_path(video.id)
            with open(srt_path, "w", encoding="utf-8") as f:
                f.write(srt_content)
                
            db.commit()
            
            update_task_progress(db, subtitle_task.id, 100, TaskStatus.COMPLETED)
            logger.info(f"Subtitles generated for video {video_id}")
            
            # 3. 触发后续任务：字幕增强 (异步触发)
            enhance_video_subtitles.delay(video_id)
            
            # 注意：视频状态将在所有增强任务完成后才设为 COMPLETED
            # 但在这里，我们可以认为核心处理已完成，或者保持 PROCESSING
            
        except Exception as e:
            logger.error(f"Subtitle generation failed: {e}")
            update_task_progress(db, subtitle_task.id, 0, TaskStatus.FAILED, str(e))
            video.status = VideoStatus.FAILED
            db.commit()
            return

    except Exception as e:
        logger.error(f"Video processing failed: {e}")
        # 尝试更新视频状态为失败
        try:
            video = db.query(Video).filter(Video.id == video_id).first()
            if video:
                video.status = VideoStatus.FAILED
                db.commit()
        except:
            pass
    finally:
        db.close()
