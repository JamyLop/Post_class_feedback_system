from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user, require_roles
from app.core.database import get_db
from app.grading.router import router as grading_router
from app.grading.schemas import GradeParams
from app.models.assignment import Assignment, AssignmentQuestion
from app.models.grading import (
    GRADING_STATUS_AI_COMPLETED,
    GradingResult,
)
from app.models.knowledge import KnowledgePoint
from app.models.question import Question, QuestionKnowledgePoint
from app.models.submission import (
    SUBMISSION_STATUS_AI_GRADED,
    SUBMISSION_STATUS_PROCESSING,
    Submission,
    SubmissionAnswer,
)
from app.models.user import ROLE_ADMIN, ROLE_STUDENT, ROLE_TEACHER, User
from app.schemas.grading import SubmissionAnswerGradingOut, SubmissionGradingOut
from app.tasks.grading_tasks import grade_submission

router = APIRouter(tags=["grading"])

_manager = require_roles([ROLE_ADMIN, ROLE_TEACHER])


def _get_submission(db: Session, submission_id: int) -> Submission:
    sub = db.get(Submission, submission_id)
    if sub is None:
        raise HTTPException(status_code=404, detail="提交记录不存在")
    return sub


def _can_manage(db: Session, sub: Submission, user: User) -> bool:
    if user.role == ROLE_ADMIN:
        return True
    if user.role != ROLE_TEACHER:
        return False
    assignment = db.get(Assignment, sub.assignment_id)
    return assignment is not None and assignment.teacher_id == user.id


def _build_grading_out(db: Session, submission_id: int) -> SubmissionGradingOut:
    sub = db.get(Submission, submission_id)
    answer_rows = (
        db.query(SubmissionAnswer, AssignmentQuestion)
        .join(
            AssignmentQuestion,
            AssignmentQuestion.question_id == SubmissionAnswer.question_id,
        )
        .filter(SubmissionAnswer.submission_id == submission_id)
        .order_by(AssignmentQuestion.question_order.asc())
        .all()
    )
    max_total = 0.0
    total_score = 0.0
    answers_out: list[SubmissionAnswerGradingOut] = []
    for answer, aq in answer_rows:
        question = db.get(Question, aq.question_id)
        if question is None:
            continue
        grading = (
            db.query(GradingResult)
            .filter(GradingResult.submission_answer_id == answer.id)
            .first()
        )
        if answer.max_score:
            max_total += answer.max_score
        if answer.score is not None:
            total_score += answer.score
        answers_out.append(
            SubmissionAnswerGradingOut(
                answer_id=answer.id,
                question_order=aq.question_order,
                question_type=question.question_type,
                content=question.content,
                standard_answer=question.standard_answer,
                student_answer=answer.student_answer,
                ocr_text=answer.ocr_text,
                score=answer.score,
                max_score=answer.max_score,
                is_correct=answer.is_correct,
                grading=grading,
            )
        )
    return SubmissionGradingOut(
        submission_id=submission_id,
        status=sub.status,
        total_score=round(total_score, 1),
        max_total=max_total,
        answers=answers_out,
    )


def _grade_one(db: Session, grading: GradingResult) -> GradingResult:
    answer = db.get(SubmissionAnswer, grading.submission_answer_id)
    if answer is None:
        raise HTTPException(status_code=404, detail="答题记录不存在")
    question = db.get(Question, answer.question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="题目不存在")
    kp_names = [
        r[0]
        for r in (
            db.query(KnowledgePoint.name)
            .join(
                QuestionKnowledgePoint,
                QuestionKnowledgePoint.knowledge_point_id == KnowledgePoint.id,
            )
            .filter(QuestionKnowledgePoint.question_id == question.id)
            .all()
        )
    ]
    params = GradeParams(
        question_type=question.question_type,
        content=question.content,
        standard_answer=question.standard_answer,
        student_answer=answer.student_answer or answer.ocr_text or "",
        max_score=answer.max_score or question.score or 0,
        grading_rule=question.grading_rule,
        knowledge_point_names=kp_names,
    )
    result = grading_router.grade(params)
    answer.score = result.score
    answer.max_score = result.max_score
    answer.is_correct = result.is_correct
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
    return grading


@router.post("/submissions/{submission_id}/grade")
def trigger_grading(
    submission_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    sub = _get_submission(db, submission_id)
    if user.role == ROLE_STUDENT and sub.student_id != user.id:
        raise HTTPException(status_code=403, detail="无权操作该提交")
    if not _can_manage(db, sub, user):
        raise HTTPException(status_code=403, detail="无权操作该提交")
    if sub.status in (SUBMISSION_STATUS_PROCESSING, SUBMISSION_STATUS_AI_GRADED):
        raise HTTPException(status_code=409, detail="批改已完成或正在进行")
    grade_submission.delay(submission_id)
    return {"submission_id": submission_id, "status": "queued"}


@router.get(
    "/submissions/{submission_id}/grading", response_model=SubmissionGradingOut
)
def get_grading_result(
    submission_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    sub = _get_submission(db, submission_id)
    if user.role == ROLE_STUDENT and sub.student_id != user.id:
        raise HTTPException(status_code=403, detail="无权查看该提交")
    return _build_grading_out(db, submission_id)


@router.post("/gradings/{grading_id}/retry", response_model=SubmissionGradingOut)
def retry_grading(
    grading_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(_manager),
):
    grading = db.get(GradingResult, grading_id)
    if grading is None:
        raise HTTPException(status_code=404, detail="批改记录不存在")
    answer = db.get(SubmissionAnswer, grading.submission_answer_id)
    if answer is None:
        raise HTTPException(status_code=404, detail="答题记录不存在")
    sub = db.get(Submission, answer.submission_id)
    if sub is None or not _can_manage(db, sub, user):
        raise HTTPException(status_code=403, detail="无权操作该提交")
    _grade_one(db, grading)
    db.commit()
    return _build_grading_out(db, sub.id)