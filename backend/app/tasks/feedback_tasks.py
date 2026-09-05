"""反馈生成异步任务：基于快照调用 LLM 生成报告文本。"""

import logging
from datetime import datetime, timezone

from sqlalchemy import select

from app.core.database import SessionLocal
from app.feedback.engine import generate_feedback
from app.models.feedback import (
    FEEDBACK_STATUS_FAILED,
    FEEDBACK_STATUS_GENERATED,
    FeedbackReport,
)
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=10, acks_late=True)
def generate_feedback_report(self, report_id: int):
    db = SessionLocal()
    try:
        report = db.scalar(
            select(FeedbackReport).where(FeedbackReport.id == report_id).with_for_update()
        )
        # 已生成的报告直接跳过，避免重复生成
        if report is None or report.status == FEEDBACK_STATUS_GENERATED:
            return
        result = generate_feedback(report.input_snapshot)
        report.ai_content = result.text
        report.final_content = result.text
        report.model_name = result.model
        report.prompt_tokens = result.prompt_tokens
        report.completion_tokens = result.completion_tokens
        report.total_tokens = result.total_tokens
        report.duration_ms = result.duration_ms
        report.error_message = ""
        report.status = FEEDBACK_STATUS_GENERATED
        report.generated_at = datetime.now(timezone.utc)
        db.commit()
        logger.info(
            "feedback_generated report_id=%s model=%s duration_ms=%s total_tokens=%s",
            report_id,
            result.model,
            result.duration_ms,
            result.total_tokens,
        )
    except Exception as exc:
        db.rollback()
        logger.exception(
            "feedback_generation_failed report_id=%s retry=%s",
            report_id,
            self.request.retries,
        )
        if self.request.retries >= self.max_retries:
            report = db.get(FeedbackReport, report_id)
            if report is not None:
                report.status = FEEDBACK_STATUS_FAILED
                report.error_message = str(exc)[:1000]
                db.commit()
            raise
        raise self.retry(exc=exc)
    finally:
        db.close()
