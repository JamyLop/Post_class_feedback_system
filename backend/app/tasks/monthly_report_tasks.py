"""兼容已入队的旧任务；月度评定改为手写后不再执行 AI。"""

import logging

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, acks_late=True)
def generate_monthly_report_task(self, report_id: int):
    # 保留任务名以消费旧消息，但不得生成内容或覆盖教师草稿。
    logger.info("monthly_ai_disabled report_id=%s", report_id)
    return {"skipped": True, "reason": "manual_only"}
