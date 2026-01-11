"""
视频相关 API 路由
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, BackgroundTasks
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import settings
from app.models.video import Video, VideoStatus, DifficultyLevel
from app.models.processing_task import ProcessingTask
from app.models.subtitle import Subtitle
from app.models.grammar_analysis import GrammarAnalysis
from app.schemas.video import VideoCreate, VideoResponse, VideoListResponse, VideoUpdate
from app.schemas.subtitle import ProcessingTaskResponse, SubtitleWithGrammarResponse
from app.utils.file_handler import file_handler
from app.tasks.video_tasks import process_uploaded_video
from app.tasks.subtitle_tasks import enhance_video_subtitles

router = APIRouter()


@router.post("/upload", response_model=VideoResponse)
async def upload_video(
    file: UploadFile = File(...),
    title: str = Form(None),
    description: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    difficulty_level: Optional[DifficultyLevel] = Form(None),
    db: Session = Depends(get_db)
):
    """
    上传视频
    """
    # 验证文件格式
    if not file_handler.is_video_format_supported(file.filename):
        raise HTTPException(status_code=400, detail="不支持的视频格式")
        
    # 如果未提供标题，使用文件名
    if not title:
        title = file.filename
        
    # 创建视频记录
    video = Video(
        title=title,
        description=description,
        category=category,
        difficulty_level=difficulty_level,
        file_path="",  # 暂时为空，保存后更新
        status=VideoStatus.UPLOADING
    )
    db.add(video)
    db.commit()
    db.refresh(video)
    
    try:
        # 保存文件
        content = await file.read()
        saved_path = file_handler.save_uploaded_file(content, video.id, file.filename)
        file_size = len(content)
        
        # 更新视频信息
        video.file_path = saved_path
        video.file_size = file_size
        video.status = VideoStatus.UPLOADING  # 仍然是 uploading，直到触发处理
        db.commit()
        db.refresh(video)
        
        # 触发异步处理任务
        process_uploaded_video.delay(video.id)
        
        return video
    except Exception as e:
        # 清理失败的记录
        db.delete(video)
        db.commit()
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")


@router.get("/", response_model=VideoListResponse)
def list_videos(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    status: Optional[VideoStatus] = None,
    difficulty: Optional[DifficultyLevel] = None,
    keyword: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    获取视频列表
    """
    query = db.query(Video)
    
    if status:
        query = query.filter(Video.status == status)
    if difficulty:
        query = query.filter(Video.difficulty_level == difficulty)
    if keyword:
        query = query.filter(Video.title.contains(keyword))
        
    total = query.count()
    items = query.order_by(Video.created_at.desc()).offset((page - 1) * size).limit(size).all()
    
    return {
        "total": total,
        "items": items,
        "page": page,
        "size": size
    }


@router.get("/{video_id}", response_model=VideoResponse)
def get_video(video_id: int, db: Session = Depends(get_db)):
    """
    获取视频详情
    """
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="视频不存在")
        
    # 计算总体进度
    total_progress = 0
    tasks = db.query(ProcessingTask).filter(ProcessingTask.video_id == video_id).all()
    if tasks:
        # 简单算法：平均所有任务的进度
        total_progress = sum(t.progress for t in tasks) // len(tasks)
        
    # 动态添加 progress 属性给 schema
    video.progress = total_progress
    return video


@router.delete("/{video_id}")
def delete_video(video_id: int, db: Session = Depends(get_db)):
    """
    删除视频及相关文件
    """
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="视频不存在")
        
    # 删除数据库记录（级联删除会处理关联表）
    db.delete(video)
    db.commit()
    
    # 删除物理文件
    file_handler.delete_video_files(video_id)
    
    return {"message": "删除成功"}


@router.get("/{video_id}/status", response_model=List[ProcessingTaskResponse])
def get_video_status(video_id: int, db: Session = Depends(get_db)):
    """
    获取视频处状态详情
    """
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="视频不存在")
        
    tasks = db.query(ProcessingTask).filter(ProcessingTask.video_id == video_id).all()
    return tasks


@router.post("/{video_id}/reprocess")
def reprocess_video(video_id: int, db: Session = Depends(get_db)):
    """
    重新处理视频
    """
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="视频不存在")
        
    # 清除旧的任务记录和字幕
    db.query(ProcessingTask).filter(ProcessingTask.video_id == video_id).delete()
    db.query(Subtitle).filter(Subtitle.video_id == video_id).delete()
    
    video.status = VideoStatus.PROCESSING
    db.commit()
    
    # 触发处理
    process_uploaded_video.delay(video.id)
    
    return {"message": "重新处理任务已提交"}


@router.get("/{video_id}/subtitles", response_model=List[SubtitleWithGrammarResponse])
def get_video_subtitles(
    video_id: int,
    include_grammar: bool = False,
    db: Session = Depends(get_db)
):
    """
    获取视频字幕
    """
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="视频不存在")
        
    query = db.query(Subtitle).filter(Subtitle.video_id == video_id).order_by(Subtitle.sequence_number)
    
    subtitles = query.all()
    
    if include_grammar:
        # 如果需要语法分析，确保加载关系（虽然 ORM lazy load 会做，但显式连接更高效）
        # 这里 Pydantic 会自动处理来自 relationship 的数据
        pass
        
    return subtitles
