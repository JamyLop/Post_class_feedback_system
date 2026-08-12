from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.grading.base import GradeResult
from app.grading.router import router
from app.grading.schemas import GradeParams
from app.models.assignment import AssignmentQuestion
from app.models.grading import (
    CONFIDENCE_MANUAL_REVIEW,
    GRADING_STATUS_AI_COMPLETED,
    GRADING_STATUS_CONFIRMED,
    GRADING_STATUS_MANUAL_REVIEW,
    GradingResult,
)
from app.models.knowledge import KnowledgePoint
from app.models.question import Question, QuestionKnowledgePoint
from app.models.submission import (
    SUBMISSION_STATUS_AI_GRADED,
    SUBMISSION_STATUS_FAILED,
    SUBMISSION_STATUS_PROCESSING,
    Submission,
    SubmissionAnswer,
)
from app.tasks.celery_app import celery_app


def _knowledge_point_names(db: Session, question_id: int) -> list[str]:
    rows = (
        db.query(KnowledgePoint.name)
        .join(QuestionKnowledgePoint, QuestionKnowledgePoint.knowledge_point_id == KnowledgePoint.id)
        .filter(QuestionKnowledgePoint.question_id == question_id)
        .all()
    )
    return [r[0] for r in rows]


def _save_answer_result(
    db: Session,
    answer: SubmissionAnswer,
    result: GradeResult,
) -> None:
    answer.score = result.score
    answer.max_score = result.max_score
    answer.is_correct = result.is_correct

    grading = (
        db.query(GradingResult)
        .filter(GradingResult.submission_answer_id == answer.id)
        .first()
    )
    if grading is None:
        grading = GradingResult(
            submission_answer_id=answer.id,
            grading_type=result.grading_type,
            model_name=result.model_name,
            ai_score=result.score,
            ai_comment=result.comment,
            confidence=result.confidence,
            error_type=result.error_type,
            error_points=result.error_points or None,
            knowledge_points=result.knowledge_points or None,
            raw_ai_result=result.raw_ai_result,
            prompt_version=result.prompt_version,
            status=GRADING_STATUS_AI_COMPLETED,
        )
        db.add(grading)
    else:
        grading.grading_type = result.grading_type
        grading.model_name = result.model_name
        grading.ai_score = result.score
        grading.ai_comment = result.comment
        grading.confidence = result.confidence
        grading.error_type = result.error_type
        grading.error_points = result.error_points or None
        grading.knowledge_points = result.knowledge_points or None
        grading.raw_ai_result = result.raw_ai_result
        grading.prompt_version = result.prompt_version
        grading.teacher_score = None
        grading.teacher_comment = ""
        grading.status = GRADING_STATUS_AI_COMPLETED
    db.flush()


@celery_app.task(bind=True, max_retries=2, default_retry_delay=10, acks_late=True)
def grade_submission(self, submission_id: int):
    db = SessionLocal()
    sub = None
    try:
        # 行级锁 + 状态幂等：并发/重复触发时保证只批改一次
        sub = db.scalar(
            select(Submission)
            .where(Submission.id == submission_id)
            .with_for_update()
        )
        if sub is None:
            return
        if sub.status in (SUBMISSION_STATUS_PROCESSING, SUBMISSION_STATUS_AI_GRADED):
            return

        answers = (
            db.query(SubmissionAnswer)
            .join(
                AssignmentQuestion,
                AssignmentQuestion.question_id == SubmissionAnswer.question_id,
            )
            .filter(SubmissionAnswer.submission_id == submission_id)
            .order_by(AssignmentQuestion.question_order.asc())
            .all()
        )
        for answer in answers:
            question = db.get(Question, answer.question_id)
            if question is None:
                continue
            params = GradeParams(
                question_type=question.question_type,
                content=question.content,
                standard_answer=question.standard_answer,
                student_answer=answer.student_answer or answer.ocr_text or "",
                max_score=answer.max_score or question.score or 0,
                grading_rule=question.grading_rule,
                knowledge_point_names=_knowledge_point_names(db, question.id),
            )
            result = router.grade(params)
            _save_answer_result(db, answer, result)

        needs_review = False
        gradings = (
            db.query(GradingResult)
            .join(
                SubmissionAnswer,
                SubmissionAnswer.id == GradingResult.submission_answer_id,
            )
            .filter(SubmissionAnswer.submission_id == submission_id)
            .all()
        )
        for g in gradings:
            if g.status != GRADING_STATUS_CONFIRMED and g.confidence < CONFIDENCE_MANUAL_REVIEW:
                g.status = GRADING_STATUS_MANUAL_REVIEW
                needs_review = True

        sub.status = SUBMISSION_STATUS_AI_GRADED
        db.commit()
    except Exception as exc:
        db.rollback()
        # 重试次数耗尽才算失败；进入 failed 后仍可通过 API 重新触发批改。
        # 注意：self.retry(exc=exc) 耗尽时会重新抛出原始异常，因此先按次数判定。
        if self.request.retries >= self.max_retries:
            sub = db.scalar(
                select(Submission)
                .where(Submission.id == submission_id)
                .with_for_update()
            )
            if sub is not None and sub.status not in (
                SUBMISSION_STATUS_AI_GRADED,
                SUBMISSION_STATUS_PROCESSING,
            ):
                sub.status = SUBMISSION_STATUS_FAILED
                db.commit()
            raise
        raise self.retry(exc=exc)
    finally:
        db.close()