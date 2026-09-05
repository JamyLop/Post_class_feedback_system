"""批改与教师复核 API。

- 触发/查看/重试批改
- 教师复核队列、确认/标记异常/一键确认

权限：学生仅能操作自己的提交；教师仅能操作自己作业的提交；admin 全量。
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user, require_roles
from app.analytics.service import recompute_student_stats
from app.core.database import get_db
from app.grading.router import router as grading_router
from app.grading.schemas import GradeParams
from app.models.assignment import Assignment, AssignmentQuestion
from app.models.grading import (
    CONFIDENCE_MANUAL_REVIEW,
    GRADING_STATUS_AI_COMPLETED,
    GRADING_STATUS_CONFIRMED,
    GRADING_STATUS_MANUAL_REVIEW,
    GradingResult,
)
from app.models.knowledge import KnowledgePoint, StudentKnowledgeRecord
from app.models.question import Question, QuestionKnowledgePoint
from app.models.submission import (
    SUBMISSION_STATUS_AI_GRADED,
    SUBMISSION_STATUS_PROCESSING,
    SUBMISSION_STATUS_TEACHER_REVIEWED,
    Submission,
    SubmissionAnswer,
)
from app.models.user import ROLE_ADMIN, ROLE_STUDENT, ROLE_TEACHER, User
from app.schemas.grading import (
    ConfirmGradingParams,
    FlagGradingParams,
    ReviewSubmissionOut,
    SubmissionAnswerGradingOut,
    SubmissionGradingOut,
)
from app.tasks.grading_tasks import grade_submission

router = APIRouter(tags=["grading"])

_manager = require_roles([ROLE_ADMIN, ROLE_TEACHER])


def _get_submission(db: Session, submission_id: int) -> Submission:
    """按 id 取提交记录，不存在时抛 404。"""
    sub = db.get(Submission, submission_id)
    if sub is None:
        raise HTTPException(status_code=404, detail="提交记录不存在")
    return sub


def _can_manage(db: Session, sub: Submission, user: User) -> bool:
    """判断用户是否有权管理该提交：admin 或该提交所属作业的教师。"""
    if user.role == ROLE_ADMIN:
        return True
    if user.role != ROLE_TEACHER:
        return False
    assignment = db.get(Assignment, sub.assignment_id)
    return assignment is not None and assignment.teacher_id == user.id


def _build_grading_out(db: Session, submission_id: int) -> SubmissionGradingOut:
    """组装某提交的批改详情：按题目顺序返回逐题答案、得分与批改记录。"""
    sub = db.get(Submission, submission_id)
    # 按作业题目顺序 join，保证前端展示顺序与题目一致
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
        # 每题对应的批改结果（无则说明尚未批改）
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
    """对单题重新批改：组装参数走 GradingRouter，回写答案与批改记录。

    教师重试单题时使用；重批后按置信度重新判定是否需要人工复核。
    """
    answer = db.get(SubmissionAnswer, grading.submission_answer_id)
    if answer is None:
        raise HTTPException(status_code=404, detail="答题记录不存在")
    question = db.get(Question, answer.question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="题目不存在")
    # 题目关联的知识点名，供 LLM 批改时参考
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
    grading.reviewed_at = None
    # 单题重批后同样执行置信度规则：<0.70 强制人工复核
    if result.confidence < CONFIDENCE_MANUAL_REVIEW:
        grading.status = GRADING_STATUS_MANUAL_REVIEW
    else:
        grading.status = GRADING_STATUS_AI_COMPLETED
    return grading


@router.post("/submissions/{submission_id}/grade")
def trigger_grading(
    submission_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """触发某提交的批改：投递 Celery 任务异步执行。"""
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
    """查看某提交的批改详情。"""
    sub = _get_submission(db, submission_id)
    if user.role == ROLE_STUDENT and sub.student_id != user.id:
        raise HTTPException(status_code=403, detail="无权查看该提交")
    if user.role in (ROLE_TEACHER, ROLE_ADMIN) and not _can_manage(db, sub, user):
        raise HTTPException(status_code=403, detail="无权查看该提交")
    return _build_grading_out(db, submission_id)


@router.post("/gradings/{grading_id}/retry", response_model=SubmissionGradingOut)
def retry_grading(
    grading_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(_manager),
):
    """教师手动重试单题批改（批改失败或结果异常时使用）。"""
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


# ---------------------------------------------------------------------------
# 阶段 4：教师复核
# ---------------------------------------------------------------------------

def _get_grading(db: Session, grading_id: int) -> GradingResult:
    """按 id 取批改记录，不存在时抛 404。"""
    grading = db.get(GradingResult, grading_id)
    if grading is None:
        raise HTTPException(status_code=404, detail="批改记录不存在")
    return grading


def _get_grading_submission(db: Session, grading: GradingResult) -> Submission:
    """从批改记录反查其所属提交。"""
    answer = db.get(SubmissionAnswer, grading.submission_answer_id)
    if answer is None:
        raise HTTPException(status_code=404, detail="答题记录不存在")
    sub = db.get(Submission, answer.submission_id)
    if sub is None:
        raise HTTPException(status_code=404, detail="提交记录不存在")
    return sub


def _require_manage_grading(db: Session, grading: GradingResult, user: User) -> Submission:
    """校验用户可管理该批改所在提交，通过则返回该提交。"""
    sub = _get_grading_submission(db, grading)
    if not _can_manage(db, sub, user):
        raise HTTPException(status_code=403, detail="无权操作该提交")
    return sub


def _write_knowledge_records(
    db: Session,
    sub: Submission,
    question: Question,
    answer: SubmissionAnswer,
    grading: GradingResult,
) -> list[int]:
    """确认后写入原始学习轨迹。按 (学生, 作业, 题目) 先清后写，保证幂等。

    返回受影响的知识点 id，供掌握度增量重算。
    """
    db.query(StudentKnowledgeRecord).filter(
        StudentKnowledgeRecord.student_id == sub.student_id,
        StudentKnowledgeRecord.assignment_id == sub.assignment_id,
        StudentKnowledgeRecord.question_id == question.id,
    ).delete(synchronize_session=False)
    qkp_rows = (
        db.query(QuestionKnowledgePoint)
        .filter(QuestionKnowledgePoint.question_id == question.id)
        .all()
    )
    for qkp in qkp_rows:
        db.add(
            StudentKnowledgeRecord(
                student_id=sub.student_id,
                knowledge_point_id=qkp.knowledge_point_id,
                question_id=question.id,
                assignment_id=sub.assignment_id,
                is_correct=answer.is_correct,
                score=answer.score,
                max_score=answer.max_score,
                difficulty=question.difficulty,
                error_type=grading.error_type,
                answered_at=sub.submitted_at,
            )
        )
    return [qkp.knowledge_point_id for qkp in qkp_rows]


def _confirm_one(
    db: Session,
    grading: GradingResult,
    teacher_score: float | None = None,
    teacher_comment: str = "",
) -> None:
    """确认单题批改：以教师分数为准（缺省沿用 AI 分数），同步 answer 并写知识点记录。"""
    answer = db.get(SubmissionAnswer, grading.submission_answer_id)
    if answer is None:
        raise HTTPException(status_code=404, detail="答题记录不存在")
    question = db.get(Question, answer.question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="题目不存在")
    max_score = answer.max_score or question.score or 0
    final_score = teacher_score
    if final_score is None:
        final_score = grading.teacher_score
    if final_score is None:
        final_score = grading.ai_score
    if final_score is None:
        final_score = 0.0
    final_score = round(float(final_score), 1)
    if final_score < 0 or final_score > max_score + 1e-6:
        raise HTTPException(status_code=400, detail=f"分数需在 0 ~ {max_score} 之间")

    grading.teacher_score = final_score
    grading.teacher_comment = teacher_comment or grading.teacher_comment
    grading.status = GRADING_STATUS_CONFIRMED
    grading.reviewed_at = datetime.now(timezone.utc)
    answer.score = final_score
    answer.is_correct = max_score > 0 and final_score >= max_score
    db.flush()

    sub = db.get(Submission, answer.submission_id)
    if sub is not None:
        kp_ids = _write_knowledge_records(db, sub, question, answer, grading)
        db.flush()
        # 阶段 5：确认后增量更新该学生的知识点掌握度聚合
        recompute_student_stats(db, sub.student_id, kp_ids)


def _finalize_submission(db: Session, sub: Submission) -> None:
    """该提交全部批改确认后，submission 进入 teacher_reviewed。"""
    gradings = (
        db.query(GradingResult)
        .join(SubmissionAnswer, SubmissionAnswer.id == GradingResult.submission_answer_id)
        .filter(SubmissionAnswer.submission_id == sub.id)
        .all()
    )
    if gradings and all(g.status == GRADING_STATUS_CONFIRMED for g in gradings):
        sub.status = SUBMISSION_STATUS_TEACHER_REVIEWED


@router.get("/reviews", response_model=list[ReviewSubmissionOut])
def list_review_queue(
    review_status: str = "pending",
    assignment_id: int | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(_manager),
):
    """教师复核队列。review_status=pending（有待确认）| confirmed（已全部确认）。"""
    if review_status not in ("pending", "confirmed"):
        raise HTTPException(status_code=400, detail="review_status 仅支持 pending/confirmed")
    q = (
        db.query(Submission, Assignment, User)
        .join(Assignment, Assignment.id == Submission.assignment_id)
        .join(User, User.id == Submission.student_id)
    )
    if user.role == ROLE_TEACHER:
        q = q.filter(Assignment.teacher_id == user.id)
    if assignment_id is not None:
        q = q.filter(Submission.assignment_id == assignment_id)
    rows = q.order_by(Submission.submitted_at.desc()).all()

    out: list[ReviewSubmissionOut] = []
    for sub, assignment, student in rows:
        gradings = (
            db.query(GradingResult)
            .join(SubmissionAnswer, SubmissionAnswer.id == GradingResult.submission_answer_id)
            .filter(SubmissionAnswer.submission_id == sub.id)
            .all()
        )
        if not gradings:
            continue
        total = len(gradings)
        confirmed = sum(1 for g in gradings if g.status == GRADING_STATUS_CONFIRMED)
        state = "confirmed" if confirmed == total else "pending"
        if state != review_status:
            continue
        answers = (
            db.query(SubmissionAnswer)
            .filter(SubmissionAnswer.submission_id == sub.id)
            .all()
        )
        max_total = round(sum(a.max_score or 0 for a in answers), 1)
        total_score = round(sum(a.score or 0 for a in answers), 1)
        out.append(
            ReviewSubmissionOut(
                submission_id=sub.id,
                assignment_id=assignment.id,
                assignment_title=assignment.title,
                student_id=student.id,
                student_name=student.name,
                content_type=sub.content_type,
                status=sub.status,
                total_score=total_score,
                max_total=max_total,
                answer_count=total,
                confirmed_count=confirmed,
                review_state=state,
                submitted_at=sub.submitted_at,
            )
        )
    return out


@router.put("/gradings/{grading_id}/confirm", response_model=SubmissionGradingOut)
def confirm_grading(
    grading_id: int,
    body: ConfirmGradingParams,
    db: Session = Depends(get_db),
    user: User = Depends(_manager),
):
    grading = _get_grading(db, grading_id)
    sub = _require_manage_grading(db, grading, user)
    _confirm_one(db, grading, body.teacher_score, body.teacher_comment)
    _finalize_submission(db, sub)
    db.commit()
    return _build_grading_out(db, sub.id)


@router.post("/gradings/{grading_id}/flag", response_model=SubmissionGradingOut)
def flag_grading(
    grading_id: int,
    body: FlagGradingParams,
    db: Session = Depends(get_db),
    user: User = Depends(_manager),
):
    """标记异常：记录原因并保留为待复核（不确认）。"""
    if not body.teacher_comment.strip():
        raise HTTPException(status_code=400, detail="标记异常需填写原因")
    grading = _get_grading(db, grading_id)
    sub = _require_manage_grading(db, grading, user)
    grading.teacher_comment = "【标记异常】" + body.teacher_comment.strip()
    if grading.status != GRADING_STATUS_CONFIRMED:
        grading.status = GRADING_STATUS_MANUAL_REVIEW
    db.commit()
    return _build_grading_out(db, sub.id)


@router.post("/submissions/{submission_id}/confirm-all", response_model=SubmissionGradingOut)
def confirm_all_grading(
    submission_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(_manager),
):
    """作业级一键确认：未确认的题沿用 AI 分数确认，然后整份进入 teacher_reviewed。"""
    sub = _get_submission(db, submission_id)
    if not _can_manage(db, sub, user):
        raise HTTPException(status_code=403, detail="无权操作该提交")
    gradings = (
        db.query(GradingResult)
        .join(SubmissionAnswer, SubmissionAnswer.id == GradingResult.submission_answer_id)
        .filter(SubmissionAnswer.submission_id == submission_id)
        .all()
    )
    for g in gradings:
        if g.status != GRADING_STATUS_CONFIRMED:
            _confirm_one(db, g)
    _finalize_submission(db, sub)
    db.commit()
    return _build_grading_out(db, submission_id)