from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.submission import (
    SUBMISSION_STATUS_FAILED,
    SUBMISSION_STATUS_SUBMITTED,
    Submission,
)
from app.ocr.provider import get_ocr_provider
from app.storage import download_bytes
from app.tasks.celery_app import celery_app
from app.tasks.grading_tasks import grade_submission


@celery_app.task(bind=True, max_retries=2, default_retry_delay=5, acks_late=True)
def ocr_submission(self, submission_id: int):
    db = SessionLocal()
    sub = None
    try:
        sub = db.scalar(
            select(Submission)
            .where(Submission.id == submission_id)
            .with_for_update()
        )
        if sub is None:
            return
        if sub.content_type in ("image", "pdf"):
            data = download_bytes(sub.content_url)
            result = get_ocr_provider().extract(data, sub.content_type)
            # 阶段 2 仅完成 OCR 文本提取；真实第三方 OCR 接入后在此做答案切分，
            # 按题目顺序将 raw_text 切分写入各 submission_answers.ocr_text。
            for answer in sub.answers:
                answer.ocr_text = result.raw_text
        sub.status = SUBMISSION_STATUS_SUBMITTED
        db.commit()
        # OCR 完成后触发异步批改
        grade_submission.delay(submission_id)
    except Exception as exc:
        db.rollback()
        if self.request.retries >= self.max_retries:
            sub = db.scalar(
                select(Submission)
                .where(Submission.id == submission_id)
                .with_for_update()
            )
            if sub is not None:
                sub.status = SUBMISSION_STATUS_FAILED
                db.commit()
            raise
        raise self.retry(exc=exc)
    finally:
        db.close()
