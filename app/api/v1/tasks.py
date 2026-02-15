from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload
from typing import Optional
from app.core.database import get_db
from app.models.processing_task import ProcessingTask, TaskStatus, TaskType
from app.models.video import Video
from app.schemas.task import TaskListResponse, TaskResponse

router = APIRouter()

@router.get("/", response_model=TaskListResponse)
def list_tasks(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    status: Optional[TaskStatus] = None,
    type: Optional[TaskType] = None,
    video_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Get backend processing task list.
    Supports pagination, filtering by status, type and video_id.
    """
    query = db.query(ProcessingTask)

    if status:
        query = query.filter(ProcessingTask.status == status)
    if type:
        query = query.filter(ProcessingTask.task_type == type)
    if video_id:
        query = query.filter(ProcessingTask.video_id == video_id)

    # Preload video to get title
    query = query.options(joinedload(ProcessingTask.video))

    total = query.count()
    items = query.order_by(ProcessingTask.created_at.desc()) \
                 .offset((page - 1) * size) \
                 .limit(size) \
                 .all()

    # Manual mapping to include video_title
    task_responses = []
    for item in items:
        # Map TaskType/TaskStatus from models to schema Enums (if necessary)
        # sqlalchemy Enums sometimes need casting or just match string value
        
        task_dict = {
            "id": item.id,
            "video_id": item.video_id,
            "video_title": item.video.title if item.video else None,
            "task_type": item.task_type.value if hasattr(item.task_type, 'value') else item.task_type,
            "status": item.status.value if hasattr(item.status, 'value') else item.status,
            "progress": item.progress,
            "error_message": item.error_message,
            "created_at": item.created_at,
            "started_at": item.started_at,
            "completed_at": item.completed_at
        }
        task_responses.append(TaskResponse(**task_dict))

    return {
        "total": total,
        "items": task_responses,
        "page": page,
        "size": size
    }
