from datetime import date, datetime, timedelta, timezone
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user, require_roles
from app.core.database import get_db
from app.feedback.engine import build_assignment_snapshot, build_weekly_snapshot
from app.models.assignment import Assignment
from app.models.class_ import Class, ClassStudent
from app.models.feedback import (
    FEEDBACK_STATUS_FAILED,
    FEEDBACK_STATUS_GENERATED,
    FEEDBACK_STATUS_GENERATING,
    FEEDBACK_STATUS_PUBLISHED,
    FEEDBACK_TYPE_ASSIGNMENT,
    FEEDBACK_TYPE_WEEKLY,
    FeedbackReport,
)
from app.models.user import ROLE_ADMIN, ROLE_STUDENT, ROLE_TEACHER, User
from app.schemas.feedback import FeedbackGenerateIn, FeedbackOut, FeedbackUpdateIn
from app.tasks.feedback_tasks import generate_feedback_report

router = APIRouter(tags=["feedback"])
_manager = require_roles([ROLE_ADMIN, ROLE_TEACHER])
logger = logging.getLogger(__name__)


def _student(db: Session, student_id: int) -> User:
    student = db.get(User, student_id)
    if student is None or student.role != ROLE_STUDENT:
        raise HTTPException(status_code=404, detail="学生不存在")
    return student


def _authorize_class_student(
    db: Session, student_id: int, class_id: int, user: User
) -> Class:
    cls = db.get(Class, class_id)
    if cls is None:
        raise HTTPException(status_code=404, detail="班级不存在")
    if user.role == ROLE_TEACHER and cls.teacher_id != user.id:
        raise HTTPException(status_code=403, detail="无权操作该班级反馈")
    member = db.query(ClassStudent).filter(
        ClassStudent.class_id == class_id,
        ClassStudent.student_id == student_id,
    ).first()
    if member is None:
        raise HTTPException(status_code=403, detail="学生不属于该班级")
    return cls


def _report_access(db: Session, report_id: int, user: User) -> FeedbackReport:
    report = db.get(FeedbackReport, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="反馈不存在")
    if user.role == ROLE_ADMIN:
        return report
    if user.role == ROLE_STUDENT:
        if report.student_id != user.id or report.status != FEEDBACK_STATUS_PUBLISHED:
            raise HTTPException(status_code=403, detail="无权查看该反馈")
        return report
    _authorize_class_student(db, report.student_id, report.class_id, user)
    return report


@router.post("/students/{student_id}/feedback/generate", response_model=FeedbackOut)
def generate_student_feedback(
    student_id: int,
    body: FeedbackGenerateIn,
    db: Session = Depends(get_db),
    user: User = Depends(_manager),
):
    _student(db, student_id)
    _authorize_class_student(db, student_id, body.class_id, user)
    assignment_id = body.assignment_id
    period_start = body.period_start
    period_end = body.period_end
    try:
        if body.report_type == FEEDBACK_TYPE_ASSIGNMENT:
            if assignment_id is None:
                raise HTTPException(status_code=400, detail="单次作业反馈必须指定 assignment_id")
            snapshot = build_assignment_snapshot(db, student_id, body.class_id, assignment_id)
        else:
            today = date.today()
            period_start = period_start or (today - timedelta(days=today.weekday()))
            period_end = period_end or (period_start + timedelta(days=6))
            if period_end < period_start:
                raise HTTPException(status_code=400, detail="period_end 不能早于 period_start")
            snapshot = build_weekly_snapshot(
                db, student_id, body.class_id, period_start, period_end
            )
            if snapshot["assignment_count"] == 0:
                raise HTTPException(status_code=409, detail="该周期没有已确认作业，无法生成周报")
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    query = db.query(FeedbackReport).filter(
        FeedbackReport.student_id == student_id,
        FeedbackReport.class_id == body.class_id,
        FeedbackReport.report_type == body.report_type,
    )
    if body.report_type == FEEDBACK_TYPE_ASSIGNMENT:
        query = query.filter(FeedbackReport.assignment_id == assignment_id)
    else:
        query = query.filter(
            FeedbackReport.period_start == period_start,
            FeedbackReport.period_end == period_end,
        )
    report = query.first()
    if report is None:
        report = FeedbackReport(
            student_id=student_id,
            class_id=body.class_id,
            assignment_id=assignment_id,
            report_type=body.report_type,
            period_start=period_start,
            period_end=period_end,
            input_snapshot=snapshot,
        )
        db.add(report)
    else:
        report.input_snapshot = snapshot
        report.status = FEEDBACK_STATUS_GENERATING
        report.error_message = ""
        report.ai_content = ""
        report.final_content = ""
        report.published_at = None
    db.commit()
    db.refresh(report)
    try:
        generate_feedback_report.delay(report.id)
    except Exception as exc:
        report.status = FEEDBACK_STATUS_FAILED
        report.error_message = str(exc)[:1000]
        db.commit()
        raise HTTPException(status_code=503, detail="反馈任务启动失败，请稍后重试") from exc
    db.refresh(report)
    return report


@router.get("/students/{student_id}/feedback", response_model=list[FeedbackOut])
def list_student_feedback(
    student_id: int,
    class_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _student(db, student_id)
    query = db.query(FeedbackReport).filter(FeedbackReport.student_id == student_id)
    if user.role == ROLE_STUDENT:
        if user.id != student_id:
            raise HTTPException(status_code=403, detail="无权查看该学生反馈")
        query = query.filter(FeedbackReport.status == FEEDBACK_STATUS_PUBLISHED)
    elif user.role == ROLE_TEACHER:
        if class_id is None:
            raise HTTPException(status_code=400, detail="教师查看反馈时必须指定班级")
        _authorize_class_student(db, student_id, class_id, user)
        query = query.filter(FeedbackReport.class_id == class_id)
    elif class_id is not None:
        query = query.filter(FeedbackReport.class_id == class_id)
    return query.order_by(FeedbackReport.created_at.desc()).all()


@router.get("/students/{student_id}/feedback-report", response_model=list[FeedbackOut])
def student_feedback_report(
    student_id: int,
    period: str = Query(default="week"),
    class_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if period != "week":
        raise HTTPException(status_code=400, detail="第一版仅支持 period=week")
    rows = list_student_feedback(student_id, class_id, db, user)
    return [row for row in rows if row.report_type == FEEDBACK_TYPE_WEEKLY]


@router.put("/feedback/{report_id}", response_model=FeedbackOut)
def update_feedback(
    report_id: int,
    body: FeedbackUpdateIn,
    db: Session = Depends(get_db),
    user: User = Depends(_manager),
):
    report = _report_access(db, report_id, user)
    if report.status not in (FEEDBACK_STATUS_GENERATED, FEEDBACK_STATUS_PUBLISHED):
        raise HTTPException(status_code=409, detail="反馈尚未生成，不能编辑")
    report.final_content = body.final_content.strip()
    report.reviewed_by = user.id
    if report.status == FEEDBACK_STATUS_PUBLISHED:
        report.published_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(report)
    logger.info(
        "feedback_teacher_updated report_id=%s teacher_id=%s content_changed=%s",
        report.id,
        user.id,
        report.final_content != report.ai_content,
    )
    return report


@router.post("/feedback/{report_id}/publish", response_model=FeedbackOut)
def publish_feedback(
    report_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(_manager),
):
    report = _report_access(db, report_id, user)
    if report.status != FEEDBACK_STATUS_GENERATED:
        raise HTTPException(status_code=409, detail="只有已生成的反馈可以发布")
    if not report.final_content.strip():
        raise HTTPException(status_code=409, detail="反馈内容为空，不能发布")
    report.status = FEEDBACK_STATUS_PUBLISHED
    report.reviewed_by = user.id
    report.published_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(report)
    logger.info(
        "feedback_published report_id=%s teacher_id=%s student_id=%s",
        report.id,
        user.id,
        report.student_id,
    )
    return report
