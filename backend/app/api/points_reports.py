"""积分周报/月报 API：从每日打卡累加积分，一学生一周期一条。"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user, require_roles
from app.core.database import get_db
from app.models.case_points import StudentPointsReport
from app.models.class_ import Class, ClassStudent, ClassTeacher, StudentGuardian
from app.models.user import ROLE_ADMIN, ROLE_PARENT, ROLE_STUDENT, ROLE_TEACHER, User
from app.schemas.case_points import PointsReportBuildIn, PointsReportOut
from app.services.case_points_service import (
    build_points_reports,
    current_month_label,
    current_week_label,
    enrich_points_report,
)

router = APIRouter(prefix="/points-reports", tags=["points-reports"])
_manager = require_roles([ROLE_ADMIN, ROLE_TEACHER])


def _teacher_class_ids(db: Session, user: User) -> set[int]:
    legacy = [r.id for r in db.query(Class).filter(Class.teacher_id == user.id).all()]
    rel = [r.class_id for r in db.query(ClassTeacher).filter(ClassTeacher.teacher_id == user.id).all()]
    return set(legacy + rel)


def _scope_filter(query, db: Session, user: User):
    if user.role == ROLE_ADMIN:
        return query
    if user.role == ROLE_TEACHER:
        allowed = _teacher_class_ids(db, user)
        if not allowed:
            return query.filter(StudentPointsReport.id == -1)
        return query.filter(StudentPointsReport.class_id.in_(allowed))
    if user.role == ROLE_STUDENT:
        return query.filter(StudentPointsReport.student_id == user.id)
    if user.role == ROLE_PARENT:
        student_ids = [r.student_id for r in db.query(StudentGuardian).filter_by(parent_id=user.id).all()]
        if not student_ids:
            return query.filter(StudentPointsReport.id == -1)
        return query.filter(StudentPointsReport.student_id.in_(student_ids))
    return query.filter(StudentPointsReport.id == -1)


@router.get("", response_model=list[PointsReportOut])
def list_reports(
    class_id: int | None = Query(default=None),
    period_type: str | None = Query(default=None),
    period_label: str | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = db.query(StudentPointsReport)
    q = _scope_filter(q, db, user)
    if class_id is not None:
        q = q.filter(StudentPointsReport.class_id == class_id)
    if period_type:
        if period_type not in {"weekly", "monthly"}:
            raise HTTPException(status_code=400, detail="period_type 仅支持 weekly/monthly")
        q = q.filter(StudentPointsReport.period_type == period_type)
    if period_label:
        q = q.filter(StudentPointsReport.period_label == period_label)
    rows = q.order_by(StudentPointsReport.period_label.desc(), StudentPointsReport.earned_points.desc()).all()
    return [enrich_points_report(db, r) for r in rows]


@router.post("/build", response_model=list[PointsReportOut])
def build_reports(
    body: PointsReportBuildIn,
    db: Session = Depends(get_db),
    user: User = Depends(_manager),
):
    """班主任一键生成本班某周/某月积分报表（幂等：重复生成会覆盖更新）。"""
    if user.role == ROLE_TEACHER and body.class_id not in _teacher_class_ids(db, user):
        raise HTTPException(status_code=403, detail="无权生成该班级积分报表")
    if db.get(Class, body.class_id) is None:
        raise HTTPException(status_code=404, detail="班级不存在")
    label = body.period_label
    if not label:
        label = current_week_label() if body.period_type == "weekly" else current_month_label()
    try:
        rows = build_points_reports(db, body.class_id, body.period_type, label, recorded_by=user.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    from app.services.student_case_service import audit

    for row in rows:
        audit(db, user.id, "points_report.build", "student_points_report", row.id, row.student_case_id,
              {"period_type": body.period_type, "period_label": label})
    db.commit()
    for row in rows:
        db.refresh(row)
    return [enrich_points_report(db, r) for r in rows]
