"""Celery 应用工厂：配置 broker/序列化/超时，并注册任务模块。"""

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "pfs",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,
    task_soft_time_limit=270,
)

# 注册全部异步任务模块
celery_app.conf.include = [
    "app.tasks.ocr_tasks",
    "app.tasks.grading_tasks",
    "app.tasks.feedback_tasks",
]
