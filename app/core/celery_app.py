"""
Celery 应用配置
"""
from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "worker",
    broker=settings.CELERY_BROKER_URL or settings.REDIS_URL,
    backend=settings.CELERY_RESULT_BACKEND or settings.CELERY_BROKER_URL or settings.REDIS_URL,
    include=[
        "app.tasks.video_tasks",
        "app.tasks.subtitle_tasks",
    ]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    broker_connection_retry_on_startup=True,
    # 增加 Redis 连接稳定性配置
    broker_transport_options={
        "visibility_timeout": 3600,
        "max_retries": 3,
        "interval_start": 0,
        "interval_step": 0.2,
        "interval_max": 0.5,
    },
    result_backend_transport_options={
        "retry_policy": {
            "timeout": 5.0
        }
    },
    # 任务配置
    task_acks_late=True,  # 任务完成后才确认
    task_reject_on_worker_lost=True,  # worker 丢失时拒绝任务（重新入队）
    worker_prefetch_multiplier=1,  # 每个 worker 每次预取 1 个任务（避免长时间任务阻塞）
)

# 路由配置（可选：将视频处理任务分配到特定队列）
celery_app.conf.task_routes = {
    "app.tasks.video_tasks.*": {"queue": "video_processing"},
    "app.tasks.subtitle_tasks.*": {"queue": "ai_processing"},
}
