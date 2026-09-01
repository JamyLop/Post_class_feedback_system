"""月度评价异步生成任务。"""

import logging
from datetime import datetime, timezone

from sqlalchemy import select

from app.core.database import SessionLocal
from app.monthly.engine import generate_monthly_report
from app.models.monthly_report import (
    MONTHLY_STATUS_FAILED,
    MONTHLY_STATUS_GENERATED,
    MonthlyReport,
)
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=10, acks_late=True)
def generate_monthly_report_task(self, report_id: int):
    db = SessionLocal()
    try:
        report = db.scalar(select(MonthlyReport).where(MonthlyReport.id == report_id).with_for_update())
        if report is None or report.status == MONTHLY_STATUS_GENERATED:
            return
        result = generate_monthly_report(report.input_snapshot)
        report.ai_content = result.text
        report.final_content = result.text
        report.model_name = result.model
        report.prompt_tokens = result.prompt_tokens
        report.completion_tokens = result.completion_tokens
        report.total_tokens = result.total_tokens
        report.duration_ms = result.duration_ms
        report.error_message = ""
        report.status = MONTHLY_STATUS_GENERATED
        report.generated_at = datetime.now(timezone.utc)
        db.commit()
        logger.info("monthly_generated report_id=%s model=%s duration_ms=%s", report_id, result.model, result.duration_ms)
    except Exception as exc:
        db.rollback()
        logger.exception("monthly_generation_failed report_id=%s retry=%s", report_id, self.request.retries)
        if self.request.retries >= self.max_retries:
            r = db.get(MonthlyReport, report_id)
            if r is not None:
                r.status = MONTHLY_STATUS_FAILED
                r.error_message = str(exc)[:1000]
                db.commit()
            raise
        raise self.retry(exc=exc)
    finally:
        db.close()
