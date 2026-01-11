"""
字幕增强异步任务
"""
import asyncio
import logging
from datetime import datetime
from typing import List

from celery import shared_task
from sqlalchemy.orm import Session

from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.video import Video, VideoStatus
from app.models.processing_task import ProcessingTask, TaskType, TaskStatus
from app.models.subtitle import Subtitle
from app.models.grammar_analysis import GrammarAnalysis
from app.services.openai_service import openai_service

logger = logging.getLogger(__name__)

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

@celery_app.task(bind=True, name="app.tasks.subtitle_tasks.enhance_video_subtitles")
def enhance_video_subtitles(self, video_id: int):
    """
    增强视频字幕：
    1. 翻译
    2. 音标生成
    3. 语法分析
    
    使用 asyncio 获取并发处理能力
    """
    logger.info(f"Start enhancing subtitles for video {video_id}")
    
    # 由于 Celery worker 默认是同步的，我们需要手动运行异步代码
    loop = asyncio.get_event_loop()
    if loop.is_closed():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    loop.run_until_complete(_process_enhancements(video_id))
    logger.info(f"Finished enhancing subtitles for video {video_id}")

async def _process_enhancements(video_id: int):
    """实际执行增强逻辑的异步函数"""
    db = SessionLocal()
    try:
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            return

        # 获取所有字幕
        subtitles = db.query(Subtitle).filter(Subtitle.video_id == video_id).order_by(Subtitle.sequence_number).all()
        texts = [sub.original_text for sub in subtitles]
        
        if not texts:
            logger.warning(f"No subtitles found for video {video_id}")
            video.status = VideoStatus.COMPLETED
            db.commit()
            return

        # ---------------------------------------------------------------------
        # 1. 任务：翻译
        # ---------------------------------------------------------------------
        trans_task = ProcessingTask(
            video_id=video_id,
            task_type=TaskType.TRANSLATION,
            status=TaskStatus.PENDING
        )
        db.add(trans_task)
        db.commit()
        db.refresh(trans_task)
        
        try:
            update_task_progress(db, trans_task.id, 0, TaskStatus.PROCESSING)
            
            translations = await openai_service.batch_translate_text(texts, batch_size=20)
            
            # 更新数据库
            for i, trans in enumerate(translations):
                subtitles[i].translation = trans
            db.commit()
            
            update_task_progress(db, trans_task.id, 100, TaskStatus.COMPLETED)
            
        except Exception as e:
            logger.error(f"Translation failed: {e}")
            update_task_progress(db, trans_task.id, 0, TaskStatus.FAILED, str(e))
            # 继续执行其他任务，不中断

        # ---------------------------------------------------------------------
        # 2. 任务：音标
        # ---------------------------------------------------------------------
        phonetic_task = ProcessingTask(
            video_id=video_id,
            task_type=TaskType.PHONETIC,
            status=TaskStatus.PENDING
        )
        db.add(phonetic_task)
        db.commit()
        db.refresh(phonetic_task)
        
        try:
            update_task_progress(db, phonetic_task.id, 0, TaskStatus.PROCESSING)
            
            phonetics = await openai_service.batch_generate_phonetic(texts, batch_size=20)
            
            for i, pho in enumerate(phonetics):
                subtitles[i].phonetic = pho
            db.commit()
            
            update_task_progress(db, phonetic_task.id, 100, TaskStatus.COMPLETED)
            
        except Exception as e:
            logger.error(f"Phonetic generation failed: {e}")
            update_task_progress(db, phonetic_task.id, 0, TaskStatus.FAILED, str(e))

        # ---------------------------------------------------------------------
        # 3. 任务：语法分析
        # ---------------------------------------------------------------------
        grammar_task = ProcessingTask(
            video_id=video_id,
            task_type=TaskType.GRAMMAR_ANALYSIS,
            status=TaskStatus.PENDING
        )
        db.add(grammar_task)
        db.commit()
        db.refresh(grammar_task)
        
        try:
            update_task_progress(db, grammar_task.id, 0, TaskStatus.PROCESSING)
            
            # 语法分析比较耗时，批量小一点
            analyses = await openai_service.batch_analyze_grammar(texts, batch_size=5)
            
            for i, analysis_data in enumerate(analyses):
                if analysis_data:
                    # 创建或更新 GrammarAnalysis
                    grammar = db.query(GrammarAnalysis).filter(GrammarAnalysis.subtitle_id == subtitles[i].id).first()
                    if not grammar:
                        grammar = GrammarAnalysis(subtitle_id=subtitles[i].id)
                        db.add(grammar)
                    
                    grammar.sentence_structure = analysis_data.get("sentence_structure")
                    grammar.grammar_points = analysis_data.get("grammar_points")
                    grammar.difficult_words = analysis_data.get("difficult_words")
                    grammar.phrases = analysis_data.get("phrases")
                    grammar.explanation = analysis_data.get("explanation")
            
            db.commit()
            update_task_progress(db, grammar_task.id, 100, TaskStatus.COMPLETED)
            
        except Exception as e:
            logger.error(f"Grammar analysis failed: {e}")
            update_task_progress(db, grammar_task.id, 0, TaskStatus.FAILED, str(e))

        # ---------------------------------------------------------------------
        # 完成所有流程
        # ---------------------------------------------------------------------
        video.status = VideoStatus.COMPLETED
        db.commit()
        logger.info(f"All processing completed for video {video_id}")

    except Exception as e:
        logger.error(f"Error in enhance_video_subtitles: {e}")
        # 只有在非常严重的错误下才标记视频失败，否则尽量已完成的部分为准
        try:
            video = db.query(Video).filter(Video.id == video_id).first()
            if video:
                # 检查是否有任何任务成功了，如果有，可能不应该完全标记为 failed
                # 简单起见，如果这里崩溃了，标记为 FAILED
                video.status = VideoStatus.FAILED
                db.commit()
        except:
            pass
    finally:
        db.close()
