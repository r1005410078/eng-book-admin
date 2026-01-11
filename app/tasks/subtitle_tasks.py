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

async def enhance_subtitles_content(video_id: int):
    """
    增强视频字幕内容的核心异步逻辑
    """
    logger.info(f"Start enhancing subtitles content for video {video_id}")
    
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

        # 1. 任务：翻译
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

        # 2. 任务：音标
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

        # 3. 任务：语法分析
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
                    # 确保 grammar_points 是字符串列表
                    grammar_points = analysis_data.get("grammar_points", [])
                    if isinstance(grammar_points, list):
                        grammar.grammar_points = [
                            str(gp) if not isinstance(gp, str) else gp 
                            for gp in grammar_points
                        ]
                    else:
                        grammar.grammar_points = []
                        
                    grammar.difficult_words = analysis_data.get("difficult_words")
                    
                    # 确保 phrases 是字符串列表
                    phrases = analysis_data.get("phrases", [])
                    if isinstance(phrases, list):
                        grammar.phrases = [
                            str(p) if not isinstance(p, str) else p 
                            for p in phrases
                        ]
                    else:
                        grammar.phrases = []

                    grammar.explanation = analysis_data.get("explanation")
            
            db.commit()
            update_task_progress(db, grammar_task.id, 100, TaskStatus.COMPLETED)
            
        except Exception as e:
            logger.error(f"Grammar analysis failed: {e}")
            update_task_progress(db, grammar_task.id, 0, TaskStatus.FAILED, str(e))

        # ---------------------------------------------------------------------
        # 保存双语字幕文件
        # ---------------------------------------------------------------------
        from app.utils.file_handler import file_handler
        from app.utils.srt_parser import SRTParser
        
        # 将 SQLAlchemy 对象转换为字典列表以便生成 SRT
        sub_dicts = []
        for sub in subtitles:
            sub_dicts.append({
                "sequence_number": sub.sequence_number,
                "start_time": sub.start_time,
                "end_time": sub.end_time,
                "original_text": sub.original_text,
                "translation": sub.translation
            })
            
        srt_content = SRTParser.generate_srt(sub_dicts, dual_language=True)
        srt_path = file_handler.get_subtitle_path(video.id)
        
        # 覆盖原文件
        with open(srt_path, "w", encoding="utf-8") as f:
            f.write(srt_content)
            
        logger.info(f"Updated bilingual subtitles file for video {video_id}")

        # 完成所有流程
        video.status = VideoStatus.COMPLETED
        db.commit()
        logger.info(f"All processing completed for video {video_id}")

    except Exception as e:
        logger.error(f"Error in enhance_subtitles_content: {e}")
        try:
            video = db.query(Video).filter(Video.id == video_id).first()
            if video:
                video.status = VideoStatus.FAILED
                db.commit()
        except:
            pass
    finally:
        db.close()

@celery_app.task(bind=True, name="app.tasks.subtitle_tasks.enhance_video_subtitles")
def enhance_video_subtitles(self, video_id: int):
    """
    增强视频字幕（Celery 任务包装器）
    """
    logger.info(f"Start enhancing subtitles for video {video_id}")
    
    # Celery worker 同步环境中运行异步代码
    loop = asyncio.get_event_loop()
    if loop.is_closed():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    loop.run_until_complete(enhance_subtitles_content(video_id))
    logger.info(f"Finished enhancing subtitles for video {video_id}")
