"""
视频处理进度服务
"""
from typing import List, Optional, Dict
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.video import Video, VideoStatus
from app.models.processing_task import ProcessingTask, TaskType, TaskStatus
from app.schemas.video import SubTaskProgress, TaskProgressResponse


# 定义处理步骤及其权重（总和为 100）
PROCESSING_STEP_WEIGHTS = {
    TaskType.AUDIO_EXTRACTION: 10,
    TaskType.SUBTITLE_GENERATION: 20,
    TaskType.TRANSLATION: 30,
    TaskType.PHONETIC: 20,
    TaskType.GRAMMAR_ANALYSIS: 20,
}


class VideoProgressService:
    """视频处理进度服务"""
    
    @staticmethod
    def calculate_total_progress(tasks: List[ProcessingTask]) -> int:
        """
        计算总体进度
        
        Args:
            tasks: 处理任务列表
            
        Returns:
            总体进度 (0-100)
        """
        if not tasks:
            return 0
        
        total_progress = 0
        for task in tasks:
            weight = PROCESSING_STEP_WEIGHTS.get(task.task_type, 0)
            # 总进度 = Σ(子任务进度 × 权重 / 100)
            total_progress += (task.progress * weight) // 100
        
        return min(total_progress, 100)
    
    @staticmethod
    def get_task_progress(
        db: Session,
        video_id: int
    ) -> Optional[TaskProgressResponse]:
        """
        获取视频处理进度
        
        Args:
            db: 数据库会话
            video_id: 视频ID
            
        Returns:
            任务进度响应，如果视频不存在则返回 None
        """
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            return None
        
        tasks = db.query(ProcessingTask).filter(
            ProcessingTask.video_id == video_id
        ).order_by(ProcessingTask.created_at).all()
        
        # 如果没有任务记录，返回初始状态
        if not tasks:
            # 创建所有任务类型的初始状态
            sub_tasks = [
                SubTaskProgress(
                    name=task_type.value,
                    status=TaskStatus.PENDING.value,
                    progress=0
                )
                for task_type in TaskType
            ]
            
            return TaskProgressResponse(
                video_id=video.id,
                status=video.status.value,
                progress=0,
                tasks=sub_tasks,
                started_at=None,
                updated_at=video.updated_at
            )
        
        # 计算总体进度
        total_progress = VideoProgressService.calculate_total_progress(tasks)
        
        # 如果视频状态是 COMPLETED，强制进度为 100
        if video.status == VideoStatus.COMPLETED:
            total_progress = 100
        
        # 格式化子任务列表
        sub_tasks = [
            SubTaskProgress(
                name=task.task_type.value,
                status=task.status.value,
                progress=task.progress
            )
            for task in tasks
        ]
        
        # 获取时间信息
        started_at = min(
            (t.started_at for t in tasks if t.started_at),
            default=None
        )
        updated_at = max(
            (t.completed_at or t.started_at for t in tasks if t.started_at or t.completed_at),
            default=datetime.utcnow()
        )
        
        return TaskProgressResponse(
            video_id=video.id,
            status=video.status.value,
            progress=total_progress,
            tasks=sub_tasks,
            started_at=started_at,
            updated_at=updated_at
        )
    
    @staticmethod
    def check_running_task(db: Session, video_id: int) -> bool:
        """
        检查视频是否有正在进行的任务
        
        Args:
            db: 数据库会话
            video_id: 视频ID
            
        Returns:
            如果有正在进行的任务返回 True，否则返回 False
        """
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            return False
        
        # 检查视频状态
        if video.status == VideoStatus.PROCESSING:
            return True
        
        # 检查是否有 PENDING 或 PROCESSING 状态的任务
        running_tasks = db.query(ProcessingTask).filter(
            ProcessingTask.video_id == video_id,
            ProcessingTask.status.in_([TaskStatus.PENDING, TaskStatus.PROCESSING])
        ).count()
        
        return running_tasks > 0
    
    @staticmethod
    def create_initial_tasks(db: Session, video_id: int) -> List[ProcessingTask]:
        """
        为视频创建初始的处理任务记录
        
        Args:
            db: 数据库会话
            video_id: 视频ID
            
        Returns:
            创建的任务列表
        """
        tasks = []
        for task_type in TaskType:
            task = ProcessingTask(
                video_id=video_id,
                task_type=task_type,
                status=TaskStatus.PENDING,
                progress=0
            )
            db.add(task)
            tasks.append(task)
        
        db.commit()
        return tasks
