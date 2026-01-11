"""
视频业务逻辑服务
"""
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.video import Video, VideoStatus, DifficultyLevel
from app.models.processing_task import ProcessingTask
from app.schemas.video import VideoCreate, VideoUpdate


class VideoService:
    @staticmethod
    def get_by_id(db: Session, video_id: int) -> Optional[Video]:
        """根据 ID 获取视频"""
        return db.query(Video).filter(Video.id == video_id).first()

    @staticmethod
    def get_multi(
        db: Session,
        skip: int = 0,
        limit: int = 20,
        status: Optional[VideoStatus] = None,
        difficulty: Optional[DifficultyLevel] = None,
        keyword: Optional[str] = None
    ) -> Tuple[List[Video], int]:
        """
        查询视频列表
        
        Returns:
            (items, total_count)
        """
        query = db.query(Video)
        
        if status:
            query = query.filter(Video.status == status)
        if difficulty:
            query = query.filter(Video.difficulty_level == difficulty)
        if keyword:
            query = query.filter(Video.title.contains(keyword))
            
        total = query.count()
        items = query.order_by(desc(Video.created_at)).offset(skip).limit(limit).all()
        return items, total

    @staticmethod
    def create(db: Session, obj_in: VideoCreate) -> Video:
        """创建视频记录"""
        db_obj = Video(
            title=obj_in.title,
            description=obj_in.description,
            category=obj_in.category,
            difficulty_level=obj_in.difficulty_level,
            tags=obj_in.tags,
            file_path="",  # Create empty, update after upload
            status=VideoStatus.UPLOADING
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    @staticmethod
    def update(db: Session, db_obj: Video, obj_in: VideoUpdate) -> Video:
        """更新视频信息"""
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
            
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    @staticmethod
    def delete(db: Session, video_id: int) -> bool:
        """
        删除视频
        注意：这只删除数据库记录，物理文件删除应由 FileHandler 处理
        """
        obj = db.query(Video).filter(Video.id == video_id).first()
        if not obj:
            return False
            
        db.delete(obj)
        db.commit()
        return True

    @staticmethod
    def get_progress(db: Session, video_id: int) -> int:
        """获取视频处理总进度"""
        tasks = db.query(ProcessingTask).filter(ProcessingTask.video_id == video_id).all()
        if not tasks:
            return 0
        return sum(t.progress for t in tasks) // len(tasks)


video_service = VideoService()
