"""月度评价 API：AI生成月度评价（学情+德育+改进方案），班主任可编辑发布。"""

import calendar
import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user, require_roles
from app.core.database import get_db
from app.models.class_ import Class, ClassStudent, StudentGuardian
from app.models.monthly_report import (
    MONTHLY_STATUS_FAILED,
    MONTHLY_STATUS_GENERATED,
    MONTHLY_STATUS_GENERATING,
    MONTHLY_STATUS_PUBLISHED,
    MonthlyReport,
)
from app.models.student_case import StudentCase
from app.models.user import ROLE_ADMIN, ROLE_PARENT, ROLE_STUDENT, ROLE_TEACHER, User
from app.monthly.engine import build_monthly_snapshot
from app.schemas.monthly_report import MonthlyReportGenerateIn, MonthlyReportOut, MonthlyReportUpdateIn
from app.tasks.monthly_report_tasks import generate_monthly_report_task

router = APIRouter(prefix="/monthly-reports", tags=["monthly-reports"])
_manager = require_roles([ROLE_ADMIN, ROLE_TEACHER])
logger = logging.getLogger(__name__)

def _month_bounds(label: str) -> tuple[date, date]:
    try:
        y, m = map(int, label.split("-"))
        last = calendar.monthrange(y, m)[1]
        return date(y, m, 1), date(y, m, last)
    except Exception:
        raise HTTPException(status_code=400, detail="month_label 需为 YYYY-MM 格式")

def _enrich(row: MonthlyReport, db: Session) -> dict:
    data = MonthlyReportOut.model_validate(row).model_dump()
    stu = db.get(User, row.student_id)
    cls = db.get(Class, row.class_id)
    data["student_name"] = stu.name if stu else None
    data["class_name"] = cls.name if cls else None
    return data

def _authorize_student_class(db: Session, student_id: int, class_id: int, user: User):
    cls = db.get(Class, class_id)
    if cls is None:
        raise HTTPException(status_code=404, detail="班级不存在")
    if user.role == ROLE_TEACHER and cls.teacher_id != user.id:
        # 也允许通过 ClassTeacher 关联
        from app.models.class_ import ClassTeacher
        if not db.query(ClassTeacher).filter_by(class_id=class_id, teacher_id=user.id).first():
            raise HTTPException(status_code=403, detail="无权操作该班级月度评价")
    member = db.query(ClassStudent).filter(ClassStudent.class_id == class_id, ClassStudent.student_id == student_id).first()
    if member is None:
        raise HTTPException(status_code=403, detail="学生不属于该班级")

def _report_access(db: Session, report_id: int, user: User) -> MonthlyReport:
    r = db.get(MonthlyReport, report_id)
    if r is None:
        raise HTTPException(status_code=404, detail="月度评价不存在")
    if user.role == ROLE_ADMIN:
        return r
    if user.role == ROLE_STUDENT:
        if r.student_id != user.id or r.status != MONTHLY_STATUS_PUBLISHED:
            raise HTTPException(status_code=403, detail="无权查看该月度评价")
        return r
    if user.role == ROLE_PARENT:
        linked = db.query(StudentGuardian).filter_by(parent_id=user.id, student_id=r.student_id).first()
        if linked is None or r.status != MONTHLY_STATUS_PUBLISHED:
            raise HTTPException(status_code=403, detail="无权查看该月度评价")
        return r
    _authorize_student_class(db, r.student_id, r.class_id, user)
    return r

@router.post("/generate", response_model=MonthlyReportOut)
def generate_monthly(
    body: MonthlyReportGenerateIn,
    db: Session = Depends(get_db),
    user: User = Depends(_manager),
):
    stu = db.get(User, body.student_id)
    if stu is None or stu.role != ROLE_STUDENT:
        raise HTTPException(status_code=404, detail="学生不存在")
    _authorize_student_class(db, body.student_id, body.class_id, user)
    period_start, period_end = _month_bounds(body.month_label)

    # 校验 student_case_id 归属
    sc_id = body.student_case_id
    if sc_id is not None:
        sc = db.get(StudentCase, sc_id)
        if sc is None or sc.student_id != body.student_id or sc.class_id != body.class_id:
            raise HTTPException(status_code=400, detail="student_case_id 与学生/班级不匹配")

    # 快照
    try:
        snapshot = build_monthly_snapshot(db, body.student_id, body.class_id, body.month_label, sc_id)
    except Exception as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    # 幂等：同学生同月唯一
    report = db.query(MonthlyReport).filter(
        MonthlyReport.student_id == body.student_id,
        MonthlyReport.class_id == body.class_id,
        MonthlyReport.month_label == body.month_label,
    ).first()
    if report is None:
        report = MonthlyReport(
            student_id=body.student_id,
            class_id=body.class_id,
            student_case_id=sc_id,
            month_label=body.month_label,
            period_start=period_start,
            period_end=period_end,
            input_snapshot=snapshot,
        )
        db.add(report)
    else:
        report.student_case_id = sc_id
        report.period_start = period_start
        report.period_end = period_end
        report.input_snapshot = snapshot
        report.status = MONTHLY_STATUS_GENERATING
        report.error_message = ""
        report.ai_content = ""
        report.final_content = ""
        report.published_at = None
    db.commit()
    db.refresh(report)
    # 开发/测试环境直接同步生成，避免依赖 Celery/Redis 导致 100s 超时
    from app.core.config import settings as _settings

    use_sync = _settings.app_env == "dev" or _settings.llm_provider == "mock"
    if use_sync:
        try:
            from datetime import datetime, timezone

            from app.monthly.engine import generate_monthly_report as _gen

            result = _gen(report.input_snapshot)
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
        except Exception as inner:
            report.status = MONTHLY_STATUS_FAILED
            report.error_message = str(inner)[:1000]
            db.commit()
            raise HTTPException(status_code=500, detail=f"月度评价生成失败: {inner}") from inner
    else:
        try:
            generate_monthly_report_task.delay(report.id)
        except Exception as exc:
            logger.warning("monthly_celery_delay_failed fallback_to_sync report_id=%s err=%s", report.id, exc)
            try:
                from datetime import datetime, timezone

                from app.monthly.engine import generate_monthly_report as _gen

                result = _gen(report.input_snapshot)
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
            except Exception as inner:
                report.status = MONTHLY_STATUS_FAILED
                report.error_message = str(inner)[:1000]
                db.commit()
                raise HTTPException(status_code=500, detail=f"月度评价生成失败: {inner}") from inner
    db.refresh(report)
    return _enrich(report, db)

@router.get("", response_model=list[MonthlyReportOut])
def list_reports(
    student_id: int | None = Query(default=None),
    class_id: int | None = Query(default=None),
    month_label: str | None = Query(default=None),
    status: str | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = db.query(MonthlyReport)
    if user.role == ROLE_STUDENT:
        q = q.filter(MonthlyReport.student_id == user.id, MonthlyReport.status == MONTHLY_STATUS_PUBLISHED)
    elif user.role == ROLE_PARENT:
        student_ids = [r.student_id for r in db.query(StudentGuardian).filter_by(parent_id=user.id).all()]
        if not student_ids:
            return []
        q = q.filter(MonthlyReport.student_id.in_(student_ids), MonthlyReport.status == MONTHLY_STATUS_PUBLISHED)
    elif user.role == ROLE_TEACHER:
        # 教师仅看自己班级
        from app.models.class_ import ClassTeacher
        legacy_ids = [r.id for r in db.query(Class).filter(Class.teacher_id == user.id).all()]
        rel_ids = [r.class_id for r in db.query(ClassTeacher).filter(ClassTeacher.teacher_id == user.id).all()]
        allowed = set(legacy_ids + rel_ids)
        if not allowed:
            return []
        q = q.filter(MonthlyReport.class_id.in_(allowed))
    # 管理员不过滤
    if student_id is not None:
        q = q.filter(MonthlyReport.student_id == student_id)
    if class_id is not None:
        q = q.filter(MonthlyReport.class_id == class_id)
    if month_label:
        q = q.filter(MonthlyReport.month_label == month_label)
    if status:
        q = q.filter(MonthlyReport.status == status)
    rows = q.order_by(MonthlyReport.month_label.desc(), MonthlyReport.created_at.desc()).all()
    return [_enrich(r, db) for r in rows]

@router.get("/{report_id}", response_model=MonthlyReportOut)
def get_report(report_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    r = _report_access(db, report_id, user)
    return _enrich(r, db)

@router.put("/{report_id}", response_model=MonthlyReportOut)
def update_report(report_id: int, body: MonthlyReportUpdateIn, db: Session = Depends(get_db), user: User = Depends(_manager)):
    r = _report_access(db, report_id, user)
    if r.status not in (MONTHLY_STATUS_GENERATED, MONTHLY_STATUS_PUBLISHED):
        raise HTTPException(status_code=409, detail="月度评价尚未生成，不能编辑")
    r.final_content = body.final_content.strip()
    r.reviewed_by = user.id
    if r.status == MONTHLY_STATUS_PUBLISHED:
        from datetime import datetime, timezone
        r.published_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(r)
    logger.info("monthly_updated report_id=%s teacher_id=%s", r.id, user.id)
    return _enrich(r, db)

@router.post("/{report_id}/publish", response_model=MonthlyReportOut)
def publish_report(report_id: int, db: Session = Depends(get_db), user: User = Depends(_manager)):
    r = _report_access(db, report_id, user)
    if r.status != MONTHLY_STATUS_GENERATED:
        raise HTTPException(status_code=409, detail="只有已生成的月度评价可以发布")
    if not r.final_content.strip():
        raise HTTPException(status_code=409, detail="月度评价内容为空，不能发布")
    from datetime import datetime, timezone
    r.status = MONTHLY_STATUS_PUBLISHED
    r.reviewed_by = user.id
    r.published_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(r)
    logger.info("monthly_published report_id=%s teacher_id=%s", r.id, user.id)
    return _enrich(r, db)

@router.delete("/{report_id}")
def delete_report(report_id: int, db: Session = Depends(get_db), user: User = Depends(_manager)):
    r = _report_access(db, report_id, user)
    db.delete(r)
    db.commit()
    return {"ok": True}
