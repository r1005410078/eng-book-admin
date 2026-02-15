from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session, joinedload
from app.core.database import get_db
from app.models.course import Lesson
from app.models.video import Video
from app.models.subtitle import Subtitle
from app.models.grammar_analysis import GrammarAnalysis
from app.schemas.course import LessonContentResponse, SubtitleTrackResponse
from app.schemas.subtitle import (
    LessonSubtitlesResponse, 
    SubtitleDetailResponse, 
    GrammarAnalysisItem
)
from app.core.config import settings
import logging

# Set up logger
logger = logging.getLogger(__name__)

router = APIRouter()

def format_time_vtt(seconds: float) -> str:
    """Format seconds to VTT timestamp HH:MM:SS.mmm"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"

@router.get("/{lesson_id}/content", response_model=LessonContentResponse)
def get_lesson_content(lesson_id: int, db: Session = Depends(get_db)):
    """
    Get lesson content URLs (Video, Subtitles, Thumbnail)
    """
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
        
    if not lesson.video_id:
        raise HTTPException(status_code=404, detail="No video associated with this lesson")
        
    video = db.query(Video).filter(Video.id == lesson.video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
        
    # Construct URLs (Assuming /uploads is mounted as static)
    # Ensure paths are relative and clean
    video_path = video.file_path.replace("\\", "/") # Normalize Windows paths if any
    
    # Base URL prefix for static files
    # In production, this might be a CDN URL from settings
    static_prefix = "/uploads"
    
    video_url = f"{static_prefix}/{video_path}"
    
    thumbnail_url = None
    if video.thumbnail_path:
        thumb_path = video.thumbnail_path.replace("\\", "/")
        thumbnail_url = f"{static_prefix}/{thumb_path}"
        
    # Subtitles
    # We offer a dynamic VTT endpoint
    # TODO: In future, we might save .vtt file to disk and serve statically
    # For now, generate on fly
    subtitle_url = f"{settings.API_V1_PREFIX}/lessons/{lesson_id}/subtitle.vtt"
    
    subtitles = [
        SubtitleTrackResponse(
            language="en", 
            url=subtitle_url, 
            label="English"
        )
    ]
    
    return LessonContentResponse(
        lesson_id=lesson.id,
        title=lesson.title,
        video_url=video_url,
        duration=video.duration,
        thumbnail_url=thumbnail_url,
        subtitles=subtitles,
        status=lesson.processing_status
    )

@router.get("/{lesson_id}/subtitle.vtt", response_class=PlainTextResponse)
def get_lesson_subtitle_vtt(lesson_id: int, db: Session = Depends(get_db)):
    """
    Generate VTT subtitle file dynamically from DB
    """
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson or not lesson.video_id:
        raise HTTPException(status_code=404, detail="Lesson not found")
        
    subtitles = db.query(Subtitle).filter(
        Subtitle.video_id == lesson.video_id
    ).order_by(Subtitle.sequence_number).all()
    
    # Build VTT content
    vtt_lines = ["WEBVTT", ""]
    
    for sub in subtitles:
        start = format_time_vtt(float(sub.start_time))
        end = format_time_vtt(float(sub.end_time))
        
        vtt_lines.append(f"{sub.sequence_number}")
        vtt_lines.append(f"{start} --> {end}")
        vtt_lines.append(sub.original_text)
        vtt_lines.append("") # Empty line after each block
        
    return "\n".join(vtt_lines)


@router.get("/{lesson_id}/subtitles", response_model=LessonSubtitlesResponse)
def get_lesson_subtitles(lesson_id: int, db: Session = Depends(get_db)):
    """
    获取课程的完整字幕数据
    包括翻译、音标和语法分析
    """
    # 查询课程
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    
    if not lesson.video_id:
        raise HTTPException(
            status_code=404, 
            detail="No video associated with this lesson"
        )
    
    # 查询字幕，预加载语法分析
    subtitles = db.query(Subtitle).options(
        joinedload(Subtitle.grammar_analysis)
    ).filter(
        Subtitle.video_id == lesson.video_id
    ).order_by(Subtitle.sequence_number).all()
    
    # 构建响应
    subtitle_details = []
    for sub in subtitles:
        # Extract grammar analysis items from difficult_words JSONB
        grammar_items = []
        if sub.grammar_analysis and sub.grammar_analysis.difficult_words:
            # difficult_words stored as list of dicts: {word, definition, phonetic, part_of_speech}
            # Mapping to GrammarAnalysisItem: word, part_of_speech, explanation(definition), translation
            for word_data in sub.grammar_analysis.difficult_words:
                grammar_items.append(GrammarAnalysisItem(
                    word=word_data.get("word", ""),
                    part_of_speech=word_data.get("part_of_speech", ""),
                    explanation=word_data.get("definition", ""), # definition corresponds to explanation
                    translation=None # translation is not explicitly in difficult_words structure, maybe definition IS translation?
                ))
        
        subtitle_details.append(SubtitleDetailResponse(
            sequence_number=sub.sequence_number,
            start_time=sub.start_time,
            end_time=sub.end_time,
            original_text=sub.original_text,
            translation=sub.translation,
            phonetic=sub.phonetic,
            grammar_analysis=grammar_items
        ))
    
    return LessonSubtitlesResponse(
        lesson_id=lesson.id,
        video_id=lesson.video_id,
        subtitle_count=len(subtitle_details),
        subtitles=subtitle_details
    )

from fastapi import Header
from app.schemas.learning import ProgressUpdate, AskQuestionRequest
from app.services.learning_service import LearningService
from app.services.openai_service import openai_service

@router.post("/{lesson_id}/progress", summary="上报学习进度")
def report_lesson_progress(
    lesson_id: int,
    progress: ProgressUpdate,
    x_user_id: int = Header(..., description="用户ID (Mock Auth)"),
    db: Session = Depends(get_db)
):
    """
    上报课时学习进度 (无需鉴权，通过 Header 传递 user_id)
    """
    service = LearningService(db)
    
    # 验证 Lesson 存在
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    result = service.update_lesson_progress(
        user_id=x_user_id,
        lesson_id=lesson_id,
        status=progress.status,
        progress=progress.progress_percent,
        position=progress.last_position_seconds
    )
    return {"message": "Progress updated", "status": result.status}

@router.post("/{lesson_id}/ask-syntax", summary="语法提问")
async def ask_syntax_question(
    lesson_id: int,
    request: AskQuestionRequest,
    x_user_id: int = Header(..., description="User ID"),
    db: Session = Depends(get_db)
):
    """
    针对当前课时内容/句子进行语法提问 (调用 OpenAI)
    """
    # Verify lesson
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
        
    try:
        answer = await openai_service.answer_syntax_question(
            question=request.question,
            context=request.context_text
        )
        return {"answer": answer}
    except Exception as e:
        logger.error(f"Ask syntax failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to get answer from AI")
