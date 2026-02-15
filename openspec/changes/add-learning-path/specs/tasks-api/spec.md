# 任务列表 API 规范 (Task List API Specification)

## 概述

新增 API 端点，用于获取系统的后台处理任务列表。该接口支持分页、筛选任务状态和类型，已便于监控视频处理进度。

## API 端点

### GET /api/v1/tasks/

获取后台处理任务列表。

#### 请求参数 (Query Parameters)

| 参数名 | 类型 | 必填 |默认值 | 描述 |
| :--- | :--- | :--- | :--- | :--- |
| `page` | integer | 否 | 1 | 页码，从 1 开始 |
| `size` | integer | 否 | 20 | 每页数量，最大 100 |
| `status` | string | 否 | null | 任务状态筛选 (pending, processing, completed, failed) |
| `type` | string | 否 | null | 任务类型筛选 (audio_extraction, subtitle_generation, translation, phonetic, grammar_analysis) |
| `video_id` | integer | 否 | null | 筛选特定视频的任务 |

#### 响应格式

```json
{
  "total": 100,
  "items": [
    {
      "id": 169,
      "video_id": 92,
      "task_type": "phonetic",
      "status": "completed",
      "progress": 100,
      "error_message": null,
      "created_at": "2026-02-15T10:10:54.516000",
      "started_at": "2026-02-15T10:10:54.520000",
      "completed_at": "2026-02-15T10:11:35.000000",
      "video_title": "Video Title Example"
    }
  ],
  "page": 1,
  "size": 20
}
```

## 数据模型

### Pydantic Schemas

更新或创建 `app/schemas/task.py` (如果有，否则在 `app/schemas/video.py` 或新建)。建议新建 `app/schemas/task.py` 以保持清晰。

```python
from enum import Enum
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel

# 复用 models 中的 Enum 定义，或者重新定义以解耦
class TaskType(str, Enum):
    AUDIO_EXTRACTION = "audio_extraction"
    SUBTITLE_GENERATION = "subtitle_generation"
    TRANSLATION = "translation"
    PHONETIC = "phonetic"
    GRAMMAR_ANALYSIS = "grammar_analysis"

class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class TaskResponse(BaseModel):
    id: int
    video_id: int
    video_title: Optional[str] = None # 从关联的 Video 获取标题
    task_type: TaskType
    status: TaskStatus
    progress: int
    error_message: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class TaskListResponse(BaseModel):
    total: int
    items: List[TaskResponse]
    page: int
    size: int
```

## 实现细节

### 1. 新建 `app/api/v1/tasks.py`

创建一个新的路由文件专门处理任务相关的 API。

```python
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
    query = db.query(ProcessingTask)

    if status:
        query = query.filter(ProcessingTask.status == status)
    if type:
        query = query.filter(ProcessingTask.task_type == type)
    if video_id:
        query = query.filter(ProcessingTask.video_id == video_id)

    # 预加载 video 以获取标题
    query = query.options(joinedload(ProcessingTask.video))

    total = query.count()
    # 默认按创建时间倒序
    items = query.order_by(ProcessingTask.created_at.desc()) \
                 .offset((page - 1) * size) \
                 .limit(size) \
                 .all()

    # 转换逻辑（如果需要处理 video_title）
    # Pydantic via from_attributes 应该能处理 relationship，但需要在 schema 中定义 video: VideoSimpleResponse 或者手动映射
    # 这里我们选择手动映射或者在 Schema 中增加 video_title 字段并使用 validator 或 property
    
    task_responses = []
    for item in items:
        task_dict = {
            "id": item.id,
            "video_id": item.video_id,
            "task_type": item.task_type,
            "status": item.status,
            "progress": item.progress,
            "error_message": item.error_message,
            "created_at": item.created_at,
            "started_at": item.started_at,
            "completed_at": item.completed_at,
            "video_title": item.video.title if item.video else None
        }
        task_responses.append(TaskResponse(**task_dict))

    return {
        "total": total,
        "items": task_responses,
        "page": page,
        "size": size
    }
```

### 2. 注册路由

在 `app/api/v1/router.py` 中注册新的 `tasks` 路由。

### 3. Schema 定义

创建 `app/schemas/task.py`。

## 测试计划

1.  **列表查询**: 测试无参数查询，返回最近的任务。
2.  **筛选测试**: 测试按 `status`, `type`, `video_id` 筛选。
3.  **分页测试**: 测试 `page` 和 `size` 参数。
4.  **关联数据**: 验证返回结果中包含 `video_title`。

## 验收标准

- [ ] 新建 `app/schemas/task.py`
- [ ] 新建 `app/api/v1/tasks.py`
- [ ] 注册路由 `/api/v1/tasks`
- [ ] API 返回正确的任务列表及总数
- [ ] 支持筛选和分页
