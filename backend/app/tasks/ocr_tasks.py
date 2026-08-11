from app.core.database import SessionLocal
from app.models.submission import (
    SUBMISSION_STATUS_FAILED,
    SUBMISSION_STATUS_SUBMITTED,
    Submission,
)
from app.ocr.provider import get_ocr_provider
from app.storage import download_bytes
from app.tasks.celery_app import celery_app


@celery_app.task(bind=True, max_retries=2, default_retry_delay=5)
def ocr_submission(self, submission_id: int):
    db = SessionLocal()
    sub = None
    try:
        sub = db.get(Submission, submission_id)
        if sub is None:
            return
        if sub.content_type in ("image", "pdf"):
            data = download_bytes(sub.content_url)
            result = get_ocr_provider().extract(data, sub.content_type)
            # 阶段 2 仅完成 OCR 文本提取，答案切分与批改在阶段 3 接入。
            for answer in sub.answers:
                answer.ocr_text = result.raw_text
        sub.status = SUBMISSION_STATUS_SUBMITTED
        db.commit()
    except Exception as exc:
        if sub is not None:
            sub.status = SUBMISSION_STATUS_FAILED
            db.commit()
        raise self.retry(exc=exc)
    finally:
        db.close()
