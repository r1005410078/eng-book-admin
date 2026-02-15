from datetime import datetime, timedelta
from celery import shared_task
from app.core.database import SessionLocal
from app.models.course import Lesson
from app.models.video import Video
from app.models.processing_task import ProcessingTask, TaskStatus
from app.utils.file_handler import file_handler
import logging

logger = logging.getLogger(__name__)

@shared_task(name="app.tasks.cleanup_deleted_lessons")
def cleanup_deleted_lessons():
    """
    Garbage Collection:
    Find lessons marked as deleted and clean up their associated video files and DB records.
    执行 GC (Garbage Collection): 清理已软删除的 Lesson 所关联的视频文件及数据。
    """
    db = SessionLocal()
    try:
        # 查找已软删除且仍关联视频的课时
        deleted_lessons = db.query(Lesson).filter(
            Lesson.is_deleted == True,
            Lesson.video_id.isnot(None)
        ).all()
        
        if not deleted_lessons:
            logger.info("GC: No deleted lessons found needing cleanup.")
            return

        logger.info(f"GC: Found {len(deleted_lessons)} deleted lessons. Starting cleanup...")
        
        cleanup_count = 0
        for lesson in deleted_lessons:
            video_id = lesson.video_id
            
            try:
                # 1. 删除物理文件 (Videos, Thumbnails, Subtitles on disk if any)
                # 使用 file_handler 提供的删除方法
                file_handler.delete_video_files(video_id)
                logger.info(f"GC: Deleted files for video {video_id}")
                
                # 2. 删除 Video 记录 (Cascade 会自动删除 Subtitles, ProcessingTasks)
                video = db.query(Video).filter(Video.id == video_id).first()
                if video:
                    db.delete(video)
                    cleanup_count += 1
                
                # 3. DB commit 会自动将 lesson.video_id 置为 NULL (如果设置了 ON DELETE SET NULL)
                # 无需手动设置，但为了代码清晰，ORM 对象状态更新一下
                lesson.video_id = None
                
            except Exception as e:
                logger.error(f"GC: Error cleaning up lessons resources for video {video_id}: {e}")
                # 继续处理下一个，不中断循环
                continue
            
        db.commit()
        logger.info(f"GC: Successfully cleaned up resources for {cleanup_count} lessons.")
        
    except Exception as e:
        logger.error(f"GC: System error during cleanup: {e}")
        db.rollback()
    finally:
        db.close()

@shared_task(name="app.tasks.monitor_stuck_tasks")
def monitor_stuck_tasks():
    """
    Auto Task Recovery / Monitor:
    Find tasks that have been in PROCESSING state for too long (> 1 hour) and mark as FAILED.
    监控卡死的任务：将处理时间超过 1 小时的任务标记为失败，防止前端永久 Loading。
    """
    db = SessionLocal()
    try:
        # 定义超时阈值 (1小时)
        timeout_threshold = datetime.utcnow() - timedelta(hours=1)
        
        stuck_tasks = db.query(ProcessingTask).filter(
            ProcessingTask.status == TaskStatus.PROCESSING,
            ProcessingTask.started_at < timeout_threshold
        ).all()
        
        if not stuck_tasks:
            logger.info("Monitor: No stuck tasks found.")
            return

        logger.warning(f"Monitor: Found {len(stuck_tasks)} stuck tasks. Marking as FAILED.")
        
        for task in stuck_tasks:
            task.status = TaskStatus.FAILED
            task.error_message = "Task timed out (stuck in PROCESSING for > 1h)"
            task.completed_at = datetime.utcnow()
            # 这里可以扩展：尝试由于某些原因自动重试 (Retry logic)
            
        db.commit()
        logger.info(f"Monitor: Automatically failed {len(stuck_tasks)} tasks.")
        
    except Exception as e:
        logger.error(f"Monitor: Error checking stuck tasks: {e}")
        db.rollback()
    finally:
        db.close()
